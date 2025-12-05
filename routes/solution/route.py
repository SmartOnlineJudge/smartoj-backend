from datetime import timedelta, datetime

from fastapi import APIRouter, Query, Body, Request

from core.user.session import cookie_scheme, get_current_user
from utils.responses import SmartOJResponse, ResponseCodes
from utils.generic import random_avatar_name, decode_cursor, encode_cursor
from utils.dependencies import (
    CurrentUserDependency, 
    SolutionServiceDependency, 
    MinioClientDependency,
    SessionRedisDependency,
    SubmitRecordDependency
)
from storage.oss import SOLUTION_IMAGE_BUCKET_NAME
from .models import CreateSolution, UpdateSolution, SolutionOut


router = APIRouter()


@router.post("/upload-image/signature", summary="获取上传题解图片的临时签名URL")
def upload_solution_image(
    _: CurrentUserDependency, 
    minio_client: MinioClientDependency,
    file_type_suffix: str = Body(embed=True)
):
    """
    ## 参数列表说明:
    **file_type_suffix**: 图片的文件类型后缀（jpg、png等等），不包含“.”；必须；请求体
    ## 响应代码说明:
    **200**: 业务逻辑执行成功，并返回签名URL、文件名、文件路径
    """
    if not minio_client.bucket_exists(SOLUTION_IMAGE_BUCKET_NAME):
        minio_client.make_bucket(SOLUTION_IMAGE_BUCKET_NAME)
    filename = random_avatar_name() + "." + file_type_suffix
    filepath = f"/{SOLUTION_IMAGE_BUCKET_NAME}/{filename}"
    signature_url = minio_client.presigned_put_object(SOLUTION_IMAGE_BUCKET_NAME, filename, timedelta(minutes=1))
    return SmartOJResponse(
        ResponseCodes.OK, 
        data={
            "url": signature_url, 
            "filename": filename,
            "filepath": filepath
        }
    )


@router.post("", summary="发布题解")
async def create_solution(
    user: CurrentUserDependency,
    solution_service: SolutionServiceDependency,
    submit_record_service: SubmitRecordDependency,
    solution: CreateSolution
):
    """
    ## 参数列表说明:
    **content**: 题解内容；必须；请求体 </br>
    **title**: 题解标题；必须；请求体 </br>
    **question_id**: 题目的ID；必须；请求体
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    **700**: 每个用户只能对一道题目创建一个题解 </br>
    **710**: 只有通过一次提交才可以编写题解
    """
    old_solution = await solution_service.query_by_user_and_question_id(user["id"], solution.question_id)
    if old_solution is not None:
        return SmartOJResponse(ResponseCodes.SOLUTION_ALREADY_EXISTS)
    submit_records = await submit_record_service.query_by_user_and_question_id(user["id"], solution.question_id)
    is_passed = False
    for submit_record in submit_records:
        if submit_record.type == "submit" and submit_record.pass_test_quantity == submit_record.total_test_quantity:
            is_passed = True
            break
    if not is_passed:
        return SmartOJResponse(ResponseCodes.NOT_PASSED_ALL_TESTS)
    await solution_service.create(user["id"], **solution.model_dump())
    return SmartOJResponse(ResponseCodes.OK)


@router.put("", summary="修改题解")
async def update_solution(
    user: CurrentUserDependency,
    service: SolutionServiceDependency,
    solution: UpdateSolution
):
    """
    ## 参数列表说明:
    **content**: 题解内容；必须；请求体 </br>
    **title**: 题解标题；必须；请求体 </br>
    **solution_id**: 题解的ID；必须；请求体
    ## 响应代码说明:
    **200**: 业务逻辑执行成功
    """
    await service.update(user_id=user["id"], **solution.model_dump(exclude=("question_id",)))
    return SmartOJResponse(ResponseCodes.OK)


@router.delete("", summary="逻辑删除题解")
async def delete_solution(
    user: CurrentUserDependency,
    service: SolutionServiceDependency,
    solution_id: int = Body(ge=1, embed=True)
):
    """
    ## 参数列表说明:
    **solution_id**: 题解的ID；必须；请求体
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    **705**: 题解删除失败
    """
    is_success = await service.logic_delete(solution_id, user["id"])
    if not is_success:
        return SmartOJResponse(ResponseCodes.SOLUTION_DELETE_FAILED)
    return SmartOJResponse(ResponseCodes.OK)


@router.get("/list", summary="获取题解列表")
async def get_solution_list(
    service: SolutionServiceDependency,
    question_id: int = Query(ge=1),
    cursor: str = Query(None),
    size: int = Query(5, ge=1)
):
    """
    ## 参数列表说明:
    **question_id**: 要获取的题解列表对应的题目ID；必须；查询参数 </br>
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
    solutions = await service.get_solution_list(question_id, last_created_at, size)
    for solution, content_preview in solutions:
        solution.content = content_preview
    has_more, next_cursor = False, None
    if len(solutions) == size:
        has_more = True
        last_solution, _ = solutions[-1]
        next_cursor = encode_cursor(last_solution.id, last_solution.created_at)
    results = [SolutionOut.model_validate(solution) for solution, _ in solutions]
    return SmartOJResponse(ResponseCodes.OK, data={"results": results, "has_more": has_more, "cursor": next_cursor})


@router.get("", summary="获取题解详情")
async def get_solution_detail(
    session_redis: SessionRedisDependency,
    request: Request,
    service: SolutionServiceDependency, 
    solution_id: int = Query(None, ge=1),
    question_id: int = Query(None, ge=1)
):
    """
    ## 参数列表说明:
    **solution_id**: 题解的ID；可选；查询参数 </br>
    **question_id**: 题目的ID；可选；查询参数
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    **255**: 请求的资源不存在
    """
    if not solution_id and not question_id:
        return SmartOJResponse(ResponseCodes.PARAMS_ERROR)
    if not solution_id:
        session_id = await cookie_scheme(request)
        user: dict = await get_current_user(session_id, session_redis)
        solution = await service.query_by_user_and_question_id(user["id"], question_id)
    else:
        solution = await service.query_by_primary_key(solution_id)
    if solution is None:
        return SmartOJResponse(ResponseCodes.NOT_FOUND)
    solution = SolutionOut.model_validate(solution)
    await service.increment_view_count(solution_id)
    return SmartOJResponse(ResponseCodes.OK, data=solution)
