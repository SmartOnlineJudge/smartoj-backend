import base64
import string
import random
from datetime import datetime

from python_socks import parse_proxy_url as python_parse_proxy_url


def parse_proxy_url(url: str) -> dict:
    proxy_type, proxy_host, proxy_port, username, password = python_parse_proxy_url(url)
    return {
        "proxy_type": proxy_type,
        "proxy_host": proxy_host,
        "proxy_port": proxy_port,
        "username": username,
        "password": password,
    }


def random_avatar_name(length: int = 32):
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def encode_cursor(primary_key: int, created_at: datetime) -> str:
    now_timestamp = datetime.now().timestamp()
    return base64.urlsafe_b64encode(f"{primary_key},{created_at.timestamp()},{now_timestamp}".encode()).decode()


def decode_cursor(cursor: str) -> tuple[int, datetime]:
    primary_key, created_at, _ = base64.urlsafe_b64decode(cursor).decode().split(",")
    return int(primary_key), datetime.fromtimestamp(float(created_at))


if __name__ == '__main__':
    for _ in range(10):
        print(random_avatar_name())
