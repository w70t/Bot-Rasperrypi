"""
Usage Tracking Models
Defines models for API usage tracking and analytics
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any
from datetime import datetime


class UsageLog(BaseModel):
    """
    Usage Log Model
    Logs every API request for tracking and analytics
    """
    # User info
    user_email: EmailStr
    api_key: str  # Partially masked (tk_abc***xyz)

    # Request info
    endpoint: str  # /api/v1/video/extract
    method: str = "POST"
    video_url: Optional[str] = None

    # Response info
    success: bool = True
    status_code: int = 200
    cached: bool = False
    error: Optional[str] = None

    # Performance
    response_time_ms: int = 0

    # Client info
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    country: Optional[str] = None  # Client's country (from IP)

    # Timestamp
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Additional metadata
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "user_email": "user@example.com",
                "api_key": "tk_abc***xyz",
                "endpoint": "/api/v1/video/extract",
                "video_url": "https://tiktok.com/...",
                "success": True,
                "status_code": 200,
                "cached": False,
                "response_time_ms": 1234,
                "ip_address": "1.2.3.4",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


class DailyUsageStats(BaseModel):
    """
    Daily Usage Statistics
    Aggregated stats for a specific day
    """
    date: datetime
    user_email: EmailStr

    # Counts
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    cached_requests: int = 0

    # Performance
    avg_response_time_ms: float = 0.0
    min_response_time_ms: int = 0
    max_response_time_ms: int = 0

    # Errors
    error_count: int = 0
    error_types: Dict[str, int] = {}

    # Cache
    cache_hit_rate: float = 0.0


class MonthlyUsageStats(BaseModel):
    """
    Monthly Usage Statistics
    Aggregated stats for a specific month
    """
    year: int
    month: int
    user_email: EmailStr

    # Counts
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    cached_requests: int = 0

    # Daily breakdown
    daily_stats: Dict[str, int] = {}

    # Performance
    avg_response_time_ms: float = 0.0

    # Plan info
    plan: str
    requests_limit: int
    usage_percentage: float = 0.0


class SystemStats(BaseModel):
    """
    System-Wide Statistics
    Overall platform statistics
    """
    # Time period
    period_start: datetime
    period_end: datetime

    # Users
    total_users: int = 0
    active_users: int = 0  # Users who made requests
    new_users: int = 0

    # Usage by plan
    free_users: int = 0
    basic_users: int = 0
    pro_users: int = 0
    business_users: int = 0

    # Requests
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    cached_requests: int = 0

    # Performance
    avg_response_time_ms: float = 0.0
    uptime_percentage: float = 0.0

    # Revenue
    mrr: float = 0.0  # Monthly Recurring Revenue
    arr: float = 0.0  # Annual Recurring Revenue

    # Growth
    user_growth_rate: float = 0.0
    revenue_growth_rate: float = 0.0


class ErrorStats(BaseModel):
    """
    Error Statistics
    Tracks error patterns and frequencies
    """
    period_start: datetime
    period_end: datetime

    # Error counts
    total_errors: int = 0
    error_rate: float = 0.0  # Percentage of requests that failed

    # Error types
    error_types: Dict[str, int] = {
        "invalid_url": 0,
        "video_not_found": 0,
        "scraping_failed": 0,
        "rate_limit_exceeded": 0,
        "quota_exceeded": 0,
        "timeout": 0,
        "server_error": 0,
    }

    # Most common errors
    top_errors: list = []


class PerformanceMetrics(BaseModel):
    """
    Performance Metrics
    System performance tracking
    """
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Response times
    avg_response_time_ms: float = 0.0
    p50_response_time_ms: float = 0.0  # Median
    p95_response_time_ms: float = 0.0
    p99_response_time_ms: float = 0.0

    # Cache performance
    cache_hit_rate: float = 0.0
    cache_miss_rate: float = 0.0

    # Database performance
    db_query_time_ms: float = 0.0
    slow_queries: int = 0

    # System resources
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    disk_usage: float = 0.0

    # Network
    bandwidth_in_mb: float = 0.0
    bandwidth_out_mb: float = 0.0


class AnalyticsEvent(BaseModel):
    """
    Analytics Event
    Track specific events for business intelligence
    """
    event_type: str  # new_user, upgrade, downgrade, cancellation, etc.
    user_email: EmailStr

    # Event data
    event_data: Dict[str, Any] = {}

    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source: str = "api"  # api, admin_panel, telegram_bot, etc.

    class Config:
        json_schema_extra = {
            "example": {
                "event_type": "upgrade",
                "user_email": "user@example.com",
                "event_data": {
                    "from_plan": "basic",
                    "to_plan": "pro",
                    "reason": "quota_exceeded"
                },
                "timestamp": "2024-01-15T10:30:00Z",
                "source": "api"
            }
        }


class UserBehaviorAnalytics(BaseModel):
    """
    User Behavior Analytics
    Analyze individual user patterns
    """
    user_email: EmailStr

    # Activity patterns
    most_active_hour: int = 0  # 0-23
    most_active_day: str = "monday"
    avg_daily_requests: float = 0.0

    # Content preferences
    top_authors_extracted: List[str] = []
    top_hashtags: List[str] = []

    # Engagement
    days_since_signup: int = 0
    days_since_last_request: int = 0
    lifetime_requests: int = 0

    # Risk indicators
    churn_risk_score: float = 0.0  # 0.0 to 1.0
    upgrade_likelihood: float = 0.0  # 0.0 to 1.0


class RevenueMetrics(BaseModel):
    """
    Revenue Metrics
    Financial tracking and projections
    """
    period_start: datetime
    period_end: datetime

    # Current revenue
    revenue_today: float = 0.0
    revenue_this_month: float = 0.0
    revenue_last_month: float = 0.0

    # Projections
    mrr: float = 0.0  # Monthly Recurring Revenue
    arr: float = 0.0  # Annual Recurring Revenue
    projected_eom_revenue: float = 0.0  # End of Month

    # By plan
    revenue_by_plan: Dict[str, float] = {
        "free": 0.0,
        "basic": 0.0,
        "pro": 0.0,
        "business": 0.0
    }

    # Growth
    mom_growth: float = 0.0  # Month over Month
    yoy_growth: float = 0.0  # Year over Year

    # Subscribers
    paying_subscribers: int = 0
    free_to_paid_rate: float = 0.0
    churn_rate: float = 0.0


class CacheMetrics(BaseModel):
    """
    Cache Performance Metrics
    Redis caching statistics
    """
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Hit rates
    cache_hits: int = 0
    cache_misses: int = 0
    cache_hit_rate: float = 0.0

    # Performance impact
    avg_cached_response_ms: float = 0.0
    avg_uncached_response_ms: float = 0.0
    time_saved_ms: float = 0.0

    # Storage
    cache_size_mb: float = 0.0
    cached_items: int = 0

    # Efficiency
    bandwidth_saved_mb: float = 0.0
    cost_savings_usd: float = 0.0
