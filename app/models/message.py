from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class KapsoTextContent(BaseModel):
    body: str


class KapsoMessage(BaseModel):
    id: str
    from_: str = Field(alias="from")
    type: Literal["text", "audio", "image", "document", "interactive"]
    text: Optional[KapsoTextContent] = None
    timestamp: str

    model_config = ConfigDict(populate_by_name=True)


class KapsoWebhookPayload(BaseModel):
    event: str
    phone_number_id: str
    message: Optional[KapsoMessage] = None
