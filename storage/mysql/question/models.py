from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import Column, TIMESTAMP, func
from sqlmodel import Field, Relationship

from utils.models import SmartOJSQLModel
from ..user.models import User


class Question(SmartOJSQLModel, table=True):
    __tablename__ = "question"

    id: int | None = Field(None, primary_key=True)
    title: str = Field(max_length=30, nullable=False)
    description: str = Field(max_length=255, nullable=False)
    difficulty: str = Field("easy", max_length=6, nullable=False)
    score: int = Field(0, nullable=False)
    created_at: datetime = Field(
        None,
        sa_column=Column(
            "created_at", TIMESTAMP(), server_default=func.now(), nullable=False
        )
    )
    submission_quantity: int = Field(0, nullable=False)
    pass_quantity: int = Field(0, nullable=False)
    is_deleted: bool = Field(False, nullable=False)
    publisher_id: int = Field(nullable=False, foreign_key="user.id")
    publisher: User = Relationship()
    tags: list["QuestionTag"] = Relationship(back_populates="question")
    tests: list["Test"] = Relationship(back_populates="question")
    judge_templates: list["JudgeTemplate"] = Relationship(back_populates="question")
    memory_time_limits: list["MemoryTimeLimit"] = Relationship(back_populates="question")
    solving_frameworks: list["SolvingFramework"] = Relationship(back_populates="question")


class Tag(SmartOJSQLModel, table=True):
    __tablename__ = "tag"

    id: int | None = Field(None, primary_key=True)
    name: str = Field(max_length=10, nullable=False, index=True)
    score: int = Field(0, nullable=False)
    is_deleted: bool = Field(False, nullable=False)
    created_at: datetime = Field(
        None,
        sa_column=Column(
            "created_at", TIMESTAMP(), server_default=func.now(), nullable=False
        )
    )


class QuestionTag(SmartOJSQLModel, table=True):
    __tablename__ = "question_tag"

    id: int | None = Field(None, primary_key=True)
    question_id: int = Field(nullable=False, index=True, foreign_key="question.id")
    tag_id: int = Field(nullable=False, index=True, foreign_key="tag.id")
    tag: Tag = Relationship()
    question: Question = Relationship(back_populates="tags")


class Language(SmartOJSQLModel, table=True):
    __tablename__ = "language"

    id: int | None = Field(None, primary_key=True)
    name: str = Field(max_length=10, nullable=False)
    version: str = Field(max_length=10, nullable=False)
    is_deleted: bool = Field(False, nullable=False)


class SolvingFramework(SmartOJSQLModel, table=True):
    __tablename__ = "solving_framework"

    id: int | None = Field(None, primary_key=True)
    code_framework: str = Field(max_length=255, nullable=False)
    question_id: int = Field(nullable=False, index=True, foreign_key="question.id")
    language_id: int = Field(nullable=False, index=True, foreign_key="language.id")
    language: Language = Relationship()
    question: Question = Relationship(back_populates="solving_frameworks")


class Test(SmartOJSQLModel, table=True):
    __tablename__ = "test"

    id: int | None = Field(None, primary_key=True)
    input_output: str = Field(max_length=255, nullable=False)
    question_id: int = Field(nullable=False, index=True, foreign_key="question.id")
    question: Question = Relationship(back_populates="tests")


class JudgeTemplate(SmartOJSQLModel, table=True):
    __tablename__ = "judge_template"

    id: int | None = Field(None, primary_key=True)
    code: str = Field(max_length=255, nullable=False)
    question_id: int = Field(nullable=False, index=True, foreign_key="question.id")
    language_id: int = Field(nullable=False, index=True, foreign_key="language.id")
    language: Language = Relationship()
    question: Question = Relationship(back_populates="judge_templates")


class MemoryTimeLimit(SmartOJSQLModel, table=True):
    __tablename__ = "memory_time_limit"

    id: int | None = Field(None, primary_key=True)
    memory_limit: Decimal = Field(nullable=False, decimal_places=2, max_digits=8)
    time_limit: int = Field(nullable=False)
    question_id: int = Field(nullable=False, index=True, foreign_key="question.id")
    language_id: int = Field(nullable=False, index=True, foreign_key="language.id")
    language: Language = Relationship()
    question: Question = Relationship(back_populates="memory_time_limits")


class DailyQuestion(SmartOJSQLModel, table=True):
    __tablename__ = "daily_question"

    id: int | None = Field(None, primary_key=True)
    created_at: datetime = Field(
        None,
        sa_column=Column(
            "created_at", TIMESTAMP(), server_default=func.now(), nullable=False
        )
    )
    is_deleted: bool = Field(False, nullable=False)
    release_time: date = Field(nullable=False, index=True)
    publisher_id: int = Field(nullable=False, foreign_key="user.id")
    question_id: int = Field(nullable=False, foreign_key="question.id")
    publisher: User = Relationship()
    question: Question = Relationship()
