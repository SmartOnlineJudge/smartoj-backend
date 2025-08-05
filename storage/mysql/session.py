from sqlmodel.ext.asyncio.session import AsyncSession

from .db_engine import engine


async def get_async_session():
    async with AsyncSession(engine) as session:
        yield session
