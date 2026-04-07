"""
integrations/aws_s3.py

AWS S3 integration for all file uploads across the AP Tourism platform.
Async implementation using aioboto3 (FastAPI compatible).

Functions:
  upload_avatar        — user profile photos
  delete_avatar        — remove old avatar on update
  upload_temple_image  — admin temple gallery
  delete_temple_image  — admin temple gallery removal
  upload_file          — generic upload for partner KYC documents  [ADDED]
  delete_file          — generic delete for partner KYC documents  [ADDED]

Fixes applied:
  - ALLOWED_IMAGE_TYPES and ALLOWED_DOC_TYPES split correctly.
    Original ALLOWED_TYPES blocked application/pdf which is the standard
    format for KYC documents (GSTIN, PAN, BANK_PROOF, PROPERTY_DOC).
  - upload_file() added — partner_service.upload_document() referenced
    this function but it did not exist, causing ImportError.
  - delete_file() added — symmetric cleanup for partner documents.
  - MAX_DOC_SIZE constant added (10 MB) — KYC PDFs can be larger than
    the 5 MB avatar limit.
"""

import uuid
import logging

import aioboto3
from botocore.exceptions import ClientError

from src.core.config import settings

logger = logging.getLogger(__name__)

# ── Shared async session (reused across requests) ────────────────────────────
_session = aioboto3.Session()

# ── Allowed file types ───────────────────────────────────────────────────────
ALLOWED_IMAGE_TYPES: frozenset[str] = frozenset({
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
})

ALLOWED_DOC_TYPES: frozenset[str] = frozenset({
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "application/pdf",           # KYC documents are almost always PDFs
})

# ── Size limits ───────────────────────────────────────────────────────────────
MAX_AVATAR_SIZE: int = 5 * 1024 * 1024    # 5 MB
MAX_DOC_SIZE:    int = 10 * 1024 * 1024   # 10 MB — KYC PDFs can be larger


# ── Internal helpers ─────────────────────────────────────────────────────────

def _s3_client():
    """Return a configured async S3 client context manager."""
    return _session.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )


def _public_url(key: str) -> str:
    """Build the public S3 URL for a given object key."""
    return (
        f"https://{settings.AWS_BUCKET_NAME}.s3."
        f"{settings.AWS_REGION}.amazonaws.com/{key}"
    )


def _extract_key(url: str) -> str | None:
    """Extract S3 object key from a full public URL. Returns None if URL doesn't match bucket."""
    prefix = _public_url("")
    if url.startswith(prefix):
        return url.replace(prefix, "")
    return None


async def _put_object(key: str, body: bytes, content_type: str) -> str:
    """
    Internal: upload bytes to S3 and return the public URL.
    Raises ValueError on ClientError so callers get a clean error message.
    """
    try:
        async with _s3_client() as s3:
            await s3.put_object(
                Bucket=settings.AWS_BUCKET_NAME,
                Key=key,
                Body=body,
                ContentType=content_type,
            )
        return _public_url(key)
    except ClientError as e:
        logger.error("S3 put_object failed key=%s error=%s", key, str(e))
        raise ValueError(f"Failed to upload file to S3: {e.response['Error']['Message']}")


async def _delete_object(url: str) -> None:
    """
    Internal: delete an S3 object by its public URL.
    Logs a warning on failure but never raises — deletion errors must not
    block the main request flow.
    """
    if not url:
        return
    key = _extract_key(url)
    if not key:
        logger.warning("S3 delete skipped — URL does not match bucket: %s", url)
        return
    try:
        async with _s3_client() as s3:
            await s3.delete_object(Bucket=settings.AWS_BUCKET_NAME, Key=key)
        logger.info("S3 object deleted key=%s", key)
    except Exception as e:
        logger.warning("S3 delete failed key=%s error=%s", key, str(e))


# ─────────────────────────────────────────────────────────────────────────────
# AVATAR UPLOADS  (Users module)
# ─────────────────────────────────────────────────────────────────────────────

async def upload_avatar(file_bytes: bytes, content_type: str, user_id: str) -> str:
    """
    Upload a user avatar image to S3.
    Path: avatars/{user_id}/{uuid}.{ext}
    Returns the public URL.
    Raises ValueError on invalid type or S3 failure.
    """
    if not content_type or content_type not in ALLOWED_IMAGE_TYPES:
        raise ValueError(
            f"Invalid avatar file type '{content_type}'. "
            f"Allowed: {', '.join(sorted(ALLOWED_IMAGE_TYPES))}"
        )

    ext = content_type.split("/")[-1].replace("jpeg", "jpg")
    key = f"avatars/{user_id}/{uuid.uuid4()}.{ext}"

    url = await _put_object(key, file_bytes, content_type)
    logger.info("Avatar uploaded user=%s key=%s", user_id, key)
    return url


async def delete_avatar(avatar_url: str) -> None:
    """Delete an existing avatar from S3. Swallows errors silently."""
    await _delete_object(avatar_url)


# ─────────────────────────────────────────────────────────────────────────────
# TEMPLE IMAGE UPLOADS  (Admin / Temple module)
# ─────────────────────────────────────────────────────────────────────────────

async def upload_temple_image(
    file_bytes: bytes,
    content_type: str,
    temple_id: str,
    filename: str,
) -> str:
    """
    Upload a temple gallery image to S3.
    Path: temples/{temple_id}/{uuid}.{ext}
    Returns the public URL.
    Raises ValueError on invalid type or S3 failure.
    """
    if not content_type or content_type not in ALLOWED_IMAGE_TYPES:
        raise ValueError(
            f"Invalid image file type '{content_type}'. "
            f"Allowed: {', '.join(sorted(ALLOWED_IMAGE_TYPES))}"
        )

    ext = content_type.split("/")[-1].replace("jpeg", "jpg")
    key = f"temples/{temple_id}/{uuid.uuid4()}.{ext}"

    url = await _put_object(key, file_bytes, content_type)
    logger.info("Temple image uploaded temple_id=%s key=%s", temple_id, key)
    return url


async def delete_temple_image(image_url: str) -> None:
    """Delete a temple image from S3. Swallows errors silently."""
    await _delete_object(image_url)


# ─────────────────────────────────────────────────────────────────────────────
# GENERIC FILE UPLOADS  (Partner KYC documents)
# ─────────────────────────────────────────────────────────────────────────────

async def upload_file(
    file_bytes: bytes,
    content_type: str,
    folder: str,
    original_filename: str,
) -> str:
    """
    Upload a generic file (image or PDF) to S3.
    Used by partner_service.upload_document() for KYC documents.

    Path: {folder}/{uuid}_{original_filename}
    Accepts: JPEG, PNG, WEBP, PDF (application/pdf)
    Max size enforced by caller (partner_service validates before calling).
    Returns the public URL.
    Raises ValueError on invalid type or S3 failure.

    Args:
        file_bytes:        Raw file content (already read by caller).
        content_type:      MIME type from UploadFile.content_type.
        folder:            S3 key prefix, e.g. "partners/{partner_id}/GSTIN".
        original_filename: Original filename for the S3 key suffix.
    """
    if not content_type or content_type not in ALLOWED_DOC_TYPES:
        raise ValueError(
            f"Invalid document file type '{content_type}'. "
            f"Allowed: {', '.join(sorted(ALLOWED_DOC_TYPES))}"
        )

    # Sanitise filename — strip path separators that could cause S3 key issues
    safe_filename = original_filename.replace("/", "_").replace("\\", "_")
    key = f"{folder}/{uuid.uuid4()}_{safe_filename}"

    url = await _put_object(key, file_bytes, content_type)
    logger.info("File uploaded folder=%s key=%s", folder, key)
    return url


async def delete_file(file_url: str) -> None:
    """
    Delete a partner document or any generic file from S3.
    Swallows errors silently — deletion failure must not block the response.
    """
    await _delete_object(file_url)