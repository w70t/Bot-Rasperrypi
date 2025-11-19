#!/bin/bash
# Deployment Script for TikTok API
# Usage: ./scripts/deploy.sh

set -e  # Exit on error

echo "🚀 Starting deployment..."

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 1. Pull latest code
echo "📥 Pulling latest code..."
git pull origin main

# 2. Activate virtual environment
echo "🐍 Activating virtual environment..."
source venv/bin/activate || {
    echo "${RED}❌ Virtual environment not found. Creating...${NC}"
    python3 -m venv venv
    source venv/bin/activate
}

# 3. Install/update dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# 4. Run tests (if test files exist)
if [ -d "tests" ] && [ "$(ls -A tests/*.py 2>/dev/null)" ]; then
    echo "🧪 Running tests..."
    pytest || echo "${RED}⚠️  Tests failed, but continuing...${NC}"
fi

# 5. Backup current data
echo "💾 Creating backup..."
python -c "
import asyncio
from app.services.backup_service import backup_service
asyncio.run(backup_service.create_backup())
" || echo "${RED}⚠️  Backup failed, but continuing...${NC}"

# 6. Restart services
echo "🔄 Restarting services..."
sudo systemctl restart tiktok-api || {
    echo "${RED}❌ Failed to restart tiktok-api service${NC}"
    exit 1
}

sudo systemctl restart nginx || {
    echo "${RED}❌ Failed to restart nginx${NC}"
    exit 1
}

# 7. Health check
echo "🏥 Health check..."
sleep 5

response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)

if [ "$response" -eq 200 ]; then
    echo "${GREEN}✅ Deployment successful!${NC}"
else
    echo "${RED}❌ Health check failed! Rolling back...${NC}"
    git checkout HEAD~1
    sudo systemctl restart tiktok-api
    exit 1
fi

echo "${GREEN}✅ All done!${NC}"
