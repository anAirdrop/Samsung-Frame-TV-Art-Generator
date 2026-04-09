"""Tests for the webhook API endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from frame_art.config import AppConfig, Settings


@pytest.fixture
def client(sample_config):
    with patch("frame_art.routers.webhook.Settings") as mock_settings_cls, \
         patch("frame_art.routers.webhook.load_config") as mock_load:
        mock_settings_cls.return_value = Settings(
            openai_api_key="sk-test",
            webhook_api_key="test-secret",
        )
        mock_load.return_value = sample_config

        from frame_art.main import app
        yield TestClient(app)


def test_generate_invalid_api_key(client):
    response = client.post("/api/generate", json={
        "description": "a sunset",
        "room": "living room",
        "api_key": "wrong-key",
    })
    assert response.status_code == 401


def test_generate_unknown_room(client):
    response = client.post("/api/generate", json={
        "description": "a sunset",
        "room": "kitchen",
        "api_key": "test-secret",
    })
    assert response.status_code == 422


@patch("frame_art.routers.webhook.TVController")
@patch("frame_art.routers.webhook.generate_image", new_callable=AsyncMock)
@patch("frame_art.routers.webhook.process_image")
def test_generate_success(mock_process, mock_gen, mock_tv_cls, client):
    mock_gen.return_value = b"raw-image"
    mock_process.return_value = b"processed-image"
    mock_controller = MagicMock()
    mock_controller.upload_and_display.return_value = "content_123"
    mock_tv_cls.return_value = mock_controller

    response = client.post("/api/generate", json={
        "description": "a beautiful sunset over the ocean",
        "room": "living room",
        "api_key": "test-secret",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["tv"] == "living_room"
    assert "Living Room" in data["message"]


def test_generate_missing_description(client):
    response = client.post("/api/generate", json={
        "description": "ab",
        "room": "living room",
        "api_key": "test-secret",
    })
    assert response.status_code == 422


def test_health_endpoint(client):
    with patch("frame_art.routers.health.load_config") as mock_load, \
         patch("frame_art.routers.health.TVController") as mock_tv:
        from frame_art.config import AppConfig, TVConfig
        mock_load.return_value = AppConfig(tvs={
            "living_room": TVConfig(host="192.168.1.100"),
        })
        mock_controller = MagicMock()
        mock_controller.is_reachable.return_value = True
        mock_tv.return_value = mock_controller

        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
