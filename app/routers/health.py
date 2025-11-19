"""
Health Check Endpoint
System status monitoring
"""

from fastapi import APIRouter
import logging
import os
import psutil
from datetime import datetime
from app.database import Database
from app.services.cache_service import cache_service
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

# Track start time for uptime calculation
START_TIME = datetime.utcnow()


@router.get("/health")
async def health_check():
    """
    Health check endpoint
    Returns system status and service availability
    """
    try:
        # Check MongoDB
        mongodb_healthy = await Database.check_health()

        # Check Redis
        redis_stats = await cache_service.get_stats()
        redis_healthy = redis_stats.get("connected", False)

        # Get system resources
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        # Calculate uptime
        uptime_seconds = (datetime.utcnow() - START_TIME).total_seconds()

        # Overall status
        overall_status = "healthy" if (mongodb_healthy and redis_healthy) else "degraded"

        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "version": settings.APP_VERSION,
            "services": {
                "mongodb": mongodb_healthy,
                "redis": redis_healthy,
            },
            "system": {
                "memory_usage_percent": round(memory.percent, 1),
                "disk_usage_percent": round(disk.percent, 1),
                "disk_free_gb": round(disk.free / (1024**3), 2),
            },
            "uptime_seconds": int(uptime_seconds),
        }

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)

        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
        }


@router.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "TikTok Video Intelligence API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
    }
