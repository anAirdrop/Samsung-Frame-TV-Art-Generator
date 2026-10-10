"""FastAPI application entry point."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from .config import load_settings
from .routers import alexa, health, setup, webhook
from .security import RateLimiter
from .storage import JobStore
from .worker import run_worker


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Initialize persistent storage and supervise the generation worker."""
    settings = load_settings()
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    store = JobStore(settings.database_path)
    await asyncio.to_thread(store.initialize)
    await asyncio.to_thread(store.recover_running_jobs)
    application.state.job_store = store
    application.state.rate_limiter = RateLimiter()
    stop_event = asyncio.Event()
    worker_task = asyncio.create_task(
        run_worker(store, stop_event), name="frame-art-worker"
    )
    application.state.worker_task = worker_task
    try:
        yield
    finally:
        stop_event.set()
        await worker_task


def create_app() -> FastAPI:
    """Create the web application using current process settings."""
    settings = load_settings()
    docs_url = "/docs" if settings.expose_api_docs else None
    openapi_url = "/openapi.json" if settings.expose_api_docs else None
    application = FastAPI(
        title="Frame Art",
        description="Generate AI artwork and display it on Samsung Frame TVs",
        version="0.2.0",
        docs_url=docs_url,
        redoc_url=None,
        openapi_url=openapi_url,
        lifespan=lifespan,
    )
    application.include_router(setup.router)
    application.include_router(webhook.router)
    application.include_router(alexa.router)
    application.include_router(health.router)
    return application


app = create_app()


def main() -> None:
    """Run the Frame Art server."""
    settings = load_settings()
    uvicorn.run(
        "frame_art.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
    )


if __name__ == "__main__":
    main()
