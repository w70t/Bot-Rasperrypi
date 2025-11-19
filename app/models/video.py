"""
Video Data Models
Defines video, metadata, and extraction request/response models
"""

from pydantic import BaseModel, HttpUrl, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime


class VideoExtractRequest(BaseModel):
    """
    Video Extraction Request
    Request body for /api/v1/video/extract endpoint
    """
    url: str
    extract_metadata: bool = True
    extract_country: bool = False  # Premium feature

    @validator('url')
    def validate_tiktok_url(cls, v):
        """Validate TikTok URL format"""
        if not v:
            raise ValueError("URL cannot be empty")

        # Basic TikTok URL validation
        valid_patterns = [
            'tiktok.com/@',
            'tiktok.com/t/',
            'vm.tiktok.com/',
            'vt.tiktok.com/',
        ]

        if not any(pattern in v.lower() for pattern in valid_patterns):
            raise ValueError("Invalid TikTok URL format")

        return v

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://www.tiktok.com/@username/video/1234567890",
                "extract_metadata": True,
                "extract_country": False
            }
        }


class VideoMetadata(BaseModel):
    """
    Video Metadata Model
    Contains all extracted metadata from TikTok video
    """
    video_id: str
    title: Optional[str] = None
    description: Optional[str] = None

    # Author info
    author: Optional[str] = None
    author_username: Optional[str] = None
    author_id: Optional[str] = None
    author_avatar: Optional[str] = None
    author_verified: bool = False

    # Engagement metrics
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    bookmarks: int = 0

    # Video details
    duration: Optional[int] = None  # in seconds
    format: Optional[str] = "mp4"
    resolution: Optional[str] = None
    aspect_ratio: Optional[str] = None
    filesize: Optional[int] = None  # in bytes

    # Media
    thumbnail: Optional[str] = None
    cover_image: Optional[str] = None
    dynamic_cover: Optional[str] = None

    # Audio/Music
    music: Optional[str] = None
    music_author: Optional[str] = None
    music_id: Optional[str] = None
    music_url: Optional[str] = None
    original_sound: bool = False

    # Content tags
    hashtags: List[str] = []
    mentions: List[str] = []
    challenges: List[str] = []

    # Location (Premium feature)
    country: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    location_name: Optional[str] = None

    # Timestamps
    created_at: Optional[datetime] = None
    uploaded_at: Optional[datetime] = None

    # Additional info
    is_ad: bool = False
    is_commerce: bool = False
    language: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "video_id": "1234567890",
                "title": "Amazing video title",
                "author": "User Name",
                "author_username": "username",
                "views": 1000000,
                "likes": 50000,
                "comments": 1000,
                "shares": 500,
                "music": "Song Name - Artist",
                "hashtags": ["viral", "fyp"],
                "mentions": ["user1", "user2"],
                "duration": 15,
                "thumbnail": "https://...",
                "created_at": "2024-01-15T10:30:00Z"
            }
        }


class VideoExtractResponse(BaseModel):
    """
    Video Extraction Response
    Response returned by /api/v1/video/extract endpoint
    """
    success: bool = True
    video_url: Optional[str] = None  # Direct download URL
    metadata: Optional[VideoMetadata] = None

    # Response info
    cached: bool = False
    requests_remaining: int = 0
    process_time_ms: Optional[int] = None

    # Error info (if success=False)
    error: Optional[str] = None
    detail: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "video_url": "https://direct-download-link.com/video.mp4",
                "metadata": {
                    "video_id": "1234567890",
                    "title": "Amazing video",
                    "author": "Username",
                    "views": 100000,
                    "likes": 5000
                },
                "cached": False,
                "requests_remaining": 950,
                "process_time_ms": 1234
            }
        }


class VideoCache(BaseModel):
    """
    Video Cache Model
    Stored in Redis for quick retrieval
    """
    url: str
    video_url: str
    metadata: Dict[str, Any]

    # Cache info
    cached_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    hit_count: int = 0

    # Performance
    extraction_time_ms: int = 0


class ExtractionError(BaseModel):
    """
    Extraction Error Model
    Detailed error information for debugging
    """
    url: str
    error_type: str  # validation, scraping, network, timeout, etc.
    error_message: str
    error_details: Optional[Dict[str, Any]] = None

    # Context
    user_email: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Debugging
    stack_trace: Optional[str] = None
    retry_count: int = 0


class BulkExtractRequest(BaseModel):
    """
    Bulk Extraction Request
    For extracting multiple videos at once (future feature)
    """
    urls: List[str]
    extract_metadata: bool = True
    extract_country: bool = False

    @validator('urls')
    def validate_urls_list(cls, v):
        """Validate URLs list"""
        if not v:
            raise ValueError("URLs list cannot be empty")

        if len(v) > 100:  # Limit bulk requests
            raise ValueError("Maximum 100 URLs per bulk request")

        return v


class BulkExtractResponse(BaseModel):
    """
    Bulk Extraction Response
    """
    success: bool = True
    total_requested: int
    successful: int
    failed: int

    results: List[VideoExtractResponse] = []
    errors: List[Dict[str, str]] = []

    process_time_ms: int
    requests_remaining: int


class VideoStats(BaseModel):
    """
    Video Statistics Model
    Aggregated stats for analytics
    """
    total_extractions: int = 0
    successful_extractions: int = 0
    failed_extractions: int = 0
    cache_hits: int = 0
    cache_misses: int = 0

    # Performance
    avg_extraction_time_ms: float = 0.0
    min_extraction_time_ms: int = 0
    max_extraction_time_ms: int = 0

    # Popular content
    top_authors: List[Dict[str, Any]] = []
    top_hashtags: List[str] = []
    top_songs: List[str] = []

    # Time range
    period_start: datetime
    period_end: datetime


class CountryDetectionResult(BaseModel):
    """
    Country Detection Result
    Premium feature - detected location information
    """
    country_code: str  # ISO 3166-1 alpha-2 (e.g., "US", "IQ")
    country_name: str  # Full name (e.g., "United States", "Iraq")
    region: Optional[str] = None
    city: Optional[str] = None

    # Confidence
    confidence: float = 0.0  # 0.0 to 1.0
    detection_method: str = "metadata"  # metadata, ip, geolocation

    # Additional info
    timezone: Optional[str] = None
    language: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "country_code": "IQ",
                "country_name": "Iraq",
                "region": "Baghdad",
                "city": "Baghdad",
                "confidence": 0.85,
                "detection_method": "metadata"
            }
        }
