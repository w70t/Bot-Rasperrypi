"""
TikTok Scraper Service
Handles video extraction and metadata scraping using yt-dlp
"""

import yt_dlp
import asyncio
import logging
import time
from typing import Dict, Optional, Any, Tuple
from datetime import datetime
from app.config import get_settings
from app.models.video import VideoMetadata, ExtractionError

settings = get_settings()
logger = logging.getLogger(__name__)


class TikTokScraper:
    """
    TikTok Video Scraper
    Extracts videos and metadata from TikTok URLs
    """

    def __init__(self):
        self.timeout = settings.TIKTOK_TIMEOUT
        self.max_retries = settings.TIKTOK_MAX_RETRIES

    async def extract_video(
        self,
        url: str,
        extract_metadata: bool = True
    ) -> Tuple[Optional[str], Optional[VideoMetadata], Optional[str]]:
        """
        Extract video and metadata from TikTok URL

        Args:
            url: TikTok video URL
            extract_metadata: Whether to extract metadata

        Returns:
            Tuple of (video_url, metadata, error_message)
        """
        start_time = time.time()

        try:
            logger.info(f"Starting extraction for URL: {url}")

            # Run yt-dlp in a thread pool to avoid blocking
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                self._extract_with_ytdlp,
                url,
                extract_metadata
            )

            extraction_time = int((time.time() - start_time) * 1000)
            logger.info(f"Extraction completed in {extraction_time}ms")

            return result

        except Exception as e:
            logger.error(f"Extraction failed for {url}: {str(e)}", exc_info=True)
            return None, None, str(e)

    def _extract_with_ytdlp(
        self,
        url: str,
        extract_metadata: bool = True
    ) -> Tuple[Optional[str], Optional[VideoMetadata], Optional[str]]:
        """
        Internal method to extract using yt-dlp
        This runs in a separate thread
        """
        ydl_opts = {
            'quiet': not settings.DEBUG,
            'no_warnings': not settings.DEBUG,
            'extract_flat': False,
            'socket_timeout': self.timeout,
            'http_headers': {
                'User-Agent': settings.USER_AGENT,
            },
            # Download options
            'format': 'best',
            'noplaylist': True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract info
                info = ydl.extract_info(url, download=False)

                if not info:
                    return None, None, "Failed to extract video information"

                # Get video URL
                video_url = self._get_best_video_url(info)

                if not video_url:
                    return None, None, "No video URL found"

                # Extract metadata if requested
                metadata = None
                if extract_metadata:
                    metadata = self._parse_metadata(info)

                return video_url, metadata, None

        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e)
            logger.error(f"yt-dlp download error: {error_msg}")

            # Parse specific errors
            if "private" in error_msg.lower():
                return None, None, "Video is private"
            elif "not found" in error_msg.lower() or "404" in error_msg:
                return None, None, "Video not found"
            elif "removed" in error_msg.lower():
                return None, None, "Video has been removed"
            else:
                return None, None, f"Failed to extract video: {error_msg}"

        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return None, None, str(e)

    def _get_best_video_url(self, info: Dict[str, Any]) -> Optional[str]:
        """
        Get the best quality video URL from yt-dlp info

        Args:
            info: yt-dlp extracted info

        Returns:
            Video URL or None
        """
        try:
            # Try to get direct URL
            if 'url' in info:
                return info['url']

            # Try formats
            if 'formats' in info and info['formats']:
                # Get highest quality format with video
                video_formats = [
                    f for f in info['formats']
                    if f.get('vcodec') != 'none'
                ]

                if video_formats:
                    # Sort by quality (height)
                    video_formats.sort(
                        key=lambda x: x.get('height', 0),
                        reverse=True
                    )
                    return video_formats[0].get('url')

            # Fallback to any available URL
            if 'requested_downloads' in info and info['requested_downloads']:
                return info['requested_downloads'][0].get('url')

            return None

        except Exception as e:
            logger.error(f"Error getting video URL: {str(e)}")
            return None

    def _parse_metadata(self, info: Dict[str, Any]) -> VideoMetadata:
        """
        Parse metadata from yt-dlp info

        Args:
            info: yt-dlp extracted info

        Returns:
            VideoMetadata object
        """
        try:
            # Extract basic info
            video_id = info.get('id', '')
            title = info.get('title', info.get('description', ''))
            description = info.get('description', '')

            # Author info
            author = info.get('uploader', info.get('channel', ''))
            author_username = info.get('uploader_id', info.get('channel_id', ''))
            author_id = info.get('channel_id', info.get('uploader_id', ''))
            author_verified = info.get('channel_is_verified', False)

            # Engagement metrics
            views = info.get('view_count', 0)
            likes = info.get('like_count', 0)
            comments = info.get('comment_count', 0)
            # TikTok might not provide all metrics
            shares = 0  # Not always available
            bookmarks = 0  # Not always available

            # Video details
            duration = info.get('duration', 0)
            format_id = info.get('format_id', 'mp4')
            resolution = f"{info.get('width', 0)}x{info.get('height', 0)}"
            filesize = info.get('filesize', info.get('filesize_approx', 0))

            # Thumbnails
            thumbnail = info.get('thumbnail', '')
            thumbnails = info.get('thumbnails', [])
            if thumbnails and not thumbnail:
                thumbnail = thumbnails[-1].get('url', '')

            # Music/Audio
            music = None
            music_author = None
            original_sound = False

            # TikTok-specific music info
            if 'track' in info:
                music = info['track']
            elif 'creator' in info:
                music = f"{info.get('creator', '')} - Original Sound"
                original_sound = True

            # Tags
            hashtags = []
            if 'tags' in info and info['tags']:
                hashtags = [tag.replace('#', '') for tag in info['tags']]

            # Extract hashtags from description
            if description:
                import re
                found_tags = re.findall(r'#(\w+)', description)
                hashtags.extend(found_tags)
                hashtags = list(set(hashtags))  # Remove duplicates

            # Mentions
            mentions = []
            if description:
                import re
                mentions = re.findall(r'@(\w+)', description)

            # Timestamps
            created_at = None
            if 'upload_date' in info:
                try:
                    date_str = info['upload_date']
                    created_at = datetime.strptime(date_str, '%Y%m%d')
                except:
                    pass

            if not created_at and 'timestamp' in info:
                try:
                    created_at = datetime.fromtimestamp(info['timestamp'])
                except:
                    pass

            # Create metadata object
            metadata = VideoMetadata(
                video_id=video_id,
                title=title,
                description=description,
                author=author,
                author_username=author_username,
                author_id=author_id,
                author_verified=author_verified,
                views=views or 0,
                likes=likes or 0,
                comments=comments or 0,
                shares=shares,
                bookmarks=bookmarks,
                duration=duration,
                format=format_id,
                resolution=resolution,
                filesize=filesize,
                thumbnail=thumbnail,
                music=music,
                music_author=music_author,
                original_sound=original_sound,
                hashtags=hashtags,
                mentions=mentions,
                created_at=created_at,
            )

            return metadata

        except Exception as e:
            logger.error(f"Error parsing metadata: {str(e)}", exc_info=True)
            # Return minimal metadata
            return VideoMetadata(
                video_id=info.get('id', 'unknown'),
                title=info.get('title', 'Unknown'),
            )

    async def extract_with_retry(
        self,
        url: str,
        extract_metadata: bool = True,
        max_retries: Optional[int] = None
    ) -> Tuple[Optional[str], Optional[VideoMetadata], Optional[str]]:
        """
        Extract with automatic retry on failure

        Args:
            url: TikTok video URL
            extract_metadata: Whether to extract metadata
            max_retries: Maximum retry attempts (default from settings)

        Returns:
            Tuple of (video_url, metadata, error_message)
        """
        if max_retries is None:
            max_retries = self.max_retries

        last_error = None

        for attempt in range(max_retries):
            try:
                logger.info(f"Extraction attempt {attempt + 1}/{max_retries} for {url}")

                video_url, metadata, error = await self.extract_video(
                    url,
                    extract_metadata
                )

                if video_url:
                    logger.info(f"Extraction successful on attempt {attempt + 1}")
                    return video_url, metadata, None

                last_error = error

                # Wait before retry (exponential backoff)
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 1s, 2s, 4s, etc.
                    logger.info(f"Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)

            except Exception as e:
                last_error = str(e)
                logger.error(f"Attempt {attempt + 1} failed: {last_error}")

                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)

        logger.error(f"All {max_retries} attempts failed for {url}")
        return None, None, last_error or "Failed after maximum retries"

    def validate_url(self, url: str) -> Tuple[bool, Optional[str]]:
        """
        Validate TikTok URL format

        Args:
            url: URL to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not url:
            return False, "URL cannot be empty"

        url_lower = url.lower()

        # Check if it's a TikTok URL
        valid_patterns = [
            'tiktok.com/@',
            'tiktok.com/t/',
            'vm.tiktok.com/',
            'vt.tiktok.com/',
            'tiktok.com/video/',
            'm.tiktok.com/',
        ]

        if not any(pattern in url_lower for pattern in valid_patterns):
            return False, "Not a valid TikTok URL"

        # Check for common issues
        if len(url) < 20:
            return False, "URL too short to be valid"

        if ' ' in url:
            return False, "URL contains spaces"

        return True, None


# Singleton instance
scraper = TikTokScraper()


# Convenience functions
async def extract_tiktok_video(
    url: str,
    extract_metadata: bool = True,
    use_retry: bool = True
) -> Tuple[Optional[str], Optional[VideoMetadata], Optional[str]]:
    """
    Main function to extract TikTok video

    Args:
        url: TikTok video URL
        extract_metadata: Whether to extract metadata
        use_retry: Whether to use automatic retry

    Returns:
        Tuple of (video_url, metadata, error_message)
    """
    # Validate URL first
    is_valid, error = scraper.validate_url(url)
    if not is_valid:
        return None, None, error

    # Extract
    if use_retry:
        return await scraper.extract_with_retry(url, extract_metadata)
    else:
        return await scraper.extract_video(url, extract_metadata)


def validate_tiktok_url(url: str) -> Tuple[bool, Optional[str]]:
    """
    Validate TikTok URL

    Args:
        url: URL to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    return scraper.validate_url(url)
