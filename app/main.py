from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database import init_db
from app.routers import subscriptions


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


app = FastAPI(
    title="Webhook Delivery System",
    description="Reliable webhook delivery with retries, HMAC signatures, and delivery logs.",
    version="1.0.0",
    lifespan=lifespan,
)

templates = Jinja2Templates(directory="app/templates")

app.include_router(subscriptions.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
