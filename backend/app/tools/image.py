import base64
from dataclasses import dataclass

ALLOWED_MEDIA_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/gif",
}

MAX_IMAGE_BYTES = 5 * 1024 * 1024


@dataclass
class ImageAttachment:
    filename: str
    media_type: str
    data: bytes
    storage_path: str | None = None

    def to_anthropic_block(self) -> dict:
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": self.media_type,
                "data": base64.standard_b64encode(self.data).decode("ascii"),
            },
        }


def _sniff_media_type(content: bytes, fallback: str | None) -> str:
    if content[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if content[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    if content[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if fallback in ALLOWED_MEDIA_TYPES:
        return fallback
    raise ValueError("Unsupported image format (allowed: png, jpeg, webp, gif)")


def validate_image(content: bytes, *, filename: str, content_type: str | None) -> ImageAttachment:
    if len(content) == 0:
        raise ValueError(f"Empty image: {filename}")
    if len(content) > MAX_IMAGE_BYTES:
        raise ValueError(
            f"Image '{filename}' is {len(content) // 1024} KB, max is {MAX_IMAGE_BYTES // 1024} KB"
        )
    media_type = _sniff_media_type(content, content_type)
    return ImageAttachment(filename=filename, media_type=media_type, data=content)
