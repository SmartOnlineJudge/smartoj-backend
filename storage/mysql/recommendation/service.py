import json

from sqlmodel import text, select

from ..base import MySQLService
from .models import UserProfiles


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
        total_submissions, ac_questions_count, total_ac_records, last_active_at = result.one()

        sql_total_score = """
            SELECT 
                SUM(base.score) as total_score,
                -- 通过窗口函数，在按用户分组的结果中，取 AC 数量最多的难度
                FIRST_VALUE(base.difficulty) OVER(
                    PARTITION BY base.user_id 
                    ORDER BY COUNT(*) DESC
                ) as strong_difficulty
            FROM (
                -- 子查询：先去重，每个用户每道题只保留一条通过记录
                SELECT DISTINCT 
                    sr.user_id, 
                    sr.question_id, 
                    q.score, 
                    q.difficulty
                FROM submit_record sr
                JOIN question q ON sr.question_id = q.id
                WHERE sr.total_test_quantity = sr.pass_test_quantity AND sr.type = 'submit'  -- 仅统计通过的记录
            ) AS base
            WHERE base.user_id = :user_id
            GROUP BY base.user_id, base.difficulty;
        """
        result = await self.session.exec(text(sql_total_score), params={"user_id": user_id})
        total_score, strong_difficulty = result.one()

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
