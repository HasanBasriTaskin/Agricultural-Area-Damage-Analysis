import os
import io
from minio import Minio
from minio.error import S3Error
from datetime import timedelta
from app.core.config import settings

class MinioStorageClient:
    def __init__(
        self,
        endpoint: str = None,
        access_key: str = None,
        secret_key: str = None,
        bucket_name: str = None,
        secure: bool = None
    ):
        self.endpoint = endpoint or settings.MINIO_ENDPOINT
        self.access_key = access_key or settings.MINIO_ACCESS_KEY
        self.secret_key = secret_key or settings.MINIO_SECRET_KEY
        self.bucket_name = bucket_name or settings.MINIO_BUCKET_NAME
        self.secure = secure if secure is not None else settings.MINIO_SECURE

        self.client = Minio(
            endpoint=self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure
        )
        self._ensure_bucket()

    def _ensure_bucket(self):
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
        except Exception as e:
            # MinIO might be starting or bucket already exists
            pass

    def upload_file(self, local_path: str, object_name: str, content_type: str = "application/octet-stream") -> str:
        """
        Uploads a local file to MinIO bucket and returns the object_name (minio_key).
        """
        self._ensure_bucket()
        self.client.fput_object(
            bucket_name=self.bucket_name,
            object_name=object_name,
            file_path=local_path,
            content_type=content_type
        )
        return object_name

    def upload_bytes(self, data: bytes, object_name: str, content_type: str = "application/octet-stream") -> str:
        """
        Uploads in-memory bytes to MinIO and returns the object_name.
        """
        self._ensure_bucket()
        data_stream = io.BytesIO(data)
        self.client.put_object(
            bucket_name=self.bucket_name,
            object_name=object_name,
            data=data_stream,
            length=len(data),
            content_type=content_type
        )
        return object_name

    def download_file(self, object_name: str, target_local_path: str) -> str:
        """
        Downloads an object from MinIO to local filesystem.
        """
        os.makedirs(os.path.dirname(target_local_path), exist_ok=True)
        self.client.fget_object(
            bucket_name=self.bucket_name,
            object_name=object_name,
            file_path=target_local_path
        )
        return target_local_path

    def get_presigned_download_url(self, object_name: str, expires_seconds: int = 3600) -> str:
        """
        Generates a presigned URL for downloading the object.
        """
        return self.client.presigned_get_object(
            bucket_name=self.bucket_name,
            object_name=object_name,
            expires=timedelta(seconds=expires_seconds)
        )

    def get_object(self, object_name: str):
        """
        Retrieves raw stream for an object from MinIO.
        """
        return self.client.get_object(self.bucket_name, object_name)
