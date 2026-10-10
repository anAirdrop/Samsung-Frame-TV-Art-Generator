"""Durable background worker for generation and TV upload jobs."""

from __future__ import annotations

import asyncio
import logging

from .config import Settings, load_config, load_settings, validate_runtime_settings
from .services.image_generator import generate_image
from .services.image_processor import process_image
from .services.notifier import (
    NotificationError,
    Notifier,
    notify_failure,
    notify_success,
)
from .services.tv_controller import TVController
from .storage import JobRecord, JobStore

logger = logging.getLogger(__name__)


async def run_worker(store: JobStore, stop_event: asyncio.Event) -> None:
    """Process queued jobs sequentially until application shutdown."""
    while not stop_event.is_set():
        job = await asyncio.to_thread(store.claim_next)
        if job is None:
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=1.0)
            except TimeoutError:
                continue
            continue
        await _process_job(store, job)


async def _process_job(store: JobStore, job: JobRecord) -> None:
    settings = load_settings()
    try:
        validate_runtime_settings(settings)
        config = load_config(settings.config_path)
        tv_config = config.tvs.get(job.tv_key)
        if tv_config is None:
            raise KeyError(f"Configured TV '{job.tv_key}' no longer exists")

        raw_image = await generate_image(
            description=job.description,
            config=config,
            settings=settings,
        )
        processed_image = await asyncio.to_thread(
            process_image, raw_image, config.image.output
        )
        controller = TVController(tv_config)
        content_id = await asyncio.to_thread(
            controller.upload_and_display,
            processed_image,
            config.image.output.format,
        )
        tv_display_name = job.tv_key.replace("_", " ").title()
        await asyncio.to_thread(
            store.record_artwork, content_id, job.id, job.tv_key
        )
        message = f"Image is now showing on {tv_display_name} TV"
        await asyncio.to_thread(store.complete, job.id, message)
        await _notify_success(settings, job.description, tv_display_name)
        await _remove_stale_artwork(
            store,
            controller,
            job.tv_key,
            settings.max_artworks_per_tv,
        )
    except Exception as error:
        logger.exception(
            "Generation job failed",
            extra={"job_id": job.id, "tv_key": job.tv_key},
        )
        public_message = "Generation failed; check the Frame Art service logs"
        await asyncio.to_thread(store.fail, job.id, public_message)
        await _notify_failure(settings, str(error))


async def _remove_stale_artwork(
    store: JobStore,
    controller: TVController,
    tv_key: str,
    keep_count: int,
) -> None:
    stale = await asyncio.to_thread(store.stale_artworks, tv_key, keep_count)
    for artwork in stale:
        try:
            await asyncio.to_thread(controller.delete_artwork, artwork.content_id)
            await asyncio.to_thread(store.forget_artwork, artwork.content_id)
        except Exception as error:
            logger.warning(
                "Generated artwork retention cleanup failed",
                extra={
                    "tv_key": tv_key,
                    "content_id": artwork.content_id,
                    "error": str(error),
                },
            )


async def _notify_success(
    settings: Settings, description: str, tv_display_name: str
) -> None:
    if not settings.ntfy_topic:
        return
    notifier = Notifier(settings.ntfy_server, settings.ntfy_topic)
    try:
        await notify_success(notifier, description, tv_display_name)
    except NotificationError as error:
        logger.warning(
            "Success notification could not be delivered",
            extra={"error": str(error)},
        )


async def _notify_failure(settings: Settings, error: str) -> None:
    if not settings.ntfy_topic:
        return
    notifier = Notifier(settings.ntfy_server, settings.ntfy_topic)
    try:
        await notify_failure(notifier, error)
    except NotificationError as notification_error:
        logger.warning(
            "Failure notification could not be delivered",
            extra={"error": str(notification_error)},
        )
