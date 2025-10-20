"""
Photo Upload Service for Backblaze B2

Handles photo uploads, deletions, and URL generation for B2 cloud storage.

Usage:
    from app.services.photo_service import PhotoService

    service = PhotoService()
    result = await service.upload_photo(file, user_id="123")
    # Returns: {file_url, file_key, file_size, content_type, sha1}
"""

import hashlib
import uuid
from datetime import datetime
from typing import BinaryIO, Optional, Dict
from fastapi import UploadFile, HTTPException

from app.config.b2_config import B2Config


class PhotoService:
    """Service for handling photo uploads to Backblaze B2"""

    # Max photo size: 10MB
    MAX_PHOTO_SIZE = 10 * 1024 * 1024

    def __init__(self):
        """Initialize photo service with B2 S3 client"""
        self.s3_client = B2Config.get_s3_client()
        self.bucket_photos = B2Config.BUCKET_PHOTOS
        self.bucket_thumbnails = B2Config.BUCKET_THUMBNAILS

    def generate_photo_key(self, user_id: str, filename: str) -> str:
        """
        Generate unique S3 key for photo

        Args:
            user_id: User ID for organizing files
            filename: Original filename

        Returns:
            str: Unique S3 key path

        Example:
            "users/123/photos/20250120_143022_a1b2c3d4.jpg"
        """
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        extension = filename.split('.')[-1].lower() if '.' in filename else 'jpg'

        return f"users/{user_id}/photos/{timestamp}_{unique_id}.{extension}"

    async def upload_photo(
        self,
        file: UploadFile,
        user_id: str,
        content_type: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Upload photo to Backblaze B2

        Args:
            file: FastAPI UploadFile object
            user_id: User ID for organizing files
            content_type: Optional content type override

        Returns:
            dict: Upload result with keys:
                - file_url: Public URL to access file
                - file_key: S3 object key
                - file_size: Size in bytes
                - content_type: MIME type
                - sha1: SHA1 hash of file content

        Raises:
            HTTPException: If upload fails or file too large
        """
        try:
            # Read file content
            content = await file.read()
            file_size = len(content)

            # Validate file size (max 10MB for photos)
            if file_size > self.MAX_PHOTO_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail=f"Photo size exceeds {self.MAX_PHOTO_SIZE / (1024*1024)}MB limit"
                )

            # Detect content type
            if not content_type:
                content_type = file.content_type or 'image/jpeg'

            # Generate unique key
            file_key = self.generate_photo_key(user_id, file.filename or 'photo.jpg')

            # Calculate SHA1 checksum for integrity
            sha1_hash = hashlib.sha1(content).hexdigest()

            # Upload to B2
            self.s3_client.put_object(
                Bucket=self.bucket_photos,
                Key=file_key,
                Body=content,
                ContentType=content_type,
                Metadata={
                    'user_id': user_id,
                    'original_filename': file.filename or 'unknown',
                    'upload_timestamp': datetime.utcnow().isoformat(),
                    'sha1': sha1_hash
                },
                # Server-side encryption
                ServerSideEncryption='AES256'
            )

            # Generate public URL
            file_url = self._generate_file_url(file_key)

            return {
                'file_url': file_url,
                'file_key': file_key,
                'file_size': file_size,
                'content_type': content_type,
                'sha1': sha1_hash
            }

        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload photo: {str(e)}"
            )

    def _generate_file_url(self, file_key: str) -> str:
        """
        Generate public URL for file

        Args:
            file_key: S3 object key

        Returns:
            str: Public URL (CDN if configured, otherwise B2 native)
        """
        if B2Config.CDN_URL:
            # Use CDN URL if configured
            cdn_url = B2Config.CDN_URL.rstrip('/')
            return f"{cdn_url}/{file_key}"
        else:
            # Use B2 native URL
            endpoint = B2Config.ENDPOINT_URL.rstrip('/')
            return f"{endpoint}/{self.bucket_photos}/{file_key}"

    async def delete_photo(self, file_key: str) -> bool:
        """
        Delete photo from Backblaze B2

        Args:
            file_key: S3 object key to delete

        Returns:
            bool: True if deleted successfully

        Raises:
            HTTPException: If deletion fails
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_photos,
                Key=file_key
            )
            return True

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete photo: {str(e)}"
            )

    def generate_presigned_url(
        self,
        file_key: str,
        expiration: int = 3600
    ) -> str:
        """
        Generate pre-signed URL for temporary access

        Useful for private files that need temporary public access.

        Args:
            file_key: S3 object key
            expiration: URL validity in seconds (default 1 hour)

        Returns:
            str: Pre-signed URL valid for specified duration

        Example:
            url = service.generate_presigned_url('users/123/photo.jpg', 7200)
            # URL expires after 2 hours
        """
        try:
            return self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_photos,
                    'Key': file_key
                },
                ExpiresIn=expiration
            )

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate presigned URL: {str(e)}"
            )

    def get_photo_metadata(self, file_key: str) -> Dict[str, any]:
        """
        Get metadata for a photo

        Args:
            file_key: S3 object key

        Returns:
            dict: Photo metadata including size, content type, etc.

        Raises:
            HTTPException: If photo not found or error occurs
        """
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_photos,
                Key=file_key
            )

            return {
                'file_key': file_key,
                'content_type': response.get('ContentType'),
                'content_length': response.get('ContentLength'),
                'last_modified': response.get('LastModified'),
                'metadata': response.get('Metadata', {}),
                'etag': response.get('ETag')
            }

        except self.s3_client.exceptions.NoSuchKey:
            raise HTTPException(
                status_code=404,
                detail=f"Photo not found: {file_key}"
            )

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get photo metadata: {str(e)}"
            )
