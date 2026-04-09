"""Multi-provider AI image generation service.

Supports OpenAI (gpt-image-1), Google Gemini (Imagen), and xAI Grok.
"""

from __future__ import annotations

import base64
import logging
from abc import ABC, abstractmethod
from io import BytesIO
from typing import Optional

from ..config import AppConfig, Settings

logger = logging.getLogger(__name__)


class ImageProvider(ABC):
    """Base class for image generation providers."""

    @abstractmethod
    async def generate(self, prompt: str) -> bytes:
        """Generate an image from a text prompt. Returns raw image bytes."""


class OpenAIProvider(ImageProvider):
    """Generate images using OpenAI's gpt-image-1."""

    def __init__(self, api_key: str, model: str, quality: str, size: str):
        from openai import AsyncOpenAI

        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.quality = quality
        self.size = size

    async def generate(self, prompt: str) -> bytes:
        logger.info("Generating image with OpenAI %s", self.model)
        response = await self.client.images.generate(
            model=self.model,
            prompt=prompt,
            size=self.size,
            quality=self.quality,
            n=1,
        )
        # gpt-image-1 returns b64_json by default
        if response.data[0].b64_json:
            return base64.b64decode(response.data[0].b64_json)
        # Fallback: download from URL
        import httpx

        async with httpx.AsyncClient() as http:
            img_resp = await http.get(response.data[0].url)
            img_resp.raise_for_status()
            return img_resp.content


class GeminiProvider(ImageProvider):
    """Generate images using Google Gemini's Imagen model."""

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    async def generate(self, prompt: str) -> bytes:
        from google import genai

        logger.info("Generating image with Gemini %s", self.model)
        client = genai.Client(api_key=self.api_key)
        response = client.models.generate_images(
            model=self.model,
            prompt=prompt,
            config=genai.types.GenerateImagesConfig(number_of_images=1),
        )
        if not response.generated_images:
            raise RuntimeError("Gemini returned no images")
        return response.generated_images[0].image.image_bytes


class GrokProvider(ImageProvider):
    """Generate images using xAI's Grok (OpenAI-compatible API)."""

    def __init__(self, api_key: str, model: str):
        from openai import AsyncOpenAI

        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1",
        )
        self.model = model

    async def generate(self, prompt: str) -> bytes:
        logger.info("Generating image with Grok %s", self.model)
        response = await self.client.images.generate(
            model=self.model,
            prompt=prompt,
            n=1,
        )
        if response.data[0].b64_json:
            return base64.b64decode(response.data[0].b64_json)
        import httpx

        async with httpx.AsyncClient() as http:
            img_resp = await http.get(response.data[0].url)
            img_resp.raise_for_status()
            return img_resp.content


def create_provider(
    provider_name: str, config: AppConfig, settings: Settings
) -> ImageProvider:
    """Factory to create the appropriate image provider."""
    if provider_name == "openai":
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when using OpenAI provider")
        return OpenAIProvider(
            api_key=settings.openai_api_key,
            model=config.image.openai.model,
            quality=config.image.openai.quality,
            size=config.image.openai.size,
        )
    elif provider_name == "gemini":
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required when using Gemini provider")
        return GeminiProvider(
            api_key=settings.gemini_api_key,
            model=config.image.gemini.model,
        )
    elif provider_name == "grok":
        if not settings.grok_api_key:
            raise ValueError("GROK_API_KEY is required when using Grok provider")
        return GrokProvider(
            api_key=settings.grok_api_key,
            model=config.image.grok.model,
        )
    else:
        raise ValueError(
            f"Unknown image provider '{provider_name}'. "
            "Supported: openai, gemini, grok"
        )


async def generate_image(
    description: str,
    config: AppConfig,
    settings: Settings,
    provider_override: Optional[str] = None,
) -> bytes:
    """Generate an image using the configured (or overridden) provider.

    Returns raw image bytes (PNG or JPEG depending on provider).
    """
    provider_name = provider_override or config.image.provider
    provider = create_provider(provider_name, config, settings)

    full_prompt = f"{config.prompt_prefix}{description}{config.prompt_suffix}"
    return await provider.generate(full_prompt)
