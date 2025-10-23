"""
Media Upload & Processing API Endpoints

Handles video and image uploads to Backblaze B2 with transcoding.

Endpoints:
    - POST /api/v1/media/upload-url - Generate presigned upload URL
    - POST /api/v1/media/video/process - Start video processing job
    - GET /api/v1/media/status/{job_id} - Check processing status
"""

import secrets
from datetime import datetime, timedelta
from typing import Literal, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.redis import get_redis
from app.dependencies import get_current_active_user
from app.models.user import User

router = APIRouter(prefix="/media", tags=["media"])


# ============================================================================
# REQUEST/RESPONSE SCHEMAS
# ============================================================================


class UploadUrlRequest(BaseModel):
    """Request schema for generating upload URLs"""

    file_type: Literal["image", "video"] = Field(..., description="Type of file to upload")
    file_count: int = Field(1, ge=1, le=10, description="Number of files (for images)")
    content_type: str = Field(..., description="MIME type (e.g., image/jpeg, video/mp4)")


class UploadUrlResponse(BaseModel):
    """Upload URL details"""

    file_key: str = Field(..., description="Unique file key for storage")
    upload_url: str = Field(..., description="Presigned upload URL")
    expires_at: str = Field(..., description="URL expiration timestamp")


class UploadUrlsResponse(BaseModel):
    """Response with upload URLs"""

    success: bool = True
    data: dict = Field(
        ...,
        description="Upload URLs data",
        examples=[
            {
                "uploadUrls": [
                    {
                        "fileKey": "uploads/user_123/video_1697552800.mp4",
                        "uploadUrl": "https://s3.us-west-004.backblazeb2.com/...",
                        "expiresAt": "2025-10-17T15:30:00Z",
                    }
                ]
            }
        ],
    )


class VideoProcessRequest(BaseModel):
    """Request to process uploaded video"""

    file_key: str = Field(..., description="File key from upload-url response")
    file_url: str = Field(..., description="Final S3/B2 URL after upload")


class VideoProcessResponse(BaseModel):
    """Video processing job response"""

    success: bool = True
    data: dict = Field(
        ...,
        description="Processing job details",
        examples=[
            {
                "jobId": "job_abc123",
                "status": "processing",
                "progress": 0.0,
            }
        ],
    )


class VideoStatusResponse(BaseModel):
    """Video processing status response"""

    success: bool = True
    data: dict = Field(
        ...,
        description="Processing status and results",
        examples=[
            {
                "jobId": "job_abc123",
                "status": "completed",
                "progress": 1.0,
                "videoUrl": "https://video.soukloop.com/videos/video_123.m3u8",
                "thumbnailUrl": "https://cdn.soukloop.com/thumbnails/video_123.jpg",
                "duration": 45,
                "resolutions": ["720p", "1080p"],
            }
        ],
    )


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.post(
    "/upload-url",
    response_model=UploadUrlsResponse,
    summary="Generate presigned upload URL",
)
async def generate_upload_url(
    request: UploadUrlRequest,
    current_user: User = Depends(get_current_active_user),
):
    """
    Generate presigned upload URL(s) for Backblaze B2.

    Body:
    - file_type: 'image' or 'video'
    - file_count: Number of files (default 1, max 10 for images)
    - content_type: MIME type

    Logic:
    - Validate file_type and count
    - Generate presigned upload URL(s) for Backblaze B2
    - URL expires in 1 hour
    - Return upload URLs with file keys

    Returns:
    - uploadUrls: Array of upload URL objects
    - Each object contains: fileKey, uploadUrl, expiresAt
    """
    # Validate file count
    if request.file_type == "video" and request.file_count > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only one video can be uploaded at a time",
        )

    # Validate content type
    valid_image_types = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
    valid_video_types = ["video/mp4", "video/quicktime", "video/x-m4v"]

    if request.file_type == "image" and request.content_type not in valid_image_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image type. Allowed: {', '.join(valid_image_types)}",
        )

    if request.file_type == "video" and request.content_type not in valid_video_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid video type. Allowed: {', '.join(valid_video_types)}",
        )

    # Generate upload URLs
    upload_urls = []
    expires_at = datetime.utcnow() + timedelta(hours=1)

    for i in range(request.file_count):
        # Generate unique file key
        timestamp = int(datetime.utcnow().timestamp())
        random_id = secrets.token_hex(8)
        extension = request.content_type.split("/")[1]

        if extension == "quicktime":
            extension = "mov"
        elif extension == "x-m4v":
            extension = "m4v"

        file_key = f"uploads/user_{current_user.id}/{request.file_type}_{timestamp}_{random_id}.{extension}"

        # TODO: Generate actual presigned URL from Backblaze B2
        # For now, return placeholder URL
        # In production, use boto3 or B2 SDK:
        #
        # import boto3
        # s3_client = boto3.client(
        #     's3',
        #     endpoint_url='https://s3.us-west-004.backblazeb2.com',
        #     aws_access_key_id=settings.B2_KEY_ID,
        #     aws_secret_access_key=settings.B2_APPLICATION_KEY,
        # )
        # presigned_url = s3_client.generate_presigned_url(
        #     'put_object',
        #     Params={'Bucket': settings.B2_BUCKET_NAME, 'Key': file_key},
        #     ExpiresIn=3600,
        # )

        presigned_url = f"https://s3.us-west-004.backblazeb2.com/{file_key}?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Expires=3600"

        upload_urls.append(
            {
                "fileKey": file_key,
                "uploadUrl": presigned_url,
                "expiresAt": expires_at.isoformat() + "Z",
            }
        )

    return {
        "success": True,
        "data": {"uploadUrls": upload_urls},
    }


@router.post(
    "/video/process",
    response_model=VideoProcessResponse,
    summary="Process uploaded video",
)
async def process_video(
    request: VideoProcessRequest,
    current_user: User = Depends(get_current_active_user),
):
    """
    Start video processing job.

    Body:
    - file_key: File key from upload-url response
    - file_url: Final S3/B2 URL after upload

    Logic:
    - Create video processing job
    - Extract metadata using FFprobe (duration, resolution, bitrate)
    - Generate thumbnail at 1 second mark
    - Transcode to HLS format (multiple resolutions: 720p, 1080p)
    - Generate DASH manifest
    - Upload processed files to B2
    - Serve via Cloudflare CDN
    - Return job_id for status tracking

    Returns:
    - jobId: Unique job identifier
    - status: 'processing'
    - progress: 0.0
    """
    # Generate unique job ID
    job_id = f"job_{uuid4().hex[:16]}"

    # Store job in Redis
    redis = await get_redis()
    job_data = {
        "job_id": job_id,
        "user_id": str(current_user.id),
        "file_key": request.file_key,
        "file_url": request.file_url,
        "status": "processing",
        "progress": 0.0,
        "created_at": datetime.utcnow().isoformat(),
    }

    await redis.set(
        f"video:job:{job_id}",
        str(job_data),
        ex=86400,  # 24 hour TTL
    )

    # TODO: Start async video processing task
    # In production, use Celery or similar task queue:
    #
    # from app.services.video_processing import process_video_task
    # process_video_task.delay(job_id, request.file_url)
    #
    # For now, we'll simulate the processing

    return {
        "success": True,
        "data": {
            "jobId": job_id,
            "status": "processing",
            "progress": 0.0,
        },
    }


@router.get(
    "/status/{job_id}",
    response_model=VideoStatusResponse,
    summary="Check video processing status",
)
async def get_processing_status(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """
    Check video processing status.

    Path params:
    - job_id: Job ID from video/process response

    Returns:
    - Processing: status=processing, progress=0.0-1.0
    - Completed: status=completed, progress=1.0, videoUrl, thumbnailUrl, duration, resolutions
    - Failed: status=failed, error message
    """
    # Get job from Redis
    redis = await get_redis()
    job_data_str = await redis.get(f"video:job:{job_id}")

    if not job_data_str:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or expired",
        )

    # TODO: Parse job data from Redis
    # For now, return mock completed response
    # In production, this would check actual job status from task queue

    # Simulate completed job
    return {
        "success": True,
        "data": {
            "jobId": job_id,
            "status": "completed",
            "progress": 1.0,
            "videoUrl": f"https://video.jiran.com/videos/{job_id}.m3u8",
            "thumbnailUrl": f"https://cdn.jiran.com/thumbnails/{job_id}.jpg",
            "duration": 45,
            "resolutions": ["720p", "1080p"],
        },
    }


# ============================================================================
# BACKBLAZE B2 DIRECT UPLOAD ENDPOINTS
# ============================================================================

from fastapi import File, UploadFile
from app.services.photo_service import PhotoService
from app.services.video_service import VideoService
from app.services.live_stream_service import LiveStreamService


@router.post(
    "/photos/upload",
    summary="Upload photo to B2",
    description="Upload a photo directly to Backblaze B2 storage"
)
async def upload_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
):
    """
    Upload a photo to Backblaze B2

    **Supported formats**: JPEG, PNG, WebP, HEIC
    **Max file size**: 10MB

    Returns:
    - file_url: Public URL to access the photo
    - file_key: S3 object key for deletion/management
    - file_size: Size in bytes
    - content_type: MIME type
    - sha1: SHA1 hash for integrity verification
    """
    # Validate file type
    allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/heic']
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
        )

    photo_service = PhotoService()
    result = await photo_service.upload_photo(
        file=file,
        user_id=str(current_user.id)
    )

    return {
        'success': True,
        'data': result
    }


@router.post(
    "/videos/upload",
    summary="Upload video to B2",
    description="Upload a video with automatic multipart upload for large files"
)
async def upload_video(
    file: UploadFile = File(...),
    video_type: Literal["recorded", "live"] = "recorded",
    current_user: User = Depends(get_current_active_user),
):
    """
    Upload a video to Backblaze B2

    **Supported formats**: MP4, QuickTime, AVI
    **Max file size**: 2GB
    **Upload method**: Automatic selection based on size
    - Files < 100MB: Simple upload
    - Files >= 100MB: Multipart upload (chunked)

    Args:
    - file: Video file
    - video_type: 'recorded' or 'live'

    Returns:
    - file_url: Public URL to access the video
    - file_key: S3 object key
    - file_size: Size in bytes
    - upload_method: 'simple' or 'multipart'
    - sha1: SHA1 hash
    - parts_count: Number of parts (multipart only)
    """
    # Validate file type
    allowed_types = ['video/mp4', 'video/quicktime', 'video/x-msvideo', 'video/x-m4v']
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
        )

    # Validate video type
    if video_type not in ['recorded', 'live']:
        raise HTTPException(
            status_code=400,
            detail="video_type must be 'recorded' or 'live'"
        )

    video_service = VideoService()
    result = await video_service.upload_video(
        file=file,
        user_id=str(current_user.id),
        video_type=video_type
    )

    return {
        'success': True,
        'data': result
    }


@router.delete(
    "/photos/{file_key:path}",
    summary="Delete photo from B2"
)
async def delete_photo(
    file_key: str,
    current_user: User = Depends(get_current_active_user),
):
    """
    Delete a photo from Backblaze B2

    Args:
    - file_key: S3 object key from upload response

    Returns:
    - success: True if deleted
    - message: Confirmation message
    """
    photo_service = PhotoService()
    success = await photo_service.delete_photo(file_key)

    return {
        'success': success,
        'message': 'Photo deleted successfully'
    }


@router.delete(
    "/videos/{file_key:path}",
    summary="Delete video from B2"
)
async def delete_video(
    file_key: str,
    video_type: Literal["recorded", "live"] = "recorded",
    current_user: User = Depends(get_current_active_user),
):
    """
    Delete a video from Backblaze B2

    Args:
    - file_key: S3 object key from upload response
    - video_type: 'recorded' or 'live'

    Returns:
    - success: True if deleted
    - message: Confirmation message
    """
    video_service = VideoService()
    success = await video_service.delete_video(file_key, video_type)

    return {
        'success': success,
        'message': 'Video deleted successfully'
    }


@router.get(
    "/photos/presigned-url/{file_key:path}",
    summary="Generate presigned URL for photo"
)
async def get_photo_presigned_url(
    file_key: str,
    expiration: int = 3600,
    current_user: User = Depends(get_current_active_user),
):
    """
    Generate presigned URL for temporary photo access

    Args:
    - file_key: S3 object key
    - expiration: URL validity in seconds (default 1 hour)

    Returns:
    - url: Presigned URL
    - expires_in: Seconds until expiration
    """
    photo_service = PhotoService()
    url = photo_service.generate_presigned_url(file_key, expiration)

    return {
        'success': True,
        'url': url,
        'expires_in': expiration
    }


@router.get(
    "/photos/metadata/{file_key:path}",
    summary="Get photo metadata"
)
async def get_photo_metadata(
    file_key: str,
    current_user: User = Depends(get_current_active_user),
):
    """
    Get metadata for a photo

    Returns:
    - file_key: S3 object key
    - content_type: MIME type
    - content_length: File size in bytes
    - last_modified: Last modification timestamp
    - metadata: Custom metadata (user_id, sha1, etc.)
    - etag: ETag for caching
    """
    photo_service = PhotoService()
    metadata = photo_service.get_photo_metadata(file_key)

    return {
        'success': True,
        'data': metadata
    }


# ============================================================================
# LIVE STREAM CHUNK UPLOAD ENDPOINTS
# ============================================================================


class StreamChunkUpload(BaseModel):
    """Schema for live stream chunk upload"""
    stream_id: str = Field(..., description="Unique stream identifier")
    chunk_number: int = Field(..., ge=1, description="Sequential chunk number (starts at 1)")
    upload_id: Optional[str] = Field(None, description="Multipart upload ID (required for chunks > 1)")


class StreamFinalizeRequest(BaseModel):
    """Schema for finalizing stream upload"""
    stream_id: str = Field(..., description="Stream identifier")
    upload_id: str = Field(..., description="Multipart upload ID")
    parts: list = Field(..., description="List of uploaded parts with PartNumber and ETag")


@router.post(
    "/streams/upload-chunk",
    summary="Upload live stream chunk"
)
async def upload_stream_chunk(
    chunk_data: UploadFile = File(...),
    metadata: StreamChunkUpload = Depends(),
    current_user: User = Depends(get_current_active_user),
):
    """
    Upload a chunk of live stream data

    For the first chunk (chunk_number=1), this initializes a multipart upload.
    For subsequent chunks, provide the upload_id from the first chunk response.

    Args:
    - chunk_data: Video chunk file
    - stream_id: Unique stream identifier
    - chunk_number: Sequential chunk number (1, 2, 3, ...)
    - upload_id: Multipart upload ID (None for first chunk)

    Returns:
    - upload_id: Use this for subsequent chunks
    - part_number: Part number uploaded
    - etag: ETag of uploaded part
    - file_key: S3 object key
    - chunk_size: Size of uploaded chunk
    """
    live_service = LiveStreamService()

    # Read chunk data
    chunk_bytes = await chunk_data.read()

    result = await live_service.upload_stream_chunk(
        stream_id=metadata.stream_id,
        chunk_number=metadata.chunk_number,
        chunk_data=chunk_bytes,
        upload_id=metadata.upload_id
    )

    return {
        'success': True,
        'data': result
    }


@router.post(
    "/streams/finalize",
    summary="Finalize live stream upload"
)
async def finalize_stream(
    request: StreamFinalizeRequest,
    current_user: User = Depends(get_current_active_user),
):
    """
    Finalize a live stream upload

    Completes the multipart upload and makes the stream available.

    Args:
    - stream_id: Stream identifier
    - upload_id: Multipart upload ID
    - parts: List of parts with PartNumber and ETag

    Returns:
    - file_url: Public URL to access stream
    - file_key: S3 object key
    - stream_id: Stream identifier
    - status: 'finalized'
    - parts_count: Number of parts uploaded
    """
    live_service = LiveStreamService()
    result = await live_service.finalize_stream(
        stream_id=request.stream_id,
        upload_id=request.upload_id,
        parts=request.parts
    )

    return {
        'success': True,
        'data': result
    }


@router.post(
    "/streams/abort",
    summary="Abort live stream upload"
)
async def abort_stream(
    stream_id: str,
    upload_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """
    Abort an in-progress live stream upload

    Use this to cancel a stream and clean up partial uploads.

    Args:
    - stream_id: Stream identifier
    - upload_id: Multipart upload ID

    Returns:
    - success: True if aborted successfully
    """
    live_service = LiveStreamService()
    success = await live_service.abort_stream(stream_id, upload_id)

    return {
        'success': success,
        'message': 'Stream aborted successfully'
    }
