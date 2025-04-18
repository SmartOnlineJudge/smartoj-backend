from enum import Enum
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr

from utils.models import DatetimeModel


class AuthType(Enum):
    GITHUB = "github"
    QQ = "qq"
    EMAIL = "email"
    PASSWORD = "password"


class LoginModel(BaseModel):
    email: Optional[EmailStr] = ""
    password: Optional[str] = ""
    code: Optional[str] = ""  # 第三方平台认证完毕后传递给前端的参数
    verification_code: Optional[str] = ""
    auth_type: AuthType


class UserOutModel(DatetimeModel):
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


class UserListModel(UserOutModel):
    id: int
