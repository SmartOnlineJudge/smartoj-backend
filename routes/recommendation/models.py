import json
from datetime import datetime

from pydantic import Field


from utils.models import SmartOJSQLModel


class UserProfileTag(SmartOJSQLModel):
    tag_id: int
    ac_rate: float
    tag_name: str
    ac_question_count: int
    total_submissions: int


class UserProfileOut(SmartOJSQLModel):
    last_active_at: datetime
    strong_difficulty: str
    avg_try_count: float
    total_score: int
    global_ac_rate: float
