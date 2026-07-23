from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette import status

from app.config import get_settings
from app.database import engine
from app.logging_config import configure_logging
from app.models.db_models import Base
from app.routes import behavior, health, history, news, rankings, research, scanner, statistics, telemetry
from app.scheduler import scheduler_loop

settings = get_settings()
configure_logging(settings.LOG_LEVEL)
logger = logging.getLogger("bpm.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.APP_ENV in {"development", "test"}:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    scheduler_task = asyncio.create_task(scheduler_loop(settings))
    logger.info("BPM platform started (env=%s)", settings.APP_ENV)
    try:
        yield
    finally:
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass


app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION, lifespan=lifespan)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=False,
        allow_methods=["GET", "POST"], allow_headers=["*"],
    )


@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            too_large = int(content_length) > settings.MAX_REQUEST_BYTES
        except ValueError:
            too_large = False
        if too_large:
            return JSONResponse(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                                 content={"detail": "Request body exceeds MAX_REQUEST_BYTES."})
    return await call_next(request)


app.include_router(health.router)
app.include_router(telemetry.router)
app.include_router(scanner.router)
app.include_router(rankings.router)
app.include_router(news.router)
app.include_router(behavior.router)
app.include_router(history.router)
app.include_router(statistics.router)
app.include_router(research.router)
