from .base import MySQLService
from .db_engine import engine
from .session import get_async_session
from .user.services import UserService, UserDynamicService
from .question.services import (
    QuestionService,
    TagService,
    QuestionTagService,
    LanguageService,
    TestService,
    JudgeTemplateService,
    MemoryTimeLimitService,
    SolvingFrameworkService
)
from .codesandbox.services import SubmitRecordService, JudgeRecordService
from .interaction.services import CommentService, SolutionService


async def create_user_and_dynamic(
    name: str,
    password: str = None,
    email: str = "",
    github_token: str = "",
    qq_token: str = "",
    is_superuser: bool = False,
    profile: str = "",
    avatar: str = "",
) -> tuple[int, int]:
    async with UserService() as service:
        user_row_id, dynamic_id = await service.create_user_and_dynamic(
            name,
            password,
            email,
            github_token,
            qq_token,
            is_superuser,
            profile,
            avatar
        )
    return user_row_id, dynamic_id
