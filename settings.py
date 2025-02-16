import json

# 是否是开发环境
DEV_ENV: bool = True

# 元数据文件名
METADATA_FILENAME: str = "metadata_dev.json" if DEV_ENV else "metadata.json"

# 元数据
METADATA: dict = json.load(open(METADATA_FILENAME))["metadata"]

# MySQL 连接配置
MYSQL_CONF: dict = METADATA["databases"]["mysql"]["default"]

# Redis 连接配置
REDIS_CONF: dict = METADATA["databases"]["redis"]

# 加密密钥
SECRETS: dict = METADATA["secrets"]

# 登录状态最大保存时间
SESSION_MAX_AGE: int = 60 * 60 * 24
