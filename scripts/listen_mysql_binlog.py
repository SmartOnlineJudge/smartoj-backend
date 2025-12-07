"""
运行方式：python3 -m scripts.listen_mysql_binlog
"""
import logging
import json
import asyncio
import traceback
from datetime import datetime

from taskiq import AsyncTaskiqDecoratedTask
from pymysqlreplication import BinLogStreamReader
from pymysqlreplication.row_event import (
    DeleteRowsEvent,
    UpdateRowsEvent,
    WriteRowsEvent
)

import settings
from storage.cache import get_default_redis
from mq.broker import broker, update_question_tag_task, update_question_task, create_reply_message_task


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

table2task: dict[str, AsyncTaskiqDecoratedTask] = {
    "question": update_question_task,
    "question_tag": update_question_tag_task,
    "tag": update_question_tag_task,
    "comment": create_reply_message_task,
}


def load_binlog_position(event_loop: asyncio.AbstractEventLoop) -> tuple[str | None, int | None]:
    conn = get_default_redis()
    result = event_loop.run_until_complete(conn.get("binlog_position"))
    if result is None:
        return None, None
    binlog_position = json.loads(result)
    return binlog_position["log_file"], binlog_position["log_pos"]


def save_binlog_position(event_loop: asyncio.AbstractEventLoop, log_file: str, log_pos: int):
    conn = get_default_redis()
    binlog_position = {"log_file": log_file, "log_pos": log_pos}
    event_loop.run_until_complete(conn.set("binlog_position", json.dumps(binlog_position)))


def pop_datetime_value(values: dict):
    filtered_values = {}
    for k, v in values.items():
        if isinstance(v, datetime):
            continue
        filtered_values[k] = v
    return filtered_values


def listen_binlog(server_id: int = 1):
    """
    监听 MySQL binlog 变化
    """
    connection_settings = {
        'host': settings.MYSQL_CONF["HOST"], 
        'port': settings.MYSQL_CONF["PORT"], 
        'user': settings.MYSQL_CONF["USER"], 
        'passwd': settings.MYSQL_CONF["PASSWORD"]
    }

    event_loop = asyncio.get_event_loop()

    # 加载 binlog 位置
    log_file, log_pos = load_binlog_position(event_loop)
    logger.info(f"加载 binlog：{log_file} {log_pos}")

    logger.info(f"连接到 MySQL 服务器……")
    stream = BinLogStreamReader(
        connection_settings=connection_settings, 
        server_id=server_id,
        only_events=[WriteRowsEvent, UpdateRowsEvent, DeleteRowsEvent],
        only_schemas=["smartoj"],
        only_tables=list(table2task.keys()),
        blocking=True,
        resume_stream=True,
        log_pos=log_pos,
        log_file=log_file
    )

    logger.info("启动消息队列……")
    event_loop.run_until_complete(broker.startup())

    logger.info("开始监听 binlog……")
    try:
        for binlog_event in stream:
            flag = True
            for row in binlog_event.rows:
                table = binlog_event.table
                event = {"table": table}
                
                if isinstance(binlog_event, DeleteRowsEvent):
                    event["action"] = "delete"
                    event["values"] = pop_datetime_value(row["values"])
                elif isinstance(binlog_event, UpdateRowsEvent):
                    event["action"] = "update"
                    event["before_values"] = pop_datetime_value(row["before_values"])
                    event["after_values"] = pop_datetime_value(row["after_values"])
                elif isinstance(binlog_event, WriteRowsEvent):
                    event["action"] = "insert"
                    event["values"] = pop_datetime_value(row["values"])

                logger.info(str(event))

                try:
                    task = table2task[table]
                    event_loop.run_until_complete(task.kiq(event))
                except Exception as e:
                    logger.info(f"消息发送失败：{e}")
                    flag = False
                    break

            if not flag:
                break
            # 如果循环正常结束，则保存 log_file 和 log_pos
            save_binlog_position(event_loop, stream.log_file, stream.log_pos)
    except KeyboardInterrupt:
        pass
    except Exception as _:
        logger.info(f"监听 binlog 异常，退出进程")
        traceback.print_exc()
    finally:
        event_loop.run_until_complete(broker.shutdown())
        event_loop.close()
        stream.close()
    logger.info("结束监听……")


if __name__ == "__main__":
    listen_binlog()
