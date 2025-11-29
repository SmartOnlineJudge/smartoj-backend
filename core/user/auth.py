import json

import httpx
from httpx_socks import AsyncProxyTransport
from pydantic import EmailStr

import settings
from storage.mysql import create_user_and_dynamic, UserService
from storage.mysql.user.models import User
from storage.cache import get_session_redis, CachePrefix
from storage.oss import async_upload_avatar
from routes.user.models import AuthType, UserOutModel
from .security import password_hash
from utils.generic import parse_proxy_url


def require_user_service(authenticate_method):
    async def wrapper(*args, **kwargs):
        authenticator: "Authenticator" = args[0]
        async with UserService() as service:
            authenticator.service = service
            user = await authenticate_method(*args, **kwargs)
        return user
    return wrapper


class Authenticator:
    def __init__(self):
        self.service: UserService = None

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.authenticate = require_user_service(cls.authenticate)

    async def authenticate(self, **kwargs) -> User | None:
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
            return None
        user = await self.service.query_by_index("email", email)
        if not user:
            return None
        if password_hash(password, settings.SECRETS["PASSWORD"]) == user.password:
            return user
        return None


class EmailAuthenticator(Authenticator):
    async def authenticate(self, *, email: str, verification_code: str, **kwargs):
        session_redis = get_session_redis()
        cache_name = CachePrefix.VERIFICATION_CODE_PREFIX + email
        cache_content = await session_redis.get(cache_name)
        if not cache_content:
            return None
        content = json.loads(cache_content)
        if verification_code != content["code"]:
            return None
        return await self.service.query_by_index("email", email)


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
        async with AsyncProxyTransport(**proxy_conf) as transport:
            async with httpx.AsyncClient(transport=transport) as client:
                response = await client.post(self.get_access_token_url, params=params, headers=headers)
                json_data = response.json()
                if "access_token" not in json_data:
                    return None
                access_token = json_data['access_token']
                headers['Authorization'] = f"token {access_token}"
                response = await client.get(self.get_user_info_url, headers=headers)
                github_user = response.json()
                github_user['id'] = str(github_user['id'])
                user = await self.service.query_by_index("github_token", github_user['id'])
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
                user = await self.service.query_by_index("email", github_user['email'])
                # 数据库中已经有当前邮箱对应的用户，更新当前用户的 GitHub Token，然后返回当前用户信息
                if user:
                    await self.service.update(user.user_id, {"github_token": github_user['id']})
                    user.github_token = github_user['id']
                    return user
                # 下载用户头像并上传到 MinIO 服务器
                response = await client.get(github_user['avatar_url'])
                file_type = response.headers.get('content-type').split('/')[-1]
                hole_avatar = await async_upload_avatar(response.content, file_type)
        # 创建新用户
        await create_user_and_dynamic(
            name=github_user['name'],
            github_token=github_user['id'],
            email=github_user['email'],
            profile=github_user['bio'] or '',
            avatar=hole_avatar,
        )
        user = await self.service.query_by_index("github_token", github_user['id'])
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
    user = await authenticator.authenticate(
        email=email,
        password=password,
        auth_type=auth_type,
        code=code,
        verification_code=verification_code,
    )
    if not user:
        return {}
    user = UserOutModel.model_validate(user)
    user_dict = user.model_dump()
    user_dynamic = user_dict.pop("user_dynamic")
    user_dict.update(user_dynamic)
    return user_dict
