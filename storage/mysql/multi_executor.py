import time

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

    async def get_id_by_user_id(self, user_id: str) -> int:
        """根据 user_id 获取 id"""
        cursor = await self.cursor()
        sql = f"""
            select id from user where user_id = %s
        """
        try:
            await cursor.execute(sql, user_id)
            uid = await cursor.fetchone()
        except aiomysql.MySQLError:
            return -1
        return uid

    async def get_page_user_data(self, page: int, size: int) -> tuple[list, int]:
        """分页展示用户信息"""
        cursor = await self.cursor()
        sql1 = f"""
            select u.id, u.user_id, u.email, u.github_token, u.qq_token, 
                u.created_at, u.is_deleted, u.is_superuser, ud.name, ud.avatar, 
                ud.profile, ud.grade, ud.experience
            from user u
            inner join user_dynamic ud on u.id = ud.user_id
            limit %s, %s
        """
        sql2 = f"""
            select count(*) from smartoj.user
        """
        try:
            await cursor.execute(sql1, (size * (page - 1), size))
            users = await cursor.fetchall()
            await cursor.execute(sql2)
            total = await cursor.fetchone()
        except aiomysql.MySQLError:
            return [], 0
        return users, total["count(*)"]

    async def _update_user(self, user_id: str, field: str, value: str | int | bool):
        async with self.connection() as connection:
            async with connection.cursor() as cursor:
                sql = f"""
                    UPDATE user
                    SET {field} = %s
                    WHERE user_id = %s
                """
                try:
                    await cursor.execute(sql, (value, user_id))
                    await connection.commit()
                except aiomysql.MySQLError:
                    await connection.rollback()

    async def update_user_is_delete(self, user_id: str, is_deleted: bool):
        await self._update_user(user_id, "is_deleted", is_deleted)

    async def update_user_password(self, user_id: str, password: str):
        await self._update_user(user_id, "password", password_hash(password, settings.SECRETS["PASSWORD"]))

    async def update_user_email(self,user_id: str,email: str):
        await self._update_user(user_id, "email", email)

    async def update_user_github_token(self, user_id: str, github_token: str):
        await self._update_user(user_id, "github_token", github_token)


class UserDynamicExecutor(MySQLExecutor):
    async def create_user_dynamic(
            self,
            user_id: int,
            name: str,
            profile: str = "",
            avatar: str = "",
    ) -> int:
        avatar = avatar or settings.DEFAULT_USER_AVATAR
        name = name or str(int(time.time()))
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

    async def get_publisher_by_qid(self, q_ids: list[int]) -> list:
        cursor = await self.cursor()
        placeholder = ",".join(["%s"] * len(q_ids))
        sql = f"""
            select ud.id,ud.name
            from user_dynamic ud
            inner join question q on ud.id = q.publisher_id
            where q.id in ({placeholder})
        """

        try:
            await cursor.execute(sql, q_ids)
            publisher = await cursor.fetchall()

        except aiomysql.MySQLError:
            return []
        return publisher


class QuestionExecutor(MySQLExecutor):
    async def get_question_info(self, page: int, size: int) -> tuple[list, int]:
        cursor = await self.cursor()
        sql1 = f"""
            select q.id, q.title, q.description, q.difficulty, 
             DATE_FORMAT(q.created_at, '%%Y-%%m-%%d %%H:%%i:%%s') AS created_at,q.submission_quantity,q.pass_quantity,q.is_deleted,q.publisher_id
            from question q
            limit %s, %s
        """
        sql2 = f"""
            select count(*) from smartoj.question
        """
        try:
            await cursor.execute(sql1, (size * (page - 1), size))
            questions = await cursor.fetchall()
            await cursor.execute(sql2)
            total = await cursor.fetchone()

        except aiomysql.MySQLError:
            return [], 0

        return questions, total["count(*)"]

    async def question_add(self, title: str, description: str, difficulty: int, publisher_id: int):
        async with self.connection() as connection:
            async with connection.cursor() as cursor:
                sql = """
                     insert into question (title, description, difficulty, publisher_id)
                     values (%s, %s, %s, %s)
                 """
                try:
                    await cursor.execute(sql, (title, description, difficulty, publisher_id))
                    await connection.commit()
                    insert_id = cursor.lastrowid
                    return insert_id
                except aiomysql.MySQLError:
                    await connection.rollback()


class TagExecutor(MySQLExecutor):
    async def get_tags_by_qid(self, q_ids: list[int]) -> list:
        cursor = await self.cursor()
        placeholder = ",".join(["%s"] * len(q_ids))
        sql = f"""
            select t.id,t.name,q.id as qid
            from tag t
            inner join question_tag qt on qt.tag_id = t.id
            inner join question q on q.id = qt.question_id
            where q.id in ({placeholder})
        """

        try:
            await cursor.execute(sql, q_ids)
            tags = await cursor.fetchall()

        except aiomysql.MySQLError:
            return []
        return tags

    async def add_tags_by_qid(self, q_id, t_ids: list):
        async with self.connection() as connection:
            async with connection.cursor() as cursor:
                sql = """
                     insert into question_tag (question_id, tag_id)
                     values (%s, %s)
                 """
                try:
                    values = [(q_id, t_id) for t_id in t_ids]
                    await cursor.executemany(sql, values)
                    await connection.commit()
                except aiomysql.MySQLError:
                    await connection.rollback()


class QuestionTagExecutor(MySQLExecutor):
    pass


class LanguageExecutor(MySQLExecutor):
    async def get_language_by_lid(self, lid: int) -> list:
        cursor = await self.cursor()
        sql = f"""
            select l.name,l.version
            from language l
            where l.id = %s
        """

        try:
            await cursor.execute(sql, lid)
            language = await cursor.fetchall()

        except aiomysql.MySQLError:
            return []
        return language

    async def get_all_languages(self) -> list:
        cursor = await self.cursor()
        sql = f"""
            select l.id,l.name,l.version from language l
        """
        try:
            await cursor.execute(sql)
            languages = await cursor.fetchall()

        except aiomysql.MySQLError:
            return []
        return languages


class SolvingFrameworkExecutor(MySQLExecutor):
    async def get_solving_frameworks_by_qid(self, q_ids: list[int]) -> list:
        cursor = await self.cursor()
        placeholder = ",".join(["%s"] * len(q_ids))
        sql = f"""
            select s.id,s.code_framework,s.language_id,s.question_id as qid,s.language_id as lid
            from solving_framework s
            where s.question_id in ({placeholder})
        """

        try:
            await cursor.execute(sql, q_ids)
            solving_framework = await cursor.fetchall()

        except aiomysql.MySQLError:
            return []
        return solving_framework

    async def add_solving_frameworks_by_qid(self, q_id: int, framework_datas: list):
        async with self.connection() as connection:
            async with connection.cursor() as cursor:
                values = [(data.code_framework, data.language_id, q_id) for data in framework_datas]
                sql = """
                         insert into solving_framework (code_framework, language_id,question_id)
                         values (%s, %s, %s)
                     """
                try:
                    await cursor.executemany(sql, values)
                    await connection.commit()
                except aiomysql.MySQLError:
                    await connection.rollback()


class TestExecutor(MySQLExecutor):
    async def get_tests_by_qid(self, q_ids: list[int]) -> list:
        cursor = await self.cursor()
        placeholder = ",".join(["%s"] * len(q_ids))
        sql = f"""
            select t.id,t.input_output,t.question_id as qid
            from test t
            where t.question_id in ({placeholder})
        """

        try:
            await cursor.execute(sql, q_ids)
            test = await cursor.fetchall()

        except aiomysql.MySQLError:
            return []
        return test

    async def add_test_by_qid(self, q_id: int, input_output: list):
        async with self.connection() as connection:
            async with connection.cursor() as cursor:
                sql = """
                    INSERT INTO test (input_output, question_id)
                    VALUES (%s, %s)
                """
                try:
                    values = [(io, q_id) for io in input_output]
                    await cursor.executemany(sql, values)
                    await connection.commit()
                except aiomysql.MySQLError:
                    await connection.rollback()


class JudgeTemplateExecutor(MySQLExecutor):
    async def get_judge_templates_by_qid(self, q_ids: list[int]) -> list:
        cursor = await self.cursor()
        placeholder = ",".join(["%s"] * len(q_ids))
        sql = f"""
            select j.id,j.code,j.language_id,j.question_id as qid,j.language_id as lid
            from judge_template j
            where j.language_id in ({placeholder})
        """

        try:
            await cursor.execute(sql, q_ids)
            solving_framework = await cursor.fetchall()

        except aiomysql.MySQLError:
            return []
        return solving_framework

    async def add_judge_templates_by_qid(self, q_id: int, template_datas: list):
        async with self.connection() as connection:
            async with connection.cursor() as cursor:
                values = [(data.code, data.language_id, q_id) for data in template_datas]
                sql = """
                         insert into judge_template (code, language_id,question_id)
                         values (%s, %s, %s)
                     """
                try:
                    await cursor.executemany(sql, values)
                    await connection.commit()
                except aiomysql.MySQLError:
                    await connection.rollback()


class MemoryTimeLimitExecutor(MySQLExecutor):
    async def get_memory_limits_by_qid(self, q_ids: list[int]) -> list:
        cursor = await self.cursor()
        placeholder = ",".join(["%s"] * len(q_ids))
        sql = f"""
            select m.id,m.memory_limit,m.time_limit,m.language_id,m.question_id as qid,m.language_id as lid
            from memory_time_limit m
            where m.question_id in ({placeholder})
        """

        try:
            await cursor.execute(sql, q_ids)
            memory_limit = await cursor.fetchall()

        except aiomysql.MySQLError:
            return []
        return memory_limit

    async def add_memory_time_limit_by_qid(self, q_id: int, limit_datas: list):
        async with self.connection() as connection:
            async with connection.cursor() as cursor:
                values = [(data.time_limit, data.memory_limit, data.language_id, q_id) for data in limit_datas]
                sql = """
                         insert into memory_time_limit (time_limit, memory_limit,language_id,question_id)
                         values (%s, %s, %s, %s)
                     """
                try:
                    await cursor.executemany(sql, values)
                    await connection.commit()
                except aiomysql.MySQLError:
                    await connection.rollback()


class SolvedHistoryExecutor(MySQLExecutor):
    pass


class JudgeHistoryExecutor(MySQLExecutor):
    pass
