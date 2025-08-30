from sqlmodel import select
from sqlalchemy.orm import selectinload

from ..base import MySQLService
from .models import SubmitRecord, JudgeRecord, Test


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
