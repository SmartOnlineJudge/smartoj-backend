import time
import json
import secrets
import asyncio

import user_agents
from fastapi import Request, Depends, HTTPException
from fastapi.security import APIKeyCookie
from redis.asyncio import Redis

import settings
from routes.user.models import UserModel
from storage.cache import get_session_redis, CachePrefix


SESSION_PREFIX = CachePrefix.SESSION_PREFIX
USER_PREFIX = CachePrefix.USER_PREFIX
SESSION_MAX_AGE = settings.SESSION_MAX_AGE
cookie_scheme = APIKeyCookie(name="session_id", auto_error=False)


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


def parse_user_agent(raw_user_agent: str):
    user_agent = user_agents.parse(raw_user_agent)
    return {
        "browser": user_agent.browser.family,
        "platform": user_agent.os.family,
    }


async def login(request: Request, user: dict) -> str:
    session_redis = get_session_redis()
    user_id = user["user_id"]
    # 更新 / 设置 Redis 中的用户信息
    user_str_name = USER_PREFIX + user_id
    session_version = 1
    user_str = await session_redis.get(user_str_name)
    if not user_str:  # 如果用户信息不在 Redis 中，则设置用户信息
        user_model = UserModel(**user)
        user_dict = user_model.model_dump()
        user_dict["session_version"] = session_version  # 初始化 Session 版本号
        user_str = json.dumps(user_dict)
    else:  # 如果用户信息在 Redis 中，则更新用户信息的过期时间
        user_dict = json.loads(user_str)
        session_version = user_dict["session_version"]  # 获取最新的 Session 版本号
        user_str = json.dumps(user_dict)
    task1 = session_redis.set(user_str_name, user_str, ex=SESSION_MAX_AGE)
    # 解析用户代理信息
    user_agent = parse_user_agent(request.headers.get("user-agent", ""))
    # 设置 Redis 中的 Session 信息
    session = {
        "user_id": user_id,
        "host": request.headers.get("X-Forwarded-For", "UnKnown"),
        "platform": user_agent["platform"],
        "browser": user_agent["browser"],
        "last_active": int(time.time()),  # 上次活跃时间
        "first_login": int(time.time()),  # 首次登录时间
        "session_version": session_version,
    }
    session_str = json.dumps(session)
    session_id = await generate_session_id(session_redis)
    task2 = session_redis.set(SESSION_PREFIX + session_id, session_str, ex=SESSION_MAX_AGE)
    await asyncio.gather(task1, task2)
    return session_id


async def logout(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id:
        return
    session_redis = get_session_redis()
    await session_redis.delete(SESSION_PREFIX + session_id)


async def get_current_user(
    session_id: str = Depends(cookie_scheme),
    session_redis: Redis = Depends(get_session_redis),
) -> dict | None:
    if not session_id:
        raise HTTPException(status_code=401, detail="未登录")
    session_name = SESSION_PREFIX + session_id
    session_str = await session_redis.get(session_name)
    if not session_str:
        raise HTTPException(status_code=401, detail="未登录")
    session = json.loads(session_str)
    # 获取用户信息
    user_str = await session_redis.get(USER_PREFIX + session["user_id"])
    user: dict = json.loads(user_str)
    # 判断用户是否被禁用
    if user["is_deleted"]:
        await session_redis.delete(session_name)
        raise HTTPException(status_code=401, detail="当前账号已被禁用，请联系管理员")
    # 对比 Session 版本号
    if session["session_version"] != user["session_version"]:
        await session_redis.delete(session_name)
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    # 更新活跃时间
    session["last_active"] = int(time.time())
    session_str = json.dumps(session)
    ex = await session_redis.ttl(session_name)
    await session_redis.set(session_name, session_str, ex=ex)
    return user


async def get_current_admin(user: dict = Depends(get_current_user)) -> dict | None:
    if not user["is_superuser"]:
        raise HTTPException(status_code=403, detail="当前账号权限不足")
    return user
