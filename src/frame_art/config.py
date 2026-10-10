"""Configuration loading, validation, and persistence."""

from __future__ import annotations

import os
import re
import secrets
from pathlib import Path
from typing import TypeAlias

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class ConfigurationError(RuntimeError):
    """Raised when installation configuration is missing or unsafe."""


class TVConfig(BaseModel):
    host: str
    port: int = 8002
    token_file: str
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
    """Non-secret installation configuration."""

    image: ImageConfig = Field(default_factory=ImageConfig)
    prompt_prefix: str = "Professional art suitable for display on a wall. "
    prompt_suffix: str = (
        " High resolution, vivid colors, suitable for home decor."
    )
    tvs: dict[str, TVConfig] = Field(default_factory=dict)


class Settings(BaseSettings):
    """Secrets and process settings loaded explicitly by ``load_settings``."""

    fal_key: str = ""
    webhook_api_key: str = ""
    alexa_skill_id: str = ""
    ntfy_topic: str = ""
    ntfy_server: str = "https://ntfy.sh"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"
    data_dir: Path = Path("data")
    max_artworks_per_tv: int = 20
    generation_rate_limit_per_hour: int = 20
    expose_api_docs: bool = False

    model_config = {"env_file": None, "env_file_encoding": "utf-8"}

    @property
    def config_path(self) -> Path:
        return self.data_dir / "config.yaml"

    @property
    def database_path(self) -> Path:
        return self.data_dir / "frame-art.db"

    @property
    def secrets_path(self) -> Path:
        return self.data_dir / ".env"


def _default_data_dir() -> Path:
    configured = os.environ.get("FRAME_ART_DATA_DIR")
    if configured:
        return Path(configured)
    if Path("/data").is_dir():
        return Path("/data")
    return Path("data")


def load_settings() -> Settings:
    """Load process environment and the persisted installation secrets file."""
    data_dir = _default_data_dir()
    env_path = Path(
        os.environ.get("FRAME_ART_ENV_PATH", str(data_dir / ".env"))
    )
    return Settings(_env_file=env_path, data_dir=data_dir)


def load_config(config_path: str | Path) -> AppConfig:
    """Load and validate the installation configuration."""
    path = Path(config_path)
    if not path.exists():
        raise ConfigurationError(
            f"Configuration not found at '{path}'. Open the local setup page first."
        )
    with path.open(encoding="utf-8") as config_file:
        raw = yaml.safe_load(config_file) or {}
    return AppConfig.model_validate(raw)


def save_config(config: AppConfig, config_path: Path) -> None:
    """Atomically persist validated application configuration."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = config_path.with_suffix(".yaml.tmp")
    serialized = yaml.safe_dump(
        config.model_dump(mode="json"),
        sort_keys=False,
        allow_unicode=True,
    )
    temporary_path.write_text(serialized, encoding="utf-8")
    temporary_path.replace(config_path)


def save_secrets(settings: Settings, fal_key: str, webhook_api_key: str) -> None:
    """Persist installation secrets with owner-only permissions where supported."""
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    contents = (
        f"FAL_KEY={fal_key}\n"
        f"WEBHOOK_API_KEY={webhook_api_key}\n"
        "ALEXA_SKILL_ID=\n"
        "NTFY_TOPIC=\n"
    )
    settings.secrets_path.write_text(contents, encoding="utf-8")
    try:
        settings.secrets_path.chmod(0o600)
    except OSError as error:
        raise ConfigurationError(
            f"Could not protect secrets file '{settings.secrets_path}': {error}"
        ) from error


def validate_runtime_settings(settings: Settings) -> None:
    """Reject missing or unsafe credentials before accepting generation work."""
    if not settings.fal_key.strip():
        raise ConfigurationError("FAL_KEY is required")
    secret = settings.webhook_api_key.strip()
    if len(secret) < 32 or secret.lower() in {"change-me", "your-random-secret"}:
        raise ConfigurationError(
            "WEBHOOK_API_KEY must be a random secret of at least 32 characters"
        )


def generate_webhook_secret() -> str:
    """Create a URL-safe installation secret."""
    return secrets.token_urlsafe(32)


def room_key(room_name: str) -> str:
    """Convert a room display name into a stable configuration key."""
    normalized = re.sub(r"[^a-z0-9]+", "_", room_name.strip().lower())
    result = normalized.strip("_")
    if not result:
        raise ConfigurationError("Room name must contain a letter or number")
    return result


def resolve_room(room_name: str, tvs: dict[str, TVConfig]) -> str | None:
    """Map a spoken room name to a configured TV key."""
    room_lower = room_name.strip().lower()
    for tv_key, tv_config in tvs.items():
        if room_lower == tv_key.replace("_", " "):
            return tv_key
        if room_lower in [alias.lower() for alias in tv_config.aliases]:
            return tv_key
    return None
