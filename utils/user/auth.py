import time
import json
import secrets
import asyncio

import httpx
from httpx_socks import AsyncProxyTransport
import user_agents
from redis.asyncio import Redis
from fastapi import Depends, HTTPException
from fastapi.requests import Request
from fastapi.security import APIKeyCookie
from pydantic import EmailStr

import settings
from storage.mysql import executors, create_user_and_dynamic
from storage.cache import get_session_redis, CachePrefix
from storage.oss import upload_avatar
from routes.user.models import UserOutModel, AuthType
from .security import password_hash
from utils.tools import parse_proxy_url


SESSION_PREFIX = CachePrefix.SESSION_PREFIX
USER_PREFIX = CachePrefix.USER_PREFIX
SESSION_MAX_AGE = settings.SESSION_MAX_AGE

cookie_scheme = APIKeyCookie(name="session_id", auto_error=False)


class Authenticator:
    async def authenticate(self, **kwargs) -> dict:
        ...


class OAuth2Authenticator(Authenticator):
    client_id: str = None
    client_secret: str = None
    get_access_token_url: str = None
    get_openid_url: str = None
    get_user_info_url: str = None

    async def authenticate(self, *, code: str, **kwargs):
        ...


class PasswordAuthenticator(Authenticator):
    async def authenticate(self, *, email: str, password: str, **kwargs):
        if not email or not password:
            return {}
        user = await executors.user.get_user_by_email(email)
        if not user:
            return {}
        if password_hash(password, settings.SECRETS["PASSWORD"]) == user["password"]:
            return user
        return {}


class EmailAuthenticator(Authenticator):
    async def authenticate(self, *, email: str, verification_code: str, **kwargs):
        session_redis = get_session_redis()
        cache_name = CachePrefix.VERIFICATION_CODE_PREFIX + email
        cache_content = await session_redis.get(cache_name)
        if not cache_content:
            return {}
        content = json.loads(cache_content)
        if verification_code != content["code"]:
            return {}
        return await executors.user.get_user_by_email(email)


class GithubOAuth2Authenticator(OAuth2Authenticator):
    client_id = settings.SECRETS["GITHUB_OAUTH2"]["client_id"]
    client_secret = settings.SECRETS["GITHUB_OAUTH2"]["client_secret"]
    get_access_token_url = 'https://github.com/login/oauth/access_token'
    get_user_info_url = 'https://api.github.com/user'
    get_user_email_url = 'https://api.github.com/user/emails'

    async def authenticate(self, *, code: str, **kwargs):
        params = {
            'client_id': self.client_id,
            "client_secret": self.client_secret,
            'code': code,
        }
        headers = {'Accept': 'application/json'}
        proxy_conf = parse_proxy_url(settings.PROXY_URL)
        user_executor = executors.user
        async with AsyncProxyTransport(**proxy_conf) as transport:
            async with httpx.AsyncClient(transport=transport) as client:
                response = await client.post(self.get_access_token_url, params=params, headers=headers)
                json_data = response.json()
                if "access_token" not in json_data:
                    return {}
                access_token = json_data['access_token']
                headers['Authorization'] = f"token {access_token}"
                response = await client.get(self.get_user_info_url, headers=headers)
                github_user = response.json()
                github_user['id'] = str(github_user['id'])
                user = await user_executor.get_user_by_github_token(github_user['id'])
                # 数据库中已经有该用户，直接返回用户信息
                if user:
                    return user
                # 获取新用户的邮箱
                if not github_user['email']:
                    response = await client.get(self.get_user_email_url, headers=headers)
                    emails = response.json()
                    for email in emails:
                        if email['primary']:
                            github_user['email'] = email['email']
                            break
                user = await user_executor.get_user_by_email(github_user['email'])
                # 数据库中已经有当前邮箱对应的用户，更新当前用户的 GitHub Token，然后返回当前用户信息
                if user:
                    await user_executor.update_user_github_token(user['user_id'], github_user['id'])
                    user['github_token'] = github_user['id']
                    return user
                # 下载用户头像并上传到 MinIO 服务器
                response = await client.get(github_user['avatar_url'])
                file_type = response.headers.get('content-type').split('/')[-1]
                hole_avatar = upload_avatar(response.content, file_type)
        # 创建新用户
        await create_user_and_dynamic(
            name=github_user['name'],
            github_token=github_user['id'],
            email=github_user['email'],
            profile=github_user['bio'] or '',
            avatar=hole_avatar,
        )
        user = await user_executor.get_user_by_github_token(github_user['id'])
        return user


class QQOAuth2Authenticator(OAuth2Authenticator):
    pass


class AuthenticatorFactory:
    authenticator_types = {
        AuthType.EMAIL.value: EmailAuthenticator,
        AuthType.PASSWORD.value: PasswordAuthenticator,
        AuthType.GITHUB.value: GithubOAuth2Authenticator,
        AuthType.QQ.value: QQOAuth2Authenticator
    }

    @classmethod
    def get_authenticator(cls, auth_type: str) -> Authenticator:
        authenticator_class = cls.authenticator_types[auth_type]
        return authenticator_class()


async def authenticate(
    *,
    email: str | EmailStr = "",
    password: str = "",
    auth_type: str | AuthType = "",
    code: str = "",
    verification_code: str = "",
) -> dict:
    """用户多方式登录认证函数 """
    if isinstance(auth_type, AuthType):
        auth_type = auth_type.value
    authenticator = AuthenticatorFactory.get_authenticator(auth_type)
    return await authenticator.authenticate(
        email=email,
        password=password,
        auth_type=auth_type,
        code=code,
        verification_code=verification_code,
    )


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
        user_model = UserOutModel(**user)
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
