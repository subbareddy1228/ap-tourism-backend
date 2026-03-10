"""
integrations/aws_s3.py
AWS S3 file upload integration — used for avatar uploads.
"""

import boto3
import uuid
import logging
from botocore.exceptions import ClientError
from src.core.config import settings

logger = logging.getLogger(__name__)


def get_s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )


async def upload_avatar(file_bytes: bytes, content_type: str, user_id: str) -> str:
    """
    Upload avatar image to S3.
    Returns the public URL of the uploaded file.
    """
    ext = content_type.split("/")[-1]   # image/jpeg → jpeg
    key = f"avatars/{user_id}/{uuid.uuid4()}.{ext}"

    try:
        s3 = get_s3_client()
        s3.put_object(
            Bucket=settings.AWS_S3_BUCKET,
            Key=key,
            Body=file_bytes,
            ContentType=content_type,
        )
        url = f"https://{settings.AWS_S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"
        logger.info("Avatar uploaded to S3 key=%s", key)
        return url

    except ClientError as e:
        logger.error("S3 upload failed: %s", str(e))
        raise ValueError("Failed to upload avatar. Please try again.")


async def delete_avatar(avatar_url: str) -> None:
    """Delete old avatar from S3 when user uploads a new one."""
    try:
        # Extract key from URL
        bucket_prefix = f"https://{settings.AWS_S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/"
        if avatar_url.startswith(bucket_prefix):
            key = avatar_url.replace(bucket_prefix, "")
            s3 = get_s3_client()
            s3.delete_object(Bucket=settings.AWS_S3_BUCKET, Key=key)
            logger.info("Old avatar deleted from S3 key=%s", key)
    except Exception as e:
        logger.warning("Failed to delete old avatar: %s", str(e))
        # Don't raise — deletion failure shouldn't block upload
