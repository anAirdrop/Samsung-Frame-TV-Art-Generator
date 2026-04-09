"""Image processing service — resize and format images for Samsung Frame TV."""

from __future__ import annotations

from io import BytesIO

from PIL import Image

from ..config import OutputConfig


def process_image(
    image_data: bytes,
    output: OutputConfig | None = None,
) -> bytes:
    """Resize an image to the TV's native resolution and convert to JPEG.

    Uses Lanczos resampling and letterbox/pillarbox padding to preserve
    aspect ratio without cropping.
    """
    if output is None:
        output = OutputConfig()

    img = Image.open(BytesIO(image_data))
    target_w, target_h = output.width, output.height
    target_ratio = target_w / target_h

    # Calculate resize dimensions preserving aspect ratio
    img_ratio = img.width / img.height

    if abs(img_ratio - target_ratio) < 0.01:
        # Close enough — just resize directly
        img = img.resize((target_w, target_h), Image.LANCZOS)
    elif img_ratio > target_ratio:
        # Image is wider — fit to width, pad top/bottom
        new_w = target_w
        new_h = int(target_w / img_ratio)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        canvas = Image.new("RGB", (target_w, target_h), (0, 0, 0))
        offset_y = (target_h - new_h) // 2
        canvas.paste(img, (0, offset_y))
        img = canvas
    else:
        # Image is taller — fit to height, pad left/right
        new_h = target_h
        new_w = int(target_h * img_ratio)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        canvas = Image.new("RGB", (target_w, target_h), (0, 0, 0))
        offset_x = (target_w - new_w) // 2
        canvas.paste(img, (offset_x, 0))
        img = canvas

    # Convert to RGB (drop alpha channel if present) and save as JPEG
    if img.mode != "RGB":
        img = img.convert("RGB")

    buf = BytesIO()
    img.save(buf, format=output.format, quality=output.jpeg_quality)
    return buf.getvalue()
