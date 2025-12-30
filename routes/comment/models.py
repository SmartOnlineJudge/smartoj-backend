from enum import Enum
from datetime import datetime

from pydantic import Field

from utils.models import SmartOJSQLModel


class CommentType(str, Enum):
    question = "question"
    solution = "solution"


class CreateComment(SmartOJSQLModel):
    content: str = Field(max_length=255)
    type: CommentType
    target_id: int = Field(ge=1)
    to_comment_id: int | None = Field(None, ge=1)
    root_comment_id: int | None = Field(None, ge=1)


class UserDynamic(SmartOJSQLModel):
    avatar: str
    name: str


class User(SmartOJSQLModel):
    user_dynamic: UserDynamic


class CommentOut(SmartOJSQLModel):
    id: int
    content: str
    created_at: datetime
    reply_count: int
    to_comment_id: int | None = None
    user: User


class UserCommentOut(SmartOJSQLModel):
    id: int
    content: str
    type: CommentType
    created_at: datetime
    reply_count: int
