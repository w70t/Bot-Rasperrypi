#!/bin/bash
# Backup Script for TikTok API
# Usage: ./scripts/backup.sh

set -e

BACKUP_DIR="$HOME/Bot-Rasperrypi/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="backup_${DATE}.tar.gz"

echo "💾 Starting backup..."

# Create backup directory
mkdir -p "$BACKUP_DIR"

# MongoDB dump
echo "📊 Backing up MongoDB..."
mongodump --uri="mongodb://localhost:27017" --db=tiktok_api --out=/tmp/mongo_backup_${DATE} || {
    echo "❌ MongoDB backup failed"
    exit 1
}

# Redis snapshot
echo "🔴 Backing up Redis..."
redis-cli SAVE
cp /var/lib/redis/dump.rdb /tmp/redis_backup_${DATE}.rdb || {
    echo "⚠️  Redis backup failed (continuing anyway)"
}

# Config files
echo "⚙️  Backing up config..."
cp .env /tmp/env_backup_${DATE} || echo "⚠️  .env not found"

# Logs (last 7 days)
echo "📝 Backing up logs..."
if [ -d "logs" ]; then
    cp -r logs /tmp/logs_backup_${DATE}
fi

# Compress everything
echo "🗜️  Compressing..."
cd /tmp
tar -czf "$BACKUP_DIR/$BACKUP_FILE" \
    mongo_backup_${DATE} \
    redis_backup_${DATE}.rdb \
    env_backup_${DATE} \
    logs_backup_${DATE} 2>/dev/null || true

# Cleanup temporary files
rm -rf /tmp/*backup*

# Delete old backups (keep last 30 days)
find "$BACKUP_DIR" -name "backup_*.tar.gz" -mtime +30 -delete

echo "✅ Backup completed: $BACKUP_FILE"
echo "📦 Size: $(du -h $BACKUP_DIR/$BACKUP_FILE | cut -f1)"
echo "📍 Location: $BACKUP_DIR/$BACKUP_FILE"
