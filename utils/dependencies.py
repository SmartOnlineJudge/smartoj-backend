"""
收集项目所有依赖项
"""
from typing import Annotated

from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import Depends

from core.user.session import get_current_user, get_current_admin
from utils.service_registry import (
    get_tag_service,
    get_question_service,
    get_user_service,
    get_language_service,
    get_test_service,
    get_user_dynamic_service,
    get_question_tag_service,
    get_solving_framework_service,
    get_judge_template_service,
    get_memory_time_limit_service,
    get_judge_record_service,
    get_submit_record_service,
    get_comment_service,
    get_solution_service,
    get_message_service,
    get_user_profiles_service
)
from storage.mysql import (
    get_async_session,
    UserService,
    QuestionService,
    TagService,
    QuestionTagService,
    JudgeTemplateService,
    LanguageService,
    TestService,
    SolvingFrameworkService,
    MemoryTimeLimitService,
    UserDynamicService,
    SubmitRecordService,
    JudgeRecordService,
    CommentService,
    SolutionService,
    MessageService,
    UserProfilesService
)
from storage.cache import get_session_redis, get_default_redis, Redis
from storage.oss import get_minio_client, Minio


# 用户相关依赖项
CurrentUserDependency = Annotated[dict, Depends(get_current_user)]  # noqa
CurrentAdminDependency = Annotated[dict, Depends(get_current_admin)]

# 缓存相关依赖项
DefaultRedisDependency = Annotated[Redis, Depends(get_default_redis)]
SessionRedisDependency = Annotated[Redis, Depends(get_session_redis)]

# OSS相关依赖项
MinioClientDependency = Annotated[Minio, Depends(get_minio_client)]

# 数据库相关依赖项
AsyncSessionDependency = Annotated[AsyncSession, Depends(get_async_session)]
UserServiceDependency = Annotated[UserService, Depends(get_user_service)]
UserDynamicServiceDependency = Annotated[UserDynamicService, Depends(get_user_dynamic_service)]
QuestionServiceDependency = Annotated[QuestionService, Depends(get_question_service)]  # noqa
TagServiceDependency = Annotated[TagService, Depends(get_tag_service)]
QuestionTagServiceDependency = Annotated[QuestionTagService, Depends(get_question_tag_service)]
JudgeTemplateServiceDependency = Annotated[JudgeTemplateService, Depends(get_judge_template_service)]
LanguageServiceDependency = Annotated[LanguageService, Depends(get_language_service)]
TestServiceDependency = Annotated[TestService, Depends(get_test_service)]
SolvingFrameworkServiceDependency = Annotated[SolvingFrameworkService, Depends(get_solving_framework_service)]
MemoryTimeLimitDependency = Annotated[MemoryTimeLimitService, Depends(get_memory_time_limit_service)]
SubmitRecordDependency = Annotated[SubmitRecordService, Depends(get_submit_record_service)]
JudgeRecordDependency = Annotated[JudgeRecordService, Depends(get_judge_record_service)]
CommentServiceDependency = Annotated[CommentService, Depends(get_comment_service)]
SolutionServiceDependency = Annotated[SolutionService, Depends(get_solution_service)]
MessageServiceDependency = Annotated[MessageService, Depends(get_message_service)]
UserProfilesServiceDependency = Annotated[UserProfilesService, Depends(get_user_profiles_service)]
