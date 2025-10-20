"""
Video Upload Service for Backblaze B2

Handles video uploads with automatic selection between simple and multipart upload
based on file size. Supports both recorded and live video types.

Usage:
    from app.services.video_service import VideoService

    service = VideoService()
    result = await service.upload_video(file, user_id="123", video_type="recorded")
    # Returns: {file_url, file_key, file_size, upload_method, sha1}
"""

import hashlib
import uuid
from datetime import datetime
from typing import Dict, Optional
from fastapi import UploadFile, HTTPException

from app.storage.b2_config import B2Config


class VideoService:
    """Service for handling video uploads to Backblaze B2"""

    # 100MB threshold for multipart upload
    MULTIPART_THRESHOLD = 100 * 1024 * 1024  # 100MB
    CHUNK_SIZE = 5 * 1024 * 1024  # 5MB chunks for multipart upload

    # Maximum video size: 2GB
    MAX_VIDEO_SIZE = 2 * 1024 * 1024 * 1024

    def __init__(self):
        """Initialize video service with B2 S3 client"""
        self.s3_client = B2Config.get_s3_client()
        self.bucket_videos = B2Config.BUCKET_VIDEOS
        self.bucket_live_videos = B2Config.BUCKET_LIVE_VIDEOS

    def generate_video_key(
        self,
        user_id: str,
        filename: str,
        video_type: str = 'recorded'
    ) -> str:
        """
        Generate unique S3 key for video

        Args:
            user_id: User ID
            filename: Original filename
            video_type: 'recorded' or 'live'

        Returns:
            str: Unique S3 key path

        Example:
            "recorded/123/20250120_143022_a1b2c3d4.mp4"
        """
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        extension = filename.split('.')[-1].lower() if '.' in filename else 'mp4'

        return f"{video_type}/{user_id}/{timestamp}_{unique_id}.{extension}"

    async def upload_video(
        self,
        file: UploadFile,
        user_id: str,
        video_type: str = 'recorded'
    ) -> Dict[str, any]:
        """
        Upload video to B2 (handles both small and large files)

        Automatically selects upload method:
        - Files < 100MB: Simple upload (single PUT request)
        - Files >= 100MB: Multipart upload (chunked)

        Args:
            file: FastAPI UploadFile object
            user_id: User ID
            video_type: 'recorded' or 'live'

        Returns:
            dict: Upload result with keys:
                - file_url: Public URL to access file
                - file_key: S3 object key
                - file_size: Size in bytes
                - upload_method: 'simple' or 'multipart'
                - sha1: SHA1 hash of file content
                - parts_count: Number of parts (multipart only)

        Raises:
            HTTPException: If upload fails or file too large
        """
        try:
            # Read file content
            content = await file.read()
            file_size = len(content)

            # Validate file size
            if file_size > self.MAX_VIDEO_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail=f"Video size exceeds {self.MAX_VIDEO_SIZE / (1024*1024*1024)}GB limit"
                )

            # Generate unique key
            file_key = self.generate_video_key(user_id, file.filename or 'video.mp4', video_type)

            # Calculate SHA1 checksum
            sha1_hash = hashlib.sha1(content).hexdigest()

            # Choose upload method based on file size
            if file_size < self.MULTIPART_THRESHOLD:
                # Simple upload for files < 100MB
                return await self._simple_upload(
                    content, file_key, file_size, user_id, sha1_hash, video_type
                )
            else:
                # Multipart upload for large files
                return await self._multipart_upload(
                    content, file_key, file_size, user_id, sha1_hash, video_type
                )

        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload video: {str(e)}"
            )

    async def _simple_upload(
        self,
        content: bytes,
        file_key: str,
        file_size: int,
        user_id: str,
        sha1_hash: str,
        video_type: str
    ) -> Dict[str, any]:
        """
        Simple upload for files < 100MB

        Args:
            content: File content as bytes
            file_key: S3 object key
            file_size: Size in bytes
            user_id: User ID
            sha1_hash: SHA1 hash of content
            video_type: 'recorded' or 'live'

        Returns:
            dict: Upload result
        """
        # Select bucket based on video type
        bucket = self.bucket_live_videos if video_type == 'live' else self.bucket_videos

        self.s3_client.put_object(
            Bucket=bucket,
            Key=file_key,
            Body=content,
            ContentType='video/mp4',
            Metadata={
                'user_id': user_id,
                'video_type': video_type,
                'upload_timestamp': datetime.utcnow().isoformat(),
                'sha1': sha1_hash
            },
            ServerSideEncryption='AES256'
        )

        file_url = self._generate_file_url(file_key, bucket)

        return {
            'file_url': file_url,
            'file_key': file_key,
            'file_size': file_size,
            'upload_method': 'simple',
            'sha1': sha1_hash
        }

    async def _multipart_upload(
        self,
        content: bytes,
        file_key: str,
        file_size: int,
        user_id: str,
        sha1_hash: str,
        video_type: str
    ) -> Dict[str, any]:
        """
        Multipart upload for large files (100MB+)

        Uploads file in 5MB chunks for better reliability and progress tracking.

        Args:
            content: File content as bytes
            file_key: S3 object key
            file_size: Size in bytes
            user_id: User ID
            sha1_hash: SHA1 hash of content
            video_type: 'recorded' or 'live'

        Returns:
            dict: Upload result

        Raises:
            Exception: If multipart upload fails (aborts upload automatically)
        """
        # Select bucket based on video type
        bucket = self.bucket_live_videos if video_type == 'live' else self.bucket_videos

        # Initiate multipart upload
        response = self.s3_client.create_multipart_upload(
            Bucket=bucket,
            Key=file_key,
            ContentType='video/mp4',
            Metadata={
                'user_id': user_id,
                'video_type': video_type,
                'upload_timestamp': datetime.utcnow().isoformat(),
                'sha1': sha1_hash
            },
            ServerSideEncryption='AES256'
        )

        upload_id = response['UploadId']
        parts = []

        try:
            # Upload parts
            part_number = 1
            offset = 0

            while offset < file_size:
                # Calculate chunk size
                chunk_size = min(self.CHUNK_SIZE, file_size - offset)
                chunk = content[offset:offset + chunk_size]

                # Upload part
                part_response = self.s3_client.upload_part(
                    Bucket=bucket,
                    Key=file_key,
                    PartNumber=part_number,
                    UploadId=upload_id,
                    Body=chunk
                )

                parts.append({
                    'PartNumber': part_number,
                    'ETag': part_response['ETag']
                })

                offset += chunk_size
                part_number += 1

            # Complete multipart upload
            self.s3_client.complete_multipart_upload(
                Bucket=bucket,
                Key=file_key,
                UploadId=upload_id,
                MultipartUpload={'Parts': parts}
            )

            file_url = self._generate_file_url(file_key, bucket)

            return {
                'file_url': file_url,
                'file_key': file_key,
                'file_size': file_size,
                'upload_method': 'multipart',
                'parts_count': len(parts),
                'sha1': sha1_hash
            }

        except Exception as e:
            # Abort multipart upload on error to prevent orphaned parts
            try:
                self.s3_client.abort_multipart_upload(
                    Bucket=bucket,
                    Key=file_key,
                    UploadId=upload_id
                )
            except Exception as abort_error:
                print(f"Failed to abort multipart upload: {abort_error}")

            raise e

    def _generate_file_url(self, file_key: str, bucket: str) -> str:
        """
        Generate public URL for video

        Args:
            file_key: S3 object key
            bucket: Bucket name

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
            return f"{endpoint}/{bucket}/{file_key}"

    async def delete_video(self, file_key: str, video_type: str = 'recorded') -> bool:
        """
        Delete video from Backblaze B2

        Args:
            file_key: S3 object key to delete
            video_type: 'recorded' or 'live'

        Returns:
            bool: True if deleted successfully

        Raises:
            HTTPException: If deletion fails
        """
        try:
            bucket = self.bucket_live_videos if video_type == 'live' else self.bucket_videos

            self.s3_client.delete_object(
                Bucket=bucket,
                Key=file_key
            )
            return True

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete video: {str(e)}"
            )

    def generate_presigned_url(
        self,
        file_key: str,
        video_type: str = 'recorded',
        expiration: int = 3600
    ) -> str:
        """
        Generate pre-signed URL for temporary access

        Args:
            file_key: S3 object key
            video_type: 'recorded' or 'live'
            expiration: URL validity in seconds (default 1 hour)

        Returns:
            str: Pre-signed URL valid for specified duration
        """
        try:
            bucket = self.bucket_live_videos if video_type == 'live' else self.bucket_videos

            return self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': bucket,
                    'Key': file_key
                },
                ExpiresIn=expiration
            )

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate presigned URL: {str(e)}"
            )
