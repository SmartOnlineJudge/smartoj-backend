import asyncio
from typing import Any

from sqlalchemy.orm import selectinload
from sqlmodel import select

import settings
from core.user.security import generate_user_id, password_hash
from ..base import MySQLService
from .models import User, UserDynamic


class UserService(MySQLService):
    async def create_user_and_dynamic(
        self,
        name: str,
        password: str = None,
        email: str = "",
        github_token: str = "",
        qq_token: str = "",
        is_superuser: bool = False,
        profile: str = "",
        avatar: str = ""
    ):
        if password is not None:
            password = password_hash(password, settings.SECRETS["PASSWORD"])
        user = User(
            email=email, 
            password=password, 
            user_id=generate_user_id(),
            is_superuser=is_superuser,
            github_token=github_token,
            qq_token=qq_token,
        )
        avatar = avatar or settings.DEFAULT_USER_AVATAR
        user_dynamic = UserDynamic(name=name, profile=profile, avatar=avatar)

        user.user_dynamic = user_dynamic

        self.session.add(user)
        await self.session.commit()

        await asyncio.gather(
            self.session.refresh(user),
            self.session.refresh(user_dynamic)
        )

        return user.id, user_dynamic.id

    async def query_by_index(self, index: str, value: Any):
        """
        通过索引字段获取用户信息（包括动态信息）
        :param index: 索引名，只能是 ('email', 'github_token', 'qq_token', 'user_id', 'id') 中的其中一个
        :param value: 索引值
        :return:
        """
        statement = (
            select(User)
            .options(selectinload(User.user_dynamic))  # type: ignore
            .where(getattr(User, index) == value)
        )
        users = await self.session.exec(statement)  # type: ignore
        return users.first()

    async def update(self, user_id: str, document: dict[str, Any]):
        """
        根据 user_id 更新指定的列名的用户基本信息
        :param user_id: 非行 ID
        :param document: 需要更新的文档信息，例如：{'name': '张三', 'profile': '张三的简介'}
        :return:
        """
        statement = select(User).where(User.user_id == user_id)
        users = await self.session.exec(statement)  # type: ignore
        user = users.first()
        if user is None:
            return
        for field, value in document.items():
            setattr(user, field, value)
        self.session.add(user)
        await self.session.commit()


class UserDynamicService(MySQLService):
    async def update(self, user_id: str, document: dict[str, Any]):
        """
        通过 user_id 更新多个用户动态信息
        :param user_id:
        :param document: 需要更新的文档信息，例如：{'name': '张三', 'profile': '张三的简介'}
        :return:
        """
        statement = (
            select(User)
            .where(User.user_id == user_id)
            .options(selectinload(User.user_dynamic))  # type: ignore
        )
        results = await self.session.exec(statement)  # type: ignore
        user = results.first()
        if user is None:
            return
        for field, value in document.items():
            setattr(user.user_dynamic, field, value)
        self.session.add(user)
        await self.session.commit()
