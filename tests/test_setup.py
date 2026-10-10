"""Tests for the local first-run setup flow."""

import asyncio
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from frame_art.config import Settings, load_config


async def _idle_worker(store: object, stop_event: asyncio.Event) -> None:
    del store
    await stop_event.wait()


@pytest.fixture
def setup_client(tmp_path: Path) -> Iterator[tuple[TestClient, Settings]]:
    settings = Settings(data_dir=tmp_path)
    with (
        patch("frame_art.main.load_settings", return_value=settings),
        patch("frame_art.routers.setup.load_settings", return_value=settings),
        patch("frame_art.main.run_worker", new=_idle_worker),
        patch(
            "frame_art.routers.setup.pair_tv",
            return_value={"device": {"name": "Frame TV"}},
        ),
    ):
        from frame_art.main import create_app

        with TestClient(create_app()) as client:
            yield client, settings


def test_setup_pairs_and_persists_installation(
    setup_client: tuple[TestClient, Settings],
) -> None:
    client, settings = setup_client

    response = client.post(
        "/api/setup/configure",
        json={
            "fal_key": "fal-example-key",
            "room_name": "Living Room",
            "tv_host": "192.168.1.100",
            "tv_port": 8002,
            "aliases": ["lounge", "main TV"],
            "test_prompt": "a quiet forest",
        },
    )

    assert response.status_code == 200
    assert len(response.json()["api_key"]) >= 32
    config = load_config(settings.config_path)
    tv = config.tvs["living_room"]
    assert tv.host == "192.168.1.100"
    assert tv.token_file == str(settings.data_dir / "tokens" / "living_room_token.txt")
    assert settings.secrets_path.exists()
    assert "change-me" not in settings.secrets_path.read_text(encoding="utf-8")


def test_setup_cannot_run_twice(
    setup_client: tuple[TestClient, Settings],
) -> None:
    client, settings = setup_client
    settings.config_path.write_text("tvs: {}\n", encoding="utf-8")

    response = client.post(
        "/api/setup/configure",
        json={
            "fal_key": "fal-example-key",
            "room_name": "Living Room",
            "tv_host": "192.168.1.100",
            "aliases": [],
        },
    )

    assert response.status_code == 409
