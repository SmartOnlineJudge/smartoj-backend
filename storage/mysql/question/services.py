from typing import Any

from sqlmodel import select, text
from sqlalchemy.orm import selectinload
from sqlalchemy import func

from ..base import MySQLService
from ..user.models import User
from .models import (
    QuestionTag, 
    JudgeTemplate, 
    MemoryTimeLimit, 
    SolvingFramework, 
    Test, 
    Tag, 
    Language,
    Question
)


class QuestionService(MySQLService):
    async def query_by_page(self, page: int, size: int):
        statement1 = (
            select(Question)
            .options(selectinload(Question.tags).selectinload(QuestionTag.tag))
            .options(selectinload(Question.tests))
            .options(selectinload(Question.solving_frameworks).selectinload(SolvingFramework.language))
            .options(selectinload(Question.memory_time_limits).selectinload(MemoryTimeLimit.language))
            .options(selectinload(Question.judge_templates).selectinload(JudgeTemplate.language))
            .options(selectinload(Question.publisher).selectinload(User.user_dynamic))
            .offset((page - 1) * size)
            .limit(size)
        )
        statement2 = select(func.count(Question.id))

        questions = await self.session.exec(statement1)
        total = (await self.session.exec(statement2)).one()

        return questions, total

    async def query_by_primary_key(self, question_id: int, online_judge: bool = False):
        if online_judge:
            statement = (
                select(Question)
                .where(Question.id == question_id)
                .options(selectinload(Question.tests))
                .options(selectinload(Question.solving_frameworks).selectinload(SolvingFramework.language))
                .options(selectinload(Question.tags).selectinload(QuestionTag.tag))
            )
        else:
            statement = select(Question).where(Question.id == question_id)
        questions = await self.session.exec(statement)
        return questions.first()

    async def create(self, title: str, description: str, difficulty: str, publisher_id: int):
        question = Question(
            title=title,
            description=description,
            difficulty=difficulty,
            publisher_id=publisher_id
        )

        self.session.add(question)
        await self.session.commit()
        await self.session.refresh(question)  # 获取该对象的最新数据
        
        return question.id

    async def update(self, question_id: str, document: dict[str, Any]):
        statement = select(Question).where(Question.id == question_id)
        questions = await self.session.exec(statement)  # type: ignore
        question = questions.first()
        if question is None:
            return
        for field, value in document.items():
            setattr(question, field, value)
        self.session.add(question)
        await self.session.commit()

    async def increment_submission_and_pass_quantity(
        self, 
        question_id: int,
        increment_pass_quantity: bool = False
    ):
        if increment_pass_quantity:
            sql = """
                UPDATE question
                SET submission_quantity = submission_quantity + 1,
                    pass_quantity = pass_quantity + 1
                WHERE id = :question_id
            """
        else:
            sql = """
                UPDATE question
                SET submission_quantity = submission_quantity + 1
                WHERE id = :question_id
            """
        await self.session.exec(text(sql), params={"question_id": question_id})
        await self.session.commit()


class TagService(MySQLService):
    async def create(self, name: str, score: int):
        """
        增加新标签
        :param name: 标签名
        :param score: 标签分数
        :return:
        """
        tag = Tag(name=name, score=score)
        self.session.add(tag)
        await self.session.commit()

    async def update(self, tag_id: str, document: dict[str, Any]):
        """
        根据 tag_id 更新指定的列名的标签基本信息
        :param tag_id: 非行 ID
        :param document: 需要更新的文档信息，例如：{'name': '双指针', 'score': '30'}
        :return:
        """
        statement = select(Tag).where(Tag.id == tag_id)
        tags = await self.session.exec(statement)  # type: ignore
        tag = tags.first()
        if tag is None:
            return
        for field, value in document.items():
            setattr(tag, field, value)
        self.session.add(tag)
        await self.session.commit()


class QuestionTagService(MySQLService):
    async def query_by_primary_key(self, question_tag_id: int):
        statement = select(QuestionTag).where(QuestionTag.id == question_tag_id)
        question_tag = await self.session.exec(statement)
        return question_tag.first()

    async def query_by_combination_index(self, question_id: int, tag_id: int):
        statement = select(QuestionTag).where(QuestionTag.question_id == question_id, QuestionTag.tag_id == tag_id)
        question_tag = await self.session.exec(statement)
        return question_tag.first()

    async def create(self, question_id: int, tag_id: int):
        question_tag = QuestionTag(question_id=question_id, tag_id=tag_id)
        self.session.add(question_tag)
        await self.session.commit()
        await self.session.refresh(question_tag)
        return question_tag.id

    async def delete(self, instance: QuestionTag):
        await self.session.delete(instance)
        await self.session.commit()

    async def update(self, question_id: int, tag_id: int, new_tag_id: int):
        """
        根据 question_id 更新指定的id的题目标签
        :param question_id: 非行 ID
        :param tag_id: 需要更新的题目标签id
        :param new_tag_id: 更新后的题目标签id
        :return:
        """
        statement = select(QuestionTag).where(QuestionTag.question_id == question_id, QuestionTag.tag_id == tag_id)
        question_tags = await self.session.exec(statement)  # type: ignore
        question_tag = question_tags.first()
        if question_tag is None:
            return
        question_tag.tag_id = new_tag_id
        self.session.add(question_tag)
        await self.session.commit()


class LanguageService(MySQLService):
    async def query_all(self):
        statement = select(Language)
        languages = await self.session.exec(statement)
        return languages.all()

    async def query_by_primary_key(self, language_id: int):
        statement = select(Language).where(Language.id == language_id)
        language = await self.session.exec(statement)
        return language.first()

    async def create(self, name: str, version: str):
        """
        增加新编程语言
        :param name: 编程语言名
        :param version: 编程语言版本
        :return:
        """
        language = Language(name=name, version=version)
        self.session.add(language)
        await self.session.commit()

    async def update(self, language_id: str, document: dict[str, Any]):
        """
        根据 language_id 更新指定的列名的编程语言基本信息
        :param language_id: 非行 ID
        :param document: 需要更新的文档信息，例如：{'name': 'python', 'version': '3.11'}
        :return:
        """
        statement = select(Language).where(Language.id == language_id)
        languages = await self.session.exec(statement)  # type: ignore
        language = languages.first()
        if language is None:
            return
        for field, value in document.items():
            setattr(language, field, value)
        self.session.add(language)
        await self.session.commit()


class SolvingFrameworkService(MySQLService):
    async def query_by_primary_key(self, solving_framework_id: int):
        statement = select(SolvingFramework).where(SolvingFramework.id == solving_framework_id)
        solving_frameworks = await self.session.exec(statement)
        return solving_frameworks.first()

    async def query_by_combination_index(self, question_id: int, language_id: int):
        statement = (
            select(SolvingFramework)
            .where(
                SolvingFramework.question_id == question_id, 
                SolvingFramework.language_id == language_id
            )
        )
        solving_frameworks = await self.session.exec(statement)
        return solving_frameworks.first()
    
    async def create(self, question_id: int, language_id: int, code_framework: str):
        solving_framework = SolvingFramework(
            question_id=question_id, 
            language_id=language_id,
            code_framework=code_framework
        )
        self.session.add(solving_framework)
        await self.session.commit()
        await self.session.refresh(solving_framework)
        return solving_framework.id
    
    async def update(self, solving_framework_id: int, code_framework: str, instance: SolvingFramework = None):
        instance = instance or await self.query_by_primary_key(solving_framework_id)
        instance.code_framework = code_framework
        self.session.add(instance)
        await self.session.commit()


class TestService(MySQLService):
    async def query_by_primary_key(self, test_id: int):
        """
        根据主键（test_id）查询测试用例信息
        :param test_id: 测试用例ID
        :return:
        """
        statement = select(Test).where(Test.id == test_id)
        tests = await self.session.exec(statement)
        return tests.first()

    async def query_by_question_id(self, question_id: int, judge_type: str = "submit"):
        """
        根据问题ID查询测试用例信息
        :param question_id: 问题ID
        :param judge_type: 判题的类型（submit / test）
        :return:
        """
        statement = select(Test).where(Test.question_id == question_id).order_by(Test.id)
        tests = await self.session.exec(statement)
        all_tests = tests.all()
        if judge_type == "submit":
            return all_tests
        return all_tests[:3]

    async def create(self, question_id: int, input_output: str):
        """
        根据 question_id 增加测试用例信息
        :param question_id: 非行 ID
        :param input_output: 增加的输入输出测试用例
        :return:
        """
        test = Test(question_id=question_id, input_output=input_output)
        self.session.add(test)
        await self.session.commit()
        await self.session.refresh(test)
        return test.id
    
    async def delete(self, test_id: int):
        test = await self.query_by_primary_key(test_id)
        await self.session.delete(test)
        await self.session.commit()
    
    async def update(self, test_id: int, input_output: str, instance: Test = None):
        instance = instance or await self.query_by_primary_key(test_id)
        instance.input_output = input_output
        self.session.add(instance)
        await self.session.commit()


class JudgeTemplateService(MySQLService):
    async def query_by_primary_key(self, judge_template_id: int):
        """
        根据主键（judge_template_id）查询判题模板信息
        :param judge_template_id: 判题模板ID
        :return:
        """
        statement = select(JudgeTemplate).where(JudgeTemplate.id == judge_template_id)
        judge_templates = await self.session.exec(statement)
        return judge_templates.first()
    
    async def query_by_combination_index(self, question_id: int, language_id: int):
        """
        根据联合索引（question_id、language_id）查询判题模板信息
        :param question_id: 题目ID
        :param language_id: 查询的判题模板所使用的编程语言信息
        :return:
        """
        statement = (
            select(JudgeTemplate).
            where(
                JudgeTemplate.question_id == question_id,
                JudgeTemplate.language_id == language_id
            )
        )
        judge_templates = await self.session.exec(statement)
        return judge_templates.first()

    async def create(self, question_id: int, language_id: int, code: str):
        """
        根据 question_id 增加判题模板信息
        :param question_id: 非行 ID
        :param language_id: 更新的判题模板所使用的编程语言信息
        :param code: 判题模板代码
        :return:
        """
        judge_template = JudgeTemplate(question_id=question_id, language_id=language_id, code=code)
        self.session.add(judge_template)
        await self.session.commit()
        await self.session.refresh(judge_template)
        return judge_template.id

    async def update(self, judge_template_id: int, code: str, instance: JudgeTemplate = None):
        instance = instance or await self.query_by_primary_key(judge_template_id)
        instance.code = code
        self.session.add(instance)
        await self.session.commit()


class MemoryTimeLimitService(MySQLService):
    async def query_by_primary_key(self, memory_time_limit_id: int):
        """
        根据主键（memory_time_limit_id）查询内存时间限制信息
        :param memory_time_limit_id: 内存时间限制ID
        :return:
        """
        statement = select(MemoryTimeLimit).where(MemoryTimeLimit.id == memory_time_limit_id)
        memory_time_limits = await self.session.exec(statement)
        return memory_time_limits.first()

    async def query_by_combination_index(self, question_id: int, language_id: int):
        """
        根据联合索引（question_id、language_id）查询内存时间限制信息
        :param question_id: 题目ID
        :param language_id: 查询的内存时间限制所使用的编程语言信息
        :return:
        """
        statement = (
            select(MemoryTimeLimit).
            where(
                MemoryTimeLimit.question_id == question_id,
                MemoryTimeLimit.language_id == language_id
            )
        )
        memory_time_limits = await self.session.exec(statement)
        return memory_time_limits.first()

    async def create(self, question_id: int, language_id: int, time_limit: int, memory_limit: float):
        """
        根据 question_id 增加内存时间限制信息
        :param question_id: 非行 ID
        :param language_id: 增加的内存时间限制所使用的编程语言信息
        :param time_limit: 时间限制
        :param memory_limit: 内存限制
        :return:
        """
        memory_time_limit = MemoryTimeLimit(
            question_id=question_id, 
            language_id=language_id, 
            time_limit=time_limit,
            memory_limit=memory_limit
        )
        self.session.add(memory_time_limit)
        await self.session.commit()
        await self.session.refresh(memory_time_limit)
        return memory_time_limit.id
    
    async def update(self, memory_time_limit_id: int, time_limit: int, memory_limit: float, instance: MemoryTimeLimit = None):
        instance = instance or await self.query_by_primary_key(memory_time_limit_id)
        instance.time_limit = time_limit
        instance.memory_limit = memory_limit
        self.session.add(instance)
        await self.session.commit()
