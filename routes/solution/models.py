from datetime import datetime

from pydantic import Field

from utils.models import SmartOJSQLModel
from ..comment.models import User


class CreateSolution(SmartOJSQLModel):
    content: str
    title: str = Field(max_length=50)
    question_id: int = Field(ge=1)


class UpdateSolution(CreateSolution):
    solution_id: int = Field(ge=1)
    question_id: None = None


class SolutionOut(SmartOJSQLModel):
    id: int
    title: str
    content: str
    created_at: datetime
    view_count: int
    comment_count: int
    user: User


class Question(SmartOJSQLModel):
    id: int
    title: str


class UserSolutionOut(SmartOJSQLModel):
    id: int
    title: str
    created_at: datetime
    view_count: int
    comment_count: int
    question: Question
