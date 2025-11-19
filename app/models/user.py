"""
User Data Models
Defines user, API key, and subscription models
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class PlanType(str, Enum):
    """Subscription plan types"""
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    BUSINESS = "business"


class UserStatus(str, Enum):
    """User account status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


class User(BaseModel):
    """
    User Model
    Represents a registered user in the system
    """
    email: EmailStr
    api_key: str
    plan: PlanType = PlanType.FREE
    status: UserStatus = UserStatus.ACTIVE

    # Usage tracking
    requests_used: int = 0
    requests_limit: int = 50  # Monthly limit based on plan

    # Rate limiting
    rate_limit_per_minute: int = 10  # Based on plan

    # Subscription info
    subscription_id: Optional[str] = None  # Stripe subscription ID
    subscription_start: Optional[datetime] = None
    subscription_end: Optional[datetime] = None

    # Payment info
    customer_id: Optional[str] = None  # Stripe customer ID
    last_payment: Optional[datetime] = None
    last_payment_amount: Optional[float] = None

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_request_at: Optional[datetime] = None

    # Features (based on plan)
    features: Dict[str, bool] = {
        "video_download": True,
        "basic_metadata": True,
        "country_detection": False,
        "priority_support": False,
        "custom_features": False,
    }

    # Settings
    language: str = "en"  # en or ar
    timezone: str = "UTC"

    # Risk management
    is_blocked: bool = False
    block_reason: Optional[str] = None
    churn_risk: str = "low"  # low, medium, high

    # Referral
    referral_code: Optional[str] = None
    referred_by: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "api_key": "tk_abc123def456",
                "plan": "pro",
                "status": "active",
                "requests_used": 847,
                "requests_limit": 10000,
                "rate_limit_per_minute": 100,
            }
        }


class UserCreate(BaseModel):
    """
    User Creation Model
    For registering new users
    """
    email: EmailStr
    plan: PlanType = PlanType.FREE
    language: str = "en"
    referred_by: Optional[str] = None


class UserUpdate(BaseModel):
    """
    User Update Model
    For updating user information
    """
    plan: Optional[PlanType] = None
    status: Optional[UserStatus] = None
    language: Optional[str] = None
    timezone: Optional[str] = None


class UserResponse(BaseModel):
    """
    User Response Model
    Returned to API consumers (hides sensitive info)
    """
    email: EmailStr
    plan: str
    status: str
    requests_used: int
    requests_limit: int
    subscription_end: Optional[datetime] = None
    created_at: datetime


class APIKey(BaseModel):
    """
    API Key Model
    Manages API keys separately (optional - can be part of User)
    """
    key: str
    user_email: EmailStr
    name: Optional[str] = None  # Optional name for the key
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used_at: Optional[datetime] = None
    usage_count: int = 0

    # Permissions (for future granular access control)
    permissions: Dict[str, bool] = {
        "video_extract": True,
        "metadata_only": False,
        "admin_access": False,
    }


class Subscription(BaseModel):
    """
    Subscription Model
    Tracks subscription details separately
    """
    user_email: EmailStr
    plan: PlanType

    # Stripe info
    subscription_id: str
    customer_id: str
    price_id: str

    # Status
    is_active: bool = True
    status: str = "active"  # active, cancelled, past_due, trialing

    # Dates
    current_period_start: datetime
    current_period_end: datetime
    cancel_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None

    # Billing
    amount: float
    currency: str = "usd"
    interval: str = "month"  # month or year

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Invoice(BaseModel):
    """
    Invoice Model
    Tracks payment invoices
    """
    user_email: EmailStr
    invoice_id: str  # Stripe invoice ID

    # Amount
    amount: float
    currency: str = "usd"

    # Status
    status: str  # paid, open, void, uncollectible
    paid: bool = False

    # Dates
    invoice_date: datetime
    due_date: Optional[datetime] = None
    paid_at: Optional[datetime] = None

    # Details
    description: Optional[str] = None
    invoice_pdf: Optional[str] = None  # URL to PDF

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Ticket(BaseModel):
    """
    Support Ticket Model
    For customer support management
    """
    user_email: EmailStr
    subject: str
    description: str

    # Status
    status: str = "open"  # open, in_progress, resolved, closed
    priority: str = "medium"  # low, medium, high, urgent

    # Assignment
    assigned_to: Optional[str] = None

    # Communication
    messages: list = []

    # Dates
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None


class ReferralStats(BaseModel):
    """
    Referral Statistics
    Tracks referral program metrics
    """
    user_email: EmailStr
    referral_code: str

    # Stats
    total_referrals: int = 0
    successful_conversions: int = 0
    total_earned: float = 0.0

    # Rewards
    free_months_earned: int = 0
    credit_earned: float = 0.0

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
