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


class VerificationCodeType(Enum):
    register = "register"
    login = "login"
    change_password = "change_password"
    change_email = "change_email"


class LoginModel(BaseModel):
    email: Optional[EmailStr] = ""
    password: Optional[str] = ""
    github_token: Optional[str] = ""
    qq_token: Optional[str] = ""
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
