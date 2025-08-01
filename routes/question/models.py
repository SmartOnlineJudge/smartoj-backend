from enum import Enum
from decimal import Decimal

from sqlmodel import Field

from utils.models import SmartOJSQLModel


class LimitDataBase(SmartOJSQLModel):
    time_limit: int = Field(ge=1000)
    memory_limit: Decimal = Field(decimal_places=2, max_digits=8, ge=1)


class LimitDataCreate(LimitDataBase):
    language_id: int = Field(ge=1)


class FrameworkDataCreate(SmartOJSQLModel):
    code_framework: str
    language_id: int = Field(ge=1)


class Difficulty(str, Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


class QuestionCreate(SmartOJSQLModel):
    title: str
    description: str
    difficulty: Difficulty


class QuestionUpdate(SmartOJSQLModel):
    id: int
    title: str
    description: str
    difficulty: Difficulty
    is_deleted: bool = False


class JudgeTemplateCreate(SmartOJSQLModel):
    code: str
    language_id: int = Field(ge=1)
    question_id: int = Field(ge=1)


class JudgeTemplateUpdate(SmartOJSQLModel):
    id: int = Field(ge=1)
    code: str


class LimitDataUpdate(LimitDataBase):
    id: int = Field(ge=1)


class FrameworkDataUpdate(SmartOJSQLModel):
    id: int = Field(ge=1)
    code_framework: str


class TestUpdate(SmartOJSQLModel):
    id: int = Field(ge=1)
    input_output: str


class QuestionAddLimitData(LimitDataCreate):
    question_id: int = Field(ge=1)


class QuestionAddFrameworkData(FrameworkDataCreate):
    question_id: int = Field(ge=1)


class QuestionAddTestData(SmartOJSQLModel):
    question_id: int = Field(ge=1)
    input_output: str


class QuestionAddTag(SmartOJSQLModel):
    question_id: int = Field(ge=1)
    tag_id: int = Field(ge=1)


class QuestionUpdateTag(QuestionAddTag):
    new_tag_id: int
