"""AI image generation through a configurable fal.ai model endpoint."""

from __future__ import annotations

import asyncio
import logging
from urllib.parse import urlsplit, urlunsplit

import fal_client
import httpx
from pydantic import BaseModel, ValidationError

from ..config import AppConfig, FalArgument, Settings

logger = logging.getLogger(__name__)

_MAX_DOWNLOAD_ATTEMPTS = 3
_MAX_IMAGE_BYTES = 40 * 1024 * 1024


class FalImage(BaseModel):
    url: str


class FalImageResult(BaseModel):
    images: list[FalImage]


class FalResponseError(RuntimeError):
    """Raised when a fal.ai model returns an incompatible response."""


class FalDownloadError(RuntimeError):
    """Raised when a generated image cannot be downloaded safely."""


def _response_shape(result: object) -> str:
    if isinstance(result, dict):
        return f"object keys={sorted(str(key) for key in result)}"
    return type(result).__name__


def _safe_url(url: str) -> str:
    parsed = urlsplit(url)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def extract_image_url(result: object, model: str) -> str:
    """Validate a fal.ai text-to-image response and return its first URL."""
    try:
        parsed = FalImageResult.model_validate(result)
    except ValidationError as error:
        raise FalResponseError(
            f"fal.ai model '{model}' returned an incompatible response "
            f"({_response_shape(result)}); expected images[].url"
        ) from error

    if not parsed.images:
        raise FalResponseError(f"fal.ai model '{model}' returned no images")

    return parsed.images[0].url


async def download_image(url: str, model: str) -> bytes:
    """Download a generated image with bounded retries."""
    last_error: httpx.HTTPError | None = None
    safe_url = _safe_url(url)

    async with httpx.AsyncClient(timeout=30.0) as client:
        for attempt in range(1, _MAX_DOWNLOAD_ATTEMPTS + 1):
            try:
                async with client.stream("GET", url) as response:
                    response.raise_for_status()
                    content_type = response.headers.get("content-type", "")
                    if not content_type.lower().startswith("image/"):
                        raise FalResponseError(
                            f"fal.ai model '{model}' returned non-image content "
                            f"from '{safe_url}': {content_type or 'unknown'}"
                        )
                    chunks: list[bytes] = []
                    total_bytes = 0
                    async for chunk in response.aiter_bytes():
                        total_bytes += len(chunk)
                        if total_bytes > _MAX_IMAGE_BYTES:
                            raise FalResponseError(
                                f"fal.ai model '{model}' returned an image larger "
                                f"than {_MAX_IMAGE_BYTES} bytes"
                            )
                        chunks.append(chunk)
                    return b"".join(chunks)
            except httpx.HTTPError as error:
                last_error = error
                logger.warning(
                    "fal.ai image download failed",
                    extra={
                        "attempt": attempt,
                        "model": model,
                        "url": safe_url,
                        "error_type": type(error).__name__,
                        "status_code": (
                            error.response.status_code
                            if isinstance(error, httpx.HTTPStatusError)
                            else None
                        ),
                    },
                )
                if attempt < _MAX_DOWNLOAD_ATTEMPTS:
                    await asyncio.sleep(2 ** (attempt - 1))

    if last_error is None:
        raise FalDownloadError(
            "fal.ai image download failed without an HTTP error: "
            f"model={model}, url={safe_url}"
        )
    status_code = (
        last_error.response.status_code
        if isinstance(last_error, httpx.HTTPStatusError)
        else None
    )
    raise FalDownloadError(
        f"fal.ai image download failed after {_MAX_DOWNLOAD_ATTEMPTS} attempts: "
        f"model={model}, url={safe_url}, error_type={type(last_error).__name__}, "
        f"status_code={status_code}"
    ) from last_error


class FalProvider:
    """Connector for fal.ai text-to-image model endpoints."""

    def __init__(self, api_key: str, model: str) -> None:
        self.client = fal_client.AsyncClient(key=api_key, default_timeout=120.0)
        self.model = model

    async def generate(
        self, prompt: str, configured_arguments: dict[str, FalArgument]
    ) -> bytes:
        arguments: dict[str, FalArgument] = {
            **configured_arguments,
            "prompt": prompt,
        }
        result = await self.client.subscribe(
            self.model,
            arguments=arguments,
            client_timeout=180.0,
        )
        image_url = extract_image_url(result, self.model)
        return await download_image(image_url, self.model)


async def generate_image(
    description: str,
    config: AppConfig,
    settings: Settings,
) -> bytes:
    """Generate an image using the configured fal.ai model."""
    if not settings.fal_key:
        raise ValueError("FAL_KEY is required for image generation")

    fal_config = config.image.fal
    full_prompt = f"{config.prompt_prefix}{description}{config.prompt_suffix}"
    provider = FalProvider(api_key=settings.fal_key, model=fal_config.model)
    return await provider.generate(full_prompt, fal_config.arguments)
