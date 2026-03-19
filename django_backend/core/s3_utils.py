# utils/s3_utils.py
import logging
import uuid
from typing import Iterable, List, Dict, Optional, Any
import boto3
from botocore.exceptions import ClientError
from django.conf import settings

logger = logging.getLogger(__name__)

# Configurable defaults
_DEFAULT_PRESIGNED_EXPIRES = int(getattr(settings, 'AWS_PRESIGNED_URL_EXPIRES', 600))
_S3_BUCKET = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)
_AWS_REGION = getattr(settings, 'AWS_S3_REGION_NAME', None)
_AWS_KEY = getattr(settings, 'AWS_ACCESS_KEY_ID', None)
_AWS_SECRET = getattr(settings, 'AWS_SECRET_ACCESS_KEY', None)

# module-level cache for client
_s3_client = None

def _get_s3_client():
    global _s3_client
    if _s3_client is None:
        if not (_AWS_KEY and _AWS_SECRET and _S3_BUCKET):
            raise RuntimeError("S3 configuration missing (AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY/AWS_STORAGE_BUCKET_NAME).")
        _s3_client = boto3.client('s3',
            aws_access_key_id=_AWS_KEY,
            aws_secret_access_key=_AWS_SECRET,
            region_name=_AWS_REGION
        )
    return _s3_client


def _safe_ext(ext: str) -> str:
    if not ext:
        raise ValueError("file_ext cannot be empty")
    ext = ext.lstrip('.').lower()
    # optionally validate allowed extensions here
    return ext


def generate_presigned_upload_url(content_type: str, file_ext: str, key: str, expires_in: Optional[int] = None) -> Dict[str, Any]:
    """
    Returns dict {'upload_url': url, 'key': key}
    - content_type: MIME type expected for the uploaded object
    - file_ext: extension without leading dot (e.g., 'jpg')
    - key: user or folder prefix (should be sanitized by caller)
    - expires_in: seconds (optional override)
    """
    if not content_type or not isinstance(content_type, str):
        raise ValueError("content_type is required")
    if not key or '..' in key:
        raise ValueError("Invalid key")
    
    # Validate allowed key prefixes
    allowed_prefixes = getattr(settings, 'ALLOWED_IMAGE_KEYS', ['profile_pictures/', 'transactions/'])
    if not any(key.startswith(prefix) for prefix in allowed_prefixes):
        raise ValueError(f"Key must start with one of: {', '.join(allowed_prefixes)}")

    ext = _safe_ext(file_ext)
    file_key = f"{key.rstrip('/')}/{uuid.uuid4()}.{ext}"
    
    # Shorter default expiration for uploads (5 minutes instead of 10)
    expires = expires_in if expires_in is not None else min(_DEFAULT_PRESIGNED_EXPIRES, 300)

    client = _get_s3_client()
    try:
        url = client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': _S3_BUCKET,
                'Key': file_key,
                'ContentType': content_type,
            },
            ExpiresIn=expires
        )
        logger.debug("Generated presigned upload url for key=%s expires=%s", file_key, expires)
        return {'upload_url': url, 'key': file_key, 'expires_in': expires}
    except ClientError as e:
        logger.exception("Failed to generate presigned upload URL: %s", e)
        raise RuntimeError("Failed to generate upload URL") from e


def generate_presigned_view_url(key: str, expires_in: Optional[int] = None) -> str:
    if not key:
        raise ValueError("key is required")
    expires = expires_in or _DEFAULT_PRESIGNED_EXPIRES
    client = _get_s3_client()
    try:
        return client.generate_presigned_url(
            'get_object',
            Params={'Bucket': _S3_BUCKET, 'Key': key},
            ExpiresIn=expires
        )
    except ClientError as e:
        logger.exception("Failed to generate presigned view URL for %s: %s", key, e)
        raise RuntimeError("Failed to generate view URL") from e


def delete_s3_objects(keys: Iterable[str]) -> Dict[str, Any]:
    """
    Delete keys from S3 in batches. Returns dict with summary:
    { 'deleted': [keys], 'errors': [{Key, Code, Message}, ...] }
    """
    keys = list(keys or [])
    if not keys:
        return {'deleted': [], 'errors': []}

    client = _get_s3_client()
    deleted = []
    errors = []
    # AWS allows up to 1000 keys per delete_objects request
    MAX_BATCH = 1000
    for i in range(0, len(keys), MAX_BATCH):
        batch = keys[i:i + MAX_BATCH]
        objects = [{'Key': k} for k in batch]
        try:
            resp = client.delete_objects(
                Bucket=_S3_BUCKET,
                Delete={'Objects': objects, 'Quiet': False}
            )
            # resp may contain 'Deleted' and 'Errors'
            deleted_batch = [d.get('Key') for d in resp.get('Deleted', []) if d.get('Key')]
            deleted.extend(deleted_batch)
            for err in resp.get('Errors', []):
                errors.append({'Key': err.get('Key'), 'Code': err.get('Code'), 'Message': err.get('Message')})
        except ClientError as e:
            logger.exception("Failed to delete S3 objects batch: %s", e)
            # Add all keys in this failed batch to errors with message
            for k in batch:
                errors.append({'Key': k, 'Code': 'ClientError', 'Message': str(e)})
    return {'deleted': deleted, 'errors': errors}
