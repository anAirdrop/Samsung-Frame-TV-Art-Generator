"""Tests for durable generation worker processing."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from frame_art.config import AppConfig, Settings, TVConfig
from frame_art.storage import JobStatus, JobStore
from frame_art.worker import _process_job


@pytest.mark.asyncio
async def test_process_job_generates_uploads_and_completes(tmp_path: Path) -> None:
    settings = Settings(
        fal_key="fal-example-key",
        webhook_api_key="s" * 32,
        data_dir=tmp_path,
    )
    config = AppConfig(
        tvs={
            "living_room": TVConfig(
                host="192.168.1.100",
                token_file=str(tmp_path / "token.txt"),
            )
        }
    )
    store = JobStore(tmp_path / "jobs.db")
    store.initialize()
    queued_job = store.enqueue("a quiet forest", "living_room", "api")
    claimed_job = store.claim_next()
    assert claimed_job is not None

    controller = MagicMock()
    controller.upload_and_display.return_value = "MY_ART_001"
    with (
        patch("frame_art.worker.load_settings", return_value=settings),
        patch("frame_art.worker.load_config", return_value=config),
        patch(
            "frame_art.worker.generate_image",
            new=AsyncMock(return_value=b"raw-image"),
        ) as generate_image,
        patch("frame_art.worker.process_image", return_value=b"processed-image"),
        patch("frame_art.worker.TVController", return_value=controller),
        patch(
            "frame_art.worker._notify_success", new=AsyncMock()
        ) as notify_success,
        patch(
            "frame_art.worker._remove_stale_artwork", new=AsyncMock()
        ) as remove_stale_artwork,
    ):
        await _process_job(store, claimed_job)

    completed_job = store.get(queued_job.id)
    assert completed_job is not None
    assert completed_job.status is JobStatus.COMPLETED
    generate_image.assert_awaited_once()
    controller.upload_and_display.assert_called_once_with(
        b"processed-image", "JPEG"
    )
    notify_success.assert_awaited_once_with(
        settings, "a quiet forest", "Living Room"
    )
    remove_stale_artwork.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_job_records_failure_without_leaking_details(
    tmp_path: Path,
) -> None:
    settings = Settings(
        fal_key="fal-example-key",
        webhook_api_key="s" * 32,
        data_dir=tmp_path,
    )
    config = AppConfig(
        tvs={
            "living_room": TVConfig(
                host="192.168.1.100",
                token_file=str(tmp_path / "token.txt"),
            )
        }
    )
    store = JobStore(tmp_path / "jobs.db")
    store.initialize()
    queued_job = store.enqueue("a quiet forest", "living_room", "api")
    claimed_job = store.claim_next()
    assert claimed_job is not None

    with (
        patch("frame_art.worker.load_settings", return_value=settings),
        patch("frame_art.worker.load_config", return_value=config),
        patch(
            "frame_art.worker.generate_image",
            new=AsyncMock(side_effect=RuntimeError("secret upstream detail")),
        ),
        patch(
            "frame_art.worker._notify_failure", new=AsyncMock()
        ) as notify_failure,
    ):
        await _process_job(store, claimed_job)

    failed_job = store.get(queued_job.id)
    assert failed_job is not None
    assert failed_job.status is JobStatus.FAILED
    assert "secret upstream detail" not in failed_job.message
    notify_failure.assert_awaited_once_with(settings, "secret upstream detail")
