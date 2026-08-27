from datetime import datetime
from typing import Any

from pydantic import BaseModel, HttpUrl, field_validator


# ── Subscription ──────────────────────────────────────────────────────────────

class SubscriptionCreate(BaseModel):
    url: HttpUrl
    event_types: list[str] = ["*"]
    description: str | None = None

    @field_validator("event_types")
    @classmethod
    def normalize_event_types(cls, v: list[str]) -> list[str]:
        return [t.strip().lower() for t in v if t.strip()]


class SubscriptionRead(BaseModel):
    id: str
    url: str
    event_types: list[str]
    description: str | None
    is_active: bool
    created_at: datetime
    # Secret is intentionally omitted from read responses

    model_config = {"from_attributes": True}

    @field_validator("event_types", mode="before")
    @classmethod
    def split_event_types(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return [t.strip() for t in v.split(",") if t.strip()]
        return v


# ── Event ─────────────────────────────────────────────────────────────────────

class EventCreate(BaseModel):
    event_type: str
    payload: dict[str, Any]


class EventRead(BaseModel):
    id: str
    event_type: str
    payload: str  # raw JSON string stored in DB
    received_at: datetime

    model_config = {"from_attributes": True}


# ── DeliveryAttempt ───────────────────────────────────────────────────────────

class DeliveryAttemptRead(BaseModel):
    id: str
    event_id: str
    subscription_id: str
    attempt_number: int
    status: str
    response_code: int | None
    error_message: str | None
    attempted_at: datetime | None
    next_retry_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Ingest response ───────────────────────────────────────────────────────────

class IngestResponse(BaseModel):
    event_id: str
    queued_deliveries: int
