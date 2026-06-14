"""MinIO file storage service."""

import io
from typing import BinaryIO

from minio import Minio

from app.core.config import settings


class MinIOService:
    """MinIO-compatible object storage service."""

    def __init__(self):
        self._client = None

    @property
    def client(self) -> Minio:
        if self._client is None:
            self._client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=False,
            )
        return self._client

    async def ensure_bucket(self, bucket_name: str | None = None) -> None:
        """Create bucket if it doesn't exist."""
        bucket = bucket_name or settings.MINIO_BUCKET_PAPERS_PAPERS
        if not self.client.bucket_exists(bucket):
            self.client.make_bucket(bucket)

    async def upload_file(
        self,
        file_data: BinaryIO | bytes,
        object_key: str,
        content_type: str = "application/octet-stream",
        bucket_name: str | None = None,
    ) -> str:
        """Upload file to MinIO and return object key."""
        bucket = bucket_name or settings.MINIO_BUCKET_PAPERS
        await self.ensure_bucket(bucket)

        if isinstance(file_data, bytes):
            file_data = io.BytesIO(file_data)
            length = len(file_data.getvalue())
        else:
            file_data.seek(0, 2)
            length = file_data.tell()
            file_data.seek(0)

        self.client.put_object(
            bucket,
            object_key,
            file_data,
            length,
            content_type=content_type,
        )
        return object_key

    async def download_file(
        self,
        object_key: str,
        bucket_name: str | None = None,
    ) -> bytes:
        """Download file from MinIO."""
        bucket = bucket_name or settings.MINIO_BUCKET_PAPERS
        response = self.client.get_object(bucket, object_key)
        data = response.read()
        response.close()
        response.release_conn()
        return data

    async def delete_file(
        self,
        object_key: str,
        bucket_name: str | None = None,
    ) -> None:
        """Delete file from MinIO."""
        bucket = bucket_name or settings.MINIO_BUCKET_PAPERS
        self.client.remove_object(bucket, object_key)

    async def get_presigned_url(
        self,
        object_key: str,
        expires_in: int = 3600,
        bucket_name: str | None = None,
    ) -> str:
        """Generate presigned URL for file access."""
        bucket = bucket_name or settings.MINIO_BUCKET_PAPERS
        return self.client.presigned_get_object(
            bucket, object_key, expires=expires_in,
        )


minio_service = MinIOService()
