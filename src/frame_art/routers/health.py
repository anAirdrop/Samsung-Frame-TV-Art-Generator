"""Health check endpoint."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter

from ..config import load_config
from ..services.tv_controller import TVController

router = APIRouter()


@router.get("/api/health")
async def health_check() -> dict:
    """Return server health and TV reachability status."""
    config = load_config()
    tv_status = {}

    for tv_key, tv_config in config.tvs.items():
        controller = TVController(tv_config)
        reachable = await asyncio.to_thread(controller.is_reachable)
        tv_status[tv_key] = "reachable" if reachable else "unreachable"

    return {
        "status": "ok",
        "provider": config.image.provider,
        "tvs": tv_status,
    }
