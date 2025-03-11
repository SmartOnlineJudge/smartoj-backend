from typing import Any

from fastapi.responses import JSONResponse


class ResponseCodes:
    # 通用响应码
    OK = (200, "OK")
    FILE_TOO_LARGE = (210, "文件过大，上传失败")
    FILE_TYPE_NOT_ALLOWED = (220, "文件类型不允许")
    FILE_UPLOAD_ERROR = (230, "文件上传异常")
    EMAIL_NOT_ALLOW_NULL = (235, "邮箱不能为空")
    REQUEST_FREQUENTLY = (240, "请求过于频繁，请稍后再试")
    # 后台管理响应码
    LOGIN_SUCCESS = (300, "登录成功")
    LOGIN_FAILED = (305, "登录失败")
    PERMISSION_DENIED = (310, "当前账号权限不足")


class SmartOJResponse(JSONResponse):
    def __init__(
        self, message_tuple: tuple[int, str], data: Any = None, *args, **kwargs
    ):
        content = {"code": message_tuple[0], "message": message_tuple[1], "data": data}
        super().__init__(content=content, *args, **kwargs)
