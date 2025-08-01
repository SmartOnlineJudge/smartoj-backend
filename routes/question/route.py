from fastapi import APIRouter, Body

from storage.mysql import executors
from utils.responses import SmartOJResponse, ResponseCodes
from utils.dependencies import (
    CurrentUserDependency, 
    QuestionTagServiceDependency, 
    JudgeTemplateServiceDependency, 
    MemoryTimeLimitDependency, 
    SolvingFrameworkServiceDependency, 
    TestServiceDependency,
    QuestionServiceDependency,
    UserServiceDependency,
)
from .models import (
    QuestionCreate,
    QuestionUpdate,
    JudgeTemplateUpdate,
    JudgeTemplateCreate,
    LimitDataUpdate,
    FrameworkDataUpdate,
    TestUpdate, 
    QuestionAddLimitData, 
    QuestionAddFrameworkData, 
    QuestionAddTestData, 
    QuestionAddTag, 
    QuestionUpdateTag,
    QuestionDeleteTag,
)

router = APIRouter()


async def permission_detection(question_id: int, user: dict):
    if not question_id:
        return 3
    user_nid = await executors.user.get_id_by_user_id(user["user_id"])
    user_id = user_nid["id"]
    publisher_nid = await executors.user_dynamic.get_publisher_by_qid([question_id])
    if not publisher_nid:
        return 3
    publisher_id = publisher_nid[0]["user_id"]
    if user_id != publisher_id and not user["is_superuser"]:
        return 0
    return 1


@router.post("", summary="题目信息增加", tags=["题目信息"])
async def add_question_info(
        user: CurrentUserDependency,
        question_service: QuestionServiceDependency,
        user_service: UserServiceDependency,
        question: QuestionCreate
):
    """
    ## 参数列表说明:
    **title**: 题目标题；必须；请求体 </br>
    **description**: 题目描述；必须；请求体 </br>
    **difficulty**: 题目难度；必须；请求体
    ## 响应代码说明:
    **200**: 业务逻辑执行成功，并返回新增加题目的ID
    """
    user = await user_service.query_by_index("user_id", user["user_id"])
    question_id = await question_service.create(publisher_id=user.id, **question.model_dump())
    return SmartOJResponse(ResponseCodes.OK, data={"question_id": question_id})


@router.delete("", summary="逻辑删除题目", tags=["题目信息"], include_in_schema=False)
async def question_delete(
        user: CurrentUserDependency,
        service: QuestionServiceDependency,
        question_id: int = Body(embed=True),
):
    """
    ## 参数列表说明:
    **question_id**: 要删除的题目id；必须；请求体 </br>
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    **255**: 请求的资源不存在 </br>
    **310**: 当前帐号权限不足 </br>
    """
    response = await permission_detection(user=user, question_id=question_id)
    if response == 0:
        return SmartOJResponse(ResponseCodes.PERMISSION_DENIED)
    if response == 3:
        return SmartOJResponse(ResponseCodes.NOT_FOUND)
    await service.update(question_id, {"is_deleted": True})
    return SmartOJResponse(ResponseCodes.OK)


@router.put("", summary="题目信息修改", tags=["题目信息"])
async def question_update(
        user: CurrentUserDependency,
        service: QuestionServiceDependency,
        question: QuestionUpdate
):
    """
    ## 参数列表说明:
    **id**: 要修改的题目ID；必须；请求体 </br>
    **title**: 题目标题；必须；请求体 </br>
    **description**: 题目描述；必须；请求体 </br>
    **difficulty**: 题目难度；必须；请求体 </br>
    **is_deleted**: 是否逻辑删除；必须；请求体
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    **255**: 请求的资源不存在 </br>
    **310**: 当前帐号权限不足
    """
    response = await permission_detection(user=user, question_id=question.id)
    if response == 0:
        return SmartOJResponse(ResponseCodes.PERMISSION_DENIED)
    if response == 3:
        return SmartOJResponse(ResponseCodes.NOT_FOUND)
    document = question.model_dump(exclude={"id": True})
    await service.update(question_id=question.id, document=document)
    return SmartOJResponse(ResponseCodes.OK)


@router.post("/judge-template", summary="创建判题模板", tags=["判题模板"])
async def judge_template_add(
        user: CurrentUserDependency,
        service: JudgeTemplateServiceDependency,
        data: JudgeTemplateCreate
):
    """
    ## 参数列表说明:
    **question_id**: 需要增加判题模板的题目id；必须；请求体 </br>
    **language_id**: 需要增加判题模板的编程语言；必须；请求体 </br>
    **code**: 需要增加判题模板的代码；必须；请求体 </br>
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    **255**: 请求的资源不存在 </br>
    **310**: 当前帐号权限不足 </br>
    """
    json_data = data.model_dump()
    response = await permission_detection(user=user, question_id=json_data['question_id'])
    if response == 0:
        return SmartOJResponse(ResponseCodes.PERMISSION_DENIED)
    if response == 3:
        return SmartOJResponse(ResponseCodes.NOT_FOUND)
    judge_template = await service.query_by_combination_index(
        question_id=json_data['question_id'], 
        language_id=json_data['language_id']
    )
    if judge_template is not None:
        return SmartOJResponse(ResponseCodes.JUDGE_TEMPLATE_ALREADY_EXISTS)
    await service.create(**json_data)
    return SmartOJResponse(ResponseCodes.OK)


@router.delete("/judge-template", summary="删除判题模板", tags=["判题模板"], include_in_schema=False)
async def judge_template_delete(
        user: CurrentUserDependency,
        judge_template_id: int = Body(embed=True)
):
    """
    ## 参数列表说明:
    **judge_template_id**: 要删除的判题模板id；必须；请求体 </br>
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    **255**: 请求的资源不存在 </br>
    **310**: 当前帐号权限不足 </br>
    """
    question_id = await executors.judge_template.get_question_id_by_template_id(judge_template_id)
    if not question_id:
        return SmartOJResponse(ResponseCodes.NOT_FOUND)
    response = await permission_detection(user=user, question_id=question_id[0]["question_id"])
    if response == 0:
        return SmartOJResponse(ResponseCodes.PERMISSION_DENIED)
    if response == 3:
        return SmartOJResponse(ResponseCodes.NOT_FOUND)
    await executors.judge_template.judge_template_delete(judge_template_id=judge_template_id)
    return SmartOJResponse(ResponseCodes.OK)


@router.put("/judge-template", summary="修改判题模板", tags=["判题模板"])
async def update_judge_template(
        user: CurrentUserDependency,
        data: JudgeTemplateUpdate,
        service: JudgeTemplateServiceDependency
):
    """
    ## 参数列表说明:
    **id**: 需要修改的判题模板id；必须；请求体 </br>
    **code**: 修改后的判题模板代码；必须；请求体
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    **255**: 请求的资源不存在 </br>
    **310**: 当前帐号权限不足 </br>
    """
    judge_template = await service.query_by_primary_key(data.id)
    if judge_template is None:
        return SmartOJResponse(ResponseCodes.NOT_FOUND)
    response = await permission_detection(user=user, question_id=judge_template.question_id)
    if response == 0:
        return SmartOJResponse(ResponseCodes.PERMISSION_DENIED)
    if response == 3:
        return SmartOJResponse(ResponseCodes.NOT_FOUND)
    await service.update(judge_template_id=data.id, code=data.code, instance=judge_template)
    return SmartOJResponse(ResponseCodes.OK)


@router.post("/memory-time-limit", summary="题目增加内存时间限制信息", tags=["内存时间限制"])
async def memory_time_limit_add(
        user: CurrentUserDependency,
        service: MemoryTimeLimitDependency,
        data: QuestionAddLimitData
):
    """
    ## 参数列表说明:
    **question_id**: 需要增加内存时间限制的题目id；必须；请求体 </br>
    **language_id**: 需要增加内存时间限制的编程语言；必须；请求体 </br>
    **time_limit**: 需要增加的时间限制（单位：毫秒，且必须是一个大于等于1000的整数）；必须；请求体 </br>
    **memory_limit**: 需要增加的内存限制（单位：MB，且必须是一个大于等于1的浮点数）；必须；请求体
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    **255**: 请求的资源不存在 </br>
    **310**: 当前帐号权限不足
    """
    json_data = data.model_dump()
    memory_time_limit = await service.query_by_combination_index(json_data['question_id'], json_data['language_id'])
    if memory_time_limit is not None:
        return SmartOJResponse(ResponseCodes.TIME_MEMORY_LIMIT_ALREADY_EXISTS)
    response = await permission_detection(user=user, question_id=json_data['question_id'])
    if response == 0:
        return SmartOJResponse(ResponseCodes.PERMISSION_DENIED)
    if response == 3:
        return SmartOJResponse(ResponseCodes.NOT_FOUND)
    await service.create(**json_data)
    return SmartOJResponse(ResponseCodes.OK)


@router.delete("/memory-time-limit", summary="内存时间限制信息删除", tags=["内存时间限制"], include_in_schema=False)
async def memory_time_limit_delete(
        user: CurrentUserDependency,
        memory_limits_id: int = Body(embed=True)
):
    """
    ## 参数列表说明:
    **memory_limits_id**: 要删除的内存时间限制id；必须；请求体 </br>
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    **255**: 请求的资源不存在 </br>
    **310**: 当前帐号权限不足 </br>
    """
    question_id = await executors.memory_time_limit.get_question_id_by_limits_id(memory_limits_id)
    if not question_id:
        return SmartOJResponse(ResponseCodes.NOT_FOUND)
    response = await permission_detection(user=user, question_id=question_id[0]["question_id"])
    if response == 0:
        return SmartOJResponse(ResponseCodes.PERMISSION_DENIED)
    if response == 3:
        return SmartOJResponse(ResponseCodes.NOT_FOUND)
    await executors.memory_time_limit.memory_limits_delete(memory_limits_id=memory_limits_id)
    return SmartOJResponse(ResponseCodes.OK)


@router.put("/memory-time-limit", summary="内存时间限制信息修改", tags=["内存时间限制"])
async def update_memory_time_limit(
        user: CurrentUserDependency,
        data: LimitDataUpdate,
        service: MemoryTimeLimitDependency
):
    """
    ## 参数列表说明:
    **id**: 需要修改的内存时间限制id；必须；请求体 </br>
    **time_limit**: 需要修改的时间限制（单位：毫秒，且必须是一个大于等于1000的整数）；必须；请求体 </br>
    **memory_limit**: 需要修改的内存限制（单位：MB，且必须是一个大于等于1的浮点数）；必须；请求体
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    **255**: 请求的资源不存在 </br>
    **310**: 当前帐号权限不足
    """
    memory_time_limit = await service.query_by_primary_key(data.id)
    if memory_time_limit is None:
        return SmartOJResponse(ResponseCodes.NOT_FOUND)
    response = await permission_detection(user=user, question_id=memory_time_limit.question_id)
    if response == 0:
        return SmartOJResponse(ResponseCodes.PERMISSION_DENIED)
    if response == 3:
        return SmartOJResponse(ResponseCodes.NOT_FOUND)
    await service.update(data.id, data.time_limit, data.memory_limit, memory_time_limit)
    return SmartOJResponse(ResponseCodes.OK)


@router.post("/solving-framework", summary="题目增加解题框架信息", tags=["解题框架"])
async def solving_framework_add(
        user: CurrentUserDependency,
        service: SolvingFrameworkServiceDependency,
        data: QuestionAddFrameworkData
):
    """
    ## 参数列表说明:
    **code_framework**: 解题框架代码；必须；请求体 </br>
    **language_id**: 编程语言ID；必须；请求体 </br>
    **question_id**: 解题框架所对应的题目ID；必须；请求体
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    **255**: 请求的资源不存在 </br>
    **310**: 当前帐号权限不足 </br>
    """
    solving_framework = await service.query_by_combination_index(data.question_id, data.language_id)
    if solving_framework is not None:
        return SmartOJResponse(ResponseCodes.SOLVING_FRAMEWORK_ALREADY_EXISTS)
    response = await permission_detection(user=user, question_id=data.question_id)
    if response == 0:
        return SmartOJResponse(ResponseCodes.PERMISSION_DENIED)
    if response == 3:
        return SmartOJResponse(ResponseCodes.NOT_FOUND)
    await service.create(**data.model_dump())
    return SmartOJResponse(ResponseCodes.OK)


@router.delete("/solving-framework", summary="解题框架信息删除", tags=["解题框架"], include_in_schema=False)
async def solving_framework_delete(
        user: CurrentUserDependency,
        solving_framework_id: int = Body(embed=True)
):
    """
    ## 参数列表说明:
    **solving_framework_id**: 要删除的解题框架id；必须；请求体 </br>
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    **255**: 请求的资源不存在 </br>
    **310**: 当前帐号权限不足 </br>
    """
    question_id = await executors.solving_framework.get_question_id_by_framework_id(solving_framework_id)
    if not question_id:
        return SmartOJResponse(ResponseCodes.NOT_FOUND)
    response = await permission_detection(user=user, question_id=question_id[0]["question_id"])
    if response == 0:
        return SmartOJResponse(ResponseCodes.PERMISSION_DENIED)
    if response == 3:
        return SmartOJResponse(ResponseCodes.NOT_FOUND)
    await executors.solving_framework.solving_framework_delete(solving_framework_id=solving_framework_id)
    return SmartOJResponse(ResponseCodes.OK)


@router.put("/solving-framework", summary="解题框架信息修改", tags=["解题框架"])
async def update_solving_framework(
        user: CurrentUserDependency,
        data: FrameworkDataUpdate,
        service: SolvingFrameworkServiceDependency
):
    """
    ## 参数列表说明:
    **id**: 解题框架的ID；必须；请求体 </br>
    **code_framework**: 解题框架代码；必须；请求体
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    **255**: 请求的资源不存在 </br>
    **310**: 当前帐号权限不足 </br>
    """
    solving_framework = await service.query_by_primary_key(data.id)
    if solving_framework is None:
        return SmartOJResponse(ResponseCodes.NOT_FOUND)
    response = await permission_detection(user=user, question_id=solving_framework.question_id)
    if response == 0:
        return SmartOJResponse(ResponseCodes.PERMISSION_DENIED)
    if response == 3:
        return SmartOJResponse(ResponseCodes.NOT_FOUND)
    await service.update(data.id, data.code_framework, solving_framework)
    return SmartOJResponse(ResponseCodes.OK)


@router.post("/test", summary="题目增加测试用例信息", tags=["测试用例"])
async def test_add(
        user: CurrentUserDependency,
        service: TestServiceDependency,
        data: QuestionAddTestData
):
    """
    ## 参数列表说明:
    **question_id**: 题目ID；必须；请求体 </br>
    **input_output**: 测试用例输入输出；必须；请求体
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    **255**: 请求的资源不存在 </br>
    **310**: 当前帐号权限不足
    """
    response = await permission_detection(user=user, question_id=data.question_id)
    if response == 0:
        return SmartOJResponse(ResponseCodes.PERMISSION_DENIED)
    if response == 3:
        return SmartOJResponse(ResponseCodes.NOT_FOUND)
    await service.create(question_id=data.question_id, input_output=data.input_output)
    return SmartOJResponse(ResponseCodes.OK)


@router.delete("/test", summary="测试用例信息删除", tags=["测试用例"])
async def test_delete(
        user: CurrentUserDependency,
        service: TestServiceDependency,
        test_id: int = Body(embed=True, ge=1)
):
    """
    ## 参数列表说明:
    **test_id**: 要删除的测试用例ID；必须；请求体 </br>
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    **255**: 请求的资源不存在 </br>
    **310**: 当前帐号权限不足
    """
    test = await service.query_by_primary_key(test_id)
    if test is None:
        return SmartOJResponse(ResponseCodes.NOT_FOUND)
    response = await permission_detection(user=user, question_id=test.question_id)
    if response == 0:
        return SmartOJResponse(ResponseCodes.PERMISSION_DENIED)
    if response == 3:
        return SmartOJResponse(ResponseCodes.NOT_FOUND)
    await service.delete(test_id)
    return SmartOJResponse(ResponseCodes.OK)


@router.put("/test", summary="测试用例信息修改", tags=["测试用例"])
async def update_test(
        user: CurrentUserDependency,
        data: TestUpdate,
        service: TestServiceDependency
):
    """
    ## 参数列表说明:
    **id**: 需要修改的测试用例信息ID；必须；请求体 </br>
    **input_output**: 修改后的输入输出；必须；请求体
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    **255**: 请求的资源不存在 </br>
    **310**: 当前帐号权限不足
    """
    test = await service.query_by_primary_key(data.id)
    if test is None:
        return SmartOJResponse(ResponseCodes.NOT_FOUND)
    response = await permission_detection(user=user, question_id=test.question_id)
    if response == 0:
        return SmartOJResponse(ResponseCodes.PERMISSION_DENIED)
    if response == 3:
        return SmartOJResponse(ResponseCodes.NOT_FOUND)
    await service.update(data.id, data.input_output, test)
    return SmartOJResponse(ResponseCodes.OK)


@router.post("/question-tag", summary="题目增加题目标签信息", tags=["题目标签"])
async def solving_framework_add(
        user: CurrentUserDependency,
        service: QuestionTagServiceDependency,
        question_tag: QuestionAddTag = Body()
):
    """
    ## 参数列表说明:
    **question_id**: 需要增加标签的题目id；必须；请求体 </br>
    **tag_id**: 增加的题目标签id；必须；请求体 </br>
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    **255**: 请求的资源不存在 </br>
    **310**: 当前帐号权限不足 </br>
    """
    response = await permission_detection(user=user, question_id=question_tag.question_id)
    if response == 0:
        return SmartOJResponse(ResponseCodes.PERMISSION_DENIED)
    if response == 3:
        return SmartOJResponse(ResponseCodes.NOT_FOUND)
    await service.create(question_id=question_tag.question_id, tag_id=question_tag.tag_id)
    return SmartOJResponse(ResponseCodes.OK)


@router.delete("/question-tag", summary="题目标签信息删除", tags=["题目标签"])
async def question_tag_delete(
        user: CurrentUserDependency,
        service: QuestionTagServiceDependency,
        question_tag: QuestionDeleteTag = Body()
):
    """
    ## 参数列表说明:
    **question_id**: 要删除标签的题目id；必须；请求体 </br>
    **tag_ids**: 要删除的标签id列表；必须；请求体 </br>
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    **255**: 请求的资源不存在 </br>
    **310**: 当前帐号权限不足 </br>
    """
    response = await permission_detection(user=user, question_id=question_tag.question_id)
    if response == 0:
        return SmartOJResponse(ResponseCodes.PERMISSION_DENIED)
    if response == 3:
        return SmartOJResponse(ResponseCodes.NOT_FOUND)
    await service.delete(question_id=question_tag.question_id, tag_ids=question_tag.tag_ids)
    return SmartOJResponse(ResponseCodes.OK)


@router.put("/question-tag", summary="题目标签信息修改", tags=["题目标签"])
async def question_tag_update(
        user: CurrentUserDependency,
        service: QuestionTagServiceDependency,
        question_tag: QuestionUpdateTag = Body(),
):
    """
    ## 参数列表说明:
    **question_id**: 要修改的标签的题目id；必须；请求体 </br>
    **tag_id**: 要修改的标签id；必须；请求体 </br>
    **new_tag_id**: 修改后的标签id；必须；请求体 </br>
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    **255**: 请求的资源不存在 </br>
    **310**: 当前帐号权限不足 </br>
    """
    response = await permission_detection(user=user, question_id=question_tag.question_id)
    if response == 0:
        return SmartOJResponse(ResponseCodes.PERMISSION_DENIED)
    if response == 3:
        return SmartOJResponse(ResponseCodes.NOT_FOUND)
    await service.update(question_id=question_tag.question_id, tag_id=question_tag.tag_id,
                         new_tag_id=question_tag.new_tag_id)
    return SmartOJResponse(ResponseCodes.OK)
