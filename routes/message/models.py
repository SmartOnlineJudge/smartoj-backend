from datetime import datetime
from enum import Enum

from utils.models import SmartOJSQLModel


class MessageType(str, Enum):
    REPLY = "reply"
    SYSTEM = "system"


class MessageOut(SmartOJSQLModel):
    id: int
    title: str
    content: str
    created_at: datetime
    type: MessageType
    is_read: bool
