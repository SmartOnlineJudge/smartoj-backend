import re
import io
import json
import asyncio
import random
import time

import filetype
from minio import Minio
from minio.error import MinioException
from pydantic import EmailStr
from fastapi import APIRouter, UploadFile, Depends, Body
from fastapi.requests import Request

from .models import VerificationCodeType
from utils.user.auth import logout, get_current_user, USER_PREFIX
from utils.user.security import mask
from utils.responses import SmartOJResponse, ResponseCodes
from storage.oss import get_minio_client, MAX_AVATAR_SIZE, AVATAR_BUCKET_NAME
from storage.mysql import executors
from storage.cache import get_session_redis, Redis, CachePrefix
from mq.broker import send_email_task

router = APIRouter()
VERIFICATION_CODE_PREFIX = CachePrefix.VERIFICATION_CODE_PREFIX


@router.get("/", summary="获取当前用户信息")
def get_user(user: dict = Depends(get_current_user)):
    return SmartOJResponse(ResponseCodes.OK, data=mask(user))


@router.post("/logout", summary="用户退出登录")
async def user_logout(request: Request):
    await logout(request)
    response = SmartOJResponse(ResponseCodes.OK)
    response.delete_cookie("session_id", httponly=True)
    return response


@router.post("/avatar", summary="用户上传头像")
async def upload_user_avatar(
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
        user_str_id = USER_PREFIX + user["user_id"]
        user_str = await session_redis.get(user_str_id)
        user_dict = json.loads(user_str)
        user_dict["avatar"] = hole_avatar
        ex = await session_redis.ttl(user_str_id)
        await session_redis.set(
            user_str_id, json.dumps(user_dict), ex
        )  # 注意使用原来的过期时间

    tasks = [update_db(), update_cache()]
    await asyncio.gather(*tasks)

    return SmartOJResponse(ResponseCodes.OK)


@router.post("/verification-code", summary="发送验证码")
async def send_verification_code(
        request: Request,
        verification_code_type: VerificationCodeType = Body(embed=True),
        recipient: EmailStr = Body("test@smartoj.com", embed=True),
        session_redis: Redis = Depends(get_session_redis),
):
    """
    ## 参数列表说明:
    **verification_code_type**: 要发送的验证码类型 `register`、`login`、`change_password`、`change_email`；必须；请求体 </br>
    **recipient**: 目标邮箱；当验证码类型是 `login` 和 `register` 时必须；请求体
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    **235**: 邮箱不能为空 </br>
    **240**: 请求过于频繁
    """
    verification_code = "".join(random.choices("0123456789", k=6))
    content = f"您的验证码是：{verification_code}，该验证码 5 分钟内有效，请勿泄露给他人，若非本人操作请忽略本邮件。"

    if verification_code_type.value in ("login", "register"):
        real_recipient = str(recipient)
    else:
        user: dict = await get_current_user(request, session_redis)
        real_recipient = user["email"]

    if not real_recipient:
        return SmartOJResponse(ResponseCodes.EMAIL_NOT_ALLOW_NULL)

    cache_name = (
            CachePrefix.VERIFICATION_CODE_PREFIX
            + real_recipient
            + "-"
            + verification_code_type.value
    )
    cache_content = await session_redis.get(cache_name)
    if cache_content and (int(time.time()) - json.loads(cache_content)["created"] < 60):
        return SmartOJResponse(ResponseCodes.REQUEST_FREQUENTLY)

    cache_content = json.dumps(
        {
            "code": verification_code,
            "created": int(time.time()),
        }
    )
    await session_redis.set(cache_name, cache_content, ex=60 * 5)

    await send_email_task.kiq(real_recipient, "你的一次性代码", content)

    return SmartOJResponse(ResponseCodes.OK)


async def get_verification_dict(
        user: dict,
        session_redis: Redis,
) -> dict:
    verification = VERIFICATION_CODE_PREFIX + user["email"] + "-change_email"
    verification_str = await session_redis.get(verification)
    if not verification_str:
        return {}
    verification_dict = json.loads(verification_str)
    return verification_dict


@router.post("/verification", summary="验证码验证")
async def verify_verification(
        vfcode: str = Body(max_length=32),
        user: dict = Depends(get_current_user),
        session_redis: Redis = Depends(get_session_redis),
):
    """
    ## 参数列表说明:
    **vfcode**: 用户输入的验证码；必须；请求体 </br>
    ## 响应代码说明:
    **200**: 业务逻辑执行成功</br>
    **250**: 验证码输入错误或已过期
    """
    verification_dict = await get_verification_dict(user, session_redis)
    if not verification_dict:
        return SmartOJResponse(ResponseCodes.CAPTCHA_INVALID)
    if vfcode != verification_dict["code"]:
        return SmartOJResponse(ResponseCodes.CAPTCHA_INVALID)
    return SmartOJResponse(ResponseCodes.OK)


@router.patch("/password", summary="用户修改密码")
async def update_password(
        vfcode_c: str = Body(max_length=32),
        user: dict = Depends(get_current_user),
        new_password: str = Body(max_length=32),
        session_redis: Redis = Depends(get_session_redis),
):
    """
    ## 参数列表说明:
    **new_password**: 用户改的新密码；必须；请求体 </br>
    **vfcode_c**: 客户端输入验证码；必须；请求体 </br>
    ## 响应代码说明:
    **200**: 业务逻辑执行成功</br>
    **250**: 验证码输入错误或已过期
    """
    response = await verify_verification(
        vfcode=vfcode_c,
        user=user,
        session_redis=session_redis,
    )
    if response.code != 200:
        return response

    async def update_db():
        await executors.user.update_user_password(
            user_id=user["user_id"],
            password=new_password
        )

    async def update_cache():
        user_str_id = USER_PREFIX + user["user_id"]
        user_str = await session_redis.get(user_str_id)
        user_dict = json.loads(user_str)
        user_dict["session_version"] += 1
        ex = await session_redis.ttl(user_str_id)
        await session_redis.set(user_str_id, json.dumps(user_dict), ex)

    tasks = [update_db(), update_cache()]
    await asyncio.gather(*tasks)
    return SmartOJResponse(ResponseCodes.OK)
