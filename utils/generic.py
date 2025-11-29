import string
import random

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


if __name__ == '__main__':
    for _ in range(10):
        print(random_avatar_name())
