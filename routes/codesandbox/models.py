from enum import Enum

from sqlmodel import Field

from utils.models import SmartOJSQLModel
from ..question.models import TestUpdate


class JudgeTypeEnum(str, Enum):
    test = "test"
    submit = "submit"


class JudgeModel(SmartOJSQLModel):
    question_id: int = Field(ge=1)
    language_id: int = Field(ge=1)
    code: str
    judge_type: JudgeTypeEnum


class JudgeRecordModel(SmartOJSQLModel):
    result: str
    answer: str
    is_success: bool
    memory_consumed: float
    submit_record_id: int = Field(ge=1)
    criterion: str
    id: int = Field(ge=1)
    time_consumed: int = Field(ge=1)
    status: int = Field(ge=1)
    test_id: int = Field(ge=1)


class JudgeRecordWithTestModel(JudgeRecordModel):
    test: TestUpdate
