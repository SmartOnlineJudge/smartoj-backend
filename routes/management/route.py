import json
import asyncio

from fastapi import APIRouter, Depends, Body, Query
from fastapi.requests import Request

import settings
from ..user.models import LoginModel, UserListModel
from ..user.route import user_logout
from utils.user.auth import authenticate, login, get_current_admin, USER_PREFIX
from utils.user.security import mask
from utils.responses import SmartOJResponse, ResponseCodes
from storage.cache import get_session_redis, Redis
from storage.mysql import executors

router = APIRouter()


@router.post("/user/login", summary="管理员登录")
async def admin_login(request: Request, form: LoginModel):
    """
    ## 参数列表说明:
    **email**: 管理员邮箱号；必须；请求体 </br>
    **password**: 管理员密码；必须；请求体 </br>
    **auth_type**: 用户认证的类型（这里必须填 "password"）；必须；请求体 </br>
    **github_token**: 可选 </br>
    **qq_token**: 可选
    ## 响应代码说明:
    **300**: 登录成功 </br>
    **305**: 账号登录失败，可能是邮箱或密码不正确 </br>
    **310**: 账号登录失败，当前账号权限不足
    """
    user: dict | None = await authenticate(
        email=form.email,
        password=form.password,
        auth_type=form.auth_type.value,
    )
    if not user:
        return SmartOJResponse(ResponseCodes.LOGIN_FAILED)
    if not user["is_superuser"]:
        return SmartOJResponse(ResponseCodes.PERMISSION_DENIED)
    session_id = await login(request, user)
    response = SmartOJResponse(ResponseCodes.LOGIN_SUCCESS)
    response.set_cookie(
        key="session_id",
        value=session_id,
        max_age=settings.SESSION_MAX_AGE,
        httponly=True,
    )
    return response


@router.post("/user/logout", summary="管理员退出登录")
async def admin_logout(request: Request):
    return await user_logout(request)


@router.get("/user", summary="获取当前管理员信息")
async def get_admin_user(admin: dict = Depends(get_current_admin)):
    return SmartOJResponse(ResponseCodes.OK, data=mask(admin))


@router.put("/user", summary="修改管理员信息")
async def update_admin_user(
        name: str = Body(max_length=20),
        profile: str = Body(max_length=255),
        admin: dict = Depends(get_current_admin),
        session_redis: Redis = Depends(get_session_redis),
):
    """
    ## 参数列表说明:
    **name**: 管理员名字（最大长度不超过20）；必须；请求体 </br>
    **profile**: 管理员介绍（最大长度不超过255）；必须；请求体
    ## 响应代码说明:
    **200**: 业务逻辑执行成功
    """

    async def update_db():
        """更新数据库"""
        await executors.user_dynamic.update_user_dynamic(
            user_id=admin["user_id"],
            name=name,
            profile=profile,
        )

    async def update_cache():
        """更新缓存"""
        user_str_id = USER_PREFIX + admin["user_id"]
        user_str = await session_redis.get(user_str_id)
        user_dict = json.loads(user_str)
        user_dict["name"] = name
        user_dict["profile"] = profile
        ex = await session_redis.ttl(user_str_id)
        await session_redis.set(user_str_id, json.dumps(user_dict), ex)

    tasks = [update_db(), update_cache()]
    await asyncio.gather(*tasks)
    return SmartOJResponse(ResponseCodes.OK)


@router.get("/users", summary="分页获取用户信息")
async def get_user_data(
        _: dict = Depends(get_current_admin),
        page: int = Query(1, ge=1),
        size: int = Query(5, ge=1)
):
    users, total = await executors.user.get_page_user_data(page, size)
    results = []
    for user in users:
        model = UserListModel(**user)
        results.append(mask(model.model_dump()))
    return SmartOJResponse(ResponseCodes.OK, data={"total": total, "results": results})
