from enum import Enum
from datetime import datetime
from typing import Optional

from pydantic import EmailStr, Field

from utils.models import SmartOJSQLModel


class AuthType(Enum):
    GITHUB = "github"
    QQ = "qq"
    EMAIL = "email"
    PASSWORD = "password"


class LoginModel(SmartOJSQLModel):
    email: Optional[EmailStr] = ""
    password: Optional[str] = ""
    code: Optional[str] = ""  # 第三方平台认证完毕后传递给前端的参数
    verification_code: Optional[str] = ""
    auth_type: AuthType


class UserModel(SmartOJSQLModel):
    id: int
    user_id: str
    name: str
    email: str
    github_token: str
    qq_token: str
    is_superuser: bool
    profile: str
    avatar: str
    created_at: datetime
    is_deleted: bool
    grade: int
    experience: int


class RegisterModel(SmartOJSQLModel):
    name: str
    password1: str
    password2: str
    email: EmailStr
    verification_code: str = Field("", pattern=r"^[0-9]{6}$", examples=["123456"])
