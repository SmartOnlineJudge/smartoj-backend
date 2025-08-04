import io
from functools import lru_cache

from minio import Minio
from minio.error import MinioException
from fastapi.concurrency import run_in_threadpool

import settings
from utils.generic import random_avatar_name


MINIO_CONF = settings.MINIO_CONF

# 用户头像存储桶名称
AVATAR_BUCKET_NAME = "user-avatars"

# 最大用户头像大小 3MB
MAX_AVATAR_SIZE = 3 * 1024 * 1024


@lru_cache()
def get_minio_client() -> Minio:
    return Minio(
        MINIO_CONF["endpoint"],
        access_key=MINIO_CONF["access_key"],
        secret_key=MINIO_CONF["secret_key"],
        secure=MINIO_CONF["secure"]
    )


def upload_avatar(avatar: bytes, file_type: str, minio_client: Minio = None) -> str:
    object_name = random_avatar_name() + "." + file_type
    if minio_client is None:
        minio_client = get_minio_client()
    try:
        minio_client.put_object(
            AVATAR_BUCKET_NAME,
            object_name,
            io.BytesIO(avatar),
            len(avatar),
        )
    except MinioException:
        return ""
    return f"/{AVATAR_BUCKET_NAME}/{object_name}"


async def async_upload_avatar(avatar: bytes, file_type: str, minio_client: Minio = None) -> str:
    return await run_in_threadpool(upload_avatar, avatar, file_type, minio_client)
