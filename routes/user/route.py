import re
import io
import json
import asyncio

import filetype
from minio import Minio
from minio.error import MinioException
from fastapi import APIRouter, UploadFile, Depends
from fastapi.requests import Request

from utils.user.auth import logout, get_current_user
from utils.responses import SmartOJResponse, ResponseCodes
from storage.oss import get_minio_client, MAX_AVATAR_SIZE, AVATAR_BUCKET_NAME
from storage.mysql import executors
from storage.cache import get_session_redis, Redis


router = APIRouter()


@router.post("/logout", summary="用户退出登录")
async def user_logout(request: Request):
    await logout(request)
    response = SmartOJResponse(ResponseCodes.OK)
    response.delete_cookie("session_id", httponly=True)
    return response


@router.post("/avatar", summary="用户上传头像")
async def upload_user_avatar(
    request: Request,
    avatar: UploadFile,
    user: dict = Depends(get_current_user),
    minio_client: Minio = Depends(get_minio_client),
    session_redis: Redis = Depends(get_session_redis),
):
    """
    ## 参数列表说明:
    **avatar**: 上传的头像；必须；表单
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    **210**: 文件过大，上传失败 </br>
    **220**: 文件类型不允许 </br>
    **230**: 文件上传异常
    """

    # 检查文件大小
    if avatar.size > MAX_AVATAR_SIZE:
        return SmartOJResponse(ResponseCodes.FILE_TOO_LARGE)
    # 初步检查文件类型
    if not re.match(r"^.*\.(jpg|jpeg|png|svg|webp|gif)$", avatar.filename.lower()):
        return SmartOJResponse(ResponseCodes.FILE_TYPE_NOT_ALLOWED)
    content = await avatar.read()
    # 根据文件内容检查文件类型
    try:
        is_image = filetype.is_image(content)
    except TypeError:
        return SmartOJResponse(ResponseCodes.FILE_TYPE_NOT_ALLOWED)
    if is_image is None:
        return SmartOJResponse(ResponseCodes.FILE_TYPE_NOT_ALLOWED)
    # 根据文件内容检查文件大小
    if len(content) > MAX_AVATAR_SIZE:
        return SmartOJResponse(ResponseCodes.FILE_TOO_LARGE)

    file_type = avatar.filename.rsplit(".", 1)[-1]
    object_name = f"{user['user_id']}.{file_type}"

    try:
        minio_client.put_object(
            AVATAR_BUCKET_NAME,
            object_name,
            io.BytesIO(content),
            len(content),
        )
    except MinioException:
        return SmartOJResponse(ResponseCodes.FILE_UPLOAD_ERROR)

    hole_avatar = f"/{AVATAR_BUCKET_NAME}/{object_name}"

    async def update_db():
        """更新数据库"""
        await executors.user_dynamic.update_user_avatar(user["user_id"], hole_avatar)

    async def update_cache():
        """更新缓存"""
        session_id = request.cookies.get("session_id")
        user_str = await session_redis.get(session_id)
        user_dict = json.loads(user_str)
        user_dict["avatar"] = hole_avatar
        ex = await session_redis.ttl(session_id)
        await session_redis.set(
            session_id, json.dumps(user_dict), ex
        )  # 注意使用原来的过期时间

    tasks = [update_db(), update_cache()]
    await asyncio.gather(*tasks)

    return SmartOJResponse(ResponseCodes.OK)
