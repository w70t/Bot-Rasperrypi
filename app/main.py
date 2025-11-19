"""
TikTok Video Intelligence API
Main FastAPI Application
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import time

# Import configuration and setup
from app.config import get_settings
from app.utils.logger import setup_logging
from app.database import Database
from app.services.cache_service import cache_service

# Import routers
from app.routers import health, video, user

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Professional TikTok Video Intelligence API - Extract videos and metadata",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests"""
    start_time = time.time()

    # Process request
    response = await call_next(request)

    # Calculate duration
    duration = time.time() - start_time
    duration_ms = int(duration * 1000)

    # Log
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Duration: {duration_ms}ms"
    )

    # Add response time header
    response.headers["X-Process-Time"] = str(duration_ms)

    return response


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions"""
    logger.error(
        f"Unhandled exception: {str(exc)}",
        exc_info=True,
        extra={
            "path": request.url.path,
            "method": request.method,
        }
    )

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An unexpected error occurred",
        }
    )


# Startup event
@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

    try:
        # Connect to MongoDB
        await Database.connect_db()
        logger.info("✓ MongoDB connected")

        # Connect to Redis
        await cache_service.connect()
        logger.info("✓ Redis connected")

        logger.info("✓ Application started successfully")

    except Exception as e:
        logger.error(f"✗ Startup failed: {str(e)}", exc_info=True)
        raise


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    logger.info("Shutting down application...")

    try:
        # Close MongoDB connection
        await Database.close_db()
        logger.info("✓ MongoDB disconnected")

        # Close Redis connection
        await cache_service.disconnect()
        logger.info("✓ Redis disconnected")

        logger.info("✓ Application shut down successfully")

    except Exception as e:
        logger.error(f"✗ Shutdown error: {str(e)}", exc_info=True)


# Include routers
app.include_router(health.router)
app.include_router(video.router)
app.include_router(user.router)


# Main entry point for development
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
