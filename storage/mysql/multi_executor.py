import aiomysql

import settings
from utils.user.security import password_hash, generate_user_id
from .base import MySQLExecutor


class UserExecutor(MySQLExecutor):
    async def create_user(
        self,
        password: str = None,
        email: str = "",
        github_token: str = "",
        qq_token: str = "",
        is_superuser: bool = False,
    ) -> int:
        if password is not None:
            db_password = password_hash(password, settings.SECRETS["PASSWORD"])
        else:
            db_password = ""
        user_id = generate_user_id()
        sql = """
            INSERT INTO 
            user (user_id, password, email, github_token, qq_token, is_superuser)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        async with self.connection() as connection:
            async with connection.cursor() as cursor:
                try:
                    await cursor.execute(
                        sql,
                        (
                            user_id,
                            db_password,
                            email,
                            github_token,
                            qq_token,
                            is_superuser,
                        ),
                    )
                    await connection.commit()
                except aiomysql.MySQLError:
                    await connection.rollback()
                    return -1
                return cursor.lastrowid

    async def _get_user(self, field: str, value: str) -> dict:
        cursor = await self.cursor()
        sql = f"""
            select u.id, u.user_id, u.email, u.password, u.github_token, u.qq_token, 
                u.created_at, u.is_deleted, u.is_superuser, ud.name, ud.avatar, 
                ud.profile, ud.grade, ud.experience
            from user u
            inner join user_dynamic ud on u.id = ud.user_id
            WHERE u.{field} = %s
        """
        try:
            await cursor.execute(sql, (value,))
            user = await cursor.fetchone()
        except aiomysql.MySQLError:
            return {}
        return user if user else {}

    async def get_user_by_user_id(self, user_id: str) -> dict:
        """根据 user_id 获取用户"""
        return await self._get_user('user_id', user_id)

    async def get_user_by_email(self, email: str) -> dict:
        """根据 email 获取用户"""
        return await self._get_user('email', email)

    async def get_user_by_github_token(self, github_token: str) -> dict:
        """根据 github_token 获取用户"""
        return await self._get_user('github_token', github_token)


class UserDynamicExecutor(MySQLExecutor):
    async def create_user_dynamic(
        self,
        user_id: int,
        name: str,
        profile: str = "",
        avatar: str = "",
    ) -> int:
        avatar = avatar or "/user-avatars/default.webp"
        async with self.connection() as connection:
            async with connection.cursor() as cursor:
                sql = """
                    INSERT INTO user_dynamic (user_id, name, profile, avatar)
                    VALUES (%s, %s, %s, %s)
                """
                try:
                    await cursor.execute(sql, (user_id, name, profile, avatar))
                    await connection.commit()
                except aiomysql.MySQLError:
                    await connection.rollback()
                    return -1
                return cursor.lastrowid

    async def update_user_avatar(self, user_id: str, avatar: str):
        async with self.connection() as connection:
            async with connection.cursor() as cursor:
                sql = """
                    UPDATE user_dynamic
                    SET avatar = %s
                    WHERE user_id = (SELECT id FROM user WHERE user_id = %s)
                """
                try:
                    await cursor.execute(sql, (avatar, user_id))
                    await connection.commit()
                except aiomysql.MySQLError:
                    await connection.rollback()

    async def update_user_dynamic(
        self,
        user_id: str,
        name: str = "",
        profile: str = "",
    ):
        async with self.connection() as connection:
            async with connection.cursor() as cursor:
                sql = """
                    UPDATE user_dynamic
                    SET name = %s, profile = %s
                    WHERE user_id = (SELECT id FROM user WHERE user_id = %s)
                """
                try:
                    await cursor.execute(sql, (name, profile, user_id))
                    await connection.commit()
                except aiomysql.MySQLError:
                   await connection.rollback()


class QuestionExecutor(MySQLExecutor):
    pass


class TagExecutor(MySQLExecutor):
    pass


class QuestionTagExecutor(MySQLExecutor):
    pass


class LanguageExecutor(MySQLExecutor):
    pass


class SolvingFrameworkExecutor(MySQLExecutor):
    pass


class TestExecutor(MySQLExecutor):
    pass


class JudgeTemplateExecutor(MySQLExecutor):
    pass


class MemoryTimeLimitExecutor(MySQLExecutor):
    pass


class SolvedHistoryExecutor(MySQLExecutor):
    pass


class JudgeHistoryExecutor(MySQLExecutor):
    pass
