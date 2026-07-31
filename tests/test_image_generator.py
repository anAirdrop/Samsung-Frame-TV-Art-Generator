"""Tests for fal.ai image generation."""

from unittest.mock import AsyncMock, patch

import pytest

from frame_art.config import AppConfig, Settings
from frame_art.services.image_generator import (
    FalProvider,
    FalResponseError,
    extract_image_url,
    generate_image,
)


def test_extract_image_url() -> None:
    result = {"images": [{"url": "https://example.com/image.jpg"}]}

    assert extract_image_url(result, "fal-ai/nano-banana-2") == result["images"][0]["url"]


def test_extract_image_url_rejects_incompatible_response() -> None:
    with pytest.raises(FalResponseError, match="incompatible response"):
        extract_image_url({"image": {"url": "https://example.com/image.jpg"}}, "other/model")


def test_extract_image_url_rejects_empty_images() -> None:
    with pytest.raises(FalResponseError, match="returned no images"):
        extract_image_url({"images": []}, "fal-ai/nano-banana-2")


@pytest.mark.asyncio
async def test_generate_image_requires_fal_key() -> None:
    with pytest.raises(ValueError, match="FAL_KEY"):
        await generate_image(
            description="a sunset",
            config=AppConfig(),
            settings=Settings(),
            model_override=None,
        )


@pytest.mark.asyncio
async def test_generate_image_uses_configured_model() -> None:
    config = AppConfig(prompt_prefix="Art: ", prompt_suffix=" HD.")

    with patch.object(
        FalProvider,
        "generate",
        new_callable=AsyncMock,
        return_value=b"image",
    ) as generate:
        result = await generate_image(
            description="a sunset",
            config=config,
            settings=Settings(fal_key="fal-test"),
            model_override=None,
        )

    assert result == b"image"
    generate.assert_awaited_once_with(
        "Art: a sunset HD.", config.image.fal.arguments
    )


@pytest.mark.asyncio
async def test_generate_image_accepts_model_override() -> None:
    config = AppConfig()

    with patch.object(
        FalProvider,
        "generate",
        new_callable=AsyncMock,
        return_value=b"image",
    ), patch(
        "frame_art.services.image_generator.FalProvider.__init__",
        return_value=None,
    ) as initialize:
        await generate_image(
            description="a mountain",
            config=config,
            settings=Settings(fal_key="fal-test"),
            model_override="fal-ai/flux/krea",
        )

    initialize.assert_called_once_with(
        api_key="fal-test", model="fal-ai/flux/krea"
    )
