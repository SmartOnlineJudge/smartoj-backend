import asyncio

from taskiq_redis import RedisAsyncResultBackend
from taskiq_aio_pika import AioPikaBroker

import settings
from core.mail import send_email
from core.codesandbox.caller import codesandbox_caller
from storage.mysql import (
    JudgeRecordService,
    SubmitRecordService,
    JudgeTemplateService,
    LanguageService,
    MemoryTimeLimitService,
    TestService,
    QuestionService
)


_mq_conf = settings.REDIS_CONF["mq"]
if _mq_conf["PASSWORD"] is not None:
    _redis_url = f"redis://:{_mq_conf['PASSWORD']}@{_mq_conf['HOST']}:{_mq_conf['PORT']}/{_mq_conf['DB']}"
else:
    _redis_url = f"redis://{_mq_conf['HOST']}:{_mq_conf['PORT']}/{_mq_conf['DB']}"

broker = AioPikaBroker(
    url=settings.RABBITMQ_CONF["url"],
).with_result_backend(RedisAsyncResultBackend(redis_url=_redis_url))


@broker.task("send-email")
async def send_email_task(recipient: str, subject: str, content: str):
    await send_email(recipient, subject, content)


@broker.task("call-codesandbox")
async def call_codesandbox_task(
    user_id: str,
    code: str,
    language_id: int,
    question_id: int,
    submit_record_id: int,
    judge_type: str,
):
    async with (
        TestService() as test_service,
        JudgeTemplateService() as judge_template_service,
        MemoryTimeLimitService() as memory_time_limit_service,
        LanguageService() as language_service
    ):
        memory_time_limit, language, judge_template, tests = await asyncio.gather(
            memory_time_limit_service.query_by_combination_index(question_id, language_id),
            language_service.query_by_primary_key(language_id),
            judge_template_service.query_by_combination_index(question_id, language_id),
            test_service.query_by_question_id(question_id, judge_type)
        )
    _tests = [{"test_id": test.id, "input_output": test.input_output} for test in tests]

    # 调用代码沙箱
    response = await codesandbox_caller.call(
        user_id=user_id,
        question_id=question_id,
        solution_code=code,
        language=language.name.lower(),
        judge_template=judge_template.code,
        tests=_tests,
        time_limit=memory_time_limit.time_limit,
        memory_limit=memory_time_limit.memory_limit
    )
    if response["code"] != 200:
        # 判题异常
        async with SubmitRecordService() as service:
            await service.update(submit_record_id, {"status": -1})
        return
    
    # 解析判题结果并保存到数据库中
    results = response["results"]
    max_memory_consumed = -1
    max_time_consumed = -1
    total_test_quantity = len(results)
    pass_test_quantity = 0
    for result in results:
        max_memory_consumed = max(max_memory_consumed, result["memory_consumed"])
        max_time_consumed = max(max_time_consumed, result["time_consumed"])
        pass_test_quantity += result["is_success"]
        result["submit_record_id"] = submit_record_id

    async with (
        SubmitRecordService() as submit_record_service,
        JudgeRecordService() as judge_record_service,
        QuestionService() as question_service
    ):
        await asyncio.gather(
            submit_record_service.update(submit_record_id, {
                "max_memory_consumed": max_memory_consumed,
                "max_time_consumed": max_time_consumed,
                "pass_test_quantity": pass_test_quantity,
                "total_test_quantity": total_test_quantity,
                "status": 1,
            }),
            judge_record_service.create_many(results),
            question_service.increment_submission_and_pass_quantity(
                question_id, 
                (total_test_quantity == pass_test_quantity) and (judge_type == "submit")
            )
        )
