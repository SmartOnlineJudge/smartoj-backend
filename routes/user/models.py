from enum import Enum
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator

from utils.models import DatetimeModel


class AuthType(Enum):
    GITHUB = "github"
    QQ = "qq"
    EMAIL = "email"
    PASSWORD = "password"


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

    @field_validator("email", mode="before")  # noqa
    @classmethod
    def mask_email(cls, v: str) -> str:
        """
        邮箱脱敏：
        1111111@qq.com -> 111******@qq.com
        1@qq.com -> 1******@qq.com
        """

        local_part, domain = v.split("@", maxsplit=1)
        mask = "*" * 6
        return local_part[:3] + mask + "@" + domain
