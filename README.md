# Webhook Delivery System

A production-style webhook infrastructure service — reliable event delivery to subscriber URLs with HMAC-SHA256 signature verification, exponential-backoff retries, and a live delivery log dashboard.

This is exactly how Stripe and GitHub-style webhook infrastructure works.

---

## Features

| Feature | Detail |
|---|---|
| **Event ingestion** | `POST /events/` accepts any JSON payload + event type |
| **Subscription management** | Register subscriber URLs with per-event-type filtering |
| **HMAC-SHA256 signing** | Every delivery carries `X-Webhook-Signature: sha256=<hex>` |
| **Reliable delivery** | Immediate attempt on ingest; retries on failure |
| **Exponential backoff** | Retry ladder: 0s → 1m → 5m → 30m → 2h → dead |
| **Dead-letter tracking** | Exhausted attempts are marked `dead`, not silently dropped |
| **Delivery log dashboard** | HTML UI at `/` showing every event and its delivery status |
| **Auto-generated API docs** | Swagger UI at `/docs` |

---

## Tech Stack

| Layer | Choice |
|---|---|
| Framework | FastAPI + uvicorn |
| Database | SQLite via SQLAlchemy (no external service) |
| HTTP client | httpx |
| Retry worker | asyncio background task |
| Templates | Jinja2 + Tailwind CSS CDN |
| Signatures | stdlib `hmac` + `hashlib` |
| Tests | pytest |

---

## Quick Start

### 1. Clone and set up

```bash
git clone <your-repo-url>
cd webhook-delivery-system

python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env if needed — defaults work for local development
```

### 3. Create the data directory and run

```bash
mkdir data
uvicorn app.main:app --reload
```

The server starts on **http://localhost:8000**.

---

## Usage

### Create a subscription

```bash
curl -X POST http://localhost:8000/subscriptions/ \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://webhook.site/your-uuid",
    "event_types": ["order.created", "order.cancelled"],
    "description": "Order events handler"
  }'
```

Use `"event_types": ["*"]` to receive all events.

**Response** includes a generated `id`. The `secret` is stored server-side only — it is never returned via the API.

### Send an event

```bash
curl -X POST http://localhost:8000/events/ \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "order.created",
    "payload": {"order_id": "ORD-001", "amount": 99.99, "currency": "USD"}
  }'
```

**Response:**
```json
{"event_id": "abc123...", "queued_deliveries": 1}
```

The system immediately attempts delivery and retries on failure.

### Verify a signature (subscriber side)

Every delivery includes:

```
X-Webhook-Signature: sha256=<hex>
X-Webhook-Event: order.created
X-Webhook-ID: <event-uuid>
X-Webhook-Attempt: 1
```

To verify (Python):

```python
import hashlib, hmac

def verify(secret: str, body: bytes, signature: str) -> bool:
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
```

---

## API Reference

Full interactive docs at **http://localhost:8000/docs**

| Method | Path | Description |
|---|---|---|
| `POST` | `/events/` | Ingest an event |
| `GET` | `/events/` | List recent events |
| `GET` | `/events/{id}` | Get a specific event |
| `POST` | `/subscriptions/` | Create a subscription |
| `GET` | `/subscriptions/` | List active subscriptions |
| `GET` | `/subscriptions/{id}` | Get a subscription |
| `PATCH` | `/subscriptions/{id}/deactivate` | Deactivate |
| `PATCH` | `/subscriptions/{id}/activate` | Activate |
| `DELETE` | `/subscriptions/{id}` | Delete |
| `GET` | `/delivery-attempts/` | List delivery attempts (filterable) |
| `GET` | `/delivery-attempts/{id}` | Get a single attempt |
| `GET` | `/` | Delivery dashboard (HTML) |
| `GET` | `/dashboard/events/{id}` | Event detail page (HTML) |
| `GET` | `/subscriptions-ui` | Subscriptions page (HTML) |

---

## Retry Ladder

| Attempt | Delay after previous failure |
|---|---|
| 1 | Immediate (on ingest) |
| 2 | +1 minute |
| 3 | +5 minutes |
| 4 | +30 minutes |
| 5 | +2 hours |
| > 5 | Marked `dead` — no further retries |

---

## Running Tests

```bash
pytest tests/ -v
```

Tests use an in-memory SQLite DB with `StaticPool` — no setup required, no side effects on the development DB.

---

## Project Structure

```
webhook-delivery-system/
├── app/
│   ├── main.py               # FastAPI app + lifespan (retry worker start)
│   ├── config.py             # Settings from .env
│   ├── database.py           # SQLAlchemy engine, session, init_db()
│   ├── models/
│   │   ├── orm.py            # Subscription, Event, DeliveryAttempt
│   │   └── schemas.py        # Pydantic request/response models
│   ├── routers/
│   │   ├── subscriptions.py  # Subscription CRUD
│   │   ├── events.py         # Event ingestion
│   │   ├── attempts.py       # Delivery attempt queries
│   │   └── dashboard.py      # HTML dashboard pages
│   ├── services/
│   │   ├── delivery.py       # Fan-out, HTTP delivery, retry scheduling
│   │   ├── signer.py         # HMAC-SHA256 sign + verify
│   │   └── scheduler.py      # Asyncio retry worker
│   └── templates/            # Jinja2 HTML templates
├── tests/                    # pytest test suite (25 tests)
├── data/                     # SQLite DB lives here (gitignored)
├── requirements.txt
├── .env.example
└── README.md
```
