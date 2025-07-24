import traceback
from typing import AsyncGenerator, Any
from contextlib import asynccontextmanager

import aiomysql
from sqlalchemy.ext.asyncio import (
    create_async_engine as _create_async_engine,
    AsyncEngine
)
from sqlmodel.ext.asyncio.session import AsyncSession

import settings


class MySQLExecutor:
    """
    MySQL 执行器基类
    """

    _pool: aiomysql.Pool = None

    @classmethod
    async def initialize_connection_pool(cls):
        if MySQLExecutor._pool is None:
            MySQLExecutor._pool = await aiomysql.create_pool(
                host=settings.MYSQL_CONF["HOST"],
                user=settings.MYSQL_CONF["USER"],
                password=settings.MYSQL_CONF["PASSWORD"],
                db=settings.MYSQL_CONF["NAME"],
                cursorclass=aiomysql.DictCursor,
                pool_recycle=60,
                init_command="SET SESSION transaction_isolation='READ-COMMITTED'"
            )

    @asynccontextmanager
    async def connection(self) -> AsyncGenerator:
        await self.initialize_connection_pool()
        async with self._pool.acquire() as conn:
            yield conn

    async def cursor(self) -> aiomysql.DictCursor:
        async with self.connection() as connection:
            cursor = await connection.cursor()
            return cursor

    async def execute(
        self,
        sql: str,
        args: tuple | list = (),
        *,
        error_return: Any = None,
        require_lastrowid: bool = False,
        fetchone: bool = False,
        executemany: bool = False,
        require_commit: bool = False
    ) -> Any:
        """
        SQL 语句统一执行函数
        :param sql: 要执行的 SQL 语句。
        :param args: 当前 SQL 语句依赖的参数。
        :param error_return: 当执行 SQL 语句报错时的返回值。
        :param require_lastrowid: 在新增数据、更新数据的情况下，如果需要得到上次修改的行 ID，请将这个参数设置为真。
        :param fetchone: 在查询的情况下，如果这个参数为真，那么只返回一条数据。
        :param executemany: 是否需要批量执行 SQL 语句。
        :param require_commit: 除了查询操作以外，这个参数请设置为真，否则事务将不会被提交。
        :return: 根据参数的设置情况返回。
        """
        async with self.connection() as connection:
            async with connection.cursor() as cursor:
                execute = cursor.executemany if executemany else cursor.execute
                try:
                    await execute(sql, args)
                    if require_commit:
                        await connection.commit()
                except aiomysql.MySQLError:
                    traceback.print_exc()  # 打印错误信息
                    if require_commit:
                        await connection.rollback()
                    return error_return
                if require_lastrowid:
                    return cursor.lastrowid
                fetch = cursor.fetchone if fetchone else cursor.fetchall
                return await fetch()

    async def close(self):
        if self._pool is not None:
            self._pool.close()
            await self._pool.wait_closed()


class MySQLService:
    def __init__(self, session: AsyncSession):
        self.session = session


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
