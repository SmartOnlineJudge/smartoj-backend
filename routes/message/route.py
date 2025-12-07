from fastapi import APIRouter, Query, Body

from utils.dependencies import MessageServiceDependency, CurrentUserDependency
from utils.responses import SmartOJResponse, ResponseCodes
from .models import MessageOut


router = APIRouter()


@router.get("/user-message-count", summary="查询用户消息数量")
async def query_message_count(
    user: CurrentUserDependency,
    service: MessageServiceDependency,
    is_read: bool = Query(False)
):
    """
    ## 参数列表说明:
    **is_read**: 是否已读；可选；查询参数 </br>
    ## 响应代码说明:
    **200**: 业务逻辑执行成功
    """
    total = await service.get_message_count(user["id"], is_read)
    return SmartOJResponse(ResponseCodes.OK, data={"total": total})


@router.get("/user-messages", summary="查询用户消息列表")
async def query_user_messages(
    user: CurrentUserDependency,
    service: MessageServiceDependency,
    page: int = Query(1, ge=1),
    size: int = Query(5, ge=1),
    is_read: bool = Query(False)
):
    """
    ## 参数列表说明:
    **page**: 当前页码；必须；查询参数 </br>
    **size**: 每页的数据数；必须；查询参数 </br>
    **is_read**: 是否已读；可选；查询参数 </br>
    ## 响应代码说明:
    **200**: 业务逻辑执行成功
    """
    user_id = user["id"]
    messages = await service.get_messages_by_recipient_id(user_id, page, size, is_read)
    total = await service.get_message_count(user_id, is_read)
    results = [MessageOut.model_validate(message) for message in messages]
    return SmartOJResponse(ResponseCodes.OK, data={"results": results, "total": total})


@router.delete("", summary="删除消息")
async def delete_message(
    user: CurrentUserDependency,
    service: MessageServiceDependency,
    message_id: int = Body(embed=True),
):
    """
    ## 响应参数说明:
    **message_id**: 消息ID；必须；请求体
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    **310**: 当前账号权限不足
    """
    message = await service.query_by_primary_key(message_id)
    if message.recipient_id != user["id"]:
        return SmartOJResponse(ResponseCodes.PERMISSION_DENIED)
    await service.update(message_id, {"is_deleted": True})
    return SmartOJResponse(ResponseCodes.OK)


@router.patch("", summary="设置消息为已读")
async def set_message_as_read(
    user: CurrentUserDependency,
    service: MessageServiceDependency,
    message_id: int = Body(embed=True),
):
    """
    ## 响应参数说明:
    **message_id**: 消息ID；必须；请求体
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    **310**: 当前账号权限不足
    """
    message = await service.query_by_primary_key(message_id)
    if message.recipient_id != user["id"]:
        return SmartOJResponse(ResponseCodes.PERMISSION_DENIED)
    await service.update(message_id, {"is_read": True})
    return SmartOJResponse(ResponseCodes.OK)
