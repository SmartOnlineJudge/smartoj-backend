from fastapi import APIRouter, Body, Query

from utils.responses import SmartOJResponse, ResponseCodes
from utils.dependencies import (
    CurrentUserDependency, 
    QuestionTagServiceDependency, 
    JudgeTemplateServiceDependency, 
    MemoryTimeLimitDependency, 
    SolvingFrameworkServiceDependency, 
    TestServiceDependency,
    QuestionServiceDependency,
    LanguageServiceDependency,
    TagServiceDependency
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
    QuestionOnlineJudge
)

router = APIRouter()


@router.post("/permission-detection", summary="检查当前用户对当前题目是否有操作权限", tags=["题目信息"])
async def permission_detection(
    user: CurrentUserDependency,
    service: QuestionServiceDependency,
    question_id: int = Body(embed=True, ge=1), 
):
    """
    ## 参数列表说明:
    **question_id**: 题目ID；必须；请求体
    ## 响应代码说明:
    **200**: 有权限操作该题目 </br>
    **255**: 请求的资源不存在 </br>
    **310**: 无权限操作该题目
    """
    question = await service.query_by_primary_key(question_id)
    if question is None:
        return SmartOJResponse(ResponseCodes.NOT_FOUND)
    if (user["id"] != question.publisher_id) and (not user["is_superuser"]):
        return SmartOJResponse(ResponseCodes.PERMISSION_DENIED)
    return SmartOJResponse(ResponseCodes.OK)


@router.post("", summary="题目信息增加", tags=["题目信息"])
async def add_question_info(
        user: CurrentUserDependency,
        question_service: QuestionServiceDependency,
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
    question_id = await question_service.create(publisher_id=user["id"], **question.model_dump())
    return SmartOJResponse(ResponseCodes.OK, data={"question_id": question_id})


@router.delete("", summary="逻辑删除题目", tags=["题目信息"], include_in_schema=False)
async def question_delete(
        _: CurrentUserDependency,
        service: QuestionServiceDependency,
        question_id: int = Body(embed=True),
):
    """
    ## 参数列表说明:
    **question_id**: 要删除的题目id；必须；请求体 </br>
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    """
    await service.update(question_id, {"is_deleted": True})
    return SmartOJResponse(ResponseCodes.OK)


@router.put("", summary="题目信息修改", tags=["题目信息"])
async def question_update(
        _: CurrentUserDependency,
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
    """
    document = question.model_dump(exclude={"id": True})
    await service.update(question_id=question.id, document=document)
    return SmartOJResponse(ResponseCodes.OK)


@router.post("/judge-template", summary="创建判题模板", tags=["判题模板"])
async def judge_template_add(
        _: CurrentUserDependency,
        service: JudgeTemplateServiceDependency,
        data: JudgeTemplateCreate
):
    """
    ## 参数列表说明:
    **question_id**: 需要增加判题模板的题目id；必须；请求体 </br>
    **language_id**: 需要增加判题模板的编程语言；必须；请求体 </br>
    **code**: 需要增加判题模板的代码；必须；请求体 </br>
    ## 响应代码说明:
    **200**: 业务逻辑执行成功，并返回新增加的判题模板ID </br>
    **500**: 每个题目的每个编程语言只能有一个判题模板
    """
    json_data = data.model_dump()
    judge_template = await service.query_by_combination_index(
        question_id=json_data['question_id'], 
        language_id=json_data['language_id']
    )
    if judge_template is not None:
        return SmartOJResponse(ResponseCodes.JUDGE_TEMPLATE_ALREADY_EXISTS)
    judge_template_id = await service.create(**json_data)
    return SmartOJResponse(ResponseCodes.OK, data={"judge_template_id": judge_template_id})


@router.put("/judge-template", summary="修改判题模板", tags=["判题模板"])
async def update_judge_template(
        _: CurrentUserDependency,
        data: JudgeTemplateUpdate,
        service: JudgeTemplateServiceDependency
):
    """
    ## 参数列表说明:
    **id**: 需要修改的判题模板id；必须；请求体 </br>
    **code**: 修改后的判题模板代码；必须；请求体
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    **255**: 请求的资源不存在
    """
    judge_template = await service.query_by_primary_key(data.id)
    if judge_template is None:
        return SmartOJResponse(ResponseCodes.NOT_FOUND)
    await service.update(judge_template_id=data.id, code=data.code, instance=judge_template)
    return SmartOJResponse(ResponseCodes.OK)


@router.post("/memory-time-limit", summary="题目增加内存时间限制信息", tags=["内存时间限制"])
async def memory_time_limit_add(
        _: CurrentUserDependency,
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
    **200**: 业务逻辑执行成功，并返回新增加的内存时间限制ID </br>
    **505**: 每个题目的每个编程语言只能有一个内存时间限制
    """
    json_data = data.model_dump()
    memory_time_limit = await service.query_by_combination_index(json_data['question_id'], json_data['language_id'])
    if memory_time_limit is not None:
        return SmartOJResponse(ResponseCodes.TIME_MEMORY_LIMIT_ALREADY_EXISTS)
    memory_time_limit_id = await service.create(**json_data)
    return SmartOJResponse(ResponseCodes.OK, data={"memory_time_limit_id": memory_time_limit_id})


@router.put("/memory-time-limit", summary="内存时间限制信息修改", tags=["内存时间限制"])
async def update_memory_time_limit(
        _: CurrentUserDependency,
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
    **255**: 请求的资源不存在
    """
    memory_time_limit = await service.query_by_primary_key(data.id)
    if memory_time_limit is None:
        return SmartOJResponse(ResponseCodes.NOT_FOUND)
    await service.update(data.id, data.time_limit, data.memory_limit, memory_time_limit)
    return SmartOJResponse(ResponseCodes.OK)


@router.post("/solving-framework", summary="题目增加解题框架信息", tags=["解题框架"])
async def solving_framework_add(
        _: CurrentUserDependency,
        service: SolvingFrameworkServiceDependency,
        data: QuestionAddFrameworkData
):
    """
    ## 参数列表说明:
    **code_framework**: 解题框架代码；必须；请求体 </br>
    **language_id**: 编程语言ID；必须；请求体 </br>
    **question_id**: 解题框架所对应的题目ID；必须；请求体
    ## 响应代码说明:
    **200**: 业务逻辑执行成功，并返回新增加的解题框架ID </br>
    **510**: 每个题目的每个编程语言只能有一个解题框架
    """
    solving_framework = await service.query_by_combination_index(data.question_id, data.language_id)
    if solving_framework is not None:
        return SmartOJResponse(ResponseCodes.SOLVING_FRAMEWORK_ALREADY_EXISTS)
    solving_framework_id = await service.create(**data.model_dump())
    return SmartOJResponse(ResponseCodes.OK, data={"solving_framework_id": solving_framework_id})


@router.put("/solving-framework", summary="解题框架信息修改", tags=["解题框架"])
async def update_solving_framework(
        _: CurrentUserDependency,
        data: FrameworkDataUpdate,
        service: SolvingFrameworkServiceDependency
):
    """
    ## 参数列表说明:
    **id**: 解题框架的ID；必须；请求体 </br>
    **code_framework**: 解题框架代码；必须；请求体
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    **255**: 请求的资源不存在
    """
    solving_framework = await service.query_by_primary_key(data.id)
    if solving_framework is None:
        return SmartOJResponse(ResponseCodes.NOT_FOUND)
    await service.update(data.id, data.code_framework, solving_framework)
    return SmartOJResponse(ResponseCodes.OK)


@router.post("/test", summary="题目增加测试用例信息", tags=["测试用例"])
async def test_add(
        _: CurrentUserDependency,
        service: TestServiceDependency,
        data: QuestionAddTestData
):
    """
    ## 参数列表说明:
    **question_id**: 题目ID；必须；请求体 </br>
    **input_output**: 测试用例输入输出；必须；请求体
    ## 响应代码说明:
    **200**: 业务逻辑执行成功，并返回新增加的测试用例ID
    """
    test_id = await service.create(question_id=data.question_id, input_output=data.input_output)
    return SmartOJResponse(ResponseCodes.OK, data={"test_id": test_id})


@router.delete("/test", summary="测试用例信息删除", tags=["测试用例"])
async def test_delete(
        _: CurrentUserDependency,
        service: TestServiceDependency,
        test_id: int = Body(embed=True, ge=1)
):
    """
    ## 参数列表说明:
    **test_id**: 要删除的测试用例ID；必须；请求体 </br>
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    **255**: 请求的资源不存在
    """
    test = await service.query_by_primary_key(test_id)
    if test is None:
        return SmartOJResponse(ResponseCodes.NOT_FOUND)
    await service.delete(test_id)
    return SmartOJResponse(ResponseCodes.OK)


@router.put("/test", summary="测试用例信息修改", tags=["测试用例"])
async def update_test(
        _: CurrentUserDependency,
        data: TestUpdate,
        service: TestServiceDependency
):
    """
    ## 参数列表说明:
    **id**: 需要修改的测试用例信息ID；必须；请求体 </br>
    **input_output**: 修改后的输入输出；必须；请求体
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    **255**: 请求的资源不存在
    """
    test = await service.query_by_primary_key(data.id)
    if test is None:
        return SmartOJResponse(ResponseCodes.NOT_FOUND)
    await service.update(data.id, data.input_output, test)
    return SmartOJResponse(ResponseCodes.OK)


@router.post("/question-tag", summary="题目增加题目标签信息", tags=["题目标签"])
async def create_question_tag(
        _: CurrentUserDependency,
        service: QuestionTagServiceDependency,
        data: QuestionAddTag
):
    """
    ## 参数列表说明:
    **question_id**: 需要增加标签的题目id；必须；请求体 </br>
    **tag_id**: 增加的题目标签id；必须；请求体
    ## 响应代码说明:
    **200**: 业务逻辑执行成功，并返回新增加的内存标签ID（question_tag表中的主键）
    """
    question_tag = await service.query_by_combination_index(data.question_id, data.tag_id)
    if question_tag is not None:
        return SmartOJResponse(ResponseCodes.QUESTION_TAG_ALREADY_EXISTS)
    question_tag_id = await service.create(data.question_id, data.tag_id)
    return SmartOJResponse(ResponseCodes.OK, data={"question_tag_id": question_tag_id})


@router.delete("/question-tag", summary="题目标签信息删除", tags=["题目标签"])
async def question_tag_delete(
        _: CurrentUserDependency,
        service: QuestionTagServiceDependency,
        question_tag_id: int = Body(embed=True, ge=1),
):
    """
    ## 参数列表说明:
    **question_tag_id**: question_tag表的主键ID（注意不是tag表的主键ID）；必须；请求体
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    **255**: 请求的资源不存在
    """
    question_tag = await service.query_by_primary_key(question_tag_id)
    if question_tag is None:
        return SmartOJResponse(ResponseCodes.NOT_FOUND)
    await service.delete(question_tag)
    return SmartOJResponse(ResponseCodes.OK)


@router.put("/question-tag", summary="题目标签信息修改", tags=["题目标签"], include_in_schema=False)
async def question_tag_update(
        _: CurrentUserDependency,
        service: QuestionTagServiceDependency,
        question_tag: QuestionUpdateTag = Body(),
):
    """
    ## 参数列表说明:
    **question_id**: 要修改的标签的题目id；必须；请求体 </br>
    **tag_id**: 要修改的标签id；必须；请求体 </br>
    **new_tag_id**: 修改后的标签id；必须；请求体
    ## 响应代码说明:
    **200**: 业务逻辑执行成功
    """
    await service.update(question_id=question_tag.question_id, tag_id=question_tag.tag_id,
                         new_tag_id=question_tag.new_tag_id)
    return SmartOJResponse(ResponseCodes.OK)


@router.get("/online-solving", summary="查询在线刷题时所需的题目信息", tags=["题目信息"])
async def query_online_solving_question_info(
    service: QuestionServiceDependency,
    question_id: int = Query(ge=1)
):
    """
    ## 参数列表说明:
    **question_id**: 当前题目ID；必须；查询参数
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    **255**: 请求的资源不存在
    """
    question = await service.query_by_primary_key(question_id, online_judge=True)
    if question is None:
        return SmartOJResponse(ResponseCodes.NOT_FOUND)
    question.tests = question.tests[:3]
    question = QuestionOnlineJudge.model_validate(question)
    return SmartOJResponse(ResponseCodes.OK, data=question)


@router.get("/languages", summary="查询所有编程语言信息", tags=["编程语言"])
async def query_languages(service: LanguageServiceDependency):
    """
    ## 响应代码说明:
    **200**: 业务逻辑执行成功
    """
    languages = await service.query_all()
    return SmartOJResponse(ResponseCodes.OK, data=languages)


@router.get("/tags", summary="查询所有标签信息", tags=["题目标签"])
async def query_tags(service: TagServiceDependency, require_question_count: bool = Query(False)):
    """
    ## 参数列表说明:
    **require_question_count**: 是否需要查询标签所对应的题目数量；可选；查询参数
    ## 响应代码说明:
    **200**: 业务逻辑执行成功
    """
    tags = await service.query_all(require_question_count)
    if not require_question_count:
        return SmartOJResponse(ResponseCodes.OK, data=tags)
    results = []
    for tag, question_count in tags:
        result = tag.model_dump()
        result["question_count"] = question_count
        results.append(result)
    return SmartOJResponse(ResponseCodes.OK, data=results)
