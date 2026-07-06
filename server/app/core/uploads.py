import uuid
from pathlib import Path

from fastapi import UploadFile

from app.config import settings

_MAGIC_BYTES: dict[bytes, str] = {
    b"\xff\xd8\xff": "jpg",
    b"\x89PNG\r\n\x1a\n": "png",
    b"GIF87a": "gif",
    b"GIF89a": "gif",
}


def _sniff_extension(header: bytes) -> str | None:
    for magic, ext in _MAGIC_BYTES.items():
        if header.startswith(magic):
            return ext
    if header[0:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "webp"
    return None


async def save_photo(photo: UploadFile) -> str:
    """Validates and saves an uploaded photo to local disk. Returns the served photo_url.

    Raises ValueError on invalid file type or if the file exceeds the configured size limit.
    """
    header = await photo.read(12)
    ext = _sniff_extension(header)
    if ext is None:
        raise ValueError("Unsupported or unrecognized image file type")

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid.uuid4().hex}.{ext}"
    dest_path = upload_dir / filename

    max_size = settings.max_upload_size_bytes
    written = len(header)
    if written > max_size:
        raise ValueError("Uploaded file exceeds the maximum allowed size")

    with dest_path.open("wb") as f:
        f.write(header)
        while chunk := await photo.read(64 * 1024):
            written += len(chunk)
            if written > max_size:
                f.close()
                dest_path.unlink(missing_ok=True)
                raise ValueError("Uploaded file exceeds the maximum allowed size")
            f.write(chunk)

    return f"/uploads/{filename}"
