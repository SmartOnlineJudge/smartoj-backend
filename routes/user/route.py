import re
import json
import asyncio
import random
import time
from datetime import datetime
from collections import defaultdict

import filetype
from fastapi import APIRouter, UploadFile, Body, Query
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from pydantic import EmailStr

import settings
from .models import LoginModel, RegisterModel
from core.user.session import (
    logout,
    get_current_user,
    USER_PREFIX,
    cookie_scheme,
    login
)
from core.user.auth import authenticate
from core.user.security import mask, password_hash
from utils.responses import SmartOJResponse, ResponseCodes
from utils.dependencies import (
    CurrentUserDependency,
    SessionRedisDependency,
    MinioClientDependency,
    UserDynamicServiceDependency,
    UserServiceDependency,
    SubmitRecordDependency
)
from storage.oss import MAX_AVATAR_SIZE, async_upload_avatar
from storage.mysql import create_user_and_dynamic
from storage.cache import CachePrefix, update_session_version
from mq.broker import send_email_task

router = APIRouter()
VERIFICATION_CODE_PREFIX = CachePrefix.VERIFICATION_CODE_PREFIX


@router.get("", summary="获取当前用户信息")
def get_user(user: CurrentUserDependency):
    return SmartOJResponse(ResponseCodes.OK, data=mask(user))


@router.post("/register", summary="用户注册")
async def user_register(
        request: Request,
        model: RegisterModel,
        session_redis: SessionRedisDependency,
        service: UserServiceDependency
):
    """
    ## 参数列表说明:
    **name**: 新用户名字；必须；表单 </br>
    **password1**: 密码1；必须；表单 </br>
    **password2**: 密码2；必须；表单 </br>
    **email**: 新用户邮箱；必须；表单 </br>
    **verification_code**: 邮箱验证码；必须；表单
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    **250**: 验证码输入错误或已过期 </br>
    **400**: 两次密码输入不一致 </br>
    **410**: 当前邮箱已被注册
    """
    if model.password1 != model.password2:
        return SmartOJResponse(ResponseCodes.TWICE_PASSWORD_NOT_MATCH)
    email = str(model.email)
    user = await service.query_by_index("email", email)
    if user:
        return SmartOJResponse(ResponseCodes.EMAIL_ALREADY_EXISTS)
    # 校验验证码
    response = await check_verification_code(
        request,
        model.verification_code,
        email,
        session_redis,
    )
    if response.code != 200:
        return response
    # 创建用户
    await create_user_and_dynamic(
        name=model.name,
        password=model.password1,
        email=email,
    )
    return SmartOJResponse(ResponseCodes.OK)


@router.post("/login", summary="用户登录")
async def user_login(request: Request, model: LoginModel):
    """
    ## 参数列表说明:
    **email**: 邮箱；验证码登录和邮箱登录时必须；表单 </br>
    **password**: 密码；密码登录时必须；表单 </br>
    **code**: 第三方平台授权后的代码；使用 OAuth2 登录时必须；表单 </br>
    **verification_code**: 邮箱验证码；验证码登录时必须；表单 </br>
    **auth_type**: 登录的类型（password、github、qq、email）；必须；表单
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    **305**: 登录失败
    """
    user = await authenticate(**model.model_dump())
    if not user:
        return SmartOJResponse(ResponseCodes.LOGIN_FAILED)
    session_id = await login(request, user)
    response_data = SmartOJResponse(ResponseCodes.LOGIN_SUCCESS)
    response = JSONResponse(response_data.model_dump())
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        max_age=settings.SESSION_MAX_AGE
    )
    return response


@router.post("/logout", summary="用户退出登录")
async def user_logout(request: Request):
    await logout(request)
    response_data = SmartOJResponse(ResponseCodes.OK)
    response = JSONResponse(response_data.model_dump())
    response.delete_cookie("session_id", httponly=True)
    return response


@router.post("/avatar", summary="用户上传头像")
async def upload_user_avatar(
        avatar: UploadFile,
        user: CurrentUserDependency,
        minio_client: MinioClientDependency,
        session_redis: SessionRedisDependency,
        service: UserDynamicServiceDependency
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
    
    hole_avatar = await async_upload_avatar(content, file_type, minio_client)
    if not hole_avatar:
        return SmartOJResponse(ResponseCodes.FILE_UPLOAD_ERROR)

    async def update_db():
        """更新数据库"""
        await service.update(user["user_id"], {'avatar': hole_avatar})

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
        session_redis: SessionRedisDependency,
        recipient: str = Body("", embed=True)
):
    """
    ## 参数列表说明:
    **recipient**: 收件邮箱；如果是一个空字符串，那么默认使用当前用户已绑定的邮箱；请求体
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    **235**: 邮箱不能为空 </br>
    **240**: 请求过于频繁
    """
    if not recipient:
        session_id = await cookie_scheme(request)
        user: dict = await get_current_user(session_id, session_redis)
        recipient = user["email"]

    if not recipient:
        return SmartOJResponse(ResponseCodes.EMAIL_NOT_ALLOW_NULL)

    cache_name = VERIFICATION_CODE_PREFIX + recipient
    cache_content = await session_redis.get(cache_name)
    if cache_content and (int(time.time()) - json.loads(cache_content)["created"] < 60):
        return SmartOJResponse(ResponseCodes.REQUEST_FREQUENTLY)

    verification_code = "".join(random.choices("0123456789", k=6))
    content = f"您的验证码是：{verification_code}，该验证码 5 分钟内有效，请勿泄露给他人，若非本人操作请忽略本邮件。"

    cache_content = json.dumps(
        {
            "code": verification_code,
            "created": int(time.time()),
        }
    )
    await session_redis.set(cache_name, cache_content, ex=60 * 5)

    await send_email_task.kiq(recipient, "你的一次性代码", content)

    return SmartOJResponse(ResponseCodes.OK)


@router.post("/check-verification-code", summary="校验验证码是否正确")
async def check_verification_code(
        request: Request,
        session_redis: SessionRedisDependency,
        vfcode: str = Body(pattern=r"^[0-9]{6}$"),
        email: str = Body("")
):
    """
    ## 参数列表说明:
    **vfcode**: 用户输入的验证码；必须；请求体 </br>
    **email**: 需要验证的邮箱；如果是一个空字符串，那么默认使用当前用户已绑定的邮箱；请求体
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    **250**: 验证码输入错误或已过期
    """
    if not email:
        session_id = await cookie_scheme(request)
        user: dict = await get_current_user(session_id, session_redis)
        email = user["email"]
    cache_name = VERIFICATION_CODE_PREFIX + email
    verification_str = await session_redis.get(cache_name)
    if not verification_str:
        return SmartOJResponse(ResponseCodes.CAPTCHA_INVALID)
    verification_dict = json.loads(verification_str)
    if vfcode != verification_dict["code"]:
        return SmartOJResponse(ResponseCodes.CAPTCHA_INVALID)
    return SmartOJResponse(ResponseCodes.OK)


@router.patch("/password", summary="用户修改密码")
async def update_password(
        request: Request,
        session_redis: SessionRedisDependency,
        user: CurrentUserDependency,
        service: UserServiceDependency,
        vfcode: str = Body(pattern=r"^[0-9]{6}$"),
        new_password: str = Body(max_length=32)
):
    """
    ## 参数列表说明:
    **new_password**: 用户改的新密码；必须；请求体 </br>
    **vfcode**: 客户端输入验证码；必须；请求体 </br>
    ## 响应代码说明:
    **200**: 业务逻辑执行成功 </br>
    **250**: 验证码输入错误或已过期
    """
    response = await check_verification_code(
        request,
        vfcode=vfcode,
        session_redis=session_redis,
        email=user["email"]
    )

    if response.code != 200:
        return response

    async def update_db():
        await service.update(
            user["user_id"],
            {'password': password_hash(new_password, settings.SECRETS["PASSWORD"])}
        )

    async def update_cache():
        await update_session_version(user["user_id"], session_redis)

    tasks = [update_db(), update_cache()]
    await asyncio.gather(*tasks)
    return SmartOJResponse(ResponseCodes.OK)


@router.patch("/email", summary="用户修改邮箱")
async def update_email(
        request: Request,
        user: CurrentUserDependency,
        session_redis: SessionRedisDependency,
        service: UserServiceDependency,
        vfcode: str = Body(pattern=r"^[0-9]{6}$"),
        new_email: EmailStr = Body("test@smartoj.com")
):
    """
    ## 参数列表说明:
    **new_email**: 用户改的新邮箱；必须；请求体 </br>
    **vfcode**: 用户输入的验证码；必须；请求体 </br>
    ## 响应代码说明:
    **200**: 业务逻辑执行成功</br>
    **250**: 验证码输入错误或已过期
    """
    new_email = str(new_email)
    response = await check_verification_code(
        request,
        vfcode=vfcode,
        session_redis=session_redis,
        email=new_email
    )
    if response.code != 200:
        return response

    async def update_db():
        await service.update(user["user_id"], {'email': new_email})

    async def update_cache():
        cache_name = CachePrefix.USER_PREFIX + user["user_id"]
        user_str = await session_redis.get(cache_name)
        if not user_str:
            return
        user_dict = json.loads(user_str)
        user_dict["session_version"] += 1
        user_dict["email"] = new_email
        ex = await session_redis.ttl(cache_name)
        await session_redis.set(cache_name, json.dumps(user_dict), ex=ex)

    tasks = [update_db(), update_cache()]
    await asyncio.gather(*tasks)
    return SmartOJResponse(ResponseCodes.OK)


@router.get("/passed-count-group-by-difficulty", summary="获取不同题目难度的提交通过数量")
async def get_count_group_by_difficulty(
    service: SubmitRecordDependency,
    user: CurrentUserDependency
):
    """
    ## 响应代码说明:
    **200**: 业务逻辑执行成功
    """
    results = await service.count_user_submissions_group_by_difficulty(user["id"])
    data = {"easy": 0, "medium": 0, "hard": 0}
    for difficulty, count in results:
        data[difficulty] = count
    return SmartOJResponse(ResponseCodes.OK, data=data)


@router.get("/solution-heatmap", summary="获取指定年份的刷题统计数据")
async def get_count_daily(
    service: SubmitRecordDependency,
    user: CurrentUserDependency,
    year: int = Query(datetime.now().year, ge=2022)
):
    """
    ## 参数列表说明:
    **year**: 获取数据的年份；可选，如果没有则默认为当前年份；查询参数
    ## 响应代码说明:
    **200**: 业务逻辑执行成功
    """
    results = await service.count_daily_submissions_in_year(user["id"], year)
    data = { row.submit_date.strftime("%Y-%m-%d"): row.submit_count for row in results }
    return SmartOJResponse(ResponseCodes.OK, data=data)


@router.get("/submit-records", summary="分页获取用户所有题目的提交记录")
async def get_submission_record(
    service: SubmitRecordDependency,
    user: CurrentUserDependency,
    page: int = Query(1, ge=1),
    size: int = Query(5, ge=1, le=100)
):
    """
    ## 参数列表说明:
    **page**: 查询的页码；必须；默认为1；查询参数 </br>
    **size**: 每页的数据数；必须；请求体；默认为5；查询参数
    ## 响应代码说明:
    **200**: 业务逻辑执行成功
    """
    total, submit_records, question_tags = await service.query_user_submits_with_question_info(user["id"], page, size)

    if total == 0:
        return SmartOJResponse(ResponseCodes.OK, data={"total": 0, "results": []})
    
    # 构建题目ID到标签列表的映射
    question_tag_map = defaultdict(list)
    for question_tag in question_tags:
        question_tag_map[question_tag.question_id].append(question_tag.tag.name)
    
    # 构造返回结果
    results = []
    for submit_record in submit_records:
        _submit_record, question = submit_record.SubmitRecord, submit_record.Question
        results.append({
            "question_id": question.id,
            "title": question.title,
            "difficulty": question.difficulty,
            "tags": question_tag_map.get(question.id, []),
            "created_at": _submit_record.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "is_passed": _submit_record.total_test_quantity == _submit_record.pass_test_quantity
        })

    return SmartOJResponse(ResponseCodes.OK, data={"total": total, "results": results})


@router.put("", summary="修改用户基本信息")
async def update_user_base_info(
    user: CurrentUserDependency,
    session_redis: SessionRedisDependency,
    service: UserDynamicServiceDependency,
    name: str = Body(max_length=20),
    profile: str = Body(max_length=255),
):
    """
    ## 参数列表说明:
    **name**: 用户名（最大长度不超过20）；必须；请求体 </br>
    **profile**: 用户介绍（最大长度不超过255）；必须；请求体
    ## 响应代码说明:
    **200**: 业务逻辑执行成功
    """

    async def update_db():
        """更新数据库"""
        await service.update(user["user_id"], {'name': name, 'profile': profile})

    async def update_cache():
        """更新缓存"""
        user_str_id = USER_PREFIX + user["user_id"]
        user_str = await session_redis.get(user_str_id)
        user_dict = json.loads(user_str)
        user_dict["name"] = name
        user_dict["profile"] = profile
        ex = await session_redis.ttl(user_str_id)
        await session_redis.set(user_str_id, json.dumps(user_dict), ex)

    tasks = [update_db(), update_cache()]
    await asyncio.gather(*tasks)
    return SmartOJResponse(ResponseCodes.OK)
