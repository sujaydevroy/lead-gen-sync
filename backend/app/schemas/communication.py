from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator

from app.schemas.common import CamelModel


class AttachmentOut(CamelModel):
    id: int
    name: str
    size: int
    type: str | None = None
    url: str


class CommunicationOut(CamelModel):
    """Same shape as the frontend's communication records."""

    id: str
    dealer_id: str
    dealer_name: str
    type: str
    direction: Literal["inbound", "outbound"]
    sender: str
    recipient: str
    subject: str
    body: str | None = None
    status: str
    created_at: datetime
    attachments: list[AttachmentOut] = Field(default_factory=list)


class CommunicationStats(CamelModel):
    sent: int
    received: int
    total: int


class InteractionCreate(CamelModel):
    type: Literal["Email", "Call"]
    subject: str = Field(min_length=1, max_length=200)

    @field_validator("subject", mode="before")
    @classmethod
    def _strip(cls, value):
        return value.strip() if isinstance(value, str) else value
