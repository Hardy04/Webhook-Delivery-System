def test_ingest_event_no_subscribers(client):
    r = client.post("/events/", json={"event_type": "user.login", "payload": {"uid": 1}})
    assert r.status_code == 202
    assert r.json()["queued_deliveries"] == 0


def test_ingest_event_with_matching_subscriber(client):
    client.post("/subscriptions/", json={
        "url": "https://httpbin.org/post",
        "event_types": ["user.login"],
    })
    r = client.post("/events/", json={"event_type": "user.login", "payload": {"uid": 1}})
    assert r.status_code == 202
    assert r.json()["queued_deliveries"] == 1


def test_wildcard_subscriber_receives_all_events(client):
    client.post("/subscriptions/", json={
        "url": "https://httpbin.org/post",
        "event_types": ["*"],
    })
    r = client.post("/events/", json={"event_type": "anything.happened", "payload": {}})
    assert r.json()["queued_deliveries"] == 1


def test_non_matching_event_type_not_queued(client):
    client.post("/subscriptions/", json={
        "url": "https://httpbin.org/post",
        "event_types": ["order.created"],
    })
    r = client.post("/events/", json={"event_type": "payment.failed", "payload": {}})
    assert r.json()["queued_deliveries"] == 0


def test_event_stored_and_retrievable(client):
    ev = client.post("/events/", json={
        "event_type": "test.event",
        "payload": {"key": "value"},
    }).json()
    r = client.get(f"/events/{ev['event_id']}")
    assert r.status_code == 200
    assert r.json()["event_type"] == "test.event"


def test_list_events(client):
    client.post("/events/", json={"event_type": "a.b", "payload": {}})
    client.post("/events/", json={"event_type": "c.d", "payload": {}})
    r = client.get("/events/")
    assert r.status_code == 200
    assert len(r.json()) >= 2


def test_inactive_subscriber_not_targeted(client):
    sub_id = client.post("/subscriptions/", json={
        "url": "https://httpbin.org/post",
        "event_types": ["order.created"],
    }).json()["id"]
    client.patch(f"/subscriptions/{sub_id}/deactivate")
    r = client.post("/events/", json={"event_type": "order.created", "payload": {}})
    assert r.json()["queued_deliveries"] == 0
