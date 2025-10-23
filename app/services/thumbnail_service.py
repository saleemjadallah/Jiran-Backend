"""
Video Thumbnail Generation Service

Generates high-quality thumbnails from video files using FFmpeg.
Supports:
- Single frame extraction
- Multiple frames (for preview galleries)
- Custom resolution and quality
- Automatic upload to B2 storage
"""

import logging
import os
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Optional

from app.storage.b2_config import B2Config

logger = logging.getLogger(__name__)


class ThumbnailService:
    """Service for generating video thumbnails."""

    # Default thumbnail settings
    DEFAULT_WIDTH = 720   # HD quality
    DEFAULT_HEIGHT = 720  # Square 1:1 aspect ratio (better for grids)
    DEFAULT_QUALITY = 2   # FFmpeg quality (1=best, 31=worst)

    # Thumbnail positions (which frame to extract)
    THUMBNAIL_POSITION = "00:00:01"  # 1 second into video (skip intro)

    def __init__(self):
        """Initialize thumbnail service with B2 client."""
        self.s3_client = B2Config.get_s3_client()
        self.bucket_thumbnails = B2Config.BUCKET_THUMBNAILS

    def generate_thumbnail(
        self,
        video_path: str,
        output_path: Optional[str] = None,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
        position: str = THUMBNAIL_POSITION,
        quality: int = DEFAULT_QUALITY
    ) -> str:
        """
        Generate a thumbnail from a video file.

        Args:
            video_path: Path to input video file
            output_path: Path for output thumbnail (optional, auto-generated if None)
            width: Thumbnail width in pixels
            height: Thumbnail height in pixels (use -1 for auto aspect ratio)
            position: Timestamp to extract (e.g., "00:00:01" for 1 second)
            quality: JPEG quality (1=best, 31=worst)

        Returns:
            str: Path to generated thumbnail file

        Raises:
            RuntimeError: If FFmpeg fails to generate thumbnail
        """
        # Auto-generate output path if not provided
        if output_path is None:
            temp_dir = tempfile.gettempdir()
            thumbnail_filename = f"thumb_{uuid.uuid4().hex[:8]}.jpg"
            output_path = os.path.join(temp_dir, thumbnail_filename)

        try:
            # FFmpeg command to extract frame
            # -ss: Seek to position (before -i for faster processing)
            # -i: Input file
            # -vframes 1: Extract only 1 frame
            # -vf scale: Resize frame
            # -q:v: JPEG quality
            cmd = [
                'ffmpeg',
                '-ss', position,  # Seek to timestamp
                '-i', video_path,  # Input video
                '-vframes', '1',  # Extract 1 frame
                '-vf', f'scale={width}:{height}',  # Resize
                '-q:v', str(quality),  # Quality
                '-y',  # Overwrite output file
                output_path
            ]

            # Run FFmpeg
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30  # 30 second timeout
            )

            if result.returncode != 0:
                error_msg = result.stderr.decode('utf-8')
                logger.error(f"FFmpeg failed: {error_msg}")
                raise RuntimeError(f"Failed to generate thumbnail: {error_msg}")

            # Verify thumbnail was created
            if not os.path.exists(output_path):
                raise RuntimeError("Thumbnail file was not created")

            logger.info(f"✅ Thumbnail generated: {output_path}")
            return output_path

        except subprocess.TimeoutExpired:
            logger.error("FFmpeg timeout while generating thumbnail")
            raise RuntimeError("Thumbnail generation timed out")
        except Exception as e:
            logger.error(f"Error generating thumbnail: {e}")
            raise

    def generate_and_upload_thumbnail(
        self,
        video_path: str,
        user_id: str,
        video_filename: str
    ) -> tuple[str, str]:
        """
        Generate thumbnail and upload to B2 storage.

        Args:
            video_path: Path to video file
            user_id: User ID (for organizing thumbnails)
            video_filename: Original video filename (for naming)

        Returns:
            tuple: (thumbnail_url, thumbnail_key)

        Example:
            url, key = service.generate_and_upload_thumbnail(
                '/tmp/video.mp4',
                'user123',
                'my_video.mp4'
            )
        """
        temp_thumbnail = None

        try:
            # Generate thumbnail locally
            logger.info(f"📸 Generating thumbnail for {video_filename}...")
            temp_thumbnail = self.generate_thumbnail(video_path)

            # Generate unique thumbnail filename
            base_name = Path(video_filename).stem
            thumbnail_filename = f"{base_name}_thumb_{uuid.uuid4().hex[:8]}.jpg"
            thumbnail_key = f"thumbnails/{user_id}/{thumbnail_filename}"

            # Read thumbnail file
            with open(temp_thumbnail, 'rb') as f:
                thumbnail_data = f.read()

            thumbnail_size = len(thumbnail_data)
            logger.info(f"   Thumbnail size: {thumbnail_size / 1024:.2f} KB")

            # Upload to B2
            logger.info(f"☁️  Uploading thumbnail to B2...")
            self.s3_client.put_object(
                Bucket=self.bucket_thumbnails,
                Key=thumbnail_key,
                Body=thumbnail_data,
                ContentType='image/jpeg',
                Metadata={
                    'user_id': user_id,
                    'video_filename': video_filename,
                    'generated_by': 'thumbnail_service'
                }
            )

            # Generate CDN URL using B2Config helper
            thumbnail_url = B2Config.get_public_url(self.bucket_thumbnails, thumbnail_key)

            logger.info(f"✅ Thumbnail uploaded: {thumbnail_url}")
            if B2Config.CDN_URL:
                logger.info(f"   ☁️  Served via Cloudflare CDN")

            return thumbnail_url, thumbnail_key

        except Exception as e:
            logger.error(f"❌ Failed to generate and upload thumbnail: {e}")
            raise

        finally:
            # Cleanup temporary thumbnail file
            if temp_thumbnail and os.path.exists(temp_thumbnail):
                try:
                    os.remove(temp_thumbnail)
                    logger.debug(f"🧹 Cleaned up temp thumbnail: {temp_thumbnail}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp file: {e}")

    def generate_multiple_thumbnails(
        self,
        video_path: str,
        count: int = 3,
        interval: Optional[float] = None
    ) -> list[str]:
        """
        Generate multiple thumbnails from a video (for preview gallery).

        Args:
            video_path: Path to video file
            count: Number of thumbnails to generate
            interval: Time interval between thumbnails (auto-calculated if None)

        Returns:
            list[str]: Paths to generated thumbnail files

        Example:
            # Generate 3 evenly-spaced thumbnails
            thumbnails = service.generate_multiple_thumbnails('/tmp/video.mp4', count=3)
        """
        # Get video duration first
        duration = self._get_video_duration(video_path)

        if interval is None:
            # Distribute thumbnails evenly across video
            interval = duration / (count + 1)

        thumbnails = []
        for i in range(1, count + 1):
            position_seconds = i * interval
            position = self._seconds_to_timestamp(position_seconds)

            thumbnail_path = self.generate_thumbnail(
                video_path,
                position=position
            )
            thumbnails.append(thumbnail_path)

        return thumbnails

    def _get_video_duration(self, video_path: str) -> float:
        """
        Get video duration in seconds using FFprobe.

        Args:
            video_path: Path to video file

        Returns:
            float: Duration in seconds
        """
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]

        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        duration_str = result.stdout.decode('utf-8').strip()

        try:
            return float(duration_str)
        except ValueError:
            logger.warning(f"Could not parse video duration, using default: 30s")
            return 30.0

    def _seconds_to_timestamp(self, seconds: float) -> str:
        """
        Convert seconds to FFmpeg timestamp format.

        Args:
            seconds: Time in seconds

        Returns:
            str: Timestamp in HH:MM:SS format
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"


# Global thumbnail service instance
thumbnail_service = ThumbnailService()
