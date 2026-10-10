"""Tests for authenticated queued-generation routes."""

import asyncio
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from frame_art.config import AppConfig, Settings, save_config

_API_KEY = "test-secret-that-is-longer-than-32-characters"


async def _idle_worker(store: object, stop_event: asyncio.Event) -> None:
    del store
    await stop_event.wait()


@pytest.fixture
def client(
    sample_config: AppConfig, tmp_path: Path
) -> Iterator[TestClient]:
    settings = Settings(
        fal_key="fal-test",
        webhook_api_key=_API_KEY,
        data_dir=tmp_path,
    )
    save_config(sample_config, settings.config_path)
    with (
        patch("frame_art.main.load_settings", return_value=settings),
        patch("frame_art.security.load_settings", return_value=settings),
        patch("frame_art.routers.webhook.load_config", return_value=sample_config),
        patch("frame_art.main.run_worker", new=_idle_worker),
    ):
        from frame_art.main import create_app

        with TestClient(create_app()) as test_client:
            yield test_client


def _authorization(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_generate_invalid_api_key(client: TestClient) -> None:
    response = client.post(
        "/api/generate",
        headers=_authorization("wrong-key"),
        json={"description": "a sunset", "room": "living room"},
    )
    assert response.status_code == 401


def test_generate_unknown_room(client: TestClient) -> None:
    response = client.post(
        "/api/generate",
        headers=_authorization(_API_KEY),
        json={"description": "a sunset", "room": "kitchen"},
    )
    assert response.status_code == 422


def test_generate_queues_job(client: TestClient) -> None:
    response = client.post(
        "/api/generate",
        headers=_authorization(_API_KEY),
        json={
            "description": "a beautiful sunset over the ocean",
            "room": "living room",
        },
    )
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "queued"

    status_response = client.get(
        f"/api/jobs/{data['job_id']}", headers=_authorization(_API_KEY)
    )
    assert status_response.status_code == 200
    assert status_response.json()["room"] == "living room"


def test_generate_rejects_removed_body_api_key(client: TestClient) -> None:
    response = client.post(
        "/api/generate",
        headers=_authorization(_API_KEY),
        json={
            "description": "a sunset",
            "room": "living room",
            "api_key": _API_KEY,
        },
    )
    assert response.status_code == 422


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_authenticated_status_endpoint(client: TestClient) -> None:
    with patch("frame_art.routers.health.TVController") as tv_controller:
        controller = MagicMock()
        controller.is_reachable.return_value = True
        tv_controller.return_value = controller
        response = client.get("/api/status", headers=_authorization(_API_KEY))

    assert response.status_code == 200
    assert response.json()["tvs"]["living_room"] == "reachable"
