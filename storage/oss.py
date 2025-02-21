from functools import lru_cache

from minio import Minio

import settings


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
