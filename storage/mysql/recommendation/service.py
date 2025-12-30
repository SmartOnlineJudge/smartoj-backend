import json

from sqlmodel import text, select
from sqlalchemy.orm import selectinload

from ..base import MySQLService
from .models import UserProfiles
from ..user.models import User


class UserProfilesService(MySQLService):
    async def get_user_profile(self, user_id: int):
        statement = select(UserProfiles).where(UserProfiles.user_id == user_id)
        result = await self.session.exec(statement)
        user_profile: UserProfiles = result.first()
        if not user_profile:
            return None
        return (
            user_profile, 
            {
                "strong_tags": json.loads(user_profile.strong_tags), 
                "weak_tags": json.loads(user_profile.weak_tags)
            }
        )

    async def create_or_update_profile(self, user_id: int):
        sql_stats = """
            SELECT 
                COUNT(*) total_submissions,
                COUNT(DISTINCT CASE WHEN total_test_quantity = pass_test_quantity THEN question_id END) ac_questions_count,
                SUM(CASE WHEN total_test_quantity = pass_test_quantity THEN 1 ELSE 0 END) total_ac_records,
                MAX(created_at) last_active_at
            FROM submit_record
            WHERE user_id = :user_id AND type = 'submit'
        """
        result = await self.session.exec(text(sql_stats), params={"user_id": user_id})
        total_submissions, ac_questions_count, total_ac_records, last_active_at = result.first()

        sql_total_score = """
            WITH unique_passed_questions AS (
                -- 1. 先去重：每个用户通过的每一道题只留一条记录
                SELECT 
                    sr.user_id,
                    sr.question_id,
                    q.score,
                    q.difficulty
                FROM submit_record sr
                JOIN question q ON sr.question_id = q.id
                WHERE sr.user_id = :user_id
                AND sr.total_test_quantity = sr.pass_test_quantity 
                AND sr.type = 'submit'
                GROUP BY sr.user_id, sr.question_id, q.score, q.difficulty -- 核心去重
            ),
            difficulty_stats AS (
                -- 2. 统计各难度的题目数量，并按数量排名
                SELECT 
                    difficulty,
                    SUM(score) as diff_score,
                    COUNT(*) as cnt,
                    ROW_NUMBER() OVER(ORDER BY COUNT(*) DESC, difficulty ASC) as rn
                FROM unique_passed_questions
                GROUP BY difficulty
            )
            -- 3. 最终汇总：计算总分 + 提取排名第一的难度
            SELECT 
                SUM(diff_score) as total_score,
                MAX(CASE WHEN rn = 1 THEN difficulty END) as strong_difficulty
            FROM difficulty_stats;
        """
        result = await self.session.exec(text(sql_total_score), params={"user_id": user_id})
        total_score, strong_difficulty = result.first()

        sql_tags_statistics = """
            SELECT 
                qt.tag_id,
                t.name AS tag_name,
                COUNT(CASE WHEN sr.type = 'submit' THEN sr.id END) AS total_submissions,
                COUNT(
                    DISTINCT CASE 
                    WHEN sr.total_test_quantity = sr.pass_test_quantity AND sr.type = 'submit'
                    THEN sr.question_id 
                    END
                ) AS ac_question_count -- 该标签下 AC 的去重题目数
            FROM submit_record sr
            JOIN question_tag qt ON sr.question_id = qt.question_id
            JOIN tag t ON qt.tag_id = t.id
            WHERE sr.user_id = :user_id
            GROUP BY qt.tag_id;
        """
        result = await self.session.exec(text(sql_tags_statistics), params={"user_id": user_id})
        tags_statistics = result.all()

        # 计算每个标签的AC率
        tags_with_ac_rate = []
        for tag_id, tag_name, _total_submissions, ac_question_count in tags_statistics:
            # 避免除以零错误
            ac_rate = round(ac_question_count / _total_submissions * 100, 2) if _total_submissions > 0 else 0
            tags_with_ac_rate.append({
                "tag_id": tag_id,
                "tag_name": tag_name,
                "total_submissions": _total_submissions,
                "ac_question_count": ac_question_count,
                "ac_rate": ac_rate
            })

        # 筛选strong_tags：过滤total_submissions >= 5的标签，筛选AC率 >= 80%的标签，按AC率从高到低排序
        strong_tags = json.dumps([tag for tag in tags_with_ac_rate if tag["total_submissions"] >= 5 and tag["ac_rate"] >= 80])
        # 筛选weak_tags：过滤total_submissions >= 5的标签，筛选AC率 < 20%的标签，按total_submissions从高到低排序
        weak_tags = json.dumps([tag for tag in tags_with_ac_rate if tag["total_submissions"] >= 5 and tag["ac_rate"] < 20])
        # 计算全局AC率和平均尝试次数
        global_ac_rate = round(total_ac_records / total_submissions, 2) if total_submissions > 0 else 0
        avg_try_count = round(total_submissions / ac_questions_count, 2) if ac_questions_count > 0 else 0

        statement = select(UserProfiles).where(UserProfiles.user_id == user_id)
        results = await self.session.exec(statement)
        user_profile: UserProfiles | None = results.first()
        if not user_profile:
            user_profile = UserProfiles(
                user_id=user_id,
                strong_difficulty=strong_difficulty,
                last_active_at=last_active_at,
                total_score=total_score,
                strong_tags=strong_tags,
                weak_tags=weak_tags,
                global_ac_rate=global_ac_rate,
                avg_try_count=avg_try_count,
            )
        else:
            user_profile.strong_difficulty = strong_difficulty
            user_profile.last_active_at = last_active_at
            user_profile.total_score = total_score
            user_profile.strong_tags = strong_tags
            user_profile.weak_tags = weak_tags
            user_profile.global_ac_rate = global_ac_rate
            user_profile.avg_try_count = avg_try_count

        self.session.add(user_profile)
        await self.session.commit()

    async def get_top_users_by_score(self, limit: int = 5):
        statement = (
            select(UserProfiles)
            .options(selectinload(UserProfiles.user).selectinload(User.user_dynamic))
            .order_by(UserProfiles.total_score.desc())
            .limit(limit)
        )
        result = await self.session.exec(statement)
        return result.all()
