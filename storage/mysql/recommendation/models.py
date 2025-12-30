from datetime import datetime

from sqlalchemy import Column, TIMESTAMP, func
from sqlmodel import Field, Relationship

from utils.models import SmartOJSQLModel
from ..user.models import User


class UserProfiles(SmartOJSQLModel, table=True):
    __tablename__ = "user_profiles"

    id: int | None = Field(None, primary_key=True)
    user_id: int = Field(nullable=False, index=True, foreign_key="user.id")
    last_active_at: datetime = Field(
        None,
        sa_column=Column(
            "last_active_at", TIMESTAMP(), server_default=func.now(), nullable=False
        )
    )
    total_score: int = Field(0, nullable=False)
    strong_tags: str = Field(default=[])  # JSON 类型，保存的时候是字符串
    weak_tags: str = Field(default=[])  # JSON 类型，保存的时候是字符串
    strong_difficulty: str = Field(default="easy")
    global_ac_rate: float = Field(0, nullable=False)
    avg_try_count: float = Field(0, nullable=False)
    user: User = Relationship()
