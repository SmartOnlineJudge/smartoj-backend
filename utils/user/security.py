import base64
import random
import hashlib
from datetime import datetime


def generate_user_id() -> str:
    """
    生成策略：20250118(日期) + 五位随机数
    """
    date = "".join(str(datetime.now()).split()[0].split("-"))
    num = str(random.randint(10000, 99999))
    user_id = date + num
    return user_id


def password_hash(password: str, salt: str) -> str:
    salt = base64.b64decode(salt.encode())
    password = password.encode()
    hashed = hashlib.pbkdf2_hmac("sha256", password, salt, 100000)
    store_password = salt + hashed
    return base64.b64encode(store_password).decode()


def mask(user: dict):
    """隐藏用户部分敏感信息"""
    v = user["email"]
    local_part, domain = v.split("@", maxsplit=1)
    masked = "*" * 6
    user["email"] = local_part[:3] + masked + "@" + domain
    return user
