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
    QuestionService,
    TagService,
    MessageService,
    UserService,
    SolutionService,
    CommentService,
    UserProfilesService
)
from storage.es import client as es_client


_mq_conf = settings.REDIS_CONF["mq"]
if _mq_conf["PASSWORD"] is not None:
    _redis_url = f"redis://:{_mq_conf['PASSWORD']}@{_mq_conf['HOST']}:{_mq_conf['PORT']}/{_mq_conf['DB']}"
else:
    _redis_url = f"redis://{_mq_conf['HOST']}:{_mq_conf['PORT']}/{_mq_conf['DB']}"

broker = AioPikaBroker(
    url=settings.RABBITMQ_CONF["url"],
).with_result_backend(
    RedisAsyncResultBackend(
        redis_url=_redis_url,
        health_check_interval=30,
        socket_keepalive=True,
        retry_on_timeout=True,
        socket_connect_timeout=15,
        socket_timeout=10
    )
)


@broker.task("send-email")
async def send_email_task(recipient: str, subject: str, content: str):
    await send_email(recipient, subject, content)


@broker.task("update-user-profile")
async def update_user_profile_task(user_id: str):
    async with (
        UserProfilesService() as user_profile_service,
        UserService() as user_service
    ):
        user = await user_service.query_by_index("user_id", user_id)
        if user is None:
            return
        await user_profile_service.create_or_update_profile(user.id)


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
    # 当判题类型为置为 submit 时才更新用户画像
    if judge_type == "submit":
        await update_user_profile_task.kiq(user_id=user_id)


@broker.task("update-question")
async def update_question_task(event: dict):
    """
    MySQL 中仅有 question 的数据发生变化
    """
    action = event["action"]
    match action:
        case "insert":
            document: dict = event["values"]
            document.pop("is_deleted")
            document.pop("publisher_id")
            document["tags"] = []
            await es_client.index(index="question", id=document["id"], document=document)
        case "update":
            doc: dict = event["after_values"]
            doc.pop("is_deleted")
            doc.pop("publisher_id")
            await es_client.update(index="question", id=doc["id"], doc=doc)
        case "delete":
            await es_client.delete(index="question", id=event["values"]["id"])


@broker.task("update-question-tag")
async def update_question_tag_task(event: dict):
    """
    MySQL 中涉及到 tag 相关的数据发生变化
    """
    action = event["action"]
    table = event["table"]
    if table == "question_tag":
        values = event["values"]
        async with TagService() as service:
            tag = await service.query_by_primary_key(values["tag_id"])
        tag_name = tag.name
        # 使用 Java 脚本来处理数据
        script = {"params": {"tag": tag_name}}
        if action == "insert":
            script["source"] = "ctx._source.tags.add(params.tag)"
        elif action == "delete":
            script["source"] = "ctx._source.tags.removeIf(tag -> tag == params.tag)"
        await es_client.update(index="question", id=values["question_id"], script=script)
    else:
        if action != "update":
            # 对于 tag 本身的数据变化，这里只考虑 tag 被更新的情况。
            # 对于增加标签的情况，不影响 ES 中已经存在的数据，所以不考虑；
            # 而对于删除标签的情况，这种场景很少见，因此也不考虑。
            return
        before_values = event["before_values"]
        after_values = event["after_values"]
        if before_values["name"] == after_values["name"]:
            # tag 名称没有变化，不影响 ES 中的数据，直接忽视。
            return
        body = {
            "query": {
                "term": {
                    "tags": before_values["name"]
                }
            },
            "script": {
                "source": """
                    for (int i = 0; i < ctx._source.tags.length; i++) {
                        if (ctx._source.tags[i] == params.before_tag) {
                            ctx._source.tags[i] = params.after_tag;
                        }
                    }""",
                "params": {
                    "before_tag": before_values["name"],
                    "after_tag": after_values["name"]
                }
            }
        }
        await es_client.update_by_query(index="question", body=body)


@broker.task("create-reply-message")
async def create_reply_message_task(event: dict):
    """
    MySQL 中有 comment 表的数据发生变化
    """
    action = event["action"]
    # 只处理新增评论的情况
    if action != "insert":
        return
    values = event["values"]
    #  只处理回复评论的情况
    to_comment_id = values.get("to_comment_id")
    if to_comment_id is None:
        return
    
    sender_id = values["user_id"]

    if values["type"] == "question":
        target_service_class = QuestionService
        type_chinese_name = "题目"
    else:
        target_service_class = SolutionService
        type_chinese_name = "题解"

    async with (
        UserService() as user_service,
        target_service_class() as target_service,
        CommentService() as comment_service
    ):
        user, target, comment = await asyncio.gather(
            user_service.query_by_index("id", sender_id),
            target_service.query_by_primary_key(values["target_id"]),
            comment_service.query_by_primary_key(to_comment_id)
        )
        sender_name = user.user_dynamic.name
        target_title = target.title
        recipient_id = comment.user_id

    message_title = f"@{sender_name} 在{type_chinese_name}“{target_title}”中回复了你"
    content = values["content"]

    async with MessageService() as service:
        await service.create(sender_id, recipient_id, message_title, content, "reply")
