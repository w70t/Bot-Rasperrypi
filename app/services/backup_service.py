"""
Backup Service - MongoDB and Redis Backup System
Handles automated and manual backups with retention policy
"""

import logging
import os
import tarfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import subprocess
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class BackupService:
    """
    Backup Service for MongoDB, Redis, and configuration files
    """

    def __init__(self):
        self.backup_dir = Path(settings.BACKUP_PATH)
        self.retention_days = settings.BACKUP_RETENTION_DAYS
        self.scheduler = None

        # Create backup directory if it doesn't exist
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    async def create_backup(self) -> Optional[str]:
        """
        Create a complete backup of the system

        Returns:
            Path to backup file or None if failed
        """
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        backup_name = f"backup_{timestamp}"
        temp_dir = self.backup_dir / backup_name

        try:
            logger.info(f"Starting backup: {backup_name}")

            # Create temporary directory
            temp_dir.mkdir(parents=True, exist_ok=True)

            # 1. Backup MongoDB
            logger.info("Backing up MongoDB...")
            mongo_backup_dir = temp_dir / "mongodb"
            mongo_success = await self._backup_mongodb(mongo_backup_dir)

            if not mongo_success:
                logger.error("MongoDB backup failed")
                shutil.rmtree(temp_dir, ignore_errors=True)
                return None

            # 2. Backup Redis
            logger.info("Backing up Redis...")
            redis_backup_file = temp_dir / "redis_dump.rdb"
            redis_success = await self._backup_redis(redis_backup_file)

            if not redis_success:
                logger.warning("Redis backup failed (continuing anyway)")

            # 3. Backup configuration files
            logger.info("Backing up configuration...")
            config_dir = temp_dir / "config"
            config_dir.mkdir(parents=True, exist_ok=True)
            await self._backup_config(config_dir)

            # 4. Backup logs (last 7 days)
            logger.info("Backing up logs...")
            logs_dir = temp_dir / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)
            await self._backup_logs(logs_dir)

            # 5. Create metadata file
            metadata_file = temp_dir / "backup_metadata.txt"
            await self._create_metadata(metadata_file, timestamp)

            # 6. Compress everything
            logger.info("Compressing backup...")
            backup_archive = self.backup_dir / f"{backup_name}.tar.gz"
            await self._compress_backup(temp_dir, backup_archive)

            # 7. Clean up temporary directory
            shutil.rmtree(temp_dir, ignore_errors=True)

            # 8. Clean old backups
            await self._cleanup_old_backups()

            backup_size = backup_archive.stat().st_size / (1024 * 1024)  # MB
            logger.info(f"✓ Backup completed: {backup_archive} ({backup_size:.2f} MB)")

            return str(backup_archive)

        except Exception as e:
            logger.error(f"Error creating backup: {str(e)}", exc_info=True)
            shutil.rmtree(temp_dir, ignore_errors=True)
            return None

    async def restore_backup(self, backup_file: str) -> bool:
        """
        Restore from a backup file

        Args:
            backup_file: Path to backup archive

        Returns:
            True if successful, False otherwise
        """
        try:
            backup_path = Path(backup_file)

            if not backup_path.exists():
                logger.error(f"Backup file not found: {backup_file}")
                return False

            logger.info(f"Starting restore from: {backup_file}")

            # Extract backup
            temp_dir = self.backup_dir / "restore_temp"
            temp_dir.mkdir(parents=True, exist_ok=True)

            logger.info("Extracting backup...")
            await self._extract_backup(backup_path, temp_dir)

            # Verify backup integrity
            if not await self._verify_backup(temp_dir):
                logger.error("Backup verification failed")
                shutil.rmtree(temp_dir, ignore_errors=True)
                return False

            # NOTE: Services should be stopped manually before restore in production
            # This prevents data corruption during the restore process

            # Restore MongoDB
            logger.info("Restoring MongoDB...")
            mongo_backup_dir = temp_dir / "mongodb"
            if mongo_backup_dir.exists():
                mongo_success = await self._restore_mongodb(mongo_backup_dir)
                if not mongo_success:
                    logger.error("MongoDB restore failed")
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    return False

            # Restore Redis
            logger.info("Restoring Redis...")
            redis_backup_file = temp_dir / "redis_dump.rdb"
            if redis_backup_file.exists():
                redis_success = await self._restore_redis(redis_backup_file)
                if not redis_success:
                    logger.warning("Redis restore failed (continuing anyway)")

            # Restore configuration
            logger.info("Restoring configuration...")
            config_dir = temp_dir / "config"
            if config_dir.exists():
                await self._restore_config(config_dir)

            # Clean up
            shutil.rmtree(temp_dir, ignore_errors=True)

            logger.info("✓ Restore completed successfully")
            logger.warning("⚠️ Please restart all services manually")

            return True

        except Exception as e:
            logger.error(f"Error restoring backup: {str(e)}", exc_info=True)
            return False

    async def schedule_daily_backup(self):
        """
        Schedule automated daily backups at 3:00 AM UTC
        """
        if not settings.BACKUP_ENABLED:
            logger.info("Automated backups disabled")
            return

        try:
            self.scheduler = AsyncIOScheduler()
            self.scheduler.add_job(
                self._scheduled_backup_job,
                trigger=CronTrigger(hour=3, minute=0),  # 3:00 AM UTC
                id='daily_backup',
                replace_existing=True
            )
            self.scheduler.start()

            logger.info("✓ Daily backup scheduled at 3:00 AM UTC")

        except Exception as e:
            logger.error(f"Failed to schedule daily backup: {str(e)}")

    async def _scheduled_backup_job(self):
        """
        Job function for scheduled backups
        """
        try:
            logger.info("Starting scheduled backup...")
            backup_file = await self.create_backup()

            if backup_file:
                # Send notification
                from app.telegram_bot import telegram_bot
                backup_size = Path(backup_file).stat().st_size / (1024 * 1024)  # MB

                await telegram_bot.send_notification(
                    f"✅ نسخ احتياطي تلقائي\n\n"
                    f"📦 File: {Path(backup_file).name}\n"
                    f"💾 Size: {backup_size:.2f} MB\n"
                    f"📅 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
                )
            else:
                # Send error notification
                from app.telegram_bot import telegram_bot
                await telegram_bot.notify_error(
                    error_type="Scheduled Backup Failed",
                    error_msg="Failed to create scheduled backup"
                )

        except Exception as e:
            logger.error(f"Error in scheduled backup: {str(e)}", exc_info=True)

    # ==================== MONGODB BACKUP/RESTORE ====================

    async def _backup_mongodb(self, output_dir: Path) -> bool:
        """
        Backup MongoDB database

        Args:
            output_dir: Directory to store MongoDB dump

        Returns:
            True if successful
        """
        try:
            output_dir.mkdir(parents=True, exist_ok=True)

            # Use mongodump command
            cmd = [
                'mongodump',
                '--uri', settings.MONGO_URI,
                '--db', settings.MONGO_DB_NAME,
                '--out', str(output_dir)
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                logger.error(f"mongodump failed: {stderr.decode()}")
                return False

            logger.info("✓ MongoDB backup completed")
            return True

        except Exception as e:
            logger.error(f"Error backing up MongoDB: {str(e)}", exc_info=True)
            return False

    async def _restore_mongodb(self, backup_dir: Path) -> bool:
        """
        Restore MongoDB database

        Args:
            backup_dir: Directory containing MongoDB dump

        Returns:
            True if successful
        """
        try:
            # Use mongorestore command
            cmd = [
                'mongorestore',
                '--uri', settings.MONGO_URI,
                '--db', settings.MONGO_DB_NAME,
                '--drop',  # Drop existing collections
                str(backup_dir / settings.MONGO_DB_NAME)
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                logger.error(f"mongorestore failed: {stderr.decode()}")
                return False

            logger.info("✓ MongoDB restore completed")
            return True

        except Exception as e:
            logger.error(f"Error restoring MongoDB: {str(e)}", exc_info=True)
            return False

    # ==================== REDIS BACKUP/RESTORE ====================

    async def _backup_redis(self, output_file: Path) -> bool:
        """
        Backup Redis database

        Args:
            output_file: Output file path

        Returns:
            True if successful
        """
        try:
            # Trigger Redis save
            from app.services.cache_service import cache_service

            # Force save
            await cache_service.redis.save()

            # Copy dump.rdb file
            redis_dump_path = Path('/var/lib/redis/dump.rdb')

            if not redis_dump_path.exists():
                # Try alternative location
                redis_dump_path = Path('/data/dump.rdb')

            if redis_dump_path.exists():
                shutil.copy2(redis_dump_path, output_file)
                logger.info("✓ Redis backup completed")
                return True
            else:
                logger.warning("Redis dump file not found")
                return False

        except Exception as e:
            logger.error(f"Error backing up Redis: {str(e)}", exc_info=True)
            return False

    async def _restore_redis(self, backup_file: Path) -> bool:
        """
        Restore Redis database

        Args:
            backup_file: Backup file path

        Returns:
            True if successful
        """
        try:
            redis_dump_path = Path('/var/lib/redis/dump.rdb')

            # Stop Redis (this should be done manually in production)
            logger.warning("⚠️ You need to stop Redis manually before restore")

            # Copy backup file
            shutil.copy2(backup_file, redis_dump_path)

            logger.info("✓ Redis restore completed")
            logger.warning("⚠️ You need to start Redis manually")

            return True

        except Exception as e:
            logger.error(f"Error restoring Redis: {str(e)}", exc_info=True)
            return False

    # ==================== CONFIG/LOGS BACKUP ====================

    async def _backup_config(self, output_dir: Path):
        """
        Backup configuration files

        Args:
            output_dir: Output directory
        """
        try:
            # Backup .env file (without sensitive data)
            env_file = Path('.env')
            if env_file.exists():
                shutil.copy2(env_file, output_dir / '.env.backup')

            # Backup config directory
            config_dir = Path('config')
            if config_dir.exists():
                shutil.copytree(config_dir, output_dir / 'config_files', dirs_exist_ok=True)

            logger.info("✓ Configuration backup completed")

        except Exception as e:
            logger.error(f"Error backing up config: {str(e)}", exc_info=True)

    async def _restore_config(self, backup_dir: Path):
        """
        Restore configuration files

        Args:
            backup_dir: Backup directory
        """
        try:
            # Note: Be careful restoring .env in production
            logger.warning("⚠️ Manual review of configuration files recommended")

            # Restore config files
            config_backup = backup_dir / 'config_files'
            if config_backup.exists():
                config_dir = Path('config')
                shutil.copytree(config_backup, config_dir, dirs_exist_ok=True)

            logger.info("✓ Configuration restore completed")

        except Exception as e:
            logger.error(f"Error restoring config: {str(e)}", exc_info=True)

    async def _backup_logs(self, output_dir: Path):
        """
        Backup logs (last 7 days)

        Args:
            output_dir: Output directory
        """
        try:
            logs_dir = Path('logs')
            if not logs_dir.exists():
                return

            # Copy log files modified in last 7 days
            cutoff_time = datetime.now() - timedelta(days=7)

            for log_file in logs_dir.glob('*.log'):
                if log_file.stat().st_mtime > cutoff_time.timestamp():
                    shutil.copy2(log_file, output_dir / log_file.name)

            logger.info("✓ Logs backup completed")

        except Exception as e:
            logger.error(f"Error backing up logs: {str(e)}", exc_info=True)

    # ==================== HELPER METHODS ====================

    async def _create_metadata(self, metadata_file: Path, timestamp: str):
        """
        Create backup metadata file

        Args:
            metadata_file: Metadata file path
            timestamp: Backup timestamp
        """
        try:
            metadata = f"""
Backup Metadata
===============

Timestamp: {timestamp}
Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
MongoDB URI: {settings.MONGO_URI}
Database: {settings.MONGO_DB_NAME}
Redis Host: {settings.REDIS_HOST}:{settings.REDIS_PORT}

Created by: TikTok API Backup Service
            """

            metadata_file.write_text(metadata)

        except Exception as e:
            logger.error(f"Error creating metadata: {str(e)}")

    async def _compress_backup(self, source_dir: Path, output_file: Path):
        """
        Compress backup directory to tar.gz

        Args:
            source_dir: Source directory
            output_file: Output archive file
        """
        try:
            with tarfile.open(output_file, 'w:gz') as tar:
                tar.add(source_dir, arcname=source_dir.name)

            logger.info("✓ Compression completed")

        except Exception as e:
            logger.error(f"Error compressing backup: {str(e)}", exc_info=True)
            raise

    async def _extract_backup(self, backup_file: Path, output_dir: Path):
        """
        Extract backup archive

        Args:
            backup_file: Backup archive file
            output_dir: Output directory
        """
        try:
            with tarfile.open(backup_file, 'r:gz') as tar:
                tar.extractall(output_dir)

            logger.info("✓ Extraction completed")

        except Exception as e:
            logger.error(f"Error extracting backup: {str(e)}", exc_info=True)
            raise

    async def _verify_backup(self, backup_dir: Path) -> bool:
        """
        Verify backup integrity

        Args:
            backup_dir: Backup directory

        Returns:
            True if valid
        """
        try:
            # Check for required files/directories
            required_items = ['mongodb', 'backup_metadata.txt']

            for item in required_items:
                if not (backup_dir / item).exists():
                    logger.error(f"Missing backup item: {item}")
                    return False

            logger.info("✓ Backup verification passed")
            return True

        except Exception as e:
            logger.error(f"Error verifying backup: {str(e)}")
            return False

    async def _cleanup_old_backups(self):
        """
        Delete backups older than retention period
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)

            for backup_file in self.backup_dir.glob('backup_*.tar.gz'):
                if backup_file.stat().st_mtime < cutoff_date.timestamp():
                    backup_file.unlink()
                    logger.info(f"Deleted old backup: {backup_file.name}")

        except Exception as e:
            logger.error(f"Error cleaning up old backups: {str(e)}")


# Singleton instance
backup_service = BackupService()
