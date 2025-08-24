from fastapi import APIRouter, Query

from mq.broker import call_codesandbox_task
from utils.responses import SmartOJResponse, ResponseCodes
from utils.dependencies import CurrentUserDependency, SubmitRecordDependency, JudgeRecordDependency
from .models import JudgeModel

router = APIRouter()


@router.post("/judgement", summary="判题接口")
async def judge(
    data: JudgeModel,
    service: SubmitRecordDependency,
    user: CurrentUserDependency
):
    """
    ## 参数列表说明:
    **language_id**: 编程语言的id；必须；请求体 </br>
    **question_id**: 题目的id；必须；请求体 </br>
    **code**: 用户的解题代码；必须；请求体 </br>
    **judge_type**: 判题类型（'submit'，'test'）；必须；请求体
    ## 响应代码说明:
    **200**: 业务逻辑执行成功，并返回本次提交记录的ID
    """
    json_data = data.model_dump()
    submit_record_id = await service.create(**json_data, user_id=user["id"])
    await call_codesandbox_task.kiq(
        user_id=user["user_id"],
        submit_record_id=submit_record_id,
        **json_data
    )
    return SmartOJResponse(ResponseCodes.OK, data={"submit_record_id": submit_record_id})


@router.get("/submit-record", summary="查询提交记录")
async def query_submit_record(
    user: CurrentUserDependency,
    service: SubmitRecordDependency,
    submit_record_id: int = Query(1, ge=1)
):
    """
    ## 参数列表说明:
    **submit_record_id**: 提交记录的ID；必须；查询参数
    ## 响应代码说明:
    **200**: 业务逻辑执行成功，并返回本次提交记录的ID </br>
    **255**: 请求的资源不存在 </br>
    **310**: 当前账号权限不足
    """
    submit_record = await service.query_by_primary_key(submit_record_id)
    if submit_record is None:
        return SmartOJResponse(ResponseCodes.NOT_FOUND)
    if submit_record.user_id != user["id"]:
        return SmartOJResponse(ResponseCodes.PERMISSION_DENIED)
    submit_record = submit_record.model_dump(exclude={"user_id"})
    return SmartOJResponse(ResponseCodes.OK, data=submit_record)


@router.get("/judge-record", summary="查询系统判题记录")
async def query_judge_record(
    user: CurrentUserDependency,
    submit_record_service: SubmitRecordDependency,
    judge_record_service: JudgeRecordDependency,
    submit_record_id: int = Query(1, ge=1)
):
    """
    ## 参数列表说明:
    **submit_record_id**: 提交记录的ID；必须；查询参数
    ## 响应代码说明:
    **200**: 业务逻辑执行成功，并返回本次提交记录的ID </br>
    **255**: 请求的资源不存在 </br>
    **310**: 当前账号权限不足
    """
    submit_record = await submit_record_service.query_by_primary_key(submit_record_id)
    if submit_record is None:
        return SmartOJResponse(ResponseCodes.NOT_FOUND)
    if submit_record.user_id != user["id"]:
        return SmartOJResponse(ResponseCodes.PERMISSION_DENIED)
    judge_records = await judge_record_service.query_by_submit_record_id(submit_record_id)
    for judge_record in judge_records:
        if judge_record.status == -2:
            judge_record.result = "系统判题异常"
    return SmartOJResponse(ResponseCodes.OK, data=judge_records)
