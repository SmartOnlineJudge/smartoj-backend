from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from storage.mysql import (
    MySQLService,
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
    SolutionService
)


def service_factory(service_class: type[MySQLService]):
    def create_service(session: AsyncSession = Depends(get_async_session)) -> MySQLService:
        return service_class(session)
    return create_service


get_user_service = service_factory(UserService)
get_user_dynamic_service = service_factory(UserDynamicService)
get_question_service = service_factory(QuestionService)
get_tag_service = service_factory(TagService)
get_question_tag_service = service_factory(QuestionTagService)
get_judge_template_service = service_factory(JudgeTemplateService)
get_language_service = service_factory(LanguageService)
get_test_service = service_factory(TestService)
get_solving_framework_service = service_factory(SolvingFrameworkService)
get_memory_time_limit_service = service_factory(MemoryTimeLimitService)
get_submit_record_service = service_factory(SubmitRecordService)
get_judge_record_service = service_factory(JudgeRecordService)
get_comment_service = service_factory(CommentService)
get_solution_service = service_factory(SolutionService)
