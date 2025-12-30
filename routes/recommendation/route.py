import asyncio

from fastapi import APIRouter

from utils.responses import SmartOJResponse, ResponseCodes
from utils.dependencies import (
    CurrentUserDependency, 
    UserProfilesServiceDependency, 
    QuestionTagServiceDependency, 
    SubmitRecordDependency
)
from core.algorithm_knowledge_graph import graph
from .models import UserProfileOut


router = APIRouter()


@router.get("/user-profile", summary="查询用户画像")
async def query_user_profiles(
    user: CurrentUserDependency,
    service: UserProfilesServiceDependency
):
    """
    ## 响应代码说明:
    **200**: 业务逻辑执行成功
    """
    user_profile, tags_metadata = await service.get_user_profile(user["id"])
    if user_profile is None:
        return SmartOJResponse(ResponseCodes.OK, data={})
    result = UserProfileOut.model_validate(user_profile)
    result = result.model_dump()
    result.update(tags_metadata)
    return SmartOJResponse(ResponseCodes.OK, data=result)


@router.get("/questions", summary="查询推荐题目列表")
async def query_recommend_questions(
    user: CurrentUserDependency,
    user_profiles_service: UserProfilesServiceDependency,
    question_tag_service: QuestionTagServiceDependency,
    submit_record_service: SubmitRecordDependency
):
    """
    ## 响应代码说明:
    **200**: 业务逻辑执行成功
    """
    user_profile, tags_metadata = await user_profiles_service.get_user_profile(user["id"])
    if user_profile is None:
        return SmartOJResponse(ResponseCodes.OK, data=[])
    # 1. 获取基础画像数据
    strong_tags = tags_metadata["strong_tags"]
    weak_tags = tags_metadata["weak_tags"]
    strong_difficulty = user_profile.strong_difficulty
    
    # --- 第一阶段：计算目标标签池 (Target Tags) ---
    target_tags: set[int] = set()
    advantage_tags: set[int] = set()
    disadvantage_tags: set[int] = set()
    
    # 策略 A：对于不擅长的标签，直接加入目标池（修复逻辑）
    for item in weak_tags:
        disadvantage_tags.add(item["tag_id"])

    # 策略 B：基于擅长的标签，直接加入目标池。
    # 只有当 strong_tags 里的标签“达标”了，利用知识图谱解锁后继（进阶逻辑）
    # 达标条件：ac_rate >= 70% 且 ac_question_count >= 30
    for item in strong_tags:
        advantage_tags.add(item["tag_id"])
        if item["ac_rate"] >= 70 and item["ac_question_count"] >= 30:
            successors = graph.get_successors(item["tag_name"])
            for next_tag in successors:
                advantage_tags.add(next_tag)
    
    # 如果用户太菜，连 weak_tags 都没有，则默认推荐基础标签
    target_tags = advantage_tags | disadvantage_tags
    if not target_tags:
        target_tags = {1, 4, 15}

    # --- 第二阶段：根据标签池过滤题目 ---
    recommend_questions = []
    recommend_question_ids = set()
    # 查询所有符合标签池的题目和用户已AC的题目
    question_tags, ac_question_ids = await asyncio.gather(
        question_tag_service.query_question_tag_by_tag_ids(list(target_tags)), 
        submit_record_service.query_all_ac_question_ids(user["id"])
    )
    ac_question_ids = set(ac_question_ids)
    # 过滤出用户未AC的题目
    question_tags = [question_tag for question_tag in question_tags if question_tag.question.id not in ac_question_ids]
    for question_tag in question_tags:
        # 难度过滤：优先匹配用户 strong_difficulty 的题目
        score = 0
        if question_tag.question.difficulty == strong_difficulty:
            score += 100
        elif question_tag.question.difficulty == "easy": # 兜底逻辑：简单题总是更稳妥
            score += 50
        # 优势标签低分过滤，劣势标签高分过滤
        if question_tag.tag_id in advantage_tags:
            score += 50
        else:
            score += 100
        # 避免重复添加题目
        if question_tag.question.id in recommend_question_ids:
            continue
        recommend_question_ids.add(question_tag.question.id)
        recommend_questions.append({
            "question_id": question_tag.question.id,
            "question_title": question_tag.question.title,
            "difficulty": question_tag.question.difficulty,
            "score": score
        })
    recommend_questions.sort(key=lambda x: x["score"], reverse=True)
    return SmartOJResponse(ResponseCodes.OK, data=recommend_questions[:5])
