from datetime import datetime

from sqlalchemy import Column, TIMESTAMP, func
from sqlmodel import Field, Relationship

import settings
from utils.models import SmartOJSQLModel


class User(SmartOJSQLModel, table=True):
    __tablename__ = "user"

    id: int | None = Field(None, primary_key=True)
    user_id: str = Field(max_length=13, nullable=False, unique=True)
    password: str | None = Field("", max_length=255)
    email: str = Field(max_length=60, nullable=False, unique=True)
    github_token: str = Field("", max_length=255, index=True)
    qq_token: str = Field("", max_length=255, index=True)
    created_at: datetime = Field(
        None,
        sa_column=Column(
            "created_at", TIMESTAMP(), server_default=func.now(), nullable=False
        )
    )
    is_deleted: bool = Field(False, nullable=False)
    is_superuser: bool = Field(False, nullable=False)
    user_dynamic: "UserDynamic" = Relationship(back_populates="user")


class UserDynamic(SmartOJSQLModel, table=True):
    __tablename__ = "user_dynamic"

    id: int | None = Field(None, primary_key=True)
    name: str = Field(max_length=20, nullable=False)
    avatar: str = Field(settings.DEFAULT_USER_AVATAR, max_length=70, nullable=False)
    profile: str = Field("")
    grade: int = Field(1, nullable=False)
    experience: int = Field(0, nullable=False)
    user_id: int = Field(nullable=False, unique=True, foreign_key="user.id")
    user: User = Relationship(back_populates="user_dynamic")
