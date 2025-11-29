from sqlalchemy.ext.asyncio import (
    create_async_engine as _create_async_engine,
    AsyncEngine
)

import settings


def create_async_engine(url: str = None, **kwargs) -> AsyncEngine:
    if url is None:
        _MYSQL_CONF = settings.MYSQL_CONF
        _user = _MYSQL_CONF["USER"]
        _password = _MYSQL_CONF["PASSWORD"]
        _host = _MYSQL_CONF["HOST"]
        _port = _MYSQL_CONF["PORT"]
        _database = _MYSQL_CONF["NAME"]
        url = f"mysql+aiomysql://{_user}:{_password}@{_host}:{_port}/{_database}"
    if "echo" not in kwargs:
        kwargs["echo"] = settings.DEV_ENV
    return _create_async_engine(url, **kwargs)


engine = create_async_engine(
    pool_recycle=60, 
    isolation_level="READ COMMITTED"  # 修改 MySQL 的事务隔离级别为“读已提交”
)
