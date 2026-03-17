"""
AWS S3 integration for uploading vehicle images and documents.
"""
import boto3
from botocore.exceptions import ClientError
from src.core.config import settings


class S3Client:
    def __init__(self):
        self.client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )
        self.bucket = settings.S3_BUCKET_NAME

    def upload_file(self, file_obj, key: str, content_type: str) -> str:
        """Upload a file to S3 and return the public URL."""
        self.client.upload_fileobj(
            file_obj,
            self.bucket,
            key,
            ExtraArgs={"ContentType": content_type},
        )
        return f"https://{self.bucket}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"

    def delete_file(self, key: str):
        """Delete a file from S3."""
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def generate_presigned_url(self, key: str, expiry: int = 3600) -> str:
        """Generate a pre-signed URL for temporary access."""
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expiry,
        )
