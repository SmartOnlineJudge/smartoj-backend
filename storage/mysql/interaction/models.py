from datetime import datetime

from sqlmodel import Field, Relationship, TIMESTAMP, Column
from sqlalchemy import func

from utils.models import SmartOJSQLModel
from ..user.models import User
from ..question.models import Question


class Solution(SmartOJSQLModel, table=True):
    __tablename__ = "solution"

    id: int | None = Field(None, primary_key=True)
    title: str = Field(max_length=50, nullable=False)
    content: str = Field(max_length=255, nullable=False)
    created_at: datetime = Field(
        None,
        sa_column=Column(
            "created_at", 
            TIMESTAMP(), 
            server_default=func.now(), 
            nullable=False
        )
    )
    updated_at: datetime = Field(
        None,
        sa_column=Column(
            "updated_at", 
            TIMESTAMP(), 
            server_default=func.now(), 
            server_onupdate=func.now(), 
            nullable=False
        )
    )
    is_deleted: bool = Field(False, nullable=False)
    question_id: int = Field(nullable=False, foreign_key="question.id")
    user_id: int = Field(nullable=False, foreign_key="user.id")
    view_count: int = Field(0, nullable=False)
    comment_count: int = Field(0, nullable=False)
    user: User = Relationship()
    question: Question = Relationship()


class Comment(SmartOJSQLModel, table=True):
    __tablename__ = "comment"

    id: int | None = Field(None, primary_key=True)
    content: str = Field(max_length=255, nullable=False)
    type: str = Field(max_length=10, nullable=False)
    created_at: datetime = Field(
        None,
        sa_column=Column(
            "created_at", 
            TIMESTAMP(), 
            server_default=func.now(), 
            nullable=False
        )
    )
    is_deleted: bool = Field(False, nullable=False)
    target_id: int = Field(nullable=False)
    root_comment_id: int = Field(None, nullable=True)
    to_comment_id: int = Field(None, nullable=True)
    reply_count: int = Field(0, nullable=False)
    user_id: int = Field(nullable=False, foreign_key="user.id")
    user: User = Relationship()


class Message(SmartOJSQLModel, table=True):
    __tablename__ = "message"

    id: int | None = Field(None, primary_key=True)
    title: str = Field(max_length=50, nullable=False)
    content: str = Field(max_length=255, nullable=False)
    created_at: datetime = Field(
        None,
        sa_column=Column(
            "created_at", 
            TIMESTAMP(), 
            server_default=func.now(), 
        )
    )
    type: str = Field(max_length=10, nullable=False)
    is_deleted: bool = Field(False, nullable=False)
    is_read: bool = Field(False, nullable=False)
    recipient_id: int = Field(nullable=False, foreign_key="user.id")
    sender_id: int = Field(None, nullable=True)
