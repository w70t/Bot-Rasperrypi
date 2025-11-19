"""
Configuration Management
Handles all environment variables and application settings
"""

from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache
import secrets


class Settings(BaseSettings):
    """
    Application Settings - loaded from environment variables
    """

    # Application
    APP_NAME: str = "TikTok Video Intelligence API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"  # development, staging, production

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4

    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)
    API_KEY_PREFIX: str = "tk_"
    ALLOWED_HOSTS: list = ["*"]

    # MongoDB
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB_NAME: str = "tiktok_api"
    MONGO_MAX_POOL_SIZE: int = 10
    MONGO_MIN_POOL_SIZE: int = 1

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_CACHE_TTL: int = 3600  # 1 hour in seconds

    # Rate Limiting (requests per minute)
    RATE_LIMIT_FREE: int = 10
    RATE_LIMIT_BASIC: int = 30
    RATE_LIMIT_PRO: int = 100
    RATE_LIMIT_BUSINESS: int = 500

    # Usage Limits (requests per month)
    USAGE_LIMIT_FREE: int = 50
    USAGE_LIMIT_BASIC: int = 1000
    USAGE_LIMIT_PRO: int = 10000
    USAGE_LIMIT_BUSINESS: int = 100000

    # Plan Pricing (USD per month)
    PRICE_FREE: float = 0.0
    PRICE_BASIC: float = 5.0
    PRICE_PRO: float = 20.0
    PRICE_BUSINESS: float = 100.0

    # TikTok Scraping
    TIKTOK_TIMEOUT: int = 30  # seconds
    TIKTOK_MAX_RETRIES: int = 3
    USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    # Logging
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_FILE_PATH: str = "logs/api.log"
    ERROR_LOG_FILE_PATH: str = "logs/errors.log"
    ACCESS_LOG_FILE_PATH: str = "logs/access.log"
    LOG_ROTATION: str = "500 MB"
    LOG_RETENTION: str = "30 days"

    # Telegram Bot (for owner notifications)
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_OWNER_CHAT_ID: Optional[str] = None
    TELEGRAM_NOTIFICATIONS_ENABLED: bool = False

    # Telegram Notifications Settings
    NOTIFY_NEW_SUBSCRIBER: bool = True
    NOTIFY_ERRORS: bool = True
    NOTIFY_DAILY_REPORT: bool = True
    NOTIFY_MILESTONES: bool = True
    DAILY_REPORT_TIME: str = "09:00"  # HH:MM format

    # Stripe Payment Processing
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_PUBLISHABLE_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None

    # Stripe Plan Price IDs (from Stripe Dashboard)
    STRIPE_PRICE_BASIC: Optional[str] = None
    STRIPE_PRICE_PRO: Optional[str] = None
    STRIPE_PRICE_BUSINESS: Optional[str] = None

    # Email Settings
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: Optional[str] = None
    SMTP_FROM_NAME: str = "TikTok API"

    # Admin Panel
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "change_me_in_production"
    ADMIN_PANEL_SECRET_PATH: str = "/admin-xyz123"
    ADMIN_SESSION_TIMEOUT_MINUTES: int = 30

    # Backup
    BACKUP_ENABLED: bool = True
    BACKUP_PATH: str = "backups/"
    BACKUP_RETENTION_DAYS: int = 30

    # Performance
    MAX_RESPONSE_TIME_WARNING: float = 3.0  # seconds
    SLOW_QUERY_THRESHOLD: float = 1.0  # seconds

    # Country Detection (Premium Feature)
    GEOIP_DATABASE_PATH: Optional[str] = None
    COUNTRY_DETECTION_ENABLED: bool = False

    # Cloudflare (optional)
    CLOUDFLARE_API_TOKEN: Optional[str] = None
    CLOUDFLARE_ZONE_ID: Optional[str] = None

    # RapidAPI Integration
    RAPIDAPI_KEY: Optional[str] = None
    RAPIDAPI_HOST: Optional[str] = None

    # Monitoring & Analytics
    SENTRY_DSN: Optional[str] = None  # For error tracking
    ANALYTICS_ENABLED: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance
    This ensures we only load settings once and reuse the same instance
    """
    return Settings()


# Plan configurations
PLAN_CONFIGS = {
    "free": {
        "name": "Free",
        "price": 0.0,
        "requests_per_month": 50,
        "rate_limit_per_minute": 10,
        "features": {
            "video_download": True,
            "basic_metadata": True,
            "country_detection": False,
            "priority_support": False,
            "custom_features": False,
        }
    },
    "basic": {
        "name": "Basic",
        "price": 5.0,
        "requests_per_month": 1000,
        "rate_limit_per_minute": 30,
        "features": {
            "video_download": True,
            "basic_metadata": True,
            "country_detection": False,
            "priority_support": False,
            "custom_features": False,
        }
    },
    "pro": {
        "name": "Pro",
        "price": 20.0,
        "requests_per_month": 10000,
        "rate_limit_per_minute": 100,
        "features": {
            "video_download": True,
            "basic_metadata": True,
            "country_detection": True,  # Premium feature
            "priority_support": True,
            "custom_features": False,
        }
    },
    "business": {
        "name": "Business",
        "price": 100.0,
        "requests_per_month": 100000,
        "rate_limit_per_minute": 500,
        "features": {
            "video_download": True,
            "basic_metadata": True,
            "country_detection": True,  # Premium feature
            "priority_support": True,
            "custom_features": True,
        }
    }
}


# Error messages (support Arabic and English)
ERROR_MESSAGES = {
    "invalid_api_key": {
        "en": "Invalid API Key. Please check your credentials.",
        "ar": "مفتاح API غير صحيح. يرجى التحقق من بيانات الاعتماد."
    },
    "rate_limit_exceeded": {
        "en": "Rate limit exceeded. Please try again later.",
        "ar": "تم تجاوز الحد المسموح. يرجى المحاولة لاحقاً."
    },
    "quota_exceeded": {
        "en": "Monthly quota exceeded. Please upgrade your plan.",
        "ar": "تم تجاوز الحد الشهري. يرجى ترقية باقتك."
    },
    "invalid_url": {
        "en": "Invalid TikTok URL format.",
        "ar": "صيغة رابط TikTok غير صحيحة."
    },
    "video_not_found": {
        "en": "Video not found or is private.",
        "ar": "الفيديو غير موجود أو خاص."
    },
    "scraping_failed": {
        "en": "Failed to extract video. Please try again.",
        "ar": "فشل استخراج الفيديو. يرجى المحاولة مرة أخرى."
    },
    "server_error": {
        "en": "Internal server error. Our team has been notified.",
        "ar": "خطأ في الخادم. تم إبلاغ فريقنا."
    }
}


# HTTP Status codes
HTTP_200_OK = 200
HTTP_400_BAD_REQUEST = 400
HTTP_401_UNAUTHORIZED = 401
HTTP_403_FORBIDDEN = 403
HTTP_404_NOT_FOUND = 404
HTTP_429_TOO_MANY_REQUESTS = 429
HTTP_500_INTERNAL_SERVER_ERROR = 500
HTTP_503_SERVICE_UNAVAILABLE = 503
