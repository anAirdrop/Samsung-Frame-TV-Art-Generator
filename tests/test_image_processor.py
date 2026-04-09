"""Tests for image processing service."""

from io import BytesIO

from PIL import Image

from frame_art.config import OutputConfig
from frame_art.services.image_processor import process_image


def test_process_resizes_to_target(sample_image_bytes):
    output = OutputConfig(width=3840, height=2160, format="JPEG", jpeg_quality=85)
    result = process_image(sample_image_bytes, output)

    img = Image.open(BytesIO(result))
    assert img.size == (3840, 2160)
    assert img.format == "JPEG"


def test_process_handles_wider_image():
    """An extra-wide image should be letterboxed (padded top/bottom)."""
    img = Image.new("RGB", (800, 200), color=(0, 255, 0))
    buf = BytesIO()
    img.save(buf, format="PNG")

    output = OutputConfig(width=3840, height=2160)
    result = process_image(buf.getvalue(), output)

    out = Image.open(BytesIO(result))
    assert out.size == (3840, 2160)


def test_process_handles_taller_image():
    """A tall image should be pillarboxed (padded left/right)."""
    img = Image.new("RGB", (200, 800), color=(0, 0, 255))
    buf = BytesIO()
    img.save(buf, format="PNG")

    output = OutputConfig(width=3840, height=2160)
    result = process_image(buf.getvalue(), output)

    out = Image.open(BytesIO(result))
    assert out.size == (3840, 2160)


def test_process_handles_rgba_image():
    """RGBA images should be converted to RGB for JPEG output."""
    img = Image.new("RGBA", (100, 60), color=(255, 0, 0, 128))
    buf = BytesIO()
    img.save(buf, format="PNG")

    output = OutputConfig(width=1920, height=1080)
    result = process_image(buf.getvalue(), output)

    out = Image.open(BytesIO(result))
    assert out.mode == "RGB"
    assert out.size == (1920, 1080)


def test_process_default_output(sample_image_bytes):
    """Default output config should produce 3840x2160."""
    result = process_image(sample_image_bytes)
    img = Image.open(BytesIO(result))
    assert img.size == (3840, 2160)
