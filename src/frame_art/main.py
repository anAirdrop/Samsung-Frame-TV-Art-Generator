"""FastAPI application entry point for the Frame TV Art Generator."""

from __future__ import annotations

import logging

import uvicorn
from fastapi import FastAPI

from .config import Settings
from .routers import alexa, health, webhook

app = FastAPI(
    title="Frame TV Art Generator",
    description="Generate AI art via voice commands and display on Samsung Frame TVs",
    version="1.0.0",
)

app.include_router(webhook.router)
app.include_router(alexa.router)
app.include_router(health.router)


def main() -> None:
    """Run the server with uvicorn."""
    settings = Settings()
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    uvicorn.run(
        "frame_art.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
    )


if __name__ == "__main__":
    main()
