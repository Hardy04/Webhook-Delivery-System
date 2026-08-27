import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.orm import Event
from app.models.schemas import EventCreate, EventRead, IngestResponse
from app.services.delivery import (
    _subscriptions_for_event,
    create_delivery_attempts,
    deliver_attempt,
)

router = APIRouter(prefix="/events", tags=["events"])


def _fanout_and_deliver(event_id: str) -> None:
    """Background task: fan-out and fire first delivery attempt for all matches."""
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        event = db.get(Event, event_id)
        if not event:
            return
        subs = _subscriptions_for_event(db, event.event_type)
        attempts = create_delivery_attempts(db, event, subs)
        for attempt in attempts:
            deliver_attempt(db, attempt)
    finally:
        db.close()


@router.post("/", response_model=IngestResponse, status_code=status.HTTP_202_ACCEPTED)
def ingest_event(
    body: EventCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> IngestResponse:
    event = Event(
        id=str(uuid.uuid4()),
        event_type=body.event_type,
        payload=json.dumps(body.payload),
        received_at=datetime.now(timezone.utc),
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    subs = _subscriptions_for_event(db, event.event_type)
    background_tasks.add_task(_fanout_and_deliver, event.id)

    return IngestResponse(event_id=event.id, queued_deliveries=len(subs))


@router.get("/", response_model=list[EventRead])
def list_events(
    limit: int = 50, db: Session = Depends(get_db)
) -> list[EventRead]:
    return (
        db.query(Event)
        .order_by(Event.received_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/{event_id}", response_model=EventRead)
def get_event(event_id: str, db: Session = Depends(get_db)) -> EventRead:
    from fastapi import HTTPException
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event
