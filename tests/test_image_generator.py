"""Tests for multi-provider image generation service."""

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from frame_art.config import AppConfig, Settings
from frame_art.services.image_generator import (
    GrokProvider,
    OpenAIProvider,
    create_provider,
    generate_image,
)


def test_create_provider_openai():
    config = AppConfig()
    settings = Settings(openai_api_key="sk-test")
    provider = create_provider("openai", config, settings)
    assert isinstance(provider, OpenAIProvider)


def test_create_provider_missing_key():
    config = AppConfig()
    settings = Settings()
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        create_provider("openai", config, settings)


def test_create_provider_unknown():
    config = AppConfig()
    settings = Settings()
    with pytest.raises(ValueError, match="Unknown image provider"):
        create_provider("dalle2", config, settings)


@pytest.mark.asyncio
async def test_generate_image_uses_correct_provider():
    config = AppConfig(prompt_prefix="Art: ", prompt_suffix=" HD.")

    fake_image = b"fake-png-data"
    fake_b64 = base64.b64encode(fake_image).decode()

    mock_response = MagicMock()
    mock_response.data = [MagicMock(b64_json=fake_b64, url=None)]

    with patch("frame_art.services.image_generator.OpenAIProvider.generate",
               new_callable=AsyncMock, return_value=fake_image) as mock_gen:
        result = await generate_image(
            description="a sunset",
            config=config,
            settings=Settings(openai_api_key="sk-test"),
        )
        mock_gen.assert_called_once_with("Art: a sunset HD.")
        assert result == fake_image


@pytest.mark.asyncio
async def test_generate_image_provider_override():
    config = AppConfig(image=AppConfig().image)
    config.image.provider = "openai"

    with patch("frame_art.services.image_generator.create_provider") as mock_create:
        mock_provider = AsyncMock()
        mock_provider.generate.return_value = b"img"
        mock_create.return_value = mock_provider

        await generate_image(
            description="test",
            config=config,
            settings=Settings(grok_api_key="xai-test"),
            provider_override="grok",
        )
        # Should use grok, not the default openai
        mock_create.assert_called_once_with(
            "grok", config, Settings(grok_api_key="xai-test")
        )
