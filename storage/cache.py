from redis.asyncio import Redis, ConnectionPool

import settings


_default_connection_pool = ConnectionPool(
    max_connections=10,
    host=settings.REDIS_CONF["default"]["HOST"],
    port=settings.REDIS_CONF["default"]["PORT"],
    db=settings.REDIS_CONF["default"]["DB"],
    decode_responses=True
)

_session_connection_pool = ConnectionPool(
    max_connections=10,
    host=settings.REDIS_CONF["session"]["HOST"],
    port=settings.REDIS_CONF["session"]["PORT"],
    db=settings.REDIS_CONF["session"]["DB"],
    decode_responses=True
)


def get_default_redis():
    return Redis(connection_pool=_default_connection_pool)


def get_session_redis():
    return Redis(connection_pool=_session_connection_pool)
