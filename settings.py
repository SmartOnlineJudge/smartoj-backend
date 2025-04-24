import json


# 是否是开发环境
DEV_ENV: bool = True

# 元数据文件名
METADATA_FILENAME: str = "metadata_dev.json" if DEV_ENV else "metadata.json"

# 元数据
METADATA: dict = json.load(open(METADATA_FILENAME, encoding="utf8"))["metadata"]

# MySQL 连接配置
MYSQL_CONF: dict = METADATA["databases"]["mysql"]["default"]

# Redis 连接配置
REDIS_CONF: dict = METADATA["databases"]["redis"]

# 加密密钥
SECRETS: dict = METADATA["secrets"]

# 登录状态最大保存时间
SESSION_MAX_AGE: int = 60 * 60 * 24

# MinIO 对象存储配置
MINIO_CONF: dict = METADATA["minio"]

# RabbitMQ 消息队列配置
RABBITMQ_CONF: dict = METADATA["rabbitmq"]

# SMTP 邮箱配置
SMTP_CONF: dict = METADATA["smtp"]

# 默认用户头像，这个是在 MinIO 服务器上的头像路径
DEFAULT_USER_AVATAR: str = "/user-avatars/default.webp"

# 请求代理地址
# 后端向 GitHub 发送请求的时候会用到
PROXY_URL = "socks5://127.0.0.1:1080"
