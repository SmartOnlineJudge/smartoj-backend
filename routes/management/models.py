from datetime import datetime

from utils.models import SmartOJSQLModel


class UserDynamic(SmartOJSQLModel):
    name: str


class User(SmartOJSQLModel):
    id: int
    user_dynamic: UserDynamic


class Language(SmartOJSQLModel):
    id: int
    name: str


class Tag(SmartOJSQLModel):
    name: str


class QuestionTag(SmartOJSQLModel):
    id: int
    tag: Tag


class Test(SmartOJSQLModel):
    id: int
    input_output: str


class MemoryTimeLimit(SmartOJSQLModel):
    id: int
    memory_limit: float
    time_limit: int
    language: Language


class SolvingFramework(SmartOJSQLModel):
    id: int
    code_framework: str
    language: Language


class JudgeTemplate(SmartOJSQLModel):
    id: int
    code: str
    language: Language


class Question(SmartOJSQLModel):
    id: int
    title: str
    description: str
    difficulty: str
    created_at: datetime
    submission_quantity: int
    pass_quantity: int
    is_deleted: bool
    publisher: User
    tags: list[QuestionTag]
    tests: list[Test]
    memory_time_limits: list[MemoryTimeLimit]
    solving_frameworks: list[SolvingFramework]
    judge_templates: list[JudgeTemplate]
