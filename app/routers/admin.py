"""
Admin Panel Router - Complete Production Implementation
Provides admin dashboard, user management, and analytics with session-based authentication
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import logging
import secrets
import hashlib
from collections import defaultdict
import json

from app.config import get_settings
from app.database import Collections, Database
from app.services.auth_service import auth_service
from app.services.analytics_service import analytics_service
from app.services.usage_service import usage_service
from app.models.user import User, UserStatus, PlanType

settings = get_settings()
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/admin", tags=["admin"])

# Initialize Jinja2 templates
templates = Jinja2Templates(directory="templates")

# ============================================================================
# SESSION MANAGEMENT
# ============================================================================
# In-memory session storage
# PRODUCTION NOTE: Use Redis for distributed session storage
# Example: redis_client.setex(f"session:{session_id}", timeout, json.dumps(session_data))
ADMIN_SESSIONS: Dict[str, Dict[str, Any]] = {}

# CSRF tokens storage
CSRF_TOKENS: Dict[str, str] = {}

# Rate limiting storage (session_id -> list of timestamps)
RATE_LIMIT_STORE: Dict[str, List[datetime]] = defaultdict(list)


class SessionManager:
    """
    Session Management System
    Handles admin authentication sessions with expiry

    PRODUCTION NOTE: Replace in-memory storage with Redis:
    - redis_client.setex(f"session:{session_id}", timeout, data)
    - redis_client.get(f"session:{session_id}")
    - redis_client.delete(f"session:{session_id}")
    """

    @staticmethod
    def create_session(username: str) -> str:
        """
        Create a new admin session

        Args:
            username: Admin username

        Returns:
            Session ID
        """
        session_id = secrets.token_urlsafe(32)
        session_data = {
            "username": username,
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            "ip_address": None,  # Set by middleware
            "user_agent": None,  # Set by middleware
        }

        ADMIN_SESSIONS[session_id] = session_data

        logger.info(f"Created admin session for {username}: {session_id[:16]}...")

        return session_id

    @staticmethod
    def get_session(session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session data

        Args:
            session_id: Session ID

        Returns:
            Session data or None if expired/invalid
        """
        if not session_id or session_id not in ADMIN_SESSIONS:
            return None

        session_data = ADMIN_SESSIONS[session_id]

        # Check expiry
        last_activity = datetime.fromisoformat(session_data["last_activity"])
        timeout_minutes = settings.ADMIN_SESSION_TIMEOUT_MINUTES

        if datetime.utcnow() - last_activity > timedelta(minutes=timeout_minutes):
            # Session expired
            SessionManager.delete_session(session_id)
            logger.warning(f"Session expired: {session_id[:16]}...")
            return None

        # Update last activity
        session_data["last_activity"] = datetime.utcnow().isoformat()
        ADMIN_SESSIONS[session_id] = session_data

        return session_data

    @staticmethod
    def delete_session(session_id: str) -> bool:
        """
        Delete a session (logout)

        Args:
            session_id: Session ID

        Returns:
            Success status
        """
        if session_id in ADMIN_SESSIONS:
            username = ADMIN_SESSIONS[session_id].get("username", "unknown")
            del ADMIN_SESSIONS[session_id]
            logger.info(f"Deleted admin session for {username}")
            return True

        return False

    @staticmethod
    def cleanup_expired_sessions():
        """
        Clean up expired sessions
        Called periodically by background task
        """
        timeout_minutes = settings.ADMIN_SESSION_TIMEOUT_MINUTES
        cutoff_time = datetime.utcnow() - timedelta(minutes=timeout_minutes)

        expired_sessions = []

        for session_id, session_data in ADMIN_SESSIONS.items():
            last_activity = datetime.fromisoformat(session_data["last_activity"])
            if last_activity < cutoff_time:
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            SessionManager.delete_session(session_id)

        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired admin sessions")


class CSRFProtection:
    """
    CSRF Token Management
    Protects against Cross-Site Request Forgery attacks
    """

    @staticmethod
    def generate_token(session_id: str) -> str:
        """
        Generate CSRF token for session

        Args:
            session_id: Session ID

        Returns:
            CSRF token
        """
        token = secrets.token_urlsafe(32)
        CSRF_TOKENS[session_id] = token
        return token

    @staticmethod
    def validate_token(session_id: str, token: str) -> bool:
        """
        Validate CSRF token

        Args:
            session_id: Session ID
            token: CSRF token to validate

        Returns:
            True if valid, False otherwise
        """
        if not session_id or session_id not in CSRF_TOKENS:
            return False

        return CSRF_TOKENS.get(session_id) == token

    @staticmethod
    def delete_token(session_id: str):
        """Delete CSRF token for session"""
        if session_id in CSRF_TOKENS:
            del CSRF_TOKENS[session_id]


# ============================================================================
# DEPENDENCIES
# ============================================================================

async def get_current_admin(request: Request) -> Dict[str, Any]:
    """
    Dependency to get current authenticated admin

    Args:
        request: FastAPI request

    Returns:
        Session data

    Raises:
        HTTPException: If not authenticated
    """
    session_id = request.cookies.get("admin_session")

    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    session_data = SessionManager.get_session(session_id)

    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid"
        )

    return session_data


async def require_csrf_token(request: Request, admin: Dict = Depends(get_current_admin)):
    """
    Dependency to validate CSRF token on POST/DELETE requests

    Args:
        request: FastAPI request
        admin: Current admin session

    Raises:
        HTTPException: If CSRF token is invalid
    """
    if request.method in ["POST", "DELETE", "PUT", "PATCH"]:
        session_id = request.cookies.get("admin_session")

        # Try to get token from form data or JSON body
        csrf_token = None

        # Check form data
        if request.headers.get("content-type", "").startswith("application/x-www-form-urlencoded"):
            form_data = await request.form()
            csrf_token = form_data.get("csrf_token")
        # Check JSON body
        elif request.headers.get("content-type", "").startswith("application/json"):
            try:
                body = await request.json()
                csrf_token = body.get("csrf_token")
            except:
                pass
        # Check headers
        if not csrf_token:
            csrf_token = request.headers.get("X-CSRF-Token")

        if not csrf_token or not CSRFProtection.validate_token(session_id, csrf_token):
            logger.warning(f"CSRF token validation failed for session {session_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid CSRF token"
            )


async def rate_limit_admin(request: Request):
    """
    Rate limiting for admin panel
    Limit: 100 requests per minute per session

    Args:
        request: FastAPI request

    Raises:
        HTTPException: If rate limit exceeded
    """
    session_id = request.cookies.get("admin_session")

    if not session_id:
        return  # Not authenticated, will be handled by auth dependency

    now = datetime.utcnow()
    window_start = now - timedelta(minutes=1)

    # Get request timestamps for this session
    timestamps = RATE_LIMIT_STORE[session_id]

    # Remove old timestamps outside the window
    timestamps = [ts for ts in timestamps if ts > window_start]

    # Check limit
    if len(timestamps) >= 100:
        logger.warning(f"Rate limit exceeded for admin session: {session_id[:16]}...")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please slow down."
        )

    # Add current timestamp
    timestamps.append(now)
    RATE_LIMIT_STORE[session_id] = timestamps


# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================

@router.get("/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    """
    Render admin login page

    Returns:
        HTML login page
    """
    # Check if already logged in
    session_id = request.cookies.get("admin_session")
    if session_id and SessionManager.get_session(session_id):
        return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_302_FOUND)

    return templates.TemplateResponse(
        "admin/login.html",
        {
            "request": request,
            "app_name": settings.APP_NAME,
            "error": None
        }
    )


@router.post("/login")
async def admin_login(
    request: Request,
    username: str = None,
    password: str = None
):
    """
    Process admin login

    Args:
        request: FastAPI request
        username: Admin username
        password: Admin password

    Returns:
        Redirect to dashboard or login page with error
    """
    try:
        # Get credentials from form data
        if not username or not password:
            form_data = await request.form()
            username = form_data.get("username")
            password = form_data.get("password")

        if not username or not password:
            return templates.TemplateResponse(
                "admin/login.html",
                {
                    "request": request,
                    "app_name": settings.APP_NAME,
                    "error": "Username and password are required"
                }
            )

        # Validate credentials
        if username != settings.ADMIN_USERNAME or password != settings.ADMIN_PASSWORD:
            logger.warning(f"Failed admin login attempt for username: {username}")
            return templates.TemplateResponse(
                "admin/login.html",
                {
                    "request": request,
                    "app_name": settings.APP_NAME,
                    "error": "Invalid username or password"
                }
            )

        # Create session
        session_id = SessionManager.create_session(username)

        # Create CSRF token
        csrf_token = CSRFProtection.generate_token(session_id)

        logger.info(f"Admin logged in: {username} from IP: {request.client.host}")

        # Redirect to dashboard with session cookie
        response = RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_302_FOUND)

        # Set session cookie (secure in production)
        response.set_cookie(
            key="admin_session",
            value=session_id,
            httponly=True,
            secure=settings.ENVIRONMENT == "production",  # HTTPS only in production
            samesite="lax",
            max_age=settings.ADMIN_SESSION_TIMEOUT_MINUTES * 60
        )

        return response

    except Exception as e:
        logger.error(f"Error during admin login: {str(e)}", exc_info=True)
        return templates.TemplateResponse(
            "admin/login.html",
            {
                "request": request,
                "app_name": settings.APP_NAME,
                "error": "An error occurred during login"
            }
        )


@router.get("/logout")
async def admin_logout(request: Request):
    """
    Logout admin and destroy session

    Returns:
        Redirect to login page
    """
    session_id = request.cookies.get("admin_session")

    if session_id:
        SessionManager.delete_session(session_id)
        CSRFProtection.delete_token(session_id)

        # Clean up rate limit data
        if session_id in RATE_LIMIT_STORE:
            del RATE_LIMIT_STORE[session_id]

    response = RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("admin_session")

    return response


# ============================================================================
# DASHBOARD ROUTES
# ============================================================================

@router.get("/dashboard", response_class=HTMLResponse, dependencies=[Depends(rate_limit_admin)])
async def admin_dashboard(
    request: Request,
    admin: Dict = Depends(get_current_admin)
):
    """
    Admin dashboard with statistics and overview

    Args:
        request: FastAPI request
        admin: Current admin session

    Returns:
        HTML dashboard page with stats
    """
    try:
        # Get real-time statistics
        total_users = await auth_service.get_user_count()
        active_users = await auth_service.get_user_count(status="active")
        blocked_users = await Collections.users().count_documents({"is_blocked": True})

        # Get plan distribution
        plan_distribution = await analytics_service.get_plan_distribution()

        # Calculate revenue metrics
        mrr = await analytics_service.calculate_mrr()
        arr = await analytics_service.calculate_arr()
        conversion_rate = await analytics_service.calculate_conversion_rate()

        # Get system usage stats (last 30 days)
        system_stats = await usage_service.get_system_stats(days=30)

        # Get recent users (last 10)
        recent_users = await auth_service.get_all_users(skip=0, limit=10)
        recent_users_data = []
        for user in recent_users:
            recent_users_data.append({
                "email": user.email,
                "plan": user.plan,
                "status": user.status,
                "created_at": user.created_at.strftime("%Y-%m-%d %H:%M") if user.created_at else "N/A",
                "requests_used": user.requests_used,
                "requests_limit": user.requests_limit,
                "is_blocked": user.is_blocked
            })

        # Calculate success rate
        total_requests = system_stats.get("total_requests", 0)
        successful_requests = system_stats.get("successful_requests", 0)
        success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0

        # Generate CSRF token
        session_id = request.cookies.get("admin_session")
        csrf_token = CSRFProtection.generate_token(session_id)

        return templates.TemplateResponse(
            "admin/dashboard.html",
            {
                "request": request,
                "admin": admin,
                "csrf_token": csrf_token,
                "app_name": settings.APP_NAME,
                # User stats
                "total_users": total_users,
                "active_users": active_users,
                "blocked_users": blocked_users,
                "inactive_users": total_users - active_users,
                # Plan distribution
                "free_users": plan_distribution.get("free", 0),
                "basic_users": plan_distribution.get("basic", 0),
                "pro_users": plan_distribution.get("pro", 0),
                "business_users": plan_distribution.get("business", 0),
                # Revenue metrics
                "mrr": mrr,
                "arr": arr,
                "conversion_rate": conversion_rate,
                # System stats
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "failed_requests": system_stats.get("failed_requests", 0),
                "success_rate": round(success_rate, 1),
                "avg_response_time": round(system_stats.get("avg_response_time", 0), 0),
                "active_api_users": system_stats.get("active_users", 0),
                # Recent users
                "recent_users": recent_users_data,
                # Current time
                "current_time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            }
        )

    except Exception as e:
        logger.error(f"Error loading admin dashboard: {str(e)}", exc_info=True)
        return templates.TemplateResponse(
            "admin/error.html",
            {
                "request": request,
                "admin": admin,
                "error": "Failed to load dashboard",
                "detail": str(e) if settings.DEBUG else "An unexpected error occurred"
            },
            status_code=500
        )


# ============================================================================
# USER MANAGEMENT ROUTES
# ============================================================================

@router.get("/users", response_class=HTMLResponse, dependencies=[Depends(rate_limit_admin)])
async def admin_users(
    request: Request,
    admin: Dict = Depends(get_current_admin),
    page: int = 1,
    limit: int = 20,
    search: Optional[str] = None,
    plan: Optional[str] = None,
    status: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc"
):
    """
    User management page with pagination, search, and filters

    Args:
        request: FastAPI request
        admin: Current admin session
        page: Page number (1-indexed)
        limit: Users per page
        search: Search query (email)
        plan: Filter by plan
        status: Filter by status
        sort_by: Sort field
        sort_order: Sort order (asc/desc)

    Returns:
        HTML users page
    """
    try:
        # Build query
        query = {}

        if search:
            query["email"] = {"$regex": search, "$options": "i"}

        if plan:
            query["plan"] = plan

        if status:
            query["status"] = status

        # Calculate pagination
        skip = (page - 1) * limit

        # Get total count
        total_users = await Collections.users().count_documents(query)
        total_pages = (total_users + limit - 1) // limit

        # Get users with sorting
        sort_direction = -1 if sort_order == "desc" else 1

        cursor = Collections.users().find(query).sort(sort_by, sort_direction).skip(skip).limit(limit)

        users_data = []
        async for user_doc in cursor:
            user = User(**user_doc)

            # Calculate usage percentage
            usage_percentage = (user.requests_used / user.requests_limit * 100) if user.requests_limit > 0 else 0

            users_data.append({
                "email": user.email,
                "plan": user.plan,
                "status": user.status,
                "is_blocked": user.is_blocked,
                "block_reason": user.block_reason,
                "requests_used": user.requests_used,
                "requests_limit": user.requests_limit,
                "usage_percentage": round(usage_percentage, 1),
                "created_at": user.created_at.strftime("%Y-%m-%d") if user.created_at else "N/A",
                "last_request_at": user.last_request_at.strftime("%Y-%m-%d %H:%M") if user.last_request_at else "Never",
                "subscription_end": user.subscription_end.strftime("%Y-%m-%d") if user.subscription_end else "N/A",
                "api_key_masked": user.api_key[:10] + "..." if user.api_key else "N/A"
            })

        # Generate CSRF token
        session_id = request.cookies.get("admin_session")
        csrf_token = CSRFProtection.generate_token(session_id)

        return templates.TemplateResponse(
            "admin/users.html",
            {
                "request": request,
                "admin": admin,
                "csrf_token": csrf_token,
                "users": users_data,
                "total_users": total_users,
                "page": page,
                "limit": limit,
                "total_pages": total_pages,
                "search": search or "",
                "plan_filter": plan or "",
                "status_filter": status or "",
                "sort_by": sort_by,
                "sort_order": sort_order,
                "plans": ["free", "basic", "pro", "business"],
                "statuses": ["active", "inactive", "suspended", "cancelled"],
                "app_name": settings.APP_NAME
            }
        )

    except Exception as e:
        logger.error(f"Error loading users page: {str(e)}", exc_info=True)
        return templates.TemplateResponse(
            "admin/error.html",
            {
                "request": request,
                "admin": admin,
                "error": "Failed to load users",
                "detail": str(e) if settings.DEBUG else "An unexpected error occurred"
            },
            status_code=500
        )


# ============================================================================
# ANALYTICS ROUTES
# ============================================================================

@router.get("/analytics", response_class=HTMLResponse, dependencies=[Depends(rate_limit_admin)])
async def admin_analytics(
    request: Request,
    admin: Dict = Depends(get_current_admin),
    period: str = "30d"
):
    """
    Analytics page with charts and insights

    Args:
        request: FastAPI request
        admin: Current admin session
        period: Time period (7d, 30d, 90d)

    Returns:
        HTML analytics page with chart data
    """
    try:
        # Parse period
        days_map = {"7d": 7, "30d": 30, "90d": 90}
        days = days_map.get(period, 30)

        # Get usage over time (for chart)
        start_date = datetime.utcnow() - timedelta(days=days)

        pipeline = [
            {
                "$match": {
                    "timestamp": {"$gte": start_date}
                }
            },
            {
                "$group": {
                    "_id": {
                        "$dateToString": {
                            "format": "%Y-%m-%d",
                            "date": "$timestamp"
                        }
                    },
                    "total_requests": {"$sum": 1},
                    "successful": {"$sum": {"$cond": ["$success", 1, 0]}},
                    "failed": {"$sum": {"$cond": ["$success", 0, 1]}},
                    "unique_users": {"$addToSet": "$user_email"}
                }
            },
            {
                "$sort": {"_id": 1}
            }
        ]

        cursor = Collections.usage().aggregate(pipeline)
        usage_data = await cursor.to_list(length=None)

        # Format for charts
        chart_labels = []
        chart_requests = []
        chart_users = []
        chart_success_rate = []

        for item in usage_data:
            chart_labels.append(item["_id"])
            chart_requests.append(item["total_requests"])
            chart_users.append(len(item["unique_users"]))

            success_rate = (item["successful"] / item["total_requests"] * 100) if item["total_requests"] > 0 else 0
            chart_success_rate.append(round(success_rate, 1))

        # Get plan distribution over time
        plan_pipeline = [
            {
                "$group": {
                    "_id": "$plan",
                    "count": {"$sum": 1}
                }
            }
        ]

        cursor = Collections.users().aggregate(plan_pipeline)
        plan_data = await cursor.to_list(length=None)

        plan_chart_labels = []
        plan_chart_values = []

        for item in plan_data:
            plan_chart_labels.append(item["_id"].capitalize())
            plan_chart_values.append(item["count"])

        # Get revenue forecast
        revenue_forecast = await analytics_service.get_revenue_forecast(months=6)

        forecast_labels = [item["month"] for item in revenue_forecast]
        forecast_values = [item["mrr"] for item in revenue_forecast]

        # Generate CSRF token
        session_id = request.cookies.get("admin_session")
        csrf_token = CSRFProtection.generate_token(session_id)

        return templates.TemplateResponse(
            "admin/analytics.html",
            {
                "request": request,
                "admin": admin,
                "csrf_token": csrf_token,
                "app_name": settings.APP_NAME,
                "period": period,
                # Usage chart data
                "chart_labels": json.dumps(chart_labels),
                "chart_requests": json.dumps(chart_requests),
                "chart_users": json.dumps(chart_users),
                "chart_success_rate": json.dumps(chart_success_rate),
                # Plan distribution
                "plan_chart_labels": json.dumps(plan_chart_labels),
                "plan_chart_values": json.dumps(plan_chart_values),
                # Revenue forecast
                "forecast_labels": json.dumps(forecast_labels),
                "forecast_values": json.dumps(forecast_values),
                # Summary stats
                "total_requests_period": sum(chart_requests),
                "avg_daily_requests": round(sum(chart_requests) / len(chart_requests)) if chart_requests else 0,
                "avg_success_rate": round(sum(chart_success_rate) / len(chart_success_rate), 1) if chart_success_rate else 0,
                "peak_day": chart_labels[chart_requests.index(max(chart_requests))] if chart_requests else "N/A"
            }
        )

    except Exception as e:
        logger.error(f"Error loading analytics: {str(e)}", exc_info=True)
        return templates.TemplateResponse(
            "admin/error.html",
            {
                "request": request,
                "admin": admin,
                "error": "Failed to load analytics",
                "detail": str(e) if settings.DEBUG else "An unexpected error occurred"
            },
            status_code=500
        )


# ============================================================================
# AJAX API ENDPOINTS
# ============================================================================

@router.post("/api/users/{email}/block", dependencies=[Depends(rate_limit_admin)])
async def block_user(
    email: str,
    request: Request,
    admin: Dict = Depends(get_current_admin)
):
    """
    Block a user (AJAX endpoint)

    Args:
        email: User email to block
        request: FastAPI request
        admin: Current admin session

    Returns:
        JSON response
    """
    try:
        # Validate CSRF token
        await require_csrf_token(request, admin)

        # Get reason from request body
        try:
            body = await request.json()
            reason = body.get("reason", "Blocked by admin")
        except:
            reason = "Blocked by admin"

        # Block user
        success, error = await auth_service.block_user(email, reason)

        if not success:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "success": False,
                    "error": error or "Failed to block user"
                }
            )

        logger.info(f"Admin {admin['username']} blocked user: {email}")

        return JSONResponse(
            content={
                "success": True,
                "message": f"User {email} has been blocked",
                "email": email
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error blocking user {email}: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": "Internal server error"
            }
        )


@router.post("/api/users/{email}/unblock", dependencies=[Depends(rate_limit_admin)])
async def unblock_user(
    email: str,
    request: Request,
    admin: Dict = Depends(get_current_admin)
):
    """
    Unblock a user (AJAX endpoint)

    Args:
        email: User email to unblock
        request: FastAPI request
        admin: Current admin session

    Returns:
        JSON response
    """
    try:
        # Validate CSRF token
        await require_csrf_token(request, admin)

        # Unblock user
        success, error = await auth_service.unblock_user(email)

        if not success:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "success": False,
                    "error": error or "Failed to unblock user"
                }
            )

        logger.info(f"Admin {admin['username']} unblocked user: {email}")

        return JSONResponse(
            content={
                "success": True,
                "message": f"User {email} has been unblocked",
                "email": email
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unblocking user {email}: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": "Internal server error"
            }
        )


@router.delete("/api/users/{email}", dependencies=[Depends(rate_limit_admin)])
async def delete_user(
    email: str,
    request: Request,
    admin: Dict = Depends(get_current_admin)
):
    """
    Delete a user permanently (AJAX endpoint)

    Args:
        email: User email to delete
        request: FastAPI request
        admin: Current admin session

    Returns:
        JSON response
    """
    try:
        # Validate CSRF token
        await require_csrf_token(request, admin)

        # Check if user exists
        user = await auth_service.get_user_by_email(email)

        if not user:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "success": False,
                    "error": "User not found"
                }
            )

        # Delete user from database
        result = await Collections.users().delete_one({"email": email})

        if result.deleted_count == 0:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "success": False,
                    "error": "Failed to delete user"
                }
            )

        # Also delete user's usage logs (optional - for GDPR compliance)
        await Collections.usage().delete_many({"user_email": email})

        logger.warning(f"Admin {admin['username']} deleted user: {email}")

        return JSONResponse(
            content={
                "success": True,
                "message": f"User {email} has been permanently deleted",
                "email": email
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user {email}: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": "Internal server error"
            }
        )


@router.get("/api/stats/realtime", dependencies=[Depends(rate_limit_admin)])
async def get_realtime_stats(
    admin: Dict = Depends(get_current_admin)
):
    """
    Get real-time statistics (AJAX endpoint for dashboard refresh)

    Args:
        admin: Current admin session

    Returns:
        JSON with real-time stats
    """
    try:
        # Get current stats
        total_users = await auth_service.get_user_count()
        active_users = await auth_service.get_user_count(status="active")

        # Get system stats (last hour)
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)

        recent_requests = await Collections.usage().count_documents({
            "timestamp": {"$gte": one_hour_ago}
        })

        # Get MRR
        mrr = await analytics_service.calculate_mrr()

        return JSONResponse(
            content={
                "success": True,
                "stats": {
                    "total_users": total_users,
                    "active_users": active_users,
                    "requests_last_hour": recent_requests,
                    "mrr": mrr,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )

    except Exception as e:
        logger.error(f"Error getting real-time stats: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": "Failed to fetch stats"
            }
        )


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/health")
async def admin_health():
    """
    Admin panel health check
    Does not require authentication

    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "service": "admin_panel",
        "timestamp": datetime.utcnow().isoformat(),
        "active_sessions": len(ADMIN_SESSIONS)
    }
