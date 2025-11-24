from sqlmodel import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func

from ..base import MySQLService
from .models import SubmitRecord, JudgeRecord
from ..user.models import UserDynamic, User


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
