import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.models.orm import DeliveryAttempt, Event, Subscription
from app.services.delivery import _retry_delay_seconds, deliver_attempt


def _make_sub(db_session) -> Subscription:
    sub = Subscription(
        id=str(uuid.uuid4()),
        url="https://httpbin.org/post",
        event_types="order.created",
        secret="test-secret-value",
        is_active=True,
    )
    db_session.add(sub)
    return sub


def _make_event(db_session) -> Event:
    ev = Event(
        id=str(uuid.uuid4()),
        event_type="order.created",
        payload='{"order_id": "ORD-001"}',
    )
    db_session.add(ev)
    return ev


def _make_attempt(db_session, sub: Subscription, ev: Event, attempt_number: int = 1) -> DeliveryAttempt:
    attempt = DeliveryAttempt(
        id=str(uuid.uuid4()),
        event_id=ev.id,
        subscription_id=sub.id,
        attempt_number=attempt_number,
        status="pending",
    )
    db_session.add(attempt)
    db_session.commit()
    return attempt


def test_retry_delay_ladder():
    assert _retry_delay_seconds(1) == 0
    assert _retry_delay_seconds(2) == 60
    assert _retry_delay_seconds(3) == 300
    assert _retry_delay_seconds(4) == 1800
    assert _retry_delay_seconds(5) == 7200


def test_successful_delivery_marks_success(db_session):
    sub = _make_sub(db_session)
    ev = _make_event(db_session)
    db_session.commit()
    attempt = _make_attempt(db_session, sub, ev)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "OK"

    with patch("app.services.delivery.httpx.Client") as MockClient:
        MockClient.return_value.__enter__.return_value.post.return_value = mock_response
        deliver_attempt(db_session, attempt)

    db_session.refresh(attempt)
    assert attempt.status == "success"
    assert attempt.response_code == 200


def test_failed_delivery_creates_retry_attempt(db_session):
    sub = _make_sub(db_session)
    ev = _make_event(db_session)
    db_session.commit()
    attempt = _make_attempt(db_session, sub, ev)

    mock_response = MagicMock()
    mock_response.status_code = 503
    mock_response.text = "Service Unavailable"

    with patch("app.services.delivery.httpx.Client") as MockClient:
        MockClient.return_value.__enter__.return_value.post.return_value = mock_response
        deliver_attempt(db_session, attempt)

    db_session.refresh(attempt)
    assert attempt.status == "failed"

    retry = (
        db_session.query(DeliveryAttempt)
        .filter(
            DeliveryAttempt.event_id == ev.id,
            DeliveryAttempt.attempt_number == 2,
        )
        .first()
    )
    assert retry is not None
    assert retry.status == "pending"
    assert retry.next_retry_at is not None


def test_max_attempts_marks_dead(db_session):
    sub = _make_sub(db_session)
    ev = _make_event(db_session)
    db_session.commit()
    attempt = _make_attempt(db_session, sub, ev, attempt_number=5)

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Error"

    with patch("app.services.delivery.httpx.Client") as MockClient:
        MockClient.return_value.__enter__.return_value.post.return_value = mock_response
        deliver_attempt(db_session, attempt)

    db_session.refresh(attempt)
    assert attempt.status == "dead"

    # No further retry attempt created
    retries = (
        db_session.query(DeliveryAttempt)
        .filter(DeliveryAttempt.event_id == ev.id, DeliveryAttempt.attempt_number == 6)
        .all()
    )
    assert len(retries) == 0


def test_signature_header_sent(db_session):
    sub = _make_sub(db_session)
    ev = _make_event(db_session)
    db_session.commit()
    attempt = _make_attempt(db_session, sub, ev)

    captured_headers = {}

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "OK"

    def fake_post(url, content, headers):
        captured_headers.update(headers)
        return mock_response

    with patch("app.services.delivery.httpx.Client") as MockClient:
        MockClient.return_value.__enter__.return_value.post.side_effect = fake_post
        deliver_attempt(db_session, attempt)

    assert "X-Webhook-Signature" in captured_headers
    assert captured_headers["X-Webhook-Signature"].startswith("sha256=")
    assert captured_headers["X-Webhook-Event"] == "order.created"
