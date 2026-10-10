"""Tests for installation configuration and secret validation."""

from pathlib import Path

import pytest

from frame_art.config import (
    AppConfig,
    ConfigurationError,
    Settings,
    TVConfig,
    load_config,
    room_key,
    save_config,
    validate_runtime_settings,
)


def test_config_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    expected = AppConfig(
        tvs={
            "living_room": TVConfig(
                host="192.168.1.100",
                token_file="/data/tokens/living-room.txt",
                aliases=["living room"],
            )
        }
    )

    save_config(expected, path)

    assert load_config(path) == expected


def test_missing_config_raises_actionable_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="setup page"):
        load_config(tmp_path / "missing.yaml")


def test_runtime_settings_reject_placeholder_secret() -> None:
    settings = Settings(fal_key="fal-test", webhook_api_key="change-me")

    with pytest.raises(ConfigurationError, match="at least 32"):
        validate_runtime_settings(settings)


def test_room_key_is_stable() -> None:
    assert room_key("  Family Room / TV ") == "family_room_tv"
