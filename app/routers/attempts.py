from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.orm import DeliveryAttempt
from app.models.schemas import DeliveryAttemptRead

router = APIRouter(prefix="/delivery-attempts", tags=["delivery"])


@router.get("/", response_model=list[DeliveryAttemptRead])
def list_attempts(
    event_id: str | None = None,
    subscription_id: str | None = None,
    status: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[DeliveryAttemptRead]:
    q = db.query(DeliveryAttempt)
    if event_id:
        q = q.filter(DeliveryAttempt.event_id == event_id)
    if subscription_id:
        q = q.filter(DeliveryAttempt.subscription_id == subscription_id)
    if status:
        q = q.filter(DeliveryAttempt.status == status)
    return q.order_by(DeliveryAttempt.created_at.desc()).limit(limit).all()


@router.get("/{attempt_id}", response_model=DeliveryAttemptRead)
def get_attempt(attempt_id: str, db: Session = Depends(get_db)) -> DeliveryAttemptRead:
    attempt = db.get(DeliveryAttempt, attempt_id)
    if not attempt:
        raise HTTPException(status_code=404, detail="Delivery attempt not found")
    return attempt
