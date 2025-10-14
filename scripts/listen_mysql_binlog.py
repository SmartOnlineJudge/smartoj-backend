"""
运行方式：python3 -m scripts.listen_mysql_binlog
"""
import json
import asyncio
from datetime import datetime

import httpx
from pymysqlreplication import BinLogStreamReader
from pymysqlreplication.row_event import (
    DeleteRowsEvent,
    UpdateRowsEvent,
    WriteRowsEvent
)

import settings
from storage.cache import get_default_redis


BACKEND_TRIGGER_URL = "http://127.0.0.1:8000/question/binlog-trigger"


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

    stream = BinLogStreamReader(
        connection_settings=connection_settings, 
        server_id=server_id,
        only_events=[WriteRowsEvent, UpdateRowsEvent, DeleteRowsEvent],
        only_schemas=["smartoj"],
        only_tables=["question", "question_tag", "tag"],
        blocking=True,
        resume_stream=True,
        log_pos=log_pos,
        log_file=log_file
    )

    print("开始监听 binlog……", end="\n\n")

    try:
        for binlog_event in stream:
            flag = True
            for row in binlog_event.rows:
                event = {"table": binlog_event.table}
                
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

                print(event)
                try:
                    response = httpx.post(BACKEND_TRIGGER_URL, json=event)
                except Exception as e:
                    print("请求失败：", e)
                    flag = False
                    break
                print(response.text, end="\n\n")
            if not flag:
                break
            # 如果循环正常结束，则保存 log_file 和 log_pos
            save_binlog_position(event_loop, stream.log_file, stream.log_pos)
    except KeyboardInterrupt:
        event_loop.close()
        stream.close()
    finally:
        event_loop.close()
        stream.close()
    print("结束监听……")


if __name__ == "__main__":
    listen_binlog()
