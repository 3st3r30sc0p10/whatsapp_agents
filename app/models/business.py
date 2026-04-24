from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class Business(BaseModel):
    id: str
    name: str
    slug: str
    phone_number_id: str
    business_context: str
    agent_id: Optional[str] = None
    environment_id: Optional[str] = None
    webhook_registered: bool = False
    is_active: bool = True
    plan: Literal["basico", "estandar", "pro"] = "basico"
    monthly_message_limit: int = 500
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class BusinessCreate(BaseModel):
    name: str
    slug: str
    phone_number_id: str
    business_context: str
    plan: Literal["basico", "estandar", "pro"] = "basico"
    monthly_message_limit: int = Field(default=500, ge=-1)


class BusinessUpdate(BaseModel):
    name: Optional[str] = None
    business_context: Optional[str] = None
    plan: Optional[Literal["basico", "estandar", "pro"]] = None
    monthly_message_limit: Optional[int] = Field(default=None, ge=-1)
    is_active: Optional[bool] = None
    webhook_registered: Optional[bool] = None
