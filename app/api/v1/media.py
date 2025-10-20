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
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.redis import get_redis
from app.dependencies import get_current_active_user
from app.models.user import User

router = APIRouter(prefix="/api/v1/media", tags=["media"])


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
            "videoUrl": f"https://video.soukloop.com/videos/{job_id}.m3u8",
            "thumbnailUrl": f"https://cdn.soukloop.com/thumbnails/{job_id}.jpg",
            "duration": 45,
            "resolutions": ["720p", "1080p"],
        },
    }
