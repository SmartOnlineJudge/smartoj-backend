from typing import Any

from fastapi.responses import JSONResponse


class ResponseCodes:
    OK = (200, "OK")
    LOGIN_SUCCESS = (300, "登录成功")
    LOGIN_FAILED = (305, "登录失败")
    PERMISSION_DENIED = (310, "当前账号权限不足")


class SmartOJResponse(JSONResponse):
    def __init__(
        self, message_tuple: tuple[int, str], data: Any = None, *args, **kwargs
    ):
        content = {"code": message_tuple[0], "message": message_tuple[1], "data": data}
        super().__init__(content=content, *args, **kwargs)
