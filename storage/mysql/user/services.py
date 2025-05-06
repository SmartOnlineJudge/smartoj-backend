from sqlmodel import select

from ..base import MySQLService
from .models import User, UserDynamic


class UserService(MySQLService):
    pass


class UserDynamicService(MySQLService):
    pass
