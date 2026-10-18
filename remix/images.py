"""Shrink photos before sending them to Gemini (faster, cheaper, cache-friendly)."""
import io

from PIL import Image, ImageOps

MAX_EDGE = 1024


def downscale(data: bytes, mime: str):
    """Return (jpeg_bytes, "image/jpeg"), or the original if Pillow can't read it (e.g. HEIC)."""
    try:
        img = ImageOps.exif_transpose(Image.open(io.BytesIO(data)))
    except Exception:
        return data, mime
    img = img.convert("RGB")
    img.thumbnail((MAX_EDGE, MAX_EDGE))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue(), "image/jpeg"
