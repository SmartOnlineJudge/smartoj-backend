from typing import AsyncGenerator

from sqlmodel.ext.asyncio.session import AsyncSession

from .session import get_async_session


class MySQLService:
    def __init__(self, session: AsyncSession = None):
        self.session = session
        self.session_generator: AsyncGenerator = None

    async def __aenter__(self):
        self.session_generator = get_async_session()
        self.session = await anext(self.session_generator)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            await anext(self.session_generator)
        except StopAsyncIteration:
            pass
