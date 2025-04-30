from typing import Annotated

from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import Depends

from utils.user.auth import get_current_user, get_current_admin
from storage.mysql import get_async_session
from storage.cache import get_session_redis, get_default_redis, Redis
from storage.oss import get_minio_client, Minio


CurrentUserDependency = Annotated[dict, Depends(get_current_user)]
CurrentAdminDependency = Annotated[dict, Depends(get_current_admin)]
DefaultRedisDependency = Annotated[Redis, Depends(get_default_redis)]
SessionRedisDependency = Annotated[Redis, Depends(get_session_redis)]
MinioClientDependency = Annotated[Minio, Depends(get_minio_client)]
AsyncSessionDependency = Annotated[AsyncSession, Depends(get_async_session)]
