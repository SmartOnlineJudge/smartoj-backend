from enum import Enum
from typing import List

from pydantic import BaseModel


class LimitDataCreate(BaseModel):
    time_limit: int
    memory_limit: float
    language_id: int


class FrameworkDataCreate(BaseModel):
    code_framework: str
    language_id: int


class JudgeTemplateCreate(BaseModel):
    code: str
    language_id: int


class Difficulty(str, Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


class QuestionCreate(BaseModel):
    title: str
    description: str
    difficulty: Difficulty
    tags_ids: list[int]
    input_outputs: list[str]
    limit_datas: List[LimitDataCreate]
    framework_datas: List[FrameworkDataCreate]
    judge_templates: List[JudgeTemplateCreate]


class QuestionUpdate(BaseModel):
    id: int
    title: str
    description: str
    difficulty: Difficulty


class JudgeTemplateUpdate(BaseModel):
    id: int
    code: str


class LimitDataUpdate(BaseModel):
    id: int
    time_limit: int
    memory_limit: float


class FrameworkDataUpdate(BaseModel):
    id: int
    code_framework: str


class TestUpdate(BaseModel):
    id: int
    input_output: str
