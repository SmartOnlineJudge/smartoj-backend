from enum import Enum
from typing import List

from utils.models import SmartOJSQLModel


class LimitDataCreate(SmartOJSQLModel):
    time_limit: int
    memory_limit: float
    language_id: int


class FrameworkDataCreate(SmartOJSQLModel):
    code_framework: str
    language_id: int


class JudgeTemplateCreate(SmartOJSQLModel):
    code: str
    language_id: int


class Difficulty(str, Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


class QuestionCreate(SmartOJSQLModel):
    title: str
    description: str
    difficulty: Difficulty
    tags_ids: list[int]
    input_outputs: list[str]
    limit_datas: List[LimitDataCreate]
    framework_datas: List[FrameworkDataCreate]
    judge_templates: List[JudgeTemplateCreate]


class QuestionUpdate(SmartOJSQLModel):
    id: int
    title: str
    description: str
    difficulty: Difficulty


class JudgeTemplateUpdate(SmartOJSQLModel):
    id: int
    code: str


class LimitDataUpdate(SmartOJSQLModel):
    id: int
    time_limit: int
    memory_limit: float


class FrameworkDataUpdate(SmartOJSQLModel):
    id: int
    code_framework: str


class TestUpdate(SmartOJSQLModel):
    id: int
    input_output: str
