import asyncio

from fastapi import APIRouter, Depends, Body

from storage.mysql import executors
from utils.responses import SmartOJResponse, ResponseCodes
from utils.user.auth import get_current_user
from .models import QuestionCreate, QuestionUpdate, JudgeTemplateUpdate, LimitDataUpdate, FrameworkDataUpdate, \
    TestUpdate

router = APIRouter()


@router.post("", summary="题目信息增加")
async def get_question_info(
        user: dict = Depends(get_current_user),
        question_info: QuestionCreate = Body()
):
    """
    ## 参数列表说明:
    **question_info**: 题目信息模型；必须；请求体 </br>
    **size**: 每页的数据数；必须；请求体；默认为5；查询参数 </br>
    ## 响应代码说明:
    **200**: 业务逻辑执行成功
    """
    publisher_id = await executors.user.get_id_by_user_id(user["user_id"])
    qid = await executors.question.question_add(title=question_info.title, description=question_info.description,
                                                difficulty=question_info.difficulty,
                                                publisher_id=publisher_id["id"])
    tasks = [
        executors.tag.add_tags_by_qid(qid, question_info.tags_ids),
        executors.test.add_test_by_qid(qid, question_info.input_outputs),
        executors.memory_time_limit.add_memory_time_limit_by_qid(qid, question_info.limit_datas),
        executors.solving_framework.add_solving_frameworks_by_qid(qid, question_info.framework_datas),
        executors.judge_template.add_judge_templates_by_qid(qid, question_info.judge_templates)
    ]
    await asyncio.gather(*tasks)
    return SmartOJResponse(ResponseCodes.OK)


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


@router.put("", summary="题目信息修改")
async def question_update(
        user: dict = Depends(get_current_user),
        question_data: QuestionUpdate = Body(),
):
    """
    ## 参数列表说明:
    **question_data**: 题目基本信息模型；必须；请求体 </br>
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    **255**: 请求的资源不存在 </br>
    **310**: 当前帐号权限不足 </br>
    """
    response = await permission_detection(user=user, question_id=question_data.id)
    if response == 0:
        return SmartOJResponse(ResponseCodes.PERMISSION_DENIED)
    if response == 3:
        return SmartOJResponse(ResponseCodes.NOT_FOUND)
    await executors.question.question_update(q_id=question_data.id, title=question_data.title,
                                             description=question_data.description,
                                             difficulty=question_data.difficulty)
    return SmartOJResponse(ResponseCodes.OK)


@router.put("/judge_template", summary="判题模板信息修改")
async def update_judge_template(
        judge_template_data: JudgeTemplateUpdate = Body(),
        user: dict = Depends(get_current_user),
):
    """
    ## 参数列表说明:
    **judge_template_data**: 判题模板基本信息模型；必须；请求体 </br>
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    **255**: 请求的资源不存在 </br>
    **310**: 当前帐号权限不足 </br>
    """
    question_id = await executors.judge_template.get_question_id_by_template_id(judge_template_data.id)
    if not question_id:
        return SmartOJResponse(ResponseCodes.NOT_FOUND)
    response = await permission_detection(user=user, question_id=question_id[0]["question_id"])
    if response == 0:
        return SmartOJResponse(ResponseCodes.PERMISSION_DENIED)
    if response == 3:
        return SmartOJResponse(ResponseCodes.NOT_FOUND)
    await executors.judge_template.update_judge_template(judge_template_data.code,
                                                         judge_template_data.id)
    return SmartOJResponse(ResponseCodes.OK)


@router.put("/memory_time_limit", summary="内存时间限制信息修改")
async def update_memory_time_limit(
        memory_time_limit_data: LimitDataUpdate = Body(),
        user: dict = Depends(get_current_user),
):
    """
    ## 参数列表说明:
    **ml_data**: 内存限制基本信息模型；必须；请求体 </br>
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    **255**: 请求的资源不存在 </br>
    **310**: 当前帐号权限不足 </br>
    """
    question_id = await executors.memory_time_limit.get_question_id_by_limits_id(memory_time_limit_data.id)
    if not question_id:
        return SmartOJResponse(ResponseCodes.NOT_FOUND)
    response = await permission_detection(user=user, question_id=question_id[0]["question_id"])
    if response == 0:
        return SmartOJResponse(ResponseCodes.PERMISSION_DENIED)
    if response == 3:
        return SmartOJResponse(ResponseCodes.NOT_FOUND)
    await executors.memory_time_limit.update_memory_limits(memory_time_limit_data.time_limit,
                                                           memory_time_limit_data.memory_limit,
                                                           memory_time_limit_data.id)
    return SmartOJResponse(ResponseCodes.OK)


@router.put("/solving_framework", summary="解题框架信息修改")
async def update_solving_framework(
        solving_framework_data: FrameworkDataUpdate = Body(),
        user: dict = Depends(get_current_user),
):
    """
    ## 参数列表说明:
    **solving_framework_data**: 内存限制基本信息模型；必须；请求体 </br>
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    **255**: 请求的资源不存在 </br>
    **310**: 当前帐号权限不足 </br>
    """
    question_id = await executors.solving_framework.get_question_id_by_framework_id(solving_framework_data.id)
    if not question_id:
        return SmartOJResponse(ResponseCodes.NOT_FOUND)
    response = await permission_detection(user=user, question_id=question_id[0]["question_id"])
    if response == 0:
        return SmartOJResponse(ResponseCodes.PERMISSION_DENIED)
    if response == 3:
        return SmartOJResponse(ResponseCodes.NOT_FOUND)
    await executors.solving_framework.update_solving_framework(solving_framework_data.code_framework,
                                                               solving_framework_data.id)
    return SmartOJResponse(ResponseCodes.OK)


@router.put("/test", summary="测试案例信息修改")
async def update_test(
        test: TestUpdate = Body(),
        user: dict = Depends(get_current_user),
):
    """
    ## 参数列表说明:
    **test**: 内存限制基本信息模型；必须；请求体 </br>
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    **255**: 请求的资源不存在 </br>
    **310**: 当前帐号权限不足 </br>
    """
    question_id = await executors.test.get_question_id_by_test_id(test.id)
    if not question_id:
        return SmartOJResponse(ResponseCodes.NOT_FOUND)
    response = await permission_detection(user=user, question_id=question_id[0]["question_id"])
    if response == 0:
        return SmartOJResponse(ResponseCodes.PERMISSION_DENIED)
    if response == 3:
        return SmartOJResponse(ResponseCodes.NOT_FOUND)
    await executors.test.update_test(test.input_output, test.id)
    return SmartOJResponse(ResponseCodes.OK)


@router.delete("", summary="题目信息删除")
async def question_delete(
        user: dict = Depends(get_current_user),
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
    await executors.question.question_delete(q_id=question_id)
    return SmartOJResponse(ResponseCodes.OK)


@router.delete("/judge_template", summary="判题模板信息删除")
async def judge_template_delete(
        judge_template_id: int = Body(embed=True),
        user: dict = Depends(get_current_user),

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


@router.delete("/solving_framework", summary="解题框架信息删除")
async def solving_framework_delete(
        solving_framework_id: int = Body(embed=True),
        user: dict = Depends(get_current_user),

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


@router.delete("/test", summary="测试用例删除")
async def test_delete(
        test_id: int = Body(embed=True),
        user: dict = Depends(get_current_user),

):
    """
    ## 参数列表说明:
    **test_id**: 要删除的测试用例id；必须；请求体 </br>
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    **255**: 请求的资源不存在 </br>
    **310**: 当前帐号权限不足 </br>
    """
    question_id = await executors.test.get_question_id_by_test_id(test_id)
    if not question_id:
        return SmartOJResponse(ResponseCodes.NOT_FOUND)
    response = await permission_detection(user=user, question_id=question_id[0]["question_id"])
    if response == 0:
        return SmartOJResponse(ResponseCodes.PERMISSION_DENIED)
    if response == 3:
        return SmartOJResponse(ResponseCodes.NOT_FOUND)
    await executors.test.test_delete(test_id=test_id)
    return SmartOJResponse(ResponseCodes.OK)


@router.delete("/memory_time_limit", summary="内存时间限制删除")
async def memory_time_limit_delete(
        memory_limits_id: int = Body(embed=True),
        user: dict = Depends(get_current_user),

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
