import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.orm import Subscription
from app.models.schemas import SubscriptionCreate, SubscriptionRead

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


def _serialize(sub: Subscription) -> SubscriptionRead:
    return SubscriptionRead.model_validate(
        {
            **sub.__dict__,
            "event_types": [t.strip() for t in sub.event_types.split(",") if t.strip()],
        }
    )


@router.post("/", response_model=SubscriptionRead, status_code=status.HTTP_201_CREATED)
def create_subscription(
    body: SubscriptionCreate, db: Session = Depends(get_db)
) -> SubscriptionRead:
    sub = Subscription(
        id=str(uuid.uuid4()),
        url=str(body.url),
        event_types=",".join(body.event_types) if body.event_types else "*",
        secret=secrets.token_hex(32),
        description=body.description,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return _serialize(sub)


@router.get("/", response_model=list[SubscriptionRead])
def list_subscriptions(
    active_only: bool = True, db: Session = Depends(get_db)
) -> list[SubscriptionRead]:
    q = db.query(Subscription)
    if active_only:
        q = q.filter(Subscription.is_active == True)  # noqa: E712
    return [_serialize(s) for s in q.order_by(Subscription.created_at.desc()).all()]


@router.get("/{subscription_id}", response_model=SubscriptionRead)
def get_subscription(
    subscription_id: str, db: Session = Depends(get_db)
) -> SubscriptionRead:
    sub = db.get(Subscription, subscription_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return _serialize(sub)


@router.patch("/{subscription_id}/deactivate", response_model=SubscriptionRead)
def deactivate_subscription(
    subscription_id: str, db: Session = Depends(get_db)
) -> SubscriptionRead:
    sub = db.get(Subscription, subscription_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    sub.is_active = False
    db.commit()
    db.refresh(sub)
    return _serialize(sub)


@router.patch("/{subscription_id}/activate", response_model=SubscriptionRead)
def activate_subscription(
    subscription_id: str, db: Session = Depends(get_db)
) -> SubscriptionRead:
    sub = db.get(Subscription, subscription_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    sub.is_active = True
    db.commit()
    db.refresh(sub)
    return _serialize(sub)


@router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subscription(
    subscription_id: str, db: Session = Depends(get_db)
) -> None:
    sub = db.get(Subscription, subscription_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    db.delete(sub)
    db.commit()
