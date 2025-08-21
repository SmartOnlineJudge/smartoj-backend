from fastapi import APIRouter

from mq.broker import call_codesandbox_task
from utils.responses import SmartOJResponse, ResponseCodes
from utils.dependencies import CurrentUserDependency, SubmitRecordDependency
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
