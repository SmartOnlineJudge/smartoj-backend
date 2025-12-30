"""
运行方式：python3 -m scripts.listen_mysql_binlog
"""
import logging
import json
import asyncio
import traceback
import threading
from datetime import datetime

from taskiq import AsyncTaskiqDecoratedTask
from pymysqlreplication import BinLogStreamReader
from pymysqlreplication.row_event import (
    DeleteRowsEvent,
    UpdateRowsEvent,
    WriteRowsEvent
)

import settings
from storage.cache import get_default_redis, close_cache_connections
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


async def load_binlog_position() -> tuple[str | None, int | None]:
    conn = get_default_redis()
    result = await conn.get("binlog_position")
    if result is None:
        return None, None
    binlog_position = json.loads(result)
    return binlog_position["log_file"], binlog_position["log_pos"]


async def save_binlog_position(log_file: str, log_pos: int):
    conn = get_default_redis()
    binlog_position = {"log_file": log_file, "log_pos": log_pos}
    await conn.set("binlog_position", json.dumps(binlog_position))


def pop_datetime_value(values: dict):
    filtered_values = {}
    for k, v in values.items():
        if isinstance(v, datetime):
            continue
        filtered_values[k] = v
    return filtered_values


def producer(
    log_file: str, 
    log_pos: int,
    loop: asyncio.AbstractEventLoop, 
    queue: asyncio.Queue,
    server_id: int = 101,
):
    connection_settings = {
        'host': settings.MYSQL_CONF["HOST"], 
        'port': settings.MYSQL_CONF["PORT"], 
        'user': settings.MYSQL_CONF["USER"], 
        'passwd': settings.MYSQL_CONF["PASSWORD"]
    }
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
        log_file=log_file,
        slave_heartbeat=30
    )
    try:
        for event in stream:
            log_file, log_pos = stream.log_file, stream.log_pos
            fut = asyncio.run_coroutine_threadsafe(queue.put((event, log_file, log_pos)), loop)
            fut.result()
    except Exception as _:
        logger.info("监听binlog异常：")
        traceback.print_exc()
    finally:
        stream.close()


async def consumer(queue: asyncio.Queue):
    while True:
        binlog_event, log_file, log_pos = await queue.get()
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
                await task.kiq(event)
            except Exception as e:
                logger.info(f"消息发送失败：{e}")
                flag = False
                break

        if not flag:
            break
        # 如果循环正常结束，则保存 log_file 和 log_pos
        await save_binlog_position(log_file, log_pos)
        logger.info(f"已保存binlog位置：{log_file} {log_pos}")


async def main(server_id: int = 101, queue_size: int = 100):
    # 加载 binlog 位置
    log_file, log_pos = await load_binlog_position()
    # 启动消息队列
    logger.info("启动消息队列……")
    await broker.startup()
    queue: asyncio.Queue[tuple[WriteRowsEvent | DeleteRowsEvent | UpdateRowsEvent, str, int]]
    queue = asyncio.Queue(maxsize=queue_size)
    # 创建子线程充当生产者
    logger.info("正在创建子线程……")
    loop = asyncio.get_running_loop()
    producer_threading = threading.Thread(target=producer, args=(log_file, log_pos, loop, queue, server_id), daemon=True)
    producer_threading.start()
    # 创建消费者
    logger.info("开始监听 binlog……")
    try:
        await consumer(queue)
    except asyncio.CancelledError:
        logger.info(f"监听 binlog 已取消，正在清理资源，请稍后……")
    finally:
        await close_cache_connections()
        await broker.shutdown()
        producer_threading.join(5)
    logger.info("结束进程……")


if __name__ == "__main__":
    asyncio.run(main())
