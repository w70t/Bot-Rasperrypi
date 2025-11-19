"""
Database Connection and Management
Handles MongoDB connection using Motor (async driver)
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from typing import Optional
import logging
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class Database:
    """
    MongoDB Database Manager
    Singleton pattern for database connection
    """

    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None

    @classmethod
    async def connect_db(cls):
        """
        Connect to MongoDB
        Called on application startup
        """
        try:
            logger.info(f"Connecting to MongoDB at {settings.MONGO_URI}")

            cls.client = AsyncIOMotorClient(
                settings.MONGO_URI,
                maxPoolSize=settings.MONGO_MAX_POOL_SIZE,
                minPoolSize=settings.MONGO_MIN_POOL_SIZE,
                serverSelectionTimeoutMS=5000,
            )

            # Test connection
            await cls.client.admin.command('ping')

            cls.db = cls.client[settings.MONGO_DB_NAME]

            # Create indexes
            await cls.create_indexes()

            logger.info(f"Successfully connected to MongoDB: {settings.MONGO_DB_NAME}")

        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during MongoDB connection: {e}")
            raise

    @classmethod
    async def close_db(cls):
        """
        Close MongoDB connection
        Called on application shutdown
        """
        if cls.client:
            logger.info("Closing MongoDB connection")
            cls.client.close()
            logger.info("MongoDB connection closed")

    @classmethod
    async def create_indexes(cls):
        """
        Create database indexes for performance
        """
        if cls.db is None:
            logger.warning("Database not initialized. Cannot create indexes.")
            return

        try:
            # Users collection indexes
            await cls.db.users.create_index("email", unique=True)
            await cls.db.users.create_index("api_key", unique=True)
            await cls.db.users.create_index("plan")
            await cls.db.users.create_index("is_active")
            await cls.db.users.create_index("created_at")

            # Usage collection indexes
            await cls.db.usage.create_index("user_email")
            await cls.db.usage.create_index("timestamp")
            await cls.db.usage.create_index([("user_email", 1), ("timestamp", -1)])
            await cls.db.usage.create_index("success")

            # API Keys collection indexes (if separate)
            await cls.db.api_keys.create_index("key", unique=True)
            await cls.db.api_keys.create_index("user_email")
            await cls.db.api_keys.create_index("is_active")

            # Subscriptions collection indexes
            await cls.db.subscriptions.create_index("user_email")
            await cls.db.subscriptions.create_index("subscription_end")
            await cls.db.subscriptions.create_index("is_active")

            logger.info("Database indexes created successfully")

        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
            # Don't raise - indexes are not critical for operation

    @classmethod
    def get_db(cls) -> AsyncIOMotorDatabase:
        """
        Get database instance
        Returns the database connection
        """
        if cls.db is None:
            raise RuntimeError("Database not initialized. Call connect_db() first.")
        return cls.db

    @classmethod
    async def check_health(cls) -> bool:
        """
        Check if database is healthy
        Used by health check endpoint
        """
        try:
            if cls.client is None:
                return False

            # Ping the database
            await cls.client.admin.command('ping')
            return True

        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    @classmethod
    async def get_stats(cls) -> dict:
        """
        Get database statistics
        Returns info about database usage
        """
        try:
            if cls.db is None:
                return {}

            stats = await cls.db.command("dbStats")

            return {
                "database": stats.get("db"),
                "collections": stats.get("collections"),
                "objects": stats.get("objects"),
                "data_size_mb": round(stats.get("dataSize", 0) / (1024 * 1024), 2),
                "storage_size_mb": round(stats.get("storageSize", 0) / (1024 * 1024), 2),
                "indexes": stats.get("indexes"),
                "index_size_mb": round(stats.get("indexSize", 0) / (1024 * 1024), 2),
            }

        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}


# Dependency injection for FastAPI
async def get_database() -> AsyncIOMotorDatabase:
    """
    Dependency for FastAPI routes
    Usage: db: AsyncIOMotorDatabase = Depends(get_database)
    """
    return Database.get_db()


# Collection helpers
class Collections:
    """
    Helper class for accessing collections
    """

    @staticmethod
    def users():
        """Get users collection"""
        return Database.get_db().users

    @staticmethod
    def usage():
        """Get usage collection"""
        return Database.get_db().usage

    @staticmethod
    def api_keys():
        """Get API keys collection"""
        return Database.get_db().api_keys

    @staticmethod
    def subscriptions():
        """Get subscriptions collection"""
        return Database.get_db().subscriptions

    @staticmethod
    def invoices():
        """Get invoices collection"""
        return Database.get_db().invoices

    @staticmethod
    def tickets():
        """Get support tickets collection"""
        return Database.get_db().tickets


# Initialize database on module import (will be called by main.py)
db = Database()
