import asyncio

from fastapi import APIRouter, Depends, Body

from storage.mysql import executors
from utils.responses import SmartOJResponse, ResponseCodes
from utils.user.auth import get_current_user
from .models import Question

router = APIRouter()


@router.post("", summary="题目信息增加")
async def get_question_info(
        user: dict = Depends(get_current_user),
        question_info: Question = Body()
):
    publisher_id = await executors.user.get_id_by_user_id(user["user_id"])
    qid = await executors.question.question_add(title=question_info.title, description=question_info.description,
                                                difficulty=question_info.difficulty,
                                                publisher_id=publisher_id["id"])
    tasks = [
        executors.tag.add_tags_by_qid(qid, question_info.tags_ids),
        executors.test.add_test_by_qid(qid, question_info.input_outputs),
        executors.memory_time_limit.add_memory_time_limit_by_qid(qid, question_info.limit_datas),
        executors.solving_framework.add_solving_frameworks_by_qid(qid, question_info.framework_datas),
        executors.judge_template.add_judge_templates_by_qid(qid, question_info.judge_templates)
    ]
    await asyncio.gather(*tasks)
    return SmartOJResponse(ResponseCodes.OK)
