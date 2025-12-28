from datetime import datetime, date, time

from sqlmodel import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func, distinct

from ..base import MySQLService
from .models import SubmitRecord, JudgeRecord
from ..user.models import UserDynamic, User
from ..question.models import Question, QuestionTag


class SubmitRecordService(MySQLService):
    async def query_by_primary_key(self, submit_record_id: int):
        statement = select(SubmitRecord).where(SubmitRecord.id == submit_record_id)
        submit_records = await self.session.exec(statement)
        return submit_records.first()

    async def query_by_user_and_question_id(self, user_id: int, question_id: int):
        statement = select(SubmitRecord).where(
            SubmitRecord.user_id == user_id,
            SubmitRecord.question_id == question_id
        )
        submit_records = await self.session.exec(statement)
        return submit_records.all()

    async def create(
        self, 
        code: str, 
        judge_type: str, 
        question_id: int, 
        user_id: int, 
        language_id: int
    ):
        submit_record = SubmitRecord(
            code=code,
            type=judge_type,
            question_id=question_id,
            user_id=user_id,
            language_id=language_id
        )
        self.session.add(submit_record)
        await self.session.commit()
        await self.session.refresh(submit_record)
        return submit_record.id

    async def update(self, submit_record_id: int, document: dict):
        submit_record = await self.session.get(SubmitRecord, submit_record_id)
        for key, value in document.items():
            setattr(submit_record, key, value)
        self.session.add(submit_record)
        await self.session.commit()

    async def count_by_date(self, target_date: date):
        # 创建日期范围查询条件，查询指定日期的全部时间范围
        start_datetime = datetime.combine(target_date, time.min)  # 当天开始时间
        end_datetime = datetime.combine(target_date, time.max)    # 当天结束时间
        
        statement = (
            select(func.count(SubmitRecord.id))
            .where(
                SubmitRecord.type == "submit",
                SubmitRecord.created_at >= start_datetime,
                SubmitRecord.created_at <= end_datetime
            )
        )
        
        result = await self.session.exec(statement)
        return result.one()

    async def count_user_submissions(self):
        """
        统计每个用户的提交次数，仅统计type为'submit'的记录
        
        Returns:
            返回格式: [
                {
                    "user_id": "user123", 
                    "submit_count": 1, 
                    "user_name": "Alice",
                    "user_avatar": "avatar_url"
                },
                ...
            ]
        """        
        statement = (
            select(
                User.user_id,
                func.count().label("submit_count"),
                UserDynamic.name,
                UserDynamic.avatar
            )
            .select_from(SubmitRecord)
            .join(User, SubmitRecord.user_id == User.id)
            .join(UserDynamic, User.user_dynamic)
            .where(SubmitRecord.type == "submit")
            .group_by(User.user_id, UserDynamic.name, UserDynamic.avatar)
        )
        
        result = await self.session.exec(statement)
        rows = result.all()
        
        return [
            {
                "user_id": row.user_id, 
                "submit_count": row.submit_count,
                "user_name": row.name,
                "user_avatar": row.avatar
            } 
            for row in rows[:5]
        ]

    async def count_user_submissions_group_by_difficulty(self, user_id: int):
        statement = (
            select(Question.difficulty, func.count(distinct(Question.id)))
            .select_from(SubmitRecord)
            .join(Question, SubmitRecord.question_id == Question.id)
            .where(
                SubmitRecord.user_id == user_id,
                SubmitRecord.type == "submit",
                SubmitRecord.total_test_quantity == SubmitRecord.pass_test_quantity
            )
            .group_by(Question.difficulty)
        )
        result = await self.session.exec(statement)
        return result.all()
                
    async def count_daily_submissions_in_year(self, user_id: int, year: int):
        statement = (
            select(
                func.date(SubmitRecord.created_at).label("submit_date"),
                func.count().label("submit_count")
            )
            .where(
                SubmitRecord.user_id == user_id,
                SubmitRecord.type == "submit",
                func.year(SubmitRecord.created_at) == year
            )
            .group_by(func.date(SubmitRecord.created_at))
        )
        
        result = await self.session.exec(statement)
        return result.all()
                    
    async def query_user_submits_with_question_info(self, user_id: int, page: int, size: int):
        # 先查询总数
        count_statement = (
            select(func.count())
            .select_from(SubmitRecord)
            .where(
                SubmitRecord.user_id == user_id,
                SubmitRecord.type == "submit"
            )
        )
        count_result = await self.session.exec(count_statement)
        total = count_result.first()
        
        # 如果总数为0，直接返回空结果
        if total == 0:
            return 0, [], []
        
        # 构建查询语句，关联SubmitRecord、Question和QuestionTag表
        statement = (
            select(SubmitRecord, Question)
            .join(Question, SubmitRecord.question_id == Question.id)
            .where(
                SubmitRecord.user_id == user_id,
                SubmitRecord.type == "submit"
            )
            .order_by(SubmitRecord.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        
        result = await self.session.exec(statement)
        submit_records = result.all()
        
        # 获取题目ID列表，用于批量查询标签
        question_ids = set([row.Question.id for row in submit_records])
        
        # 如果没有查询到数据，直接返回
        if not question_ids:
            return 0, [], []
        
        # 批量查询标签
        tag_statement = (
            select(QuestionTag)
            .where(QuestionTag.question_id.in_(question_ids))
            .options(selectinload(QuestionTag.tag))
        )
        tag_result = await self.session.exec(tag_statement)
        question_tags = tag_result.all()
        
        return total, submit_records, question_tags
    
    async def query_all_ac_question_ids(self, user_id: int):
        statement = (
            select(SubmitRecord.question_id)
            .where(
                SubmitRecord.user_id == user_id,
                SubmitRecord.type == "submit",
                SubmitRecord.total_test_quantity == SubmitRecord.pass_test_quantity
            )
            .distinct()
        )
        result = await self.session.exec(statement)
        return result.all()

    async def count_submissions_by_hour(self):
        """
        统计一天中每个小时的数据总数，条件是type="submit"
        返回格式: [{"hour": 0, "count": 10}, {"hour": 1, "count": 15}, ...]
        """
        # 使用EXTRACT函数提取小时部分，然后按小时分组统计
        statement = (
            select(
                func.extract("hour", SubmitRecord.created_at).label("hour"),
                func.count(SubmitRecord.id).label("count")
            )
            .where(SubmitRecord.type == "submit")
            .group_by(func.extract("hour", SubmitRecord.created_at))
            .order_by(func.extract("hour", SubmitRecord.created_at))
        )
        
        result = await self.session.exec(statement)
        rows = result.all()
        
        # 创建一个包含24小时的列表，确保没有数据的小时显示为0
        hour_counts = [{"hour": i, "count": 0} for i in range(24)]
        
        # 填入实际查询到的数据
        for row in rows:
            hour_counts[row.hour]["count"] = row.count
            
        return hour_counts

    async def count_submissions_by_language(self):
        """
        统计不同编程语言的提交数量
        返回格式: [{"language_id": 1, "count": 10}, {"language_id": 2, "count": 15}, ...]
        """
        statement = (
            select(
                SubmitRecord.language_id,
                func.count(SubmitRecord.id).label("count")
            )
            .where(SubmitRecord.type == "submit")
            .group_by(SubmitRecord.language_id)
            .order_by(func.count(SubmitRecord.id).desc())  # 按提交数量降序排列
        )
        
        result = await self.session.exec(statement)
        rows = result.all()

        # 返回语言ID和对应提交数量的列表
        return [
            {
                "language_id": row.language_id,
                "count": row.count
            }
            for row in rows
        ]


class JudgeRecordService(MySQLService):
    async def create_many(self, judge_records: list[dict]):
        _judge_records = [JudgeRecord(**judge_record) for judge_record in judge_records]
        self.session.add_all(_judge_records)
        await self.session.commit()

    async def query_by_submit_record_id(self, submit_record_id: int, require_input_output: bool = False):
        if require_input_output:
            statement = (
                select(JudgeRecord)
                .where(JudgeRecord.submit_record_id == submit_record_id)
                .options(selectinload(JudgeRecord.test))
            )
        else:
            statement = select(JudgeRecord).where(JudgeRecord.submit_record_id == submit_record_id)
        judge_records = await self.session.exec(statement)
        return judge_records.all()
