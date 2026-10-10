"""Authenticated queued-generation API for Siri and direct integrations."""

from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from ..config import Settings, load_config, resolve_room
from ..models import GenerateRequest, JobAcceptedResponse, JobStatusResponse
from ..security import require_api_token
from ..storage import JobStore

router = APIRouter(prefix="/api")


@router.post(
    "/generate",
    response_model=JobAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_art(
    payload: GenerateRequest,
    request: Request,
    settings: Annotated[Settings, Depends(require_api_token)],
) -> JobAcceptedResponse:
    """Queue image generation and return immediately for voice assistants."""
    config = load_config(settings.config_path)
    tv_key = resolve_room(payload.room, config.tvs)
    if tv_key is None:
        known_rooms = [key.replace("_", " ") for key in config.tvs]
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"message": "Unknown room", "known_rooms": known_rooms},
        )

    identity = request.client.host if request.client is not None else "unknown"
    request.app.state.rate_limiter.check(
        identity, settings.generation_rate_limit_per_hour
    )
    store: JobStore = request.app.state.job_store
    job = await asyncio.to_thread(
        store.enqueue,
        payload.description.strip(),
        tv_key,
        "api",
    )
    return JobAcceptedResponse(
        job_id=job.id,
        status=job.status,
        message=(
            f"Creating art for the {tv_key.replace('_', ' ')} TV. "
            "You can close this shortcut."
        ),
    )


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job(
    job_id: str,
    request: Request,
    settings: Annotated[Settings, Depends(require_api_token)],
) -> JobStatusResponse:
    """Return durable status for a previously accepted generation job."""
    del settings
    store: JobStore = request.app.state.job_store
    job = await asyncio.to_thread(store.get, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation job not found",
        )
    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        message=job.message,
        description=job.description,
        room=job.tv_key.replace("_", " "),
        created_at=job.created_at,
        updated_at=job.updated_at,
    )
