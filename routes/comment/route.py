from datetime import datetime

from fastapi import APIRouter, Body, Query

from utils.dependencies import CurrentUserDependency, CommentServiceDependency, SolutionServiceDependency
from utils.responses import SmartOJResponse, ResponseCodes
from utils.generic import decode_cursor, encode_cursor
from .models import CreateComment, CommentType, CommentOut


router = APIRouter()


@router.post("", summary="创建一条评论")
async def create_comment(
    user: CurrentUserDependency,
    comment_service: CommentServiceDependency,
    solution_service: SolutionServiceDependency,
    comment: CreateComment
):
    """
    ## 参数列表说明:
    **content**: 评论内容；必须；请求体 </br>
    **type**: 评论的类型（question、solution）；必须；请求体；</br>
    **target_id**: 被评论对象的ID（只能是question_id或solution_id）；必须；请求体；</br>
    **to_comment_id**: 被回复的评论ID；可选；请求体 </br>
    **root_comment_id**: 被回复的一级评论ID；可选；请求体
    ## 响应代码说明:
    **200**: 业务逻辑执行成功，并返回新评论的ID和创建时间
    """
    data = comment.model_dump()
    if comment.root_comment_id is not None:
        await comment_service.increment_reply_count(comment.root_comment_id)
    if comment.type == CommentType.solution:
        await solution_service.increment_comment_count(comment.target_id)
    comment_metadata = await comment_service.create(**data, user_id=user["id"])
    comment_metadata["created_at"] = comment_metadata["created_at"].strftime("%Y-%m-%d %H:%M:%S")
    return SmartOJResponse(ResponseCodes.OK, data=comment_metadata)


@router.delete("", summary="逻辑删除评论")
async def logic_delete_comment(
    user: CurrentUserDependency,
    service: CommentServiceDependency,
    comment_id: int = Body(embed=True, ge=1)
):
    """
    ## 参数列表说明:
    **comment_id**: 要操作的评论ID；必须；请求体
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    **600**: 评论删除失败 </br>
    """
    is_success = await service.logic_delete(comment_id, user["id"])
    if not is_success:
        return SmartOJResponse(ResponseCodes.COMMENT_DELETE_FAILED)
    return SmartOJResponse(ResponseCodes.OK)


@router.get("/root-comments", summary="获取一级评论列表")
async def get_root_comments(
    service: CommentServiceDependency,
    comment_type: CommentType = Query(),
    target_id: int = Query(ge=1),
    page: int = Query(1, ge=1),
    size: int = Query(5, ge=1)
):
    """
    ## 参数列表说明:
    **comment_type**: 评论的类型（question、solution）；必须；查询参数 </br>
    **target_id**: 被评论对象的ID（只能是question_id或solution_id）；必须；查询参数 </br>
    **page**: 当前页码；必须；查询参数 </br>
    **size**: 每页的数据数；必须；查询参数
    ## 响应代码说明:
    **200**: 业务逻辑执行成功
    """
    comments, total = await service.get_root_comments(target_id, comment_type, page, size)
    results = [CommentOut.model_validate(comment) for comment in comments]
    return SmartOJResponse(ResponseCodes.OK, data={"results": results, "total": total})


@router.get("/child-comments", summary="获取一级评论的子评论")
async def get_child_comments(
    service: CommentServiceDependency,
    root_comment_id: int = Query(ge=1),
    cursor: str = Query(None),
    size: int = Query(5, ge=1)
):
    """
    ## 参数列表说明:
    **root_comment_id**: 要获取的子评论对应的一级评论ID；必须；查询参数 </br>
    **cursor**: 当前游标，如果为空则获取第一页；可选；查询参数 </br>
    **size**: 每页的数据数；可选，默认为5；查询参数
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    **260**: 请求参数错误
    """
    if cursor is None:
        last_created_at = datetime.now()
    else:
        try:
            last_created_at = decode_cursor(cursor)[1]
        except Exception as _:
            return SmartOJResponse(ResponseCodes.PARAMS_ERROR)
    comments = await service.get_child_comments(root_comment_id, last_created_at, size)
    has_more, next_cursor = False, None
    if len(comments) == size:
        has_more = True
        last_comment = comments[-1]
        next_cursor = encode_cursor(last_comment.id, last_comment.created_at)
    results = [CommentOut.model_validate(comment) for comment in comments]
    return SmartOJResponse(ResponseCodes.OK, data={"results": results, "has_more": has_more, "cursor": next_cursor})
