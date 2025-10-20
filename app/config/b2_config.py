"""
Backblaze B2 Cloud Storage Configuration

This module provides configuration and client initialization for Backblaze B2
using the S3-compatible API via boto3.

Usage:
    from app.config.b2_config import B2Config

    # Get S3 client
    s3_client = B2Config.get_s3_client()

    # Upload a file
    s3_client.put_object(
        Bucket=B2Config.BUCKET_PHOTOS,
        Key='users/123/photo.jpg',
        Body=file_content
    )
"""

import os
import boto3
from typing import Optional


class B2Config:
    """Backblaze B2 configuration using S3-compatible API"""

    # B2 Endpoint and Credentials
    ENDPOINT_URL: str = os.getenv('B2_ENDPOINT_URL', 'https://s3.eu-central-003.backblazeb2.com')
    ACCESS_KEY_ID: str = os.getenv('B2_ACCESS_KEY_ID', '')
    SECRET_ACCESS_KEY: str = os.getenv('B2_SECRET_ACCESS_KEY', '')
    REGION: str = os.getenv('B2_REGION', 'eu-central-003')

    # Bucket names
    BUCKET_LIVE_VIDEOS: str = os.getenv('B2_BUCKET_LIVE_VIDEOS', 'jiran-live-videos')
    BUCKET_VIDEOS: str = os.getenv('B2_BUCKET_VIDEOS', 'jiran-videos')
    BUCKET_PHOTOS: str = os.getenv('B2_BUCKET_PHOTOS', 'jiran-photos')
    BUCKET_THUMBNAILS: str = os.getenv('B2_BUCKET_THUMBNAILS', 'jiran-thumbnails')

    # CDN URL (optional)
    CDN_URL: Optional[str] = os.getenv('B2_CDN_URL') or None

    @classmethod
    def get_s3_client(cls):
        """
        Create and return S3 client for Backblaze B2

        Returns:
            boto3.client: Configured S3 client for B2

        Raises:
            ValueError: If required credentials are missing
        """
        if not cls.ACCESS_KEY_ID or not cls.SECRET_ACCESS_KEY:
            raise ValueError(
                "B2 credentials not configured. Set B2_ACCESS_KEY_ID and "
                "B2_SECRET_ACCESS_KEY environment variables."
            )

        return boto3.client(
            's3',
            endpoint_url=cls.ENDPOINT_URL,
            aws_access_key_id=cls.ACCESS_KEY_ID,
            aws_secret_access_key=cls.SECRET_ACCESS_KEY,
            region_name=cls.REGION
        )

    @classmethod
    def get_s3_resource(cls):
        """
        Create and return S3 resource for Backblaze B2

        Returns:
            boto3.resource: Configured S3 resource for B2

        Raises:
            ValueError: If required credentials are missing
        """
        if not cls.ACCESS_KEY_ID or not cls.SECRET_ACCESS_KEY:
            raise ValueError(
                "B2 credentials not configured. Set B2_ACCESS_KEY_ID and "
                "B2_SECRET_ACCESS_KEY environment variables."
            )

        return boto3.resource(
            's3',
            endpoint_url=cls.ENDPOINT_URL,
            aws_access_key_id=cls.ACCESS_KEY_ID,
            aws_secret_access_key=cls.SECRET_ACCESS_KEY,
            region_name=cls.REGION
        )

    @classmethod
    def validate_config(cls) -> bool:
        """
        Validate B2 configuration

        Returns:
            bool: True if configuration is valid

        Raises:
            ValueError: If configuration is invalid
        """
        errors = []

        if not cls.ENDPOINT_URL:
            errors.append("B2_ENDPOINT_URL is not set")

        if not cls.ACCESS_KEY_ID:
            errors.append("B2_ACCESS_KEY_ID is not set")

        if not cls.SECRET_ACCESS_KEY:
            errors.append("B2_SECRET_ACCESS_KEY is not set")

        if not cls.BUCKET_PHOTOS:
            errors.append("B2_BUCKET_PHOTOS is not set")

        if not cls.BUCKET_VIDEOS:
            errors.append("B2_BUCKET_VIDEOS is not set")

        if not cls.BUCKET_LIVE_VIDEOS:
            errors.append("B2_BUCKET_LIVE_VIDEOS is not set")

        if not cls.BUCKET_THUMBNAILS:
            errors.append("B2_BUCKET_THUMBNAILS is not set")

        if errors:
            raise ValueError(
                f"B2 configuration validation failed:\n" +
                "\n".join(f"  - {error}" for error in errors)
            )

        return True
