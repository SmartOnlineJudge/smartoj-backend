from typing import Any

from pydantic import BaseModel


class ResponseCodes:
    # 通用响应码
    OK = (200, "OK")
    FILE_TOO_LARGE = (210, "文件过大，上传失败")
    FILE_TYPE_NOT_ALLOWED = (220, "文件类型不允许")
    FILE_UPLOAD_ERROR = (230, "文件上传异常")
    EMAIL_NOT_ALLOW_NULL = (235, "邮箱不能为空")
    REQUEST_FREQUENTLY = (240, "请求过于频繁，请稍后再试")
    CAPTCHA_INVALID = (250, "验证码错误或已过期")
    NOT_FOUND = (255, "请求的资源不存在")
    PARAMS_ERROR = (260, "请求参数错误")
    # 后台管理响应码
    LOGIN_SUCCESS = (300, "登录成功")
    LOGIN_FAILED = (305, "登录失败")
    PERMISSION_DENIED = (310, "当前账号权限不足")
    # 用户响应码
    TWICE_PASSWORD_NOT_MATCH = (400, "两次密码输入不一致")
    EMAIL_ALREADY_EXISTS = (410, "当前邮箱已被注册")
    # 题目响应码
    JUDGE_TEMPLATE_ALREADY_EXISTS = (500, "每个题目的每个编程语言只能有一个判题模板")
    TIME_MEMORY_LIMIT_ALREADY_EXISTS = (505, "每个题目的每个编程语言只能有一个内存时间限制")
    SOLVING_FRAMEWORK_ALREADY_EXISTS = (510, "每个题目的每个编程语言只能有一个解题框架")
    QUESTION_TAG_ALREADY_EXISTS = (515, "当前标签已存在")
    # 评论响应代码
    COMMENT_DELETE_FAILED = (600, "评论删除失败")


class SmartOJResponse(BaseModel):
    code: int
    message: str
    data: Any

    def __init__(self, message_tuple: tuple[int, str], *, data: Any = None):
        response_data = {
            "code": message_tuple[0],
            "message": message_tuple[1],
            "data": data,
        }
        super().__init__(**response_data)
