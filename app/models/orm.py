import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    # Comma-separated event types, or "*" for all
    event_types: Mapped[str] = mapped_column(Text, nullable=False, default="*")
    secret: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    attempts: Mapped[list["DeliveryAttempt"]] = relationship(
        "DeliveryAttempt", back_populates="subscription"
    )


class Event(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)  # JSON string
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    attempts: Mapped[list["DeliveryAttempt"]] = relationship(
        "DeliveryAttempt", back_populates="event"
    )


class DeliveryAttempt(Base):
    __tablename__ = "delivery_attempts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    event_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("events.id"), nullable=False
    )
    subscription_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("subscriptions.id"), nullable=False
    )
    attempt_number: Mapped[int] = mapped_column(Integer, default=1)
    # pending | delivering | success | failed | dead
    status: Mapped[str] = mapped_column(String(16), default="pending")
    response_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    next_retry_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    event: Mapped["Event"] = relationship("Event", back_populates="attempts")
    subscription: Mapped["Subscription"] = relationship(
        "Subscription", back_populates="attempts"
    )
