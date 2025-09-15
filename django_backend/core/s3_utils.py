# utils/s3_utils.py
import boto3
from django.conf import settings
import uuid

s3 = boto3.client('s3',
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_S3_REGION_NAME
)

def generate_presigned_upload_url(content_type, file_ext):
    key = f"transactions/{uuid.uuid4()}.{file_ext}"
    url = s3.generate_presigned_url(
        'put_object',
        Params={
            'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
            'Key': key,
            'ContentType': content_type,
        },
        ExpiresIn=600
    )
    return {'upload_url': url, 'key': key}

def generate_presigned_view_url(key):
    return s3.generate_presigned_url(
        'get_object',
        Params={
            'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
            'Key': key,
        },
        ExpiresIn=600
    )

def generate_presigned_delete_url(key):
    return s3.generate_presigned_url(
        'delete_object',
        Params={
            'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
            'Key': key,
        },
        ExpiresIn=600
    )

def delete_s3_objects(keys: list[str]):
    if not keys:
        return
    objects = [{'Key': key} for key in keys]

    s3.delete_objects(
        Bucket=settings.AWS_STORAGE_BUCKET_NAME,
        Delete={'Objects': objects}
    )
