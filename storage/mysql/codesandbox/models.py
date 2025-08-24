from datetime import datetime

from sqlmodel import Field
from sqlalchemy import Column, TIMESTAMP, func

from utils.models import SmartOJSQLModel


class SubmitRecord(SmartOJSQLModel, table=True):
    __tablename__ = "submit_record"

    id: int | None = Field(None, primary_key=True)
    created_at: datetime = Field(
        None,
        sa_column=Column(
            "created_at", TIMESTAMP(), server_default=func.now(), nullable=False
        )
    )
    total_test_quantity: int = Field(0, nullable=False)
    pass_test_quantity: int = Field(0, nullable=False)
    max_time_consumed: int = Field(0, nullable=False)
    max_memory_consumed: float = Field(0, nullable=False, decimal_places=2, max_digits=8)
    status: int = Field(0, nullable=False)
    code: str = Field(nullable=False)
    type: str = Field(nullable=False)
    language_id: int = Field(nullable=False, index=True, foreign_key="language.id")
    user_id: int = Field(nullable=False, index=True, foreign_key="user.id")
    question_id: int = Field(nullable=False, index=True, foreign_key="question.id")


class JudgeRecord(SmartOJSQLModel, table=True):
    __tablename__ = "judge_record"

    id: int | None = Field(None, primary_key=True)
    result: str = Field(nullable=False)
    answer: str = Field(nullable=False)
    criterion: str = Field(nullable=False)
    is_success: bool = Field(nullable=False)
    time_consumed: int = Field(nullable=False)
    memory_consumed: float = Field(nullable=False, decimal_places=2, max_digits=8)
    status: int = Field(nullable=False)
    submit_record_id: int = Field(nullable=False, index=True, foreign_key="submit_record.id")
    test_id: int = Field(nullable=False, index=True, foreign_key="test.id")
