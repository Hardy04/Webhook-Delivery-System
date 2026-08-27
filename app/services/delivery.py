import json
import uuid
from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models.orm import DeliveryAttempt, Event, Subscription
from app.services.signer import sign_payload


def _retry_delay_seconds(attempt_number: int) -> int:
    """Exponential backoff ladder (seconds):  1→0, 2→60, 3→300, 4→1800, 5→7200."""
    ladder = [0, 60, 300, 1800, 7200]
    idx = min(attempt_number - 1, len(ladder) - 1)
    return ladder[idx]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_delivery_attempts(
    db: Session, event: Event, subscriptions: list[Subscription]
) -> list[DeliveryAttempt]:
    """Fan-out: create one pending DeliveryAttempt per matching active subscription."""
    attempts = []
    for sub in subscriptions:
        attempt = DeliveryAttempt(
            id=str(uuid.uuid4()),
            event_id=event.id,
            subscription_id=sub.id,
            attempt_number=1,
            status="pending",
        )
        db.add(attempt)
        attempts.append(attempt)
    db.commit()
    return attempts


def _subscriptions_for_event(db: Session, event_type: str) -> list[Subscription]:
    all_active = (
        db.query(Subscription).filter(Subscription.is_active == True).all()  # noqa: E712
    )
    matched = []
    for sub in all_active:
        types = [t.strip() for t in sub.event_types.split(",")]
        if "*" in types or event_type in types:
            matched.append(sub)
    return matched


def deliver_attempt(db: Session, attempt: DeliveryAttempt) -> None:
    """Execute one delivery attempt, update status, schedule retry if needed."""
    sub = db.get(Subscription, attempt.subscription_id)
    event = db.get(Event, attempt.event_id)
    if not sub or not event:
        attempt.status = "dead"
        attempt.error_message = "Subscription or event no longer exists"
        db.commit()
        return

    payload_bytes = event.payload.encode()
    signature = sign_payload(sub.secret, payload_bytes)

    headers = {
        "Content-Type": "application/json",
        "X-Webhook-ID": event.id,
        "X-Webhook-Event": event.event_type,
        "X-Webhook-Signature": signature,
        "X-Webhook-Attempt": str(attempt.attempt_number),
    }

    attempt.status = "delivering"
    attempt.attempted_at = _now()
    db.commit()

    try:
        with httpx.Client(timeout=settings.request_timeout_seconds) as client:
            response = client.post(sub.url, content=payload_bytes, headers=headers)

        attempt.response_code = response.status_code
        attempt.response_body = response.text[:2000]  # cap stored body size

        if 200 <= response.status_code < 300:
            attempt.status = "success"
            attempt.next_retry_at = None
        else:
            _schedule_retry_or_dead(db, attempt)

    except httpx.RequestError as exc:
        attempt.error_message = str(exc)
        _schedule_retry_or_dead(db, attempt)

    db.commit()


def _schedule_retry_or_dead(db: Session, attempt: DeliveryAttempt) -> None:
    if attempt.attempt_number >= settings.max_delivery_attempts:
        attempt.status = "dead"
        return

    # Create the next retry attempt record
    delay = _retry_delay_seconds(attempt.attempt_number + 1)
    from datetime import timedelta

    next_at = _now() + timedelta(seconds=delay)

    next_attempt = DeliveryAttempt(
        id=str(uuid.uuid4()),
        event_id=attempt.event_id,
        subscription_id=attempt.subscription_id,
        attempt_number=attempt.attempt_number + 1,
        status="pending",
        next_retry_at=next_at,
    )
    db.add(next_attempt)
    attempt.status = "failed"
