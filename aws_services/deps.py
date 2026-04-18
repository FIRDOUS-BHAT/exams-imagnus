import boto3
from fastapi import HTTPException, status
from botocore.client import BaseClient

from aws_services.settings import has_s3_credentials, settings


def s3_auth() -> BaseClient:
    if not has_s3_credentials(settings):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AWS S3 storage is not configured",
        )
    s3 = boto3.client(service_name='s3', aws_access_key_id=settings.AWS_SERVER_PUBLIC_KEY,
                      aws_secret_access_key=settings.AWS_SERVER_SECRET_KEY
                      )

    return s3
