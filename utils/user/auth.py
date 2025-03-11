import time
import json
import secrets
import asyncio

from redis.asyncio import Redis
from fastapi import Depends, HTTPException
from fastapi.requests import Request
from pydantic import EmailStr

import settings
from storage.mysql import executors
from storage.cache import get_session_redis, CachePrefix
from routes.user.models import UserOutModel
from .security import password_hash


SESSION_PREFIX = CachePrefix.SESSION_PREFIX
USER_PREFIX = CachePrefix.USER_PREFIX


async def _password_auth(email: str, password: str, **_) -> dict:
    if not email or not password:
        return {}
    user = await executors.user.get_user_by_email(email)
    if not user:
        return {}
    if password_hash(password, settings.SECRETS["PASSWORD"]) == user["password"]:
        return user
    return {}


async def _email_auth(email: str, **_):
    pass


async def _github_auth(github_token: str, **_):
    pass


async def _qq_auth(qq_token: str, **_):
    pass


auth_functions = {
    "password": _password_auth,
    "email": _email_auth,
    "github": _github_auth,
    "qq": _qq_auth,
}


async def generate_session_id(session_redis: Redis) -> str:
    """
    生成全局唯一 Session ID
    """
    while True:
        session_id = secrets.token_hex(16)
        session_name = SESSION_PREFIX + session_id
        if not await session_redis.exists(session_name):
            break
    return session_id


async def authenticate(
    email: str | EmailStr = "",
    password: str = "",
    github_token: str = "",
    qq_token: str = "",
    auth_type: str = "",
) -> dict:
    if auth_type not in auth_functions:
        return {}
    auth_function = auth_functions[auth_type]
    return await auth_function(
        email=email, password=password, github_token=github_token, qq_token=qq_token
    )


async def login(request: Request, user: dict) -> str:
    session_redis = get_session_redis()
    # 更新 / 设置 Redis 中的用户信息
    user_str_name = USER_PREFIX + user["user_id"]
    user_str_exists = await session_redis.exists(user_str_name)
    if not user_str_exists:  # 如果用户信息不在 Redis 中，则设置用户信息
        user_model = UserOutModel(**user)
        user_str = json.dumps(user_model.model_dump())
        task1 = session_redis.set(user_str_name, user_str, ex=settings.SESSION_MAX_AGE)
    else:  # 如果用户信息在 Redis 中，则更新用户信息的过期时间
        task1 = session_redis.expire(user_str_name, time=settings.SESSION_MAX_AGE)
    # 设置 Redis 中的 Session 信息
    session = {
        "user_id": user["user_id"],
        "ip": request.client.host,
        "platform": request.headers.get("sec-ch-ua-platform", ""),
        "last_active": int(time.time()),  # 上次活跃时间
    }
    session_str = json.dumps(session)
    session_id = await generate_session_id(session_redis)
    task2 = session_redis.set(SESSION_PREFIX + session_id, session_str, ex=settings.SESSION_MAX_AGE)
    await asyncio.gather(task1, task2)
    return session_id


async def logout(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id:
        return
    session_redis = get_session_redis()
    await session_redis.delete(SESSION_PREFIX + session_id)


async def get_current_user(
    request: Request,
    session_redis: Redis = Depends(get_session_redis),
) -> dict | None:
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="未登录")
    session_name = SESSION_PREFIX + session_id
    session_str = await session_redis.get(session_name)
    if not session_str:
        raise HTTPException(status_code=401, detail="未登录")
    session = json.loads(session_str)
    # 更新活跃时间
    session["last_active"] = int(time.time())
    session_str = json.dumps(session)
    ex = await session_redis.ttl(session_name)
    await session_redis.set(session_name, session_str, ex=ex)
    # 获取用户信息
    user_str = await session_redis.get(USER_PREFIX + session["user_id"])
    return json.loads(user_str)


async def get_current_admin(user: dict = Depends(get_current_user)) -> dict | None:
    if not user["is_superuser"]:
        raise HTTPException(status_code=403, detail="当前账号权限不足")
    return user
