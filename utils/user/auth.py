import json
import secrets

from redis.asyncio import Redis
from fastapi import Depends, HTTPException
from fastapi.requests import Request
from pydantic import EmailStr

import settings
from storage.mysql import executors
from storage.cache import get_session_redis
from routes.user.models import UserOutModel
from .security import password_hash


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


async def login(user: dict) -> str:
    session_redis = get_session_redis()
    user_model = UserOutModel(**user)
    user_str = json.dumps(user_model.model_dump())
    while True:
        session_id = secrets.token_hex(16)
        if not await session_redis.exists(session_id):
            await session_redis.set(session_id, user_str, ex=settings.SESSION_MAX_AGE)
            return session_id


async def logout(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id:
        return
    session_redis = get_session_redis()
    await session_redis.delete(session_id)


async def get_current_user(
    request: Request,
    session_redis: Redis = Depends(get_session_redis),
) -> dict | None:
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="未登录")
    user_str = await session_redis.get(session_id)
    if not user_str:
        raise HTTPException(status_code=401, detail="未登录")
    return json.loads(user_str)


async def get_current_admin(user: dict = Depends(get_current_user)) -> dict | None:
    if not user["is_superuser"]:
        raise HTTPException(status_code=403, detail="当前账号权限不足")
    return user
