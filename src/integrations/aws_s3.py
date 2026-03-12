"""
integrations/aws_s3.py

AWS S3 integration for avatar uploads.
Async implementation using aioboto3 (FastAPI compatible).
"""

import uuid
import logging
import aioboto3
from botocore.exceptions import ClientError
from src.core.config import settings

logger = logging.getLogger(__name__)

# Shared async session (reused across requests)
_session = aioboto3.Session()

# Allowed avatar file types
ALLOWED_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}


def _s3_client():
    """Return async S3 client."""
    return _session.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )


async def upload_avatar(
    file_bytes: bytes,
    content_type: str,
    user_id: str,
) -> str:
    """
    Upload avatar to AWS S3.

    Returns public URL of uploaded image.
    """

    if not content_type or content_type not in ALLOWED_TYPES:
        raise ValueError("Invalid avatar file type")

    extension = content_type.split("/")[-1].replace("jpeg", "jpg")

    key = f"avatars/{user_id}/{uuid.uuid4()}.{extension}"

    try:

        async with _s3_client() as s3:

            await s3.put_object(
                Bucket=settings.AWS_S3_BUCKET,
                Key=key,
                Body=file_bytes,
                ContentType=content_type,
                ACL="public-read",  # makes image accessible publicly
            )

        url = (
            f"https://{settings.AWS_S3_BUCKET}.s3."
            f"{settings.AWS_REGION}.amazonaws.com/{key}"
        )

        logger.info("Avatar uploaded successfully user=%s key=%s", user_id, key)

        return url

    except ClientError as e:

        logger.error("S3 upload failed: %s", str(e))

        raise ValueError("Failed to upload avatar")


async def delete_avatar(avatar_url: str) -> None:
    """
    Delete avatar from S3.
    Used when user uploads new avatar.
    """

    if not avatar_url:
        return

    try:

        prefix = (
            f"https://{settings.AWS_S3_BUCKET}.s3."
            f"{settings.AWS_REGION}.amazonaws.com/"
        )

        if avatar_url.startswith(prefix):

            key = avatar_url.replace(prefix, "")

            async with _s3_client() as s3:

                await s3.delete_object(
                    Bucket=settings.AWS_S3_BUCKET,
                    Key=key,
                )

            logger.info("Avatar deleted key=%s", key)

    except Exception as e:

        logger.warning("Failed to delete avatar: %s", str(e))