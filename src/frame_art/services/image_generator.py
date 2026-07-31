"""AI image generation through a configurable fal.ai model endpoint."""

from __future__ import annotations

import asyncio
import logging

import fal_client
import httpx
from pydantic import BaseModel, ValidationError

from ..config import AppConfig, FalArgument, Settings

logger = logging.getLogger(__name__)

_MAX_ATTEMPTS = 3


class FalImage(BaseModel):
    url: str


class FalImageResult(BaseModel):
    images: list[FalImage]


class FalResponseError(RuntimeError):
    """Raised when a fal.ai model returns an incompatible response."""


def extract_image_url(result: object, model: str) -> str:
    """Validate a fal.ai text-to-image response and return its first URL."""
    try:
        parsed = FalImageResult.model_validate(result)
    except ValidationError as error:
        raise FalResponseError(
            f"fal.ai model '{model}' returned an incompatible response: {result!r}"
        ) from error

    if not parsed.images:
        raise FalResponseError(
            f"fal.ai model '{model}' returned no images: {result!r}"
        )

    return parsed.images[0].url


async def download_image(url: str, model: str) -> bytes:
    """Download a generated image with bounded retries."""
    last_error: httpx.HTTPError | None = None

    async with httpx.AsyncClient(timeout=30.0) as client:
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                response = await client.get(url)
                response.raise_for_status()
                return response.content
            except httpx.HTTPError as error:
                last_error = error
                logger.warning(
                    "fal.ai image download failed",
                    extra={
                        "attempt": attempt,
                        "model": model,
                        "url": url,
                        "error": str(error),
                    },
                )
                if attempt < _MAX_ATTEMPTS:
                    await asyncio.sleep(2 ** (attempt - 1))

    if last_error is None:
        raise RuntimeError(
            f"fal.ai image download failed without an HTTP error: model={model}, url={url}"
        )
    raise last_error


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
        result = await self._subscribe(arguments)
        image_url = extract_image_url(result, self.model)
        return await download_image(image_url, self.model)

    async def _subscribe(
        self, arguments: dict[str, FalArgument]
    ) -> object:
        last_error: fal_client.FalClientError | None = None

        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                logger.info(
                    "Generating image with fal.ai",
                    extra={"attempt": attempt, "model": self.model},
                )
                return await self.client.subscribe(
                    self.model,
                    arguments=arguments,
                    client_timeout=120.0,
                )
            except fal_client.FalClientError as error:
                last_error = error
                logger.warning(
                    "fal.ai generation request failed",
                    extra={
                        "attempt": attempt,
                        "model": self.model,
                        "error": str(error),
                    },
                )
                if attempt < _MAX_ATTEMPTS:
                    await asyncio.sleep(2 ** (attempt - 1))

        if last_error is None:
            raise RuntimeError(
                f"fal.ai generation failed without a client error: model={self.model}"
            )
        raise last_error


async def generate_image(
    description: str,
    config: AppConfig,
    settings: Settings,
    model_override: str | None,
) -> bytes:
    """Generate an image using the configured or request-specific fal.ai model."""
    if not settings.fal_key:
        raise ValueError("FAL_KEY is required for image generation")

    fal_config = config.image.fal
    model = model_override or fal_config.model
    full_prompt = f"{config.prompt_prefix}{description}{config.prompt_suffix}"
    provider = FalProvider(api_key=settings.fal_key, model=model)
    return await provider.generate(full_prompt, fal_config.arguments)
