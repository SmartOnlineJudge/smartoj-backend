from typing import AsyncGenerator
from contextlib import asynccontextmanager

import aiomysql

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
                pool_recycle=60
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

    async def close(self):
        if self._pool is not None:
            self._pool.close()
            await self._pool.wait_closed()
