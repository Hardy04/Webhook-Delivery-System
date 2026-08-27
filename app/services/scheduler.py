import asyncio
import logging
from datetime import datetime, timezone

from app.config import settings
from app.models.orm import DeliveryAttempt
from app.services.delivery import deliver_attempt

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _run_due_retries() -> int:
    """Find pending attempts whose next_retry_at is due and execute them. Returns count."""
    from app.database import SessionLocal

    db = SessionLocal()
    processed = 0
    try:
        due = (
            db.query(DeliveryAttempt)
            .filter(
                DeliveryAttempt.status == "pending",
                DeliveryAttempt.next_retry_at <= _now(),
            )
            .all()
        )
        for attempt in due:
            logger.info(
                "Retrying attempt %s (attempt #%d for event %s)",
                attempt.id,
                attempt.attempt_number,
                attempt.event_id,
            )
            deliver_attempt(db, attempt)
            processed += 1
    except Exception:
        logger.exception("Error in retry worker cycle")
    finally:
        db.close()
    return processed


async def retry_worker() -> None:
    """Asyncio task: poll for due retry attempts on a fixed interval."""
    logger.info(
        "Retry worker started (interval=%ds)", settings.worker_poll_interval_seconds
    )
    while True:
        count = _run_due_retries()
        if count:
            logger.info("Retry worker processed %d attempts", count)
        await asyncio.sleep(settings.worker_poll_interval_seconds)
