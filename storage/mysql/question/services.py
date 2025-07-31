from typing import Any

from ..base import MySQLService
from sqlmodel import select
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
    async def create(self, title: str, description: str, difficulty: str, publisher_id: int):
        question = Question(
            title=title,
            description=description,
            difficulty=difficulty,
            publisher_id=publisher_id
        )
        self.session.add(question)
        await self.session.commit()

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

    async def create(self, question_id: int, tag_id: int):
        """
        根据 question_id 增加题目标签信息
        :param question_id: 非行 ID
        :param tag_id: 增加的题目标签id
        :return:
        """
        question_tag = QuestionTag(question_id=question_id, tag_id=tag_id)
        self.session.add(question_tag)
        await self.session.commit()

    async def delete(self, question_id: int, tag_ids: list[int]):
        """
        根据 question_id 删除指定的id的题目标签基本信息
        :param question_id: 非行 ID
        :param tag_ids: 需要删除的标签id数组
        :return:
        """
        statement = select(QuestionTag).where(QuestionTag.question_id == question_id, QuestionTag.tag_id.in_(tag_ids))
        tags = await self.session.exec(statement)  # type: ignore
        for tag in tags:
            await self.session.delete(tag)
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
    async def create(self, question_id: int, language_id: int, code_framework: str):
        """
        根据 question_id 增加解题框架信息
        :param question_id: 非行 ID
        :param language_id: 更新的解题框架所使用的编程语言信息
        :param code_framework: 解题框架代码
        :return:
        """
        solving_framework = SolvingFramework(question_id=question_id, language_id=language_id,
                                             code_framework=code_framework)
        self.session.add(solving_framework)
        await self.session.commit()


class TestService(MySQLService):
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


class JudgeTemplateService(MySQLService):
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


class MemoryTimeLimitService(MySQLService):
    async def create(self, question_id: int, language_id: int, time_limit: int, memory_limit: float):
        """
        根据 question_id 增加内存时间限制信息
        :param question_id: 非行 ID
        :param language_id: 增加的内存时间限制所使用的编程语言信息
        :param time_limit: 时间限制
        :param memory_limit: 内存限制
        :return:
        """
        memory_time_limit = MemoryTimeLimit(question_id=question_id, language_id=language_id, time_limit=time_limit,
                                            memory_limit=memory_limit)
        self.session.add(memory_time_limit)
        await self.session.commit()
