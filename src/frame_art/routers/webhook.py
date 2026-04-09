"""Unified webhook endpoint for Siri Shortcuts and direct API use."""

from __future__ import annotations

import asyncio
import logging
import time

from fastapi import APIRouter, BackgroundTasks, HTTPException

from ..config import Settings, load_config, resolve_room
from ..models import GenerateRequest, GenerateResponse
from ..services.image_generator import generate_image
from ..services.image_processor import process_image
from ..services.notifier import Notifier, notify_failure, notify_success
from ..services.tv_controller import TVController

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/api/generate", response_model=GenerateResponse)
async def generate_art(
    request: GenerateRequest, background_tasks: BackgroundTasks
) -> GenerateResponse:
    """Generate an AI image and display it on a Samsung Frame TV.

    This endpoint is used by Siri Shortcuts and direct HTTP calls.
    """
    settings = Settings()

    # Authenticate
    if request.api_key != settings.webhook_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    config = load_config()

    # Resolve room name to TV config
    tv_key = resolve_room(request.room, config.tvs)
    if not tv_key:
        known = list(config.tvs.keys())
        raise HTTPException(
            status_code=422,
            detail=f"Unknown room '{request.room}'. Known TVs: {known}",
        )

    tv_config = config.tvs[tv_key]
    tv_display_name = tv_key.replace("_", " ").title()
    start = time.time()

    # Set up notifier
    notifier = Notifier(settings.ntfy_server, settings.ntfy_topic)

    try:
        # Step 1: Generate image with chosen provider
        provider = request.provider or config.image.provider
        raw_image = await generate_image(
            description=request.description,
            config=config,
            settings=settings,
            provider_override=provider,
        )
        logger.info(
            "Image generated (%d bytes) with provider '%s'",
            len(raw_image),
            provider,
        )

        # Step 2: Resize to TV resolution
        processed = process_image(raw_image, config.image.output)
        logger.info("Image processed to %dx%d (%d bytes)",
                     config.image.output.width, config.image.output.height,
                     len(processed))

        # Step 3: Upload to Samsung TV (sync library, run in thread)
        controller = TVController(tv_config)
        content_id = await asyncio.to_thread(
            controller.upload_and_display,
            processed,
            file_type=config.image.output.format,
        )
        logger.info("Art set on %s TV (content_id=%s)", tv_display_name, content_id)

        duration = round(time.time() - start, 1)

        # Step 4: Send success notification (non-blocking)
        background_tasks.add_task(
            notify_success, notifier, request.description, tv_display_name
        )

        return GenerateResponse(
            status="success",
            message=f"Image set on {tv_display_name} TV",
            image_description=request.description,
            tv=tv_key,
            duration_seconds=duration,
        )

    except Exception as e:
        logger.exception("Failed to generate/upload art")
        background_tasks.add_task(notify_failure, notifier, str(e))
        raise HTTPException(status_code=500, detail=str(e))
