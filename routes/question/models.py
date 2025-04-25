from enum import Enum
from typing import List

from pydantic import BaseModel


class LimitData(BaseModel):
    time_limit: int
    memory_limit: float
    language_id: int


class FrameworkData(BaseModel):
    code_framework: str
    language_id: int


class JudgeTemplate(BaseModel):
    code: str
    language_id: int


class Difficulty(str, Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


class Question(BaseModel):
    title: str
    description: str
    difficulty: Difficulty
    tags_ids: list[int]
    input_outputs: list[str]
    limit_datas: List[LimitData]
    framework_datas: List[FrameworkData]
    judge_templates: List[JudgeTemplate]
