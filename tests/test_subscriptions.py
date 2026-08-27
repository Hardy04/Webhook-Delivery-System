def test_create_subscription(client):
    r = client.post("/subscriptions/", json={
        "url": "https://example.com/hook",
        "event_types": ["order.created"],
        "description": "Test sub",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["url"] == "https://example.com/hook"
    assert data["event_types"] == ["order.created"]
    assert data["is_active"] is True
    assert "id" in data
    # Secret must not be returned
    assert "secret" not in data


def test_create_wildcard_subscription(client):
    r = client.post("/subscriptions/", json={"url": "https://example.com/hook"})
    assert r.status_code == 201
    assert r.json()["event_types"] == ["*"]


def test_list_subscriptions(client):
    client.post("/subscriptions/", json={"url": "https://a.com/hook"})
    client.post("/subscriptions/", json={"url": "https://b.com/hook"})
    r = client.get("/subscriptions/")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_deactivate_removes_from_active_list(client):
    sub_id = client.post("/subscriptions/", json={"url": "https://a.com/hook"}).json()["id"]
    client.patch(f"/subscriptions/{sub_id}/deactivate")
    active = client.get("/subscriptions/?active_only=true").json()
    assert all(s["id"] != sub_id for s in active)


def test_activate_subscription(client):
    sub_id = client.post("/subscriptions/", json={"url": "https://a.com/hook"}).json()["id"]
    client.patch(f"/subscriptions/{sub_id}/deactivate")
    r = client.patch(f"/subscriptions/{sub_id}/activate")
    assert r.json()["is_active"] is True


def test_delete_subscription(client):
    sub_id = client.post("/subscriptions/", json={"url": "https://a.com/hook"}).json()["id"]
    r = client.delete(f"/subscriptions/{sub_id}")
    assert r.status_code == 204
    r2 = client.get(f"/subscriptions/{sub_id}")
    assert r2.status_code == 404


def test_get_nonexistent_subscription(client):
    r = client.get("/subscriptions/does-not-exist")
    assert r.status_code == 404
