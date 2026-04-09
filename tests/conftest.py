"""Shared test fixtures."""

import pytest

from frame_art.config import AppConfig, ImageConfig, OpenAIConfig, OutputConfig, TVConfig


@pytest.fixture
def sample_config():
    return AppConfig(
        image=ImageConfig(
            provider="openai",
            openai=OpenAIConfig(model="gpt-image-1", quality="low", size="1024x1024"),
            output=OutputConfig(width=3840, height=2160, format="JPEG", jpeg_quality=85),
        ),
        prompt_prefix="Art: ",
        prompt_suffix=" HD.",
        tvs={
            "living_room": TVConfig(
                host="192.168.1.100",
                port=8002,
                token_file="/tmp/test_token.txt",
                aliases=["living room", "lounge"],
                matte="none",
            ),
            "bedroom": TVConfig(
                host="192.168.1.101",
                port=8002,
                token_file="/tmp/test_token2.txt",
                aliases=["bedroom", "master bedroom"],
                matte="modern_apricot",
            ),
        },
    )


@pytest.fixture
def sample_image_bytes():
    """Create a minimal valid PNG image (1x1 red pixel)."""
    from PIL import Image
    from io import BytesIO

    img = Image.new("RGB", (100, 60), color=(255, 0, 0))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
