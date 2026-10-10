"""Liveness and authenticated installation status routes."""

from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from ..config import Settings, load_config
from ..security import require_api_token
from ..services.tv_controller import TVController

router = APIRouter()


@router.get("/healthz", include_in_schema=False)
async def health_check(request: Request) -> dict[str, str]:
    """Return process and worker liveness without installation details."""
    worker_task = getattr(request.app.state, "worker_task", None)
    if worker_task is not None and worker_task.done():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Generation worker is not running",
        )
    return {"status": "ok"}


@router.get("/api/status")
async def installation_status(
    settings: Annotated[Settings, Depends(require_api_token)],
) -> dict[str, object]:
    """Return model and TV reachability to an authenticated administrator."""
    config = load_config(settings.config_path)
    tv_status: dict[str, str] = {}
    for tv_key, tv_config in config.tvs.items():
        controller = TVController(tv_config)
        reachable = await asyncio.to_thread(controller.is_reachable)
        tv_status[tv_key] = "reachable" if reachable else "unreachable"
    return {
        "status": "ok",
        "model": config.image.fal.model,
        "tvs": tv_status,
    }
