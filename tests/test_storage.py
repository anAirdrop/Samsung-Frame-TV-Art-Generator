"""Tests for durable generation and retention storage."""

from pathlib import Path

from frame_art.storage import JobStatus, JobStore


def test_job_lifecycle_is_durable(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "frame-art.db")
    store.initialize()

    queued = store.enqueue("a sunset", "living_room", "test")
    claimed = store.claim_next()

    assert claimed is not None
    assert claimed.id == queued.id
    assert claimed.status is JobStatus.RUNNING

    store.complete(claimed.id, "Displayed")
    completed = store.get(claimed.id)
    assert completed is not None
    assert completed.status is JobStatus.COMPLETED
    assert completed.message == "Displayed"


def test_running_jobs_are_requeued_after_restart(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "frame-art.db")
    store.initialize()
    queued = store.enqueue("a forest", "living_room", "test")
    assert store.claim_next() is not None

    store.recover_running_jobs()

    recovered = store.get(queued.id)
    assert recovered is not None
    assert recovered.status is JobStatus.QUEUED


def test_retention_only_returns_old_managed_artwork(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "frame-art.db")
    store.initialize()
    jobs = [
        store.enqueue(f"image {number}", "living_room", "test")
        for number in range(3)
    ]
    for number, job in enumerate(jobs):
        store.record_artwork(f"content-{number}", job.id, "living_room")

    stale = store.stale_artworks("living_room", keep_count=2)

    assert [artwork.content_id for artwork in stale] == ["content-0"]
