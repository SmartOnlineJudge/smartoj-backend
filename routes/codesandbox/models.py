from enum import Enum

from sqlmodel import Field

from utils.models import SmartOJSQLModel 


class JudgeTypeEnum(str, Enum):
    test = "test"
    submit = "submit"


class JudgeModel(SmartOJSQLModel):
    question_id: int = Field(ge=1)
    language_id: int = Field(ge=1)
    code: str
    judge_type: JudgeTypeEnum
