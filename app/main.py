import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database import init_db
from app.routers import attempts, events, subscriptions
from app.services.scheduler import retry_worker

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    worker_task = asyncio.create_task(retry_worker())
    try:
        yield
    finally:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Webhook Delivery System",
    description="Reliable webhook delivery with retries, HMAC signatures, and delivery logs.",
    version="1.0.0",
    lifespan=lifespan,
)

templates = Jinja2Templates(directory="app/templates")

app.include_router(subscriptions.router)
app.include_router(events.router)
app.include_router(attempts.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
