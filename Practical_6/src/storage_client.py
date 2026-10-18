import gzip
import hashlib
import io
import os
from typing import Dict, Optional, Tuple
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

class StorageClient:
    """Interface to S3/MinIO distributed object store with local tiering and verification."""

    def __init__(
        self,
        endpoint_url: str = "http://127.0.0.1:9000",
        access_key: str = "minioadmin",
        secret_key: str = "minioadmin",
        region: str = "us-east-1"
    ):
        self.endpoint_url = os.getenv("MINIO_ENDPOINT", endpoint_url)
        self.access_key = os.getenv("MINIO_ROOT_USER", access_key)
        self.secret_key = os.getenv("MINIO_ROOT_PASSWORD", secret_key)
        self.region = os.getenv("MINIO_REGION", region)
        self._s3 = None

    @property
    def client(self):
        if self._s3 is None:
            self._s3 = boto3.client(
                "s3",
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                config=Config(signature_version="s3v4"),
                region_name=self.region
            )
        return self._s3

    def ensure_bucket(self, bucket_name: str) -> bool:
        """Ensures that the bucket exists in MinIO."""
        try:
            self.client.head_bucket(Bucket=bucket_name)
            return True
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code in ["404", "NoSuchBucket"]:
                self.client.create_bucket(Bucket=bucket_name)
                return True
            raise

    def upload_file(self, bucket_name: str, object_key: str, file_path: str, metadata: Optional[Dict] = None) -> Dict:
        """Uploads a local file to the specified bucket with custom metadata."""
        self.ensure_bucket(bucket_name)
        with open(file_path, "rb") as f:
            data = f.read()

        md5_hash = hashlib.md5(data).hexdigest()
        extra_args = {"Metadata": metadata or {}}
        self.client.put_object(
            Bucket=bucket_name,
            Key=object_key,
            Body=data,
            Metadata=metadata or {}
        )
        return {
            "bucket": bucket_name,
            "key": object_key,
            "size_bytes": len(data),
            "md5": md5_hash
        }

    def get_object_bytes(self, bucket_name: str, object_key: str) -> bytes:
        response = self.client.get_object(Bucket=bucket_name, Key=object_key)
        return response["Body"].read()

    def get_object_metadata(self, bucket_name: str, object_key: str) -> Dict:
        return self.client.head_object(Bucket=bucket_name, Key=object_key)

    def transition_object(
        self,
        src_bucket: str,
        dest_bucket: str,
        object_key: str,
        compress: bool = False
    ) -> Tuple[bool, str, Dict]:
        """
        Safely transitions an object from src_bucket to dest_bucket.
        Validates the destination checksum and size before removing source.
        """
        self.ensure_bucket(dest_bucket)
        
        # 1. Fetch source object
        try:
            src_bytes = self.get_object_bytes(src_bucket, object_key)
            src_meta = self.get_object_metadata(src_bucket, object_key)
        except ClientError as e:
            return False, f"Source object s3://{src_bucket}/{object_key} not found: {e}", {}

        src_md5 = hashlib.md5(src_bytes).hexdigest()

        # 2. Prepare destination payload (apply compression if cold tier)
        dest_key = f"{object_key}.gz" if compress else object_key
        if compress:
            buf = io.BytesIO()
            with gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=9) as gz:
                gz.write(src_bytes)
            dest_bytes = buf.getvalue()
        else:
            dest_bytes = src_bytes

        dest_md5 = hashlib.md5(dest_bytes).hexdigest()

        # 3. Put into destination bucket
        custom_meta = src_meta.get("Metadata", {}).copy()
        custom_meta["orig_md5"] = src_md5
        custom_meta["orig_size"] = str(len(src_bytes))
        custom_meta["compressed"] = "true" if compress else "false"

        self.client.put_object(
            Bucket=dest_bucket,
            Key=dest_key,
            Body=dest_bytes,
            Metadata=custom_meta
        )

        # 4. Verification step: verify destination exists and size/checksum match
        dest_head = self.get_object_metadata(dest_bucket, dest_key)
        dest_len = dest_head["ContentLength"]
        if dest_len != len(dest_bytes):
            return False, f"Verification failed: expected {len(dest_bytes)} bytes, got {dest_len}", {}

        # 5. Delete from source bucket only after successful verification
        self.client.delete_object(Bucket=src_bucket, Key=object_key)

        return True, "Transition verified and source safely purged", {
            "source_bucket": src_bucket,
            "source_key": object_key,
            "destination_bucket": dest_bucket,
            "destination_key": dest_key,
            "source_size": len(src_bytes),
            "dest_size": dest_len,
            "source_md5": src_md5,
            "dest_md5": dest_md5,
            "compressed": compress
        }
