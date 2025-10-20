"""
Live Stream Service for Backblaze B2

Handles chunked uploads for live video streaming. Supports streaming video data
in chunks and finalizing the stream when complete.

Usage:
    from app.services.live_stream_service import LiveStreamService

    service = LiveStreamService()

    # Upload first chunk (initializes multipart upload)
    result = await service.upload_stream_chunk(
        stream_id="stream-123",
        chunk_number=1,
        chunk_data=chunk_bytes
    )
    upload_id = result['upload_id']

    # Upload subsequent chunks
    await service.upload_stream_chunk(
        stream_id="stream-123",
        chunk_number=2,
        chunk_data=chunk_bytes,
        upload_id=upload_id
    )

    # Finalize stream
    await service.finalize_stream(stream_id, upload_id, parts)
"""

import hashlib
from typing import Optional, Dict, List
from fastapi import HTTPException
from datetime import datetime

from app.storage.b2_config import B2Config


class LiveStreamService:
    """Service for handling live video streaming to Backblaze B2"""

    def __init__(self):
        """Initialize live stream service with B2 S3 client"""
        self.s3_client = B2Config.get_s3_client()
        self.bucket_live = B2Config.BUCKET_LIVE_VIDEOS

    async def upload_stream_chunk(
        self,
        stream_id: str,
        chunk_number: int,
        chunk_data: bytes,
        upload_id: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Upload a live stream chunk

        For the first chunk (chunk_number=1), this initializes a multipart upload.
        For subsequent chunks, provide the upload_id returned from the first chunk.

        Args:
            stream_id: Unique stream identifier
            chunk_number: Sequential chunk number (starts at 1)
            chunk_data: Video chunk data as bytes
            upload_id: Multipart upload ID (None for first chunk, required for others)

        Returns:
            dict: Result with keys:
                - upload_id: Multipart upload ID (use for subsequent chunks)
                - part_number: Part number uploaded
                - etag: ETag of uploaded part
                - file_key: S3 object key

        Raises:
            HTTPException: If upload fails
            ValueError: If chunk_number > 1 but upload_id not provided
        """
        try:
            file_key = f"live/{stream_id}/stream.mp4"

            # Initialize multipart upload if first chunk
            if chunk_number == 1:
                response = self.s3_client.create_multipart_upload(
                    Bucket=self.bucket_live,
                    Key=file_key,
                    ContentType='video/mp4',
                    Metadata={
                        'stream_id': stream_id,
                        'live': 'true',
                        'start_time': datetime.utcnow().isoformat()
                    },
                    ServerSideEncryption='AES256'
                )
                upload_id = response['UploadId']

            elif not upload_id:
                raise ValueError(
                    f"upload_id is required for chunk_number > 1 (got chunk {chunk_number})"
                )

            # Upload chunk as part
            part_response = self.s3_client.upload_part(
                Bucket=self.bucket_live,
                Key=file_key,
                PartNumber=chunk_number,
                UploadId=upload_id,
                Body=chunk_data
            )

            return {
                'upload_id': upload_id,
                'part_number': chunk_number,
                'etag': part_response['ETag'],
                'file_key': file_key,
                'chunk_size': len(chunk_data)
            }

        except ValueError:
            # Re-raise value errors
            raise

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload stream chunk: {str(e)}"
            )

    async def finalize_stream(
        self,
        stream_id: str,
        upload_id: str,
        parts: List[Dict[str, any]]
    ) -> Dict[str, any]:
        """
        Finalize live stream upload

        Completes the multipart upload and makes the stream file available.

        Args:
            stream_id: Stream identifier
            upload_id: Multipart upload ID
            parts: List of uploaded parts, each with:
                - PartNumber: Part number (int)
                - ETag: ETag from upload response (str)

        Returns:
            dict: Result with keys:
                - file_url: Public URL to access stream
                - file_key: S3 object key
                - stream_id: Stream identifier
                - status: 'finalized'
                - parts_count: Number of parts uploaded

        Raises:
            HTTPException: If finalization fails

        Example:
            parts = [
                {'PartNumber': 1, 'ETag': 'etag1'},
                {'PartNumber': 2, 'ETag': 'etag2'},
            ]
            result = await service.finalize_stream('stream-123', upload_id, parts)
        """
        try:
            file_key = f"live/{stream_id}/stream.mp4"

            # Sort parts by PartNumber to ensure correct order
            sorted_parts = sorted(parts, key=lambda p: p['PartNumber'])

            # Complete multipart upload
            self.s3_client.complete_multipart_upload(
                Bucket=self.bucket_live,
                Key=file_key,
                UploadId=upload_id,
                MultipartUpload={'Parts': sorted_parts}
            )

            # Generate URL
            file_url = self._generate_file_url(file_key)

            return {
                'file_url': file_url,
                'file_key': file_key,
                'stream_id': stream_id,
                'status': 'finalized',
                'parts_count': len(sorted_parts)
            }

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to finalize stream: {str(e)}"
            )

    async def abort_stream(self, stream_id: str, upload_id: str) -> bool:
        """
        Abort a live stream upload

        Use this to cancel an in-progress stream and clean up partial uploads.

        Args:
            stream_id: Stream identifier
            upload_id: Multipart upload ID

        Returns:
            bool: True if aborted successfully

        Raises:
            HTTPException: If abort fails
        """
        try:
            file_key = f"live/{stream_id}/stream.mp4"

            self.s3_client.abort_multipart_upload(
                Bucket=self.bucket_live,
                Key=file_key,
                UploadId=upload_id
            )

            return True

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to abort stream: {str(e)}"
            )

    def _generate_file_url(self, file_key: str) -> str:
        """
        Generate public URL for stream

        Args:
            file_key: S3 object key

        Returns:
            str: Public URL (CDN if configured, otherwise B2 native)
        """
        if B2Config.CDN_URL:
            cdn_url = B2Config.CDN_URL.rstrip('/')
            return f"{cdn_url}/{file_key}"
        else:
            endpoint = B2Config.ENDPOINT_URL.rstrip('/')
            return f"{endpoint}/{self.bucket_live}/{file_key}"

    async def delete_stream(self, stream_id: str) -> bool:
        """
        Delete a finalized stream from B2

        Args:
            stream_id: Stream identifier

        Returns:
            bool: True if deleted successfully

        Raises:
            HTTPException: If deletion fails
        """
        try:
            file_key = f"live/{stream_id}/stream.mp4"

            self.s3_client.delete_object(
                Bucket=self.bucket_live,
                Key=file_key
            )

            return True

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete stream: {str(e)}"
            )

    async def list_stream_parts(self, stream_id: str, upload_id: str) -> List[Dict[str, any]]:
        """
        List uploaded parts for an in-progress stream

        Useful for tracking upload progress and resuming interrupted uploads.

        Args:
            stream_id: Stream identifier
            upload_id: Multipart upload ID

        Returns:
            list: List of uploaded parts with metadata

        Raises:
            HTTPException: If listing fails
        """
        try:
            file_key = f"live/{stream_id}/stream.mp4"

            response = self.s3_client.list_parts(
                Bucket=self.bucket_live,
                Key=file_key,
                UploadId=upload_id
            )

            return response.get('Parts', [])

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to list stream parts: {str(e)}"
            )

    def generate_presigned_url(
        self,
        stream_id: str,
        expiration: int = 3600
    ) -> str:
        """
        Generate pre-signed URL for stream access

        Args:
            stream_id: Stream identifier
            expiration: URL validity in seconds (default 1 hour)

        Returns:
            str: Pre-signed URL

        Raises:
            HTTPException: If generation fails
        """
        try:
            file_key = f"live/{stream_id}/stream.mp4"

            return self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_live,
                    'Key': file_key
                },
                ExpiresIn=expiration
            )

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate presigned URL: {str(e)}"
            )
