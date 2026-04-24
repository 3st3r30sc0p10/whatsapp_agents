from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AgentSession(BaseModel):
    id: str
    client_phone: str
    business_id: str
    session_id: str
    message_count: int = 0
    last_message_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class MessageLog(BaseModel):
    id: str
    business_id: str
    client_phone: str
    direction: str
    content: str
    whatsapp_message_id: Optional[str] = None
    processed_at: Optional[datetime] = None


class UsageCounter(BaseModel):
    id: str
    business_id: str
    month_year: str
    message_count: int = 0
