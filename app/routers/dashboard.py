import json
from dataclasses import dataclass

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.orm import DeliveryAttempt, Event, Subscription

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory="app/templates")


@dataclass
class StatTile:
    label: str
    value: str | int
    color: str


@dataclass
class EventRow:
    event: Event
    total: int
    success: int
    failed: int
    pending: int
    dead: int


def _build_stats(db: Session) -> list[StatTile]:
    total_events = db.query(Event).count()
    total_subs = db.query(Subscription).filter(Subscription.is_active == True).count()  # noqa: E712
    total_success = db.query(DeliveryAttempt).filter(DeliveryAttempt.status == "success").count()
    total_dead = db.query(DeliveryAttempt).filter(DeliveryAttempt.status == "dead").count()
    return [
        StatTile("Total Events", total_events, "text-indigo-600"),
        StatTile("Active Subscriptions", total_subs, "text-indigo-600"),
        StatTile("Successful Deliveries", total_success, "text-green-600"),
        StatTile("Dead Letters", total_dead, "text-red-600"),
    ]


def _build_event_rows(db: Session, limit: int = 50) -> list[EventRow]:
    events = (
        db.query(Event).order_by(Event.received_at.desc()).limit(limit).all()
    )
    rows = []
    for ev in events:
        attempts = ev.attempts
        rows.append(
            EventRow(
                event=ev,
                total=len(attempts),
                success=sum(1 for a in attempts if a.status == "success"),
                failed=sum(1 for a in attempts if a.status == "failed"),
                pending=sum(1 for a in attempts if a.status == "pending"),
                dead=sum(1 for a in attempts if a.status == "dead"),
            )
        )
    return rows


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "stats": _build_stats(db),
            "events": _build_event_rows(db),
        },
    )


@router.get("/dashboard/events/{event_id}", response_class=HTMLResponse)
def event_detail(
    event_id: str, request: Request, db: Session = Depends(get_db)
) -> HTMLResponse:
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    try:
        payload_pretty = json.dumps(json.loads(event.payload), indent=2)
    except (ValueError, TypeError):
        payload_pretty = event.payload

    attempts = (
        db.query(DeliveryAttempt)
        .filter(DeliveryAttempt.event_id == event_id)
        .order_by(DeliveryAttempt.attempt_number)
        .all()
    )

    return templates.TemplateResponse(
        request,
        "event_detail.html",
        {
            "event": event,
            "payload_pretty": payload_pretty,
            "attempts": attempts,
        },
    )


@router.get("/subscriptions-ui", response_class=HTMLResponse)
def subscriptions_ui(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    subs = (
        db.query(Subscription).order_by(Subscription.created_at.desc()).all()
    )
    # Convert event_types string to list for template
    for sub in subs:
        sub.event_types = [t.strip() for t in sub.event_types.split(",") if t.strip()]

    return templates.TemplateResponse(
        request,
        "subscriptions_ui.html",
        {"subscriptions": subs},
    )
