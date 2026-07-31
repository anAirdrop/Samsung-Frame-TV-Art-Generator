"""Configuration loading from .env and config.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, TypeAlias

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class TVConfig(BaseModel):
    host: str
    port: int = 8002
    token_file: str = ""
    aliases: list[str] = Field(default_factory=list)
    matte: str = "none"


FalScalar: TypeAlias = str | int | float | bool | None
FalList: TypeAlias = list[FalScalar]
FalObject: TypeAlias = dict[str, FalScalar | FalList]
FalArgument: TypeAlias = FalScalar | FalList | FalObject | list[FalObject]


class FalConfig(BaseModel):
    model: str = "fal-ai/nano-banana-2"
    arguments: dict[str, FalArgument] = Field(
        default_factory=lambda: {
            "aspect_ratio": "16:9",
            "resolution": "4K",
            "num_images": 1,
            "output_format": "jpeg",
            "limit_generations": True,
        }
    )


class OutputConfig(BaseModel):
    width: int = 3840
    height: int = 2160
    format: str = "JPEG"
    jpeg_quality: int = 95


class ImageConfig(BaseModel):
    fal: FalConfig = Field(default_factory=FalConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)


class AppConfig(BaseModel):
    """Full application configuration loaded from config.yaml."""

    image: ImageConfig = Field(default_factory=ImageConfig)
    prompt_prefix: str = ""
    prompt_suffix: str = ""
    tvs: dict[str, TVConfig] = Field(default_factory=dict)


class Settings(BaseSettings):
    """Secrets and server settings loaded from environment / .env file."""

    fal_key: str = ""
    webhook_api_key: str = ""
    ntfy_topic: str = "frame-tv-art"
    ntfy_server: str = "https://ntfy.sh"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


def load_config(config_path: str = "config.yaml") -> AppConfig:
    """Load and validate application configuration from a YAML file."""
    path = Path(config_path)
    if not path.exists():
        return AppConfig()
    with open(path) as f:
        raw = yaml.safe_load(f) or {}
    return AppConfig.model_validate(raw)


def resolve_room(room_name: str, tvs: dict[str, TVConfig]) -> Optional[str]:
    """Map a spoken room name to a TV config key via aliases.

    Returns the TV key if found, otherwise None.
    """
    room_lower = room_name.strip().lower()
    for tv_key, tv_config in tvs.items():
        if room_lower == tv_key.replace("_", " "):
            return tv_key
        if room_lower in [alias.lower() for alias in tv_config.aliases]:
            return tv_key
    return None
