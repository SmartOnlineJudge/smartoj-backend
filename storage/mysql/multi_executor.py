import time

import settings
from core.user.security import password_hash, generate_user_id
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
        args = (user_id, db_password, email, github_token, qq_token, is_superuser)
        return await self.execute(sql, args, require_lastrowid=True, error_return=-1, require_commit=True)

    async def _get_user(self, field: str, value: str) -> dict:
        sql = f"""
            select u.id, u.user_id, u.email, u.password, u.github_token, u.qq_token, 
                u.created_at, u.is_deleted, u.is_superuser, ud.name, ud.avatar, 
                ud.profile, ud.grade, ud.experience
            from user u
            inner join user_dynamic ud on u.id = ud.user_id
            WHERE u.{field} = %s
        """
        user = await self.execute(sql, (value,), error_return={}, fetchone=True)
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
        sql = f"select id from user where user_id = %s"
        return await self.execute(sql, (user_id,), error_return=-1, fetchone=True)

    async def get_page_user_data(self, page: int, size: int) -> tuple[list, int]:
        """分页展示用户信息"""
        sql1 = """
            select u.id, u.user_id, u.email, u.github_token, u.qq_token, 
                u.created_at, u.is_deleted, u.is_superuser, ud.name, ud.avatar, 
                ud.profile, ud.grade, ud.experience
            from user u
            inner join user_dynamic ud on u.id = ud.user_id
            limit %s, %s
        """
        sql2 = "select count(*) from user"
        users = await self.execute(sql1, (size * (page - 1), size), error_return=[])
        total = await self.execute(sql2, error_return={'count(*)': 0}, fetchone=True)
        return users, total["count(*)"]

    async def _update_user(self, user_id: str, field: str, value: str | int | bool):
        sql = f"UPDATE user SET {field} = %s WHERE user_id = %s"
        await self.execute(sql, (value, user_id), require_commit=True)

    async def update_user_is_delete(self, user_id: str, is_deleted: bool):
        await self._update_user(user_id, "is_deleted", is_deleted)

    async def update_user_password(self, user_id: str, password: str):
        await self._update_user(user_id, "password", password_hash(password, settings.SECRETS["PASSWORD"]))

    async def update_user_email(self, user_id: str, email: str):
        await self._update_user(user_id, "email", email)

    async def update_user_github_token(self, user_id: str, github_token: str):
        await self._update_user(user_id, "github_token", github_token)

    async def test(self):
        await self.execute('select * from aaa')


class UserDynamicExecutor(MySQLExecutor):
    async def create_user_dynamic(
            self,
            user_id: int,
            name: str,
            profile: str = "",
            avatar: str = "",
    ) -> int:
        avatar = avatar or settings.DEFAULT_USER_AVATAR
        name = name or ("用户" + str(int(time.time())))
        sql = """
            INSERT INTO user_dynamic (user_id, name, profile, avatar)
            VALUES (%s, %s, %s, %s)
        """
        return await self.execute(
            sql,
            (user_id, name, profile, avatar),
            require_lastrowid=True,
            error_return=-1,
            require_commit=True
        )

    async def update_user_avatar(self, user_id: str, avatar: str):
        sql = """
            UPDATE user_dynamic
            SET avatar = %s
            WHERE user_id = (SELECT id FROM user WHERE user_id = %s)
        """
        await self.execute(sql, (avatar, user_id), require_commit=True)

    async def update_user_dynamic(
            self,
            user_id: str,
            name: str = "",
            profile: str = "",
    ):
        sql = """
            UPDATE user_dynamic
            SET name = %s, profile = %s
            WHERE user_id = (SELECT id FROM user WHERE user_id = %s)
        """
        await self.execute(sql, (name, profile, user_id), require_commit=True)

    async def get_publisher_by_qid(self, q_ids: list[int]) -> list:
        placeholder = ",".join(["%s"] * len(q_ids))
        sql = f"""
            select ud.user_id, ud.name
            from user_dynamic ud
            inner join question q on ud.user_id = q.publisher_id
            where q.id in ({placeholder})
        """
        return await self.execute(sql, q_ids, error_return=[])


class QuestionExecutor(MySQLExecutor):
    async def get_question_info(self, page: int, size: int) -> tuple[list, int]:
        sql1 = """
            select q.id, q.title, q.description, q.difficulty, 
             DATE_FORMAT(q.created_at, '%%Y-%%m-%%d %%H:%%i:%%s') AS created_at,
             q.submission_quantity, q.pass_quantity, q.is_deleted, q.publisher_id
            from question q
            limit %s, %s
        """
        sql2 = "select count(*) from question"
        questions = await self.execute(sql1, (size * (page - 1), size), error_return=[])
        total = await self.execute(sql2, error_return={'count(*)': 0}, fetchone=True)
        return questions, total["count(*)"]

    async def question_add(self, title: str, description: str, difficulty: int, publisher_id: int):
        sql = """
            insert into question (title, description, difficulty, publisher_id)
            values (%s, %s, %s, %s)
        """
        return await self.execute(
            sql,
            (title, description, difficulty, publisher_id),
            require_lastrowid=True,
            error_return=-1,
            require_commit=True
        )

    async def question_update(self, q_id: int, title: str, description: str, difficulty: int):
        sql = """
            update question
            set title = %s, description = %s, difficulty = %s
            where id = %s
        """
        return await self.execute(sql, (title, description, difficulty, q_id), require_commit=True)

    async def question_delete(self, q_id: int):
        sql = """
            update question
            set is_deleted = 1
            where id = %s
        """
        return await self.execute(sql, (q_id,), require_commit=True)


class TagExecutor(MySQLExecutor):
    async def get_tags_by_qid(self, q_ids: list[int]) -> list:
        placeholder = ",".join(["%s"] * len(q_ids))
        sql = f"""
            select t.id, t.name, q.id as qid
            from tag t
            inner join question_tag qt on qt.tag_id = t.id
            inner join question q on q.id = qt.question_id
            where q.id in ({placeholder})
        """
        return await self.execute(sql, q_ids, error_return=[])

    async def add_tags_by_qid(self, q_id, t_ids: list):
        sql = "insert into question_tag (question_id, tag_id) values (%s, %s)"
        await self.execute(sql, [(q_id, t_id) for t_id in t_ids], executemany=True, require_commit=True)


class QuestionTagExecutor(MySQLExecutor):
    pass


class LanguageExecutor(MySQLExecutor):
    async def get_language_by_lid(self, lid: int) -> list:
        sql = "select l.name, l.version from language l where l.id = %s"
        return await self.execute(sql, (lid,), error_return=[])

    async def get_all_languages(self) -> list:
        sql = "select l.id, l.name, l.version from language l"
        return await self.execute(sql, error_return=[])


class SolvingFrameworkExecutor(MySQLExecutor):
    async def get_solving_frameworks_by_qid(self, q_ids: list[int]) -> list:
        placeholder = ",".join(["%s"] * len(q_ids))
        sql = f"""
            select s.id, s.code_framework, s.language_id, s.question_id as qid, s.language_id as lid
            from solving_framework s
            where s.question_id in ({placeholder})
        """
        return await self.execute(sql, q_ids, error_return=[])

    async def update_solving_framework(self, code_framework: str, framework_id: int):
        sql = """
            update solving_framework
            set code_framework = %s
            where id = %s
        """
        return await self.execute(
            sql,
            (code_framework, framework_id),
            require_commit=True
        )

    async def get_question_id_by_framework_id(self, template_id: int) -> int:
        sql = "select question_id from solving_framework where id = %s"
        return await self.execute(
            sql, (template_id,), error_return=[]
        )

    async def solving_framework_delete(self, solving_framework_id: int):
        sql = """
            delete from solving_framework
            where id = %s
        """
        return await self.execute(sql, (solving_framework_id,), require_commit=True)

    async def add_solving_frameworks_by_qid(self, q_id: int, framework_datas: list):
        sql = """
            insert into solving_framework (code_framework, language_id, question_id)
            values (%s, %s, %s)
        """
        await self.execute(
            sql,
            [(data.code_framework, data.language_id, q_id) for data in framework_datas],
            executemany=True,
            require_commit=True
        )


class TestExecutor(MySQLExecutor):
    async def get_tests_by_qid(self, q_ids: list[int]) -> list:
        placeholder = ",".join(["%s"] * len(q_ids))
        sql = f"""
            select t.id, t.input_output, t.question_id as qid
            from test t
            where t.question_id in ({placeholder})
        """
        return await self.execute(sql, q_ids, error_return=[])

    async def add_test_by_qid(self, q_id: int, input_output: list):
        sql = "INSERT INTO test (input_output, question_id) VALUES (%s, %s)"
        await self.execute(sql, [(io, q_id) for io in input_output], executemany=True, require_commit=True)

    async def update_test(self, intput_output: str, test_id: int):
        sql = """
            update test
            set input_output = %s
            where id = %s
        """
        return await self.execute(
            sql,
            (intput_output, test_id),
            require_commit=True
        )

    async def get_question_id_by_test_id(self, test_id: int) -> int:
        sql = "select question_id from test where id = %s"
        return await self.execute(
            sql, (test_id,), error_return=[]
        )

    async def test_delete(self, test_id: int):
        sql = """
            delete from test
            where id = %s
        """
        return await self.execute(sql, (test_id,), require_commit=True)


class JudgeTemplateExecutor(MySQLExecutor):
    async def get_judge_templates_by_qid(self, q_ids: list[int]) -> list:
        placeholder = ",".join(["%s"] * len(q_ids))
        sql = f"""
            select j.id, j.code,j. language_id, j.question_id as qid, j.language_id as lid
            from judge_template j
            where j.language_id in ({placeholder})
        """
        return await self.execute(sql, q_ids, error_return=[])

    async def add_judge_templates_by_qid(self, q_id: int, template_datas: list):
        sql = """
            insert into judge_template (code, language_id, question_id)
            values (%s, %s, %s)
        """
        await self.execute(
            sql,
            [(data.code, data.language_id, q_id) for data in template_datas],
            executemany=True,
            require_commit=True
        )

    async def update_judge_template(self, code: str, template_id: int):
        sql = """
            update judge_template
            set code = %s
            where id = %s
        """
        return await self.execute(
            sql,
            (code, template_id),
            require_commit=True
        )

    async def judge_template_delete(self, judge_template_id: int):
        sql = """
            delete from judge_template
            where id = %s
        """
        return await self.execute(sql, (judge_template_id,), require_commit=True)

    async def get_question_id_by_template_id(self, template_id: int) -> int:
        sql = "select question_id from judge_template where id = %s"
        return await self.execute(
            sql, (template_id,), error_return=[]
        )


class MemoryTimeLimitExecutor(MySQLExecutor):
    async def get_memory_limits_by_qid(self, q_ids: list[int]) -> list:
        placeholder = ",".join(["%s"] * len(q_ids))
        sql = f"""
            select m.id, m.memory_limit, m.time_limit, m.language_id, m.question_id as qid, m.language_id as lid
            from memory_time_limit m
            where m.question_id in ({placeholder})
        """
        return await self.execute(sql, q_ids, error_return=[])

    async def update_memory_limits(self, time_limit: int, memory_limit: int, limit_id: int):
        sql = """
            update memory_time_limit
            set time_limit = %s, memory_limit = %s
            where id = %s
        """
        return await self.execute(
            sql,
            (time_limit, memory_limit, limit_id),
            require_commit=True
        )

    async def get_question_id_by_limits_id(self, limit_id: int) -> int:
        sql = "select question_id from memory_time_limit where id = %s"
        return await self.execute(
            sql, (limit_id,), error_return=[]
        )

    async def memory_limits_delete(self, memory_limits_id: int):
        sql = """
            delete from memory_time_limit
            where id = %s
        """
        return await self.execute(sql, (memory_limits_id,), require_commit=True, error_return=[])

    async def add_memory_time_limit_by_qid(self, q_id: int, limit_datas: list):
        sql = """
            insert into memory_time_limit (time_limit, memory_limit, language_id, question_id)
            values (%s, %s, %s, %s)
        """
        await self.execute(
            sql,
            [(data.time_limit, data.memory_limit, data.language_id, q_id) for data in limit_datas],
            executemany=True,
            require_commit=True
        )


class SolvedHistoryExecutor(MySQLExecutor):
    pass


class JudgeHistoryExecutor(MySQLExecutor):
    pass
