from sqlmodel.ext.asyncio.session import AsyncSession

from .base import MySQLService, create_async_engine
from .executors import MySQLExecutors
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


executors = MySQLExecutors()
engine = create_async_engine(
    pool_recycle=60, 
    isolation_level="READ COMMITTED"  # 修改 MySQL 的事务隔离级别为“读已提交”
)


async def get_async_session():
    async with AsyncSession(engine) as session:
        yield session


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
    async with AsyncSession(engine) as session:
        service = UserService(session)
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
