from redis.asyncio import Redis, ConnectionPool

import settings


class CachePrefix:
    SESSION_PREFIX = "smartoj-session:"  # 保存单个 Session 信息
    USER_PREFIX = "smartoj-user:"  # 保存用户信息
    VERIFICATION_CODE_PREFIX = "smartoj-verification-code:"  # 保存用户验证码信息


_default_connection_pool = ConnectionPool(
    max_connections=10,
    host=settings.REDIS_CONF["default"]["HOST"],
    port=settings.REDIS_CONF["default"]["PORT"],
    db=settings.REDIS_CONF["default"]["DB"],
    decode_responses=True,
    password=settings.REDIS_CONF["default"]["PASSWORD"]
)

_session_connection_pool = ConnectionPool(
    max_connections=10,
    host=settings.REDIS_CONF["session"]["HOST"],
    port=settings.REDIS_CONF["session"]["PORT"],
    db=settings.REDIS_CONF["session"]["DB"],
    decode_responses=True,
    password=settings.REDIS_CONF["session"]["PASSWORD"]
)


def get_default_redis():
    return Redis(connection_pool=_default_connection_pool)


def get_session_redis():
    return Redis(connection_pool=_session_connection_pool)
