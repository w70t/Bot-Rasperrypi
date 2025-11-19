# TikTok Video Intelligence API - Raspberry Pi 5 Deployment Guide

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Deployment Steps](#deployment-steps)
3. [Post-Deployment Checklist](#post-deployment-checklist)
4. [Troubleshooting](#troubleshooting)
5. [Maintenance Schedule](#maintenance-schedule)
6. [Monitoring and Optimization](#monitoring-and-optimization)
7. [Backup and Recovery](#backup-and-recovery)

---

## Prerequisites

### Hardware Requirements
- **Raspberry Pi 5** (8GB RAM recommended, 4GB minimum)
- **MicroSD Card**: 128GB+ (Class 10 or UHS-I)
- **Power Supply**: Official Raspberry Pi 5 USB-C power supply (27W)
- **Cooling**: Active cooling fan or heat sink (highly recommended)
- **Ethernet Cable**: For stable internet connection (recommended over WiFi)
- **Optional**: External SSD for better I/O performance

### Software Requirements
- Raspberry Pi OS (64-bit) - Bookworm or later
- SSH access enabled
- Internet connection
- Domain name (for SSL certificates)

### Required Accounts
1. **MongoDB Atlas Account** (optional, for cloud database)
2. **Stripe Account** (for payment processing)
3. **Telegram Bot** (from @BotFather)
4. **Cloudflare Account** (optional, for tunneling)
5. **Let's Encrypt** (free SSL certificates)
6. **Email Provider** (Gmail, SendGrid, etc.)

### Network Requirements
- **Open Ports**: 80 (HTTP), 443 (HTTPS), 22 (SSH)
- **Static IP**: Recommended for production
- **Port Forwarding**: Configured on router if hosting from home

---

## Deployment Steps

### Step 1: Initial Raspberry Pi OS Setup

**Explanation**: Flash and configure Raspberry Pi OS with optimal settings for server deployment.

**Commands**:
```bash
# Download Raspberry Pi Imager from https://www.raspberrypi.com/software/
# Flash Raspberry Pi OS (64-bit) to your SD card
# Boot up the Raspberry Pi and connect via SSH

# First login (default credentials)
# Username: pi
# Password: raspberry

# Change default password (IMPORTANT!)
passwd

# Update hostname
sudo hostnamectl set-hostname tiktok-api-server

# Configure timezone
sudo ticore set-timezone America/New_York
# Or use interactive menu:
sudo raspi-config
# Navigate to: Localisation Options > Timezone
```

**Verification**:
```bash
# Check hostname
hostname
# Expected output: tiktok-api-server

# Check timezone
timedatectl
# Expected output should show your selected timezone

# Check OS version
cat /etc/os-release
# Expected: Debian GNU/Linux 12 (bookworm)
```

**Expected Output**:
```
PRETTY_NAME="Debian GNU/Linux 12 (bookworm)"
NAME="Debian GNU/Linux"
VERSION_ID="12"
VERSION="12 (bookworm)"
```

---

### Step 2: System Updates and Dependencies

**Explanation**: Update all system packages and install essential development tools and libraries.

**Commands**:
```bash
# Update package lists
sudo apt update

# Upgrade all installed packages
sudo apt upgrade -y

# Install essential build dependencies
sudo apt install -y build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    python3-pip \
    git \
    curl \
    wget \
    vim \
    nano \
    htop \
    net-tools \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release \
    ufw \
    fail2ban

# Install system monitoring tools
sudo apt install -y sysstat iotop iftop

# Clean up
sudo apt autoremove -y
sudo apt autoclean
```

**Verification**:
```bash
# Check installed packages
dpkg -l | grep -E "build-essential|git|curl"

# Check system resources
free -h
df -h
```

**Expected Output**:
```
              total        used        free      shared  buff/cache   available
Mem:           7.8Gi       500Mi       6.8Gi        10Mi       500Mi       7.2Gi
Swap:          2.0Gi          0B       2.0Gi
```

---

### Step 3: Configure Firewall (UFW)

**Explanation**: Set up firewall rules to secure the server while allowing necessary traffic.

**Commands**:
```bash
# Reset UFW to default
sudo ufw --force reset

# Set default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (port 22)
sudo ufw allow 22/tcp comment 'SSH'

# Allow HTTP (port 80)
sudo ufw allow 80/tcp comment 'HTTP'

# Allow HTTPS (port 443)
sudo ufw allow 443/tcp comment 'HTTPS'

# Enable UFW
sudo ufw --force enable

# Check status
sudo ufw status verbose
```

**Verification**:
```bash
sudo ufw status numbered
```

**Expected Output**:
```
Status: active

     To                         Action      From
     --                         ------      ----
[ 1] 22/tcp                     ALLOW IN    Anywhere                   # SSH
[ 2] 80/tcp                     ALLOW IN    Anywhere                   # HTTP
[ 3] 443/tcp                    ALLOW IN    Anywhere                   # HTTPS
```

---

### Step 4: Configure Fail2Ban for Security

**Explanation**: Install and configure Fail2Ban to protect against brute-force attacks.

**Commands**:
```bash
# Configure Fail2Ban for SSH protection
sudo tee /etc/fail2ban/jail.local > /dev/null <<EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5
destemail = your-email@example.com
sendername = Fail2Ban
action = %(action_mwl)s

[sshd]
enabled = true
port = 22
filter = sshd
logpath = /var/log/auth.log
maxretry = 3

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
port = http,https
logpath = /var/log/nginx/error.log

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
port = http,https
logpath = /var/log/nginx/error.log
EOF

# Restart Fail2Ban
sudo systemctl restart fail2ban
sudo systemctl enable fail2ban
```

**Verification**:
```bash
# Check Fail2Ban status
sudo fail2ban-client status

# Check SSH jail
sudo fail2ban-client status sshd
```

**Expected Output**:
```
Status for the jail: sshd
|- Filter
|  |- Currently failed: 0
|  |- Total failed:     0
|  `- File list:        /var/log/auth.log
`- Actions
   |- Currently banned: 0
   |- Total banned:     0
   `- Banned IP list:
```

---

### Step 5: Install Python 3.11

**Explanation**: Install Python 3.11 which is required for the FastAPI application and modern Python features.

**Commands**:
```bash
# Add deadsnakes PPA for Python 3.11 (if not available in repos)
# For Raspberry Pi OS, we'll build from source

# Install dependencies for building Python
sudo apt install -y build-essential \
    zlib1g-dev \
    libncurses5-dev \
    libgdbm-dev \
    libnss3-dev \
    libssl-dev \
    libreadline-dev \
    libffi-dev \
    libsqlite3-dev \
    libbz2-dev \
    liblzma-dev

# Download Python 3.11
cd /tmp
wget https://www.python.org/ftp/python/3.11.9/Python-3.11.9.tgz

# Extract
tar -xzf Python-3.11.9.tgz
cd Python-3.11.9

# Configure with optimizations
./configure --enable-optimizations --with-lto --with-ensurepip=install

# Build (this takes 30-60 minutes on Raspberry Pi)
make -j4

# Install
sudo make altinstall

# Clean up
cd ~
rm -rf /tmp/Python-3.11.9*
```

**Verification**:
```bash
# Check Python version
python3.11 --version

# Check pip
python3.11 -m pip --version

# Create symbolic links (optional)
sudo update-alternatives --install /usr/bin/python3 python3 /usr/local/bin/python3.11 1
```

**Expected Output**:
```
Python 3.11.9
pip 24.0 from /usr/local/lib/python3.11/site-packages/pip (python 3.11)
```

---

### Step 6: Install MongoDB

**Explanation**: Install MongoDB database server for storing users, API keys, and usage data.

**Commands**:
```bash
# MongoDB doesn't officially support ARM64, so we'll use Docker or build from source
# Recommended: Use MongoDB Atlas (cloud) or install via Docker

# Option 1: Install Docker for MongoDB
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Log out and back in for group changes to take effect
# Then install MongoDB via Docker:
docker pull mongo:7.0

# Create MongoDB data directory
sudo mkdir -p /data/mongodb
sudo chown -R $USER:$USER /data/mongodb

# Run MongoDB container
docker run -d \
  --name mongodb \
  --restart unless-stopped \
  -p 27017:27017 \
  -v /data/mongodb:/data/db \
  -e MONGO_INITDB_ROOT_USERNAME=admin \
  -e MONGO_INITDB_ROOT_PASSWORD=your_secure_password_here \
  mongo:7.0

# Wait for MongoDB to start
sleep 10
```

**Verification**:
```bash
# Check if MongoDB container is running
docker ps | grep mongodb

# Test MongoDB connection
docker exec -it mongodb mongosh -u admin -p your_secure_password_here

# In mongosh, run:
# show dbs
# exit
```

**Expected Output**:
```
admin   100.00 KiB
config   60.00 KiB
local    72.00 KiB
```

---

### Step 7: Configure MongoDB Database and User

**Explanation**: Create dedicated database and user for the TikTok API with proper permissions.

**Commands**:
```bash
# Connect to MongoDB
docker exec -it mongodb mongosh -u admin -p your_secure_password_here

# In MongoDB shell, execute:
```

**MongoDB Commands**:
```javascript
// Switch to admin database
use admin

// Create application database
use tiktok_api

// Create application user
db.createUser({
  user: "tiktok_api_user",
  pwd: "your_app_password_here",
  roles: [
    { role: "readWrite", db: "tiktok_api" },
    { role: "dbAdmin", db: "tiktok_api" }
  ]
})

// Create collections
db.createCollection("users")
db.createCollection("api_keys")
db.createCollection("usage_logs")
db.createCollection("videos")
db.createCollection("subscriptions")
db.createCollection("payments")

// Exit
exit
```

**Verification**:
```bash
# Test application user connection
docker exec -it mongodb mongosh \
  -u tiktok_api_user \
  -p your_app_password_here \
  --authenticationDatabase tiktok_api \
  tiktok_api

# List collections
# show collections
```

**Expected Output**:
```
api_keys
payments
subscriptions
usage_logs
users
videos
```

---

### Step 8: Install and Configure Redis

**Explanation**: Install Redis for caching and rate limiting functionality.

**Commands**:
```bash
# Install Redis server
sudo apt install -y redis-server

# Configure Redis for production
sudo tee /etc/redis/redis.conf > /dev/null <<EOF
# Network
bind 127.0.0.1 ::1
protected-mode yes
port 6379
timeout 300

# General
daemonize no
supervised systemd
pidfile /var/run/redis/redis-server.pid
loglevel notice
logfile /var/log/redis/redis-server.log

# Snapshotting
save 900 1
save 300 10
save 60 10000
stop-writes-on-bgsave-error yes
rdbcompression yes
rdbchecksum yes
dbfilename dump.rdb
dir /var/lib/redis

# Security
requirepass your_redis_password_here

# Memory Management
maxmemory 512mb
maxmemory-policy allkeys-lru

# Append Only File
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec
EOF

# Restart Redis
sudo systemctl restart redis-server
sudo systemctl enable redis-server
```

**Verification**:
```bash
# Check Redis status
sudo systemctl status redis-server

# Test Redis connection
redis-cli -a your_redis_password_here ping

# Check Redis info
redis-cli -a your_redis_password_here info server
```

**Expected Output**:
```
PONG

# Server
redis_version:7.0.15
redis_mode:standalone
os:Linux 6.1.0-rpi7-rpi-v8 aarch64
```

---

### Step 9: Install Nginx Web Server

**Explanation**: Install and configure Nginx as a reverse proxy for the FastAPI application.

**Commands**:
```bash
# Install Nginx
sudo apt install -y nginx

# Remove default configuration
sudo rm /etc/nginx/sites-enabled/default

# Create application configuration
sudo tee /etc/nginx/sites-available/tiktok-api > /dev/null <<'EOF'
# Rate limiting zones
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=30r/m;
limit_req_zone $binary_remote_addr zone=login_limit:10m rate=5r/m;

# Upstream application servers
upstream tiktok_api {
    least_conn;
    server 127.0.0.1:8000 max_fails=3 fail_timeout=30s;
    keepalive 32;
}

# HTTP Server - Redirect to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name your-domain.com www.your-domain.com;

    # Let's Encrypt challenge
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    # Redirect all other traffic to HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS Server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name your-domain.com www.your-domain.com;

    # SSL Configuration (will be configured in Step 15)
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;

    # Logging
    access_log /var/log/nginx/tiktok-api-access.log;
    error_log /var/log/nginx/tiktok-api-error.log warn;

    # Client settings
    client_max_body_size 10M;
    client_body_timeout 60s;
    client_header_timeout 60s;

    # Root location
    location / {
        # Rate limiting
        limit_req zone=api_limit burst=10 nodelay;
        limit_req_status 429;

        # Proxy settings
        proxy_pass http://tiktok_api;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $server_name;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # Buffer settings
        proxy_buffering off;
        proxy_request_buffering off;
    }

    # API Documentation (only in development)
    location /docs {
        deny all;
        # proxy_pass http://tiktok_api;
    }

    location /redoc {
        deny all;
        # proxy_pass http://tiktok_api;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://tiktok_api;
        access_log off;
    }

    # Stripe webhooks (higher rate limit)
    location /api/webhooks/stripe {
        limit_req zone=api_limit burst=50 nodelay;
        proxy_pass http://tiktok_api;
    }
}
EOF

# Enable the site
sudo ln -s /etc/nginx/sites-available/tiktok-api /etc/nginx/sites-enabled/

# Test Nginx configuration
sudo nginx -t

# Don't start Nginx yet (we need SSL certificates first)
```

**Verification**:
```bash
# Test Nginx configuration
sudo nginx -t
```

**Expected Output**:
```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

---

### Step 10: Clone Project Repository

**Explanation**: Clone the TikTok API project from your Git repository to the deployment location.

**Commands**:
```bash
# Create application directory
sudo mkdir -p /opt/tiktok-api
sudo chown -R $USER:$USER /opt/tiktok-api

# Navigate to directory
cd /opt/tiktok-api

# Clone repository (replace with your repository URL)
git clone https://github.com/yourusername/Bot-Rasperrypi.git .

# Or if already have the code, copy it:
# rsync -avz ~/Bot-Rasperrypi/ /opt/tiktok-api/

# Set proper permissions
chmod +x /opt/tiktok-api

# Create necessary directories
mkdir -p logs backups uploads temp
chmod 755 logs backups uploads temp
```

**Verification**:
```bash
# Check project structure
ls -la /opt/tiktok-api/

# Verify main files exist
test -f /opt/tiktok-api/app/main.py && echo "main.py exists" || echo "main.py missing"
test -f /opt/tiktok-api/requirements.txt && echo "requirements.txt exists" || echo "requirements.txt missing"
test -f /opt/tiktok-api/.env.example && echo ".env.example exists" || echo ".env.example missing"
```

**Expected Output**:
```
main.py exists
requirements.txt exists
.env.example exists

total 48
drwxr-xr-x  8 pi pi 4096 Nov 19 10:00 .
drwxr-xr-x  3 pi pi 4096 Nov 19 09:55 ..
drwxr-xr-x  6 pi pi 4096 Nov 19 10:00 app
drwxr-xr-x  2 pi pi 4096 Nov 19 10:00 backups
drwxr-xr-x  2 pi pi 4096 Nov 19 10:00 logs
-rw-r--r--  1 pi pi 2156 Nov 19 10:00 requirements.txt
```

---

### Step 11: Create Python Virtual Environment

**Explanation**: Create an isolated Python environment for the application dependencies.

**Commands**:
```bash
# Navigate to project directory
cd /opt/tiktok-api

# Create virtual environment with Python 3.11
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip, setuptools, and wheel
pip install --upgrade pip setuptools wheel

# Install project dependencies
pip install -r requirements.txt

# Install additional production packages
pip install gunicorn supervisor

# Deactivate for now
deactivate
```

**Verification**:
```bash
# Check virtual environment
ls -la /opt/tiktok-api/venv/

# Activate and check installed packages
source /opt/tiktok-api/venv/bin/activate
pip list

# Check Python version in venv
python --version

deactivate
```

**Expected Output**:
```
Python 3.11.9

Package              Version
-------------------- --------
fastapi              0.104.1
uvicorn              0.24.0
motor                3.3.2
redis                5.0.1
stripe               7.8.0
python-telegram-bot  20.7
... (and more packages)
```

---

### Step 12: Configure Environment Variables

**Explanation**: Set up all required environment variables for the application configuration.

**Commands**:
```bash
# Navigate to project directory
cd /opt/tiktok-api

# Copy example environment file
cp .env.example .env

# Edit environment file
nano .env
```

**Environment File Configuration** (`.env`):
```bash
# Application Settings
APP_NAME=TikTok Video Intelligence API
APP_VERSION=1.0.0
DEBUG=False
ENVIRONMENT=production
HOST=0.0.0.0
PORT=8000
WORKERS=4

# Security - GENERATE A NEW SECRET KEY!
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
API_KEY_PREFIX=tk_

# MongoDB Configuration
MONGO_URI=mongodb://tiktok_api_user:your_app_password_here@localhost:27017/tiktok_api?authSource=tiktok_api
MONGO_DB_NAME=tiktok_api
MONGO_MAX_POOL_SIZE=10
MONGO_MIN_POOL_SIZE=1

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your_redis_password_here
REDIS_CACHE_TTL=3600

# Rate Limiting (requests per minute)
RATE_LIMIT_FREE=10
RATE_LIMIT_BASIC=30
RATE_LIMIT_PRO=100
RATE_LIMIT_BUSINESS=500

# Usage Limits (requests per month)
USAGE_LIMIT_FREE=50
USAGE_LIMIT_BASIC=1000
USAGE_LIMIT_PRO=10000
USAGE_LIMIT_BUSINESS=100000

# TikTok Scraping
TIKTOK_TIMEOUT=30
TIKTOK_MAX_RETRIES=3
USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36

# Logging
LOG_LEVEL=INFO
LOG_FILE_PATH=logs/api.log
ERROR_LOG_FILE_PATH=logs/errors.log
ACCESS_LOG_FILE_PATH=logs/access.log

# Telegram Bot (REQUIRED - Get from @BotFather)
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_OWNER_CHAT_ID=123456789
TELEGRAM_NOTIFICATIONS_ENABLED=True
NOTIFY_NEW_SUBSCRIBER=True
NOTIFY_ERRORS=True
NOTIFY_DAILY_REPORT=True
NOTIFY_MILESTONES=True
DAILY_REPORT_TIME=09:00

# Stripe Payment Processing (Get from Stripe Dashboard)
STRIPE_SECRET_KEY=sk_live_your_secret_key
STRIPE_PUBLISHABLE_KEY=pk_live_your_publishable_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret

# Stripe Plan Price IDs (Create in Stripe Dashboard)
STRIPE_PRICE_BASIC=price_1234567890abcdef
STRIPE_PRICE_PRO=price_0987654321fedcba
STRIPE_PRICE_BUSINESS=price_abcdef1234567890

# Email Settings
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your_app_specific_password
SMTP_FROM_EMAIL=noreply@your-domain.com
SMTP_FROM_NAME=TikTok API

# Admin Panel
ADMIN_USERNAME=admin
ADMIN_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))")
ADMIN_PANEL_SECRET_PATH=/admin-$(python3 -c "import secrets; print(secrets.token_urlsafe(8))")
ADMIN_SESSION_TIMEOUT_MINUTES=30

# Backup
BACKUP_ENABLED=True
BACKUP_PATH=backups/
BACKUP_RETENTION_DAYS=30

# Performance
MAX_RESPONSE_TIME_WARNING=3.0
SLOW_QUERY_THRESHOLD=1.0
```

**Generate Secure Values**:
```bash
# Generate secure SECRET_KEY
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"

# Generate secure ADMIN_PASSWORD
python3 -c "import secrets; print('ADMIN_PASSWORD=' + secrets.token_urlsafe(16))"

# Generate random admin path
python3 -c "import secrets; print('ADMIN_PANEL_SECRET_PATH=/admin-' + secrets.token_urlsafe(8))"
```

**Verification**:
```bash
# Check if .env file exists and has content
test -f /opt/tiktok-api/.env && echo ".env exists" || echo ".env missing"

# Verify environment variables are loaded (activate venv first)
source /opt/tiktok-api/venv/bin/activate
python3 -c "from dotenv import load_dotenv; load_dotenv(); import os; print('MongoDB URI:', os.getenv('MONGO_URI', 'NOT SET'))"
deactivate

# Secure the .env file
chmod 600 /opt/tiktok-api/.env
```

**Expected Output**:
```
.env exists
MongoDB URI: mongodb://tiktok_api_user:***@localhost:27017/tiktok_api
```

---

### Step 13: Create MongoDB Indexes

**Explanation**: Create database indexes for optimal query performance.

**Commands**:
```bash
# Create indexes script
cat > /opt/tiktok-api/create_indexes.py << 'EOF'
#!/usr/bin/env python3
"""
Create MongoDB indexes for optimal performance
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

async def create_indexes():
    # Connect to MongoDB
    mongo_uri = os.getenv('MONGO_URI')
    client = AsyncIOMotorClient(mongo_uri)
    db = client[os.getenv('MONGO_DB_NAME', 'tiktok_api')]

    print("Creating indexes...")

    # Users collection
    await db.users.create_index("email", unique=True)
    await db.users.create_index("created_at")
    await db.users.create_index([("email", 1), ("is_active", 1)])
    print("✓ Users indexes created")

    # API Keys collection
    await db.api_keys.create_index("key", unique=True)
    await db.api_keys.create_index("user_id")
    await db.api_keys.create_index([("user_id", 1), ("is_active", 1)])
    await db.api_keys.create_index("expires_at")
    print("✓ API Keys indexes created")

    # Usage Logs collection
    await db.usage_logs.create_index([("user_id", 1), ("timestamp", -1)])
    await db.usage_logs.create_index("timestamp")
    await db.usage_logs.create_index([("api_key", 1), ("timestamp", -1)])
    await db.usage_logs.create_index("endpoint")
    print("✓ Usage Logs indexes created")

    # Videos collection (cache)
    await db.videos.create_index("video_id", unique=True)
    await db.videos.create_index("created_at", expireAfterSeconds=86400)  # 24 hours TTL
    await db.videos.create_index("url")
    print("✓ Videos indexes created")

    # Subscriptions collection
    await db.subscriptions.create_index("user_id")
    await db.subscriptions.create_index("stripe_subscription_id", unique=True, sparse=True)
    await db.subscriptions.create_index([("user_id", 1), ("status", 1)])
    await db.subscriptions.create_index("current_period_end")
    print("✓ Subscriptions indexes created")

    # Payments collection
    await db.payments.create_index("user_id")
    await db.payments.create_index("stripe_payment_intent_id", unique=True, sparse=True)
    await db.payments.create_index([("user_id", 1), ("created_at", -1)])
    await db.payments.create_index("status")
    print("✓ Payments indexes created")

    print("\n✅ All indexes created successfully!")

    # Close connection
    client.close()

if __name__ == "__main__":
    asyncio.run(create_indexes())
EOF

# Make script executable
chmod +x /opt/tiktok-api/create_indexes.py

# Run the script
source /opt/tiktok-api/venv/bin/activate
python /opt/tiktok-api/create_indexes.py
deactivate
```

**Verification**:
```bash
# Connect to MongoDB and check indexes
docker exec -it mongodb mongosh \
  -u tiktok_api_user \
  -p your_app_password_here \
  --authenticationDatabase tiktok_api \
  tiktok_api \
  --eval "db.users.getIndexes()"
```

**Expected Output**:
```
✓ Users indexes created
✓ API Keys indexes created
✓ Usage Logs indexes created
✓ Videos indexes created
✓ Subscriptions indexes created
✓ Payments indexes created

✅ All indexes created successfully!
```

---

### Step 14: Local Testing

**Explanation**: Test the application locally before deploying as a service.

**Commands**:
```bash
# Navigate to project directory
cd /opt/tiktok-api

# Activate virtual environment
source venv/bin/activate

# Run the application in test mode
python -m app.main
```

**Testing in another terminal**:
```bash
# Test health endpoint
curl http://localhost:8000/health

# Test with proper formatting
curl -s http://localhost:8000/health | python3 -m json.tool

# Check application logs
tail -f /opt/tiktok-api/logs/api.log
```

**Verification**:
```bash
# Check if application is listening
sudo netstat -tulpn | grep :8000

# Test API endpoints
curl -X GET http://localhost:8000/health

# Stop the test server (Ctrl+C)
```

**Expected Output**:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-19T10:30:00.000000",
  "version": "1.0.0",
  "services": {
    "database": "connected",
    "redis": "connected"
  }
}
```

---

### Step 15: Create Systemd Service

**Explanation**: Configure the application to run as a systemd service for automatic startup and management.

**Commands**:
```bash
# Create systemd service file
sudo tee /etc/systemd/system/tiktok-api.service > /dev/null <<EOF
[Unit]
Description=TikTok Video Intelligence API
After=network.target mongodb.service redis-server.service docker.service
Wants=mongodb.service redis-server.service

[Service]
Type=notify
User=$USER
Group=$USER
WorkingDirectory=/opt/tiktok-api
Environment="PATH=/opt/tiktok-api/venv/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=/opt/tiktok-api/.env

# Start command using uvicorn with multiple workers
ExecStart=/opt/tiktok-api/venv/bin/uvicorn app.main:app \\
    --host 0.0.0.0 \\
    --port 8000 \\
    --workers 4 \\
    --log-level info \\
    --access-log \\
    --use-colors \\
    --proxy-headers \\
    --forwarded-allow-ips='*'

# Restart policy
Restart=always
RestartSec=10
StartLimitInterval=200
StartLimitBurst=5

# Resource limits
LimitNOFILE=65536
MemoryLimit=2G
CPUQuota=300%

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/tiktok-api/logs /opt/tiktok-api/backups /opt/tiktok-api/uploads /opt/tiktok-api/temp
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictRealtime=true
RestrictNamespaces=true

# Logging
StandardOutput=append:/opt/tiktok-api/logs/systemd-output.log
StandardError=append:/opt/tiktok-api/logs/systemd-error.log
SyslogIdentifier=tiktok-api

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd daemon
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable tiktok-api.service

# Start the service
sudo systemctl start tiktok-api.service
```

**Verification**:
```bash
# Check service status
sudo systemctl status tiktok-api.service

# Check if service is running
sudo systemctl is-active tiktok-api.service

# Check service logs
sudo journalctl -u tiktok-api.service -f

# Test health endpoint
curl http://localhost:8000/health
```

**Expected Output**:
```
● tiktok-api.service - TikTok Video Intelligence API
     Loaded: loaded (/etc/systemd/system/tiktok-api.service; enabled; vendor preset: enabled)
     Active: active (running) since Tue 2025-11-19 10:45:00 EST; 1min ago
   Main PID: 12345 (uvicorn)
      Tasks: 5 (limit: 9248)
     Memory: 256.0M
        CPU: 2.5s
     CGroup: /system.slice/tiktok-api.service
             └─12345 /opt/tiktok-api/venv/bin/python /opt/tiktok-api/venv/bin/uvicorn app.main:app...
```

---

### Step 16: Install SSL Certificate (Let's Encrypt)

**Explanation**: Install free SSL certificates from Let's Encrypt for HTTPS support.

**Commands**:
```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Stop Nginx temporarily
sudo systemctl stop nginx

# Obtain SSL certificate (replace with your domain)
sudo certbot certonly --standalone \
  -d your-domain.com \
  -d www.your-domain.com \
  --non-interactive \
  --agree-tos \
  --email your-email@example.com \
  --preferred-challenges http

# Update Nginx configuration with correct domain
sudo sed -i 's/your-domain.com/actual-domain.com/g' /etc/nginx/sites-available/tiktok-api

# Test Nginx configuration
sudo nginx -t

# Start Nginx
sudo systemctl start nginx
sudo systemctl enable nginx

# Set up automatic renewal
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

**Verification**:
```bash
# Check certificate
sudo certbot certificates

# Test certificate renewal (dry run)
sudo certbot renew --dry-run

# Check Nginx status
sudo systemctl status nginx

# Test HTTPS
curl -I https://your-domain.com/health
```

**Expected Output**:
```
Certificate Name: your-domain.com
  Domains: your-domain.com www.your-domain.com
  Expiry Date: 2026-02-17 09:45:00+00:00 (VALID: 89 days)
  Certificate Path: /etc/letsencrypt/live/your-domain.com/fullchain.pem
  Private Key Path: /etc/letsencrypt/live/your-domain.com/privkey.pem
```

---

### Step 17: Configure Cloudflare Tunnel (Optional)

**Explanation**: Set up Cloudflare Tunnel for secure access without port forwarding.

**Commands**:
```bash
# Download cloudflared
wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb

# Install cloudflared
sudo dpkg -i cloudflared-linux-arm64.deb

# Authenticate with Cloudflare
cloudflared tunnel login
# This will open a browser - follow the instructions

# Create a tunnel
cloudflared tunnel create tiktok-api

# Note the Tunnel ID from the output

# Create tunnel configuration
mkdir -p ~/.cloudflared
cat > ~/.cloudflared/config.yml << EOF
tunnel: TUNNEL_ID_HERE
credentials-file: /home/$USER/.cloudflared/TUNNEL_ID_HERE.json

ingress:
  - hostname: your-domain.com
    service: http://localhost:8000
  - hostname: www.your-domain.com
    service: http://localhost:8000
  - service: http_status:404
EOF

# Route DNS to tunnel
cloudflared tunnel route dns tiktok-api your-domain.com
cloudflared tunnel route dns tiktok-api www.your-domain.com

# Install as a service
sudo cloudflared service install

# Start the tunnel
sudo systemctl start cloudflared
sudo systemctl enable cloudflared
```

**Verification**:
```bash
# Check tunnel status
cloudflared tunnel info tiktok-api

# Check service status
sudo systemctl status cloudflared

# List tunnels
cloudflared tunnel list
```

**Expected Output**:
```
Your tunnel TUNNEL_ID_HERE has been created successfully.
Tunnel routed successfully to your-domain.com
```

---

### Step 18: Configure Telegram Bot

**Explanation**: Set up Telegram bot for notifications and monitoring.

**Commands**:
```bash
# The bot is already configured in .env file
# Test the bot manually

# Create test script
cat > /opt/tiktok-api/test_telegram.py << 'EOF'
#!/usr/bin/env python3
import asyncio
from telegram import Bot
import os
from dotenv import load_dotenv

load_dotenv()

async def test_bot():
    bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))
    chat_id = os.getenv('TELEGRAM_OWNER_CHAT_ID')

    try:
        # Send test message
        await bot.send_message(
            chat_id=chat_id,
            text="🚀 TikTok API deployed successfully!\n\n" +
                 "✅ Server is running\n" +
                 "✅ Database connected\n" +
                 "✅ Redis connected\n" +
                 "✅ All systems operational"
        )
        print("✅ Telegram notification sent successfully!")
    except Exception as e:
        print(f"❌ Error sending Telegram message: {e}")

if __name__ == "__main__":
    asyncio.run(test_bot())
EOF

# Run test
source /opt/tiktok-api/venv/bin/activate
python /opt/tiktok-api/test_telegram.py
deactivate
```

**Get Telegram Chat ID**:
```bash
# 1. Start a chat with your bot on Telegram
# 2. Send any message to the bot
# 3. Run this command to get updates:

curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates

# Look for "chat":{"id": XXXXXX} in the response
# Use this ID as TELEGRAM_OWNER_CHAT_ID in .env
```

**Verification**:
```bash
# Check if bot message was received in Telegram
# You should see a message from your bot

# Test bot command
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/sendMessage" \
  -d "chat_id=<YOUR_CHAT_ID>" \
  -d "text=Test message from TikTok API"
```

**Expected Output**:
```
✅ Telegram notification sent successfully!
```

---

### Step 19: Configure Stripe Webhooks

**Explanation**: Set up Stripe webhooks to handle payment events.

**Commands**:
```bash
# Stripe webhooks are handled at /api/webhooks/stripe endpoint
# You need to configure this in Stripe Dashboard

# 1. Log in to Stripe Dashboard: https://dashboard.stripe.com/
# 2. Go to Developers > Webhooks
# 3. Click "Add endpoint"
# 4. Enter your webhook URL: https://your-domain.com/api/webhooks/stripe
# 5. Select events to listen to:
#    - checkout.session.completed
#    - customer.subscription.created
#    - customer.subscription.updated
#    - customer.subscription.deleted
#    - invoice.payment_succeeded
#    - invoice.payment_failed
#    - payment_intent.succeeded
#    - payment_intent.payment_failed
# 6. Copy the webhook signing secret
# 7. Add it to .env file as STRIPE_WEBHOOK_SECRET

# Test webhook locally using Stripe CLI
curl -O https://github.com/stripe/stripe-cli/releases/download/v1.19.4/stripe_1.19.4_linux_arm64.tar.gz
tar -xzf stripe_1.19.4_linux_arm64.tar.gz
sudo mv stripe /usr/local/bin/

# Login to Stripe
stripe login

# Forward webhooks to local endpoint
stripe listen --forward-to localhost:8000/api/webhooks/stripe
```

**Verification**:
```bash
# Test webhook endpoint
curl -X POST https://your-domain.com/api/webhooks/stripe \
  -H "Content-Type: application/json" \
  -d '{"type": "ping"}'

# Check webhook logs in Stripe Dashboard
# Webhooks > Your webhook > Events

# Check application logs
tail -f /opt/tiktok-api/logs/api.log | grep webhook
```

**Expected Output**:
```
Webhook endpoint is reachable
Stripe webhook received: ping
```

---

### Step 20: Set Up Daily Backups (Cron)

**Explanation**: Configure automated daily backups of MongoDB database.

**Commands**:
```bash
# Create backup script
sudo tee /opt/tiktok-api/backup.sh > /dev/null <<'EOF'
#!/bin/bash
# TikTok API Daily Backup Script

# Configuration
BACKUP_DIR="/opt/tiktok-api/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# MongoDB credentials
MONGO_USER="tiktok_api_user"
MONGO_PASS="your_app_password_here"
MONGO_DB="tiktok_api"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup filename
BACKUP_FILE="$BACKUP_DIR/mongodb_backup_$DATE.gz"

# Perform backup
echo "Starting backup at $(date)"
docker exec mongodb mongodump \
  --username="$MONGO_USER" \
  --password="$MONGO_PASS" \
  --authenticationDatabase="$MONGO_DB" \
  --db="$MONGO_DB" \
  --archive | gzip > "$BACKUP_FILE"

# Check if backup was successful
if [ $? -eq 0 ]; then
    echo "✅ Backup completed successfully: $BACKUP_FILE"
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "Backup size: $BACKUP_SIZE"

    # Send Telegram notification
    source /opt/tiktok-api/.env
    if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_OWNER_CHAT_ID" ]; then
        curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
          -d "chat_id=$TELEGRAM_OWNER_CHAT_ID" \
          -d "text=✅ TikTok API Backup Completed%0A%0ADate: $(date)%0ASize: $BACKUP_SIZE%0AFile: mongodb_backup_$DATE.gz" \
          > /dev/null
    fi
else
    echo "❌ Backup failed!"
    # Send failure notification
    source /opt/tiktok-api/.env
    if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_OWNER_CHAT_ID" ]; then
        curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
          -d "chat_id=$TELEGRAM_OWNER_CHAT_ID" \
          -d "text=❌ TikTok API Backup Failed!%0A%0ADate: $(date)%0APlease check the server immediately." \
          > /dev/null
    fi
    exit 1
fi

# Remove backups older than retention period
echo "Cleaning old backups (older than $RETENTION_DAYS days)..."
find "$BACKUP_DIR" -name "mongodb_backup_*.gz" -type f -mtime +$RETENTION_DAYS -delete

# Log backup completion
echo "Backup process completed at $(date)"
EOF

# Make script executable
sudo chmod +x /opt/tiktok-api/backup.sh

# Test backup script
sudo /opt/tiktok-api/backup.sh

# Add to crontab (daily at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/tiktok-api/backup.sh >> /opt/tiktok-api/logs/backup.log 2>&1") | crontab -

# Create backup log rotation
sudo tee /etc/logrotate.d/tiktok-api-backup > /dev/null <<EOF
/opt/tiktok-api/logs/backup.log {
    weekly
    rotate 4
    compress
    missingok
    notifempty
}
EOF
```

**Verification**:
```bash
# Check if backup was created
ls -lh /opt/tiktok-api/backups/

# Verify crontab entry
crontab -l | grep backup

# Test backup restoration (dry run)
LATEST_BACKUP=$(ls -t /opt/tiktok-api/backups/mongodb_backup_*.gz | head -1)
echo "Latest backup: $LATEST_BACKUP"
```

**Expected Output**:
```
Starting backup at Tue Nov 19 02:00:00 EST 2025
✅ Backup completed successfully: /opt/tiktok-api/backups/mongodb_backup_20251119_020000.gz
Backup size: 15M
Backup process completed at Tue Nov 19 02:00:15 EST 2025
```

---

### Step 21: Monitoring and Final Testing

**Explanation**: Set up monitoring tools and perform comprehensive testing.

**Commands**:
```bash
# Install monitoring tools
sudo apt install -y prometheus-node-exporter

# Enable and start node exporter
sudo systemctl enable prometheus-node-exporter
sudo systemctl start prometheus-node-exporter

# Create monitoring script
cat > /opt/tiktok-api/monitor.sh << 'EOF'
#!/bin/bash
# System monitoring script

echo "=== TikTok API System Status ==="
echo ""
echo "--- Service Status ---"
systemctl is-active tiktok-api.service && echo "✅ TikTok API: Running" || echo "❌ TikTok API: Stopped"
systemctl is-active nginx.service && echo "✅ Nginx: Running" || echo "❌ Nginx: Stopped"
systemctl is-active redis-server.service && echo "✅ Redis: Running" || echo "❌ Redis: Stopped"
docker ps | grep -q mongodb && echo "✅ MongoDB: Running" || echo "❌ MongoDB: Stopped"

echo ""
echo "--- System Resources ---"
echo "CPU Usage: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}')%"
echo "Memory: $(free -h | awk 'NR==2{printf "%s/%s (%.2f%%)", $3,$2,$3*100/$2 }')"
echo "Disk: $(df -h / | awk 'NR==2{printf "%s/%s (%s)", $3,$2,$5}')"
echo "Temperature: $(vcgencmd measure_temp)"

echo ""
echo "--- Network ---"
echo "Active Connections: $(netstat -an | grep :8000 | wc -l)"
echo "Nginx Status: $(curl -s -o /dev/null -w "%{http_code}" http://localhost/health)"

echo ""
echo "--- Recent Errors ---"
tail -n 5 /opt/tiktok-api/logs/errors.log 2>/dev/null || echo "No recent errors"

echo ""
echo "--- API Response Time ---"
START=$(date +%s.%N)
curl -s http://localhost:8000/health > /dev/null
END=$(date +%s.%N)
DIFF=$(echo "$END - $START" | bc)
echo "Health endpoint response time: ${DIFF}s"
EOF

chmod +x /opt/tiktok-api/monitor.sh

# Run monitoring script
/opt/tiktok-api/monitor.sh

# Set up hourly monitoring (optional)
(crontab -l 2>/dev/null; echo "0 * * * * /opt/tiktok-api/monitor.sh >> /opt/tiktok-api/logs/monitor.log 2>&1") | crontab -
```

**Final Testing Checklist**:
```bash
# 1. Test health endpoint
curl -s https://your-domain.com/health | jq

# 2. Test API with invalid key
curl -s -X POST https://your-domain.com/api/video/extract \
  -H "X-API-Key: invalid_key" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.tiktok.com/@user/video/123"}' | jq

# 3. Test rate limiting
for i in {1..15}; do
  curl -s -o /dev/null -w "%{http_code}\n" https://your-domain.com/health
  sleep 1
done

# 4. Test SSL certificate
openssl s_client -connect your-domain.com:443 -servername your-domain.com < /dev/null | grep "Verify return code"

# 5. Check application logs
tail -f /opt/tiktok-api/logs/api.log

# 6. Check Nginx access logs
sudo tail -f /var/log/nginx/tiktok-api-access.log

# 7. Monitor system resources
htop

# 8. Check Docker containers
docker ps

# 9. Test database connection
docker exec -it mongodb mongosh -u tiktok_api_user -p your_app_password_here --authenticationDatabase tiktok_api tiktok_api --eval "db.users.countDocuments()"

# 10. Test Redis connection
redis-cli -a your_redis_password_here ping
```

**Verification**:
```bash
# Run comprehensive test
/opt/tiktok-api/monitor.sh
```

**Expected Output**:
```
=== TikTok API System Status ===

--- Service Status ---
✅ TikTok API: Running
✅ Nginx: Running
✅ Redis: Running
✅ MongoDB: Running

--- System Resources ---
CPU Usage: 15.2%
Memory: 1.2G/7.8G (15.38%)
Disk: 8.5G/115G (8%)
Temperature: temp=45.0'C

--- Network ---
Active Connections: 3
Nginx Status: 200

--- Recent Errors ---
No recent errors

--- API Response Time ---
Health endpoint response time: 0.045s
```

---

## Post-Deployment Checklist

### Security Checklist (✓ Complete all items)

- [ ] 1. Changed default passwords (pi user, MongoDB, Redis, Admin panel)
- [ ] 2. Generated secure SECRET_KEY in .env file
- [ ] 3. Configured firewall (UFW) with only necessary ports open
- [ ] 4. Enabled Fail2Ban for brute-force protection
- [ ] 5. Installed SSL certificate (Let's Encrypt) for HTTPS
- [ ] 6. Verified SSL certificate is valid and auto-renewing
- [ ] 7. Set restrictive permissions on .env file (chmod 600)
- [ ] 8. Configured Nginx security headers (HSTS, X-Frame-Options, etc.)
- [ ] 9. Disabled Nginx default site configuration
- [ ] 10. Set up MongoDB authentication with strong passwords
- [ ] 11. Configured Redis password protection
- [ ] 12. Disabled debug mode in production (.env DEBUG=False)
- [ ] 13. Removed or secured API documentation endpoints (/docs, /redoc)
- [ ] 14. Configured rate limiting in Nginx
- [ ] 15. Set up SSH key authentication (disabled password login)

### Functionality Checklist (✓ Complete all items)

- [ ] 1. Health endpoint responds correctly (https://domain.com/health)
- [ ] 2. MongoDB connection is working (check startup logs)
- [ ] 3. Redis connection is working (check startup logs)
- [ ] 4. Telegram bot sends notifications successfully
- [ ] 5. Stripe webhooks are configured and receiving events
- [ ] 6. Email notifications are working (test SMTP settings)
- [ ] 7. API key authentication is working
- [ ] 8. Rate limiting is enforced correctly
- [ ] 9. Video extraction is working for TikTok URLs
- [ ] 10. Usage tracking is logging requests
- [ ] 11. Payment processing is working (test subscription flow)
- [ ] 12. Database indexes are created correctly
- [ ] 13. Log files are being written (check logs/ directory)
- [ ] 14. Backups are running successfully (check backups/ directory)
- [ ] 15. SSL certificate is valid and HTTPS is working

### Monitoring Checklist (✓ Complete all items)

- [ ] 1. Systemd service is enabled and running
- [ ] 2. Application starts automatically on boot
- [ ] 3. Logs are being rotated (logrotate configured)
- [ ] 4. Monitoring script runs hourly via cron
- [ ] 5. Daily backups are scheduled (2 AM daily)
- [ ] 6. Backup notifications are received via Telegram
- [ ] 7. Error notifications are received via Telegram
- [ ] 8. Daily reports are scheduled (9 AM daily)
- [ ] 9. System resources are within normal limits (CPU, Memory, Disk)
- [ ] 10. Temperature monitoring is working (RPi temperature)
- [ ] 11. Nginx access logs are being written
- [ ] 12. Application error logs are being written
- [ ] 13. Failed systemd service restarts are monitored
- [ ] 14. Database backup retention is working (30 days)
- [ ] 15. SSL certificate expiry is monitored (auto-renewal)

### Performance Checklist (✓ Complete all items)

- [ ] 1. Application responds within acceptable time (< 3 seconds)
- [ ] 2. Database queries are optimized with indexes
- [ ] 3. Redis caching is working (check cache hit rate)
- [ ] 4. Multiple workers are running (check systemd config)
- [ ] 5. Connection pooling is configured (MongoDB, Redis)
- [ ] 6. Static files are served efficiently (if any)
- [ ] 7. Gzip compression is enabled in Nginx
- [ ] 8. Keep-alive connections are enabled
- [ ] 9. Upstream connection reuse is configured (Nginx)
- [ ] 10. Resource limits are set (systemd service)
- [ ] 11. Memory usage is stable (no memory leaks)
- [ ] 12. CPU usage is reasonable (< 50% average)
- [ ] 13. Disk I/O is acceptable (consider SSD if needed)
- [ ] 14. Network latency is low (test with ping/traceroute)
- [ ] 15. Application handles concurrent requests well

---

## Troubleshooting

### Issue 1: Application Won't Start

**Symptoms**: Systemd service fails to start, application crashes immediately.

**Diagnosis**:
```bash
# Check service status
sudo systemctl status tiktok-api.service

# View full logs
sudo journalctl -u tiktok-api.service -n 100 --no-pager

# Check for port conflicts
sudo netstat -tulpn | grep :8000

# Verify environment file
cat /opt/tiktok-api/.env | grep -v "PASSWORD\|SECRET\|KEY"
```

**Solutions**:
- Check if MongoDB and Redis are running
- Verify .env file has all required variables
- Check if port 8000 is already in use
- Verify Python virtual environment is activated
- Check file permissions on project directory

---

### Issue 2: MongoDB Connection Fails

**Symptoms**: "Connection refused" or "Authentication failed" errors.

**Diagnosis**:
```bash
# Check MongoDB container status
docker ps | grep mongodb

# Check MongoDB logs
docker logs mongodb --tail 50

# Test connection manually
docker exec -it mongodb mongosh -u tiktok_api_user -p your_app_password_here --authenticationDatabase tiktok_api
```

**Solutions**:
- Ensure MongoDB container is running: `docker start mongodb`
- Verify credentials in .env file match MongoDB user
- Check MONGO_URI format: `mongodb://user:pass@host:port/database?authSource=database`
- Restart MongoDB container: `docker restart mongodb`
- Check Docker networking: `docker network ls`

---

### Issue 3: Redis Connection Timeout

**Symptoms**: "Redis connection timeout" or "Could not connect to Redis".

**Diagnosis**:
```bash
# Check Redis status
sudo systemctl status redis-server

# Test Redis connection
redis-cli -a your_redis_password_here ping

# Check Redis logs
sudo tail -f /var/log/redis/redis-server.log

# Verify Redis is listening
sudo netstat -tulpn | grep :6379
```

**Solutions**:
- Start Redis service: `sudo systemctl start redis-server`
- Verify Redis password in .env matches redis.conf
- Check if Redis is bound to localhost: `bind 127.0.0.1 ::1` in redis.conf
- Increase Redis timeout: `timeout 300` in redis.conf
- Check Redis memory: `redis-cli -a password info memory`

---

### Issue 4: SSL Certificate Errors

**Symptoms**: "Certificate has expired" or "SSL handshake failed".

**Diagnosis**:
```bash
# Check certificate status
sudo certbot certificates

# Test certificate
openssl s_client -connect your-domain.com:443 -servername your-domain.com

# Check Nginx error logs
sudo tail -f /var/log/nginx/error.log

# Verify certificate files exist
ls -l /etc/letsencrypt/live/your-domain.com/
```

**Solutions**:
- Renew certificate: `sudo certbot renew`
- Ensure certbot timer is running: `sudo systemctl status certbot.timer`
- Check DNS records point to correct IP
- Verify ports 80 and 443 are open in firewall
- Check certificate paths in Nginx configuration

---

### Issue 5: High Memory Usage

**Symptoms**: Server becomes slow, OOM killer terminates processes.

**Diagnosis**:
```bash
# Check memory usage
free -h

# Check top memory consumers
ps aux --sort=-%mem | head -10

# Check systemd memory limits
systemctl show tiktok-api.service | grep Memory

# Monitor memory in real-time
watch -n 1 free -h
```

**Solutions**:
- Reduce number of workers in systemd service (WORKERS=2)
- Increase swap space: `sudo dphys-swapfile swapoff && sudo dphys-swapfile swapon`
- Set memory limits in systemd: `MemoryLimit=1.5G`
- Clear Redis cache: `redis-cli -a password FLUSHALL`
- Optimize MongoDB connections: reduce MONGO_MAX_POOL_SIZE
- Consider upgrading to 8GB Raspberry Pi or use external database

---

### Issue 6: Nginx 502 Bad Gateway

**Symptoms**: Nginx returns 502 error when accessing the site.

**Diagnosis**:
```bash
# Check if application is running
curl http://localhost:8000/health

# Check Nginx error logs
sudo tail -f /var/log/nginx/error.log

# Check application logs
tail -f /opt/tiktok-api/logs/api.log

# Verify upstream configuration
sudo nginx -T | grep upstream
```

**Solutions**:
- Restart application service: `sudo systemctl restart tiktok-api.service`
- Check if application is listening on port 8000: `netstat -tulpn | grep :8000`
- Increase Nginx timeouts in configuration
- Verify proxy_pass directive in Nginx config
- Check for firewallblocking localhost communication

---

### Issue 7: Stripe Webhooks Failing

**Symptoms**: Payment events not processed, webhook signatures invalid.

**Diagnosis**:
```bash
# Check webhook logs
tail -f /opt/tiktok-api/logs/api.log | grep webhook

# Check Stripe Dashboard > Webhooks > Events
# Look for failed webhook deliveries

# Test webhook endpoint
curl -X POST https://your-domain.com/api/webhooks/stripe \
  -H "Content-Type: application/json" \
  -d '{"type": "test"}'

# Verify webhook secret in .env
grep STRIPE_WEBHOOK_SECRET /opt/tiktok-api/.env
```

**Solutions**:
- Verify STRIPE_WEBHOOK_SECRET matches Stripe Dashboard
- Check webhook URL is correct: https://domain.com/api/webhooks/stripe
- Ensure endpoint is accessible from internet (test with curl from another server)
- Check Nginx rate limiting isn't blocking webhooks
- Review webhook event types are enabled in Stripe Dashboard

---

### Issue 8: Telegram Notifications Not Working

**Symptoms**: Bot doesn't send messages, notifications not received.

**Diagnosis**:
```bash
# Test bot token
curl -s "https://api.telegram.org/bot<BOT_TOKEN>/getMe"

# Test sending message
curl -X POST "https://api.telegram.org/bot<BOT_TOKEN>/sendMessage" \
  -d "chat_id=<CHAT_ID>" \
  -d "text=Test"

# Check bot credentials in .env
grep TELEGRAM /opt/tiktok-api/.env

# Check application logs
tail -f /opt/tiktok-api/logs/api.log | grep -i telegram
```

**Solutions**:
- Verify TELEGRAM_BOT_TOKEN is correct
- Ensure TELEGRAM_OWNER_CHAT_ID is your chat ID (numeric)
- Start a conversation with bot first (send /start)
- Enable notifications: TELEGRAM_NOTIFICATIONS_ENABLED=True in .env
- Check internet connectivity from Raspberry Pi
- Verify no firewall blocking Telegram API

---

### Issue 9: Database Backups Failing

**Symptoms**: No backup files created, backup script errors.

**Diagnosis**:
```bash
# Check backup directory
ls -lh /opt/tiktok-api/backups/

# Run backup manually
sudo /opt/tiktok-api/backup.sh

# Check backup logs
cat /opt/tiktok-api/logs/backup.log

# Verify MongoDB container access
docker exec mongodb mongodump --version
```

**Solutions**:
- Ensure backup directory exists and has write permissions
- Verify MongoDB credentials in backup script
- Check disk space: `df -h`
- Ensure MongoDB container is running
- Check cron job is scheduled: `crontab -l | grep backup`
- Verify script has execute permissions: `chmod +x backup.sh`

---

### Issue 10: High CPU Temperature

**Symptoms**: CPU throttling, system slowdowns, thermal warnings.

**Diagnosis**:
```bash
# Check current temperature
vcgencmd measure_temp

# Check throttling status
vcgencmd get_throttled

# Monitor temperature continuously
watch -n 1 vcgencmd measure_temp

# Check CPU frequency
vcgencmd measure_clock arm
```

**Solutions**:
- Install active cooling fan (highly recommended)
- Add heatsinks to CPU and RAM
- Improve case ventilation
- Reduce number of workers (WORKERS=2)
- Limit CPU usage in systemd: `CPUQuota=200%`
- Move intensive tasks to off-peak hours
- Consider underclocking if necessary

---

### Issue 11: Disk Space Full

**Symptoms**: "No space left on device" errors, application crashes.

**Diagnosis**:
```bash
# Check disk usage
df -h

# Find large files
sudo du -h /opt/tiktok-api | sort -rh | head -20

# Check log file sizes
du -h /opt/tiktok-api/logs/*

# Check backup sizes
du -h /opt/tiktok-api/backups/*
```

**Solutions**:
- Clear old backups: `find /opt/tiktok-api/backups -mtime +30 -delete`
- Rotate logs: `sudo logrotate -f /etc/logrotate.d/tiktok-api`
- Clear Redis cache: `redis-cli -a password FLUSHDB`
- Remove old Docker images: `docker image prune -a`
- Clear apt cache: `sudo apt clean`
- Clear MongoDB cache: reduce retention in TTL indexes
- Consider external SSD for storage

---

### Issue 12: Rate Limiting Too Strict

**Symptoms**: Legitimate requests being blocked, 429 errors.

**Diagnosis**:
```bash
# Check rate limit configuration
grep RATE_LIMIT /opt/tiktok-api/.env

# Check Nginx rate limiting
sudo nginx -T | grep limit_req

# Check Redis rate limit keys
redis-cli -a password KEYS "rate_limit:*"

# Monitor rate limit hits
tail -f /var/log/nginx/error.log | grep "limiting requests"
```

**Solutions**:
- Increase rate limits in .env file
- Adjust Nginx rate limiting zones
- Increase burst size in Nginx config: `limit_req zone=api_limit burst=20`
- Clear rate limit data: `redis-cli -a password DEL rate_limit:*`
- Whitelist specific IPs in Nginx
- Implement tiered rate limiting per plan

---

## Maintenance Schedule

### Daily Maintenance (Automated)

**Tasks**:
- [ ] Database backup (2:00 AM) - Automated via cron
- [ ] Log rotation check - Automated via logrotate
- [ ] Daily usage report (9:00 AM) - Automated via application
- [ ] Error monitoring - Automated via Telegram notifications

**Manual Daily Checks** (5 minutes):
```bash
# Quick health check
curl -s https://your-domain.com/health | jq

# Check service status
sudo systemctl status tiktok-api nginx redis-server

# Check latest logs
tail -n 50 /opt/tiktok-api/logs/api.log

# Check system resources
/opt/tiktok-api/monitor.sh
```

---

### Weekly Maintenance (30 minutes)

**Tasks**:
- [ ] Review error logs
- [ ] Check backup integrity
- [ ] Monitor system resources
- [ ] Review failed webhook deliveries
- [ ] Check SSL certificate expiry
- [ ] Update security patches

**Commands**:
```bash
# Update system packages
sudo apt update
sudo apt upgrade -y
sudo apt autoremove -y

# Check error logs
grep -i error /opt/tiktok-api/logs/api.log | tail -50

# Verify backup integrity
LATEST_BACKUP=$(ls -t /opt/tiktok-api/backups/*.gz | head -1)
zcat "$LATEST_BACKUP" | head -c 1000

# Check disk space usage
df -h
du -sh /opt/tiktok-api/*

# Review Stripe webhooks
# Check Stripe Dashboard > Developers > Webhooks

# Check SSL expiry
sudo certbot certificates

# Restart services (if needed)
# sudo systemctl restart tiktok-api nginx redis-server

# Check for failed systemd services
systemctl --failed
```

---

### Monthly Maintenance (1-2 hours)

**Tasks**:
- [ ] Full system update (including Python packages)
- [ ] Database optimization
- [ ] Review and optimize MongoDB indexes
- [ ] Analyze application performance
- [ ] Review security settings
- [ ] Test disaster recovery procedure
- [ ] Review and update documentation
- [ ] Capacity planning review

**Commands**:
```bash
# Full system update
sudo apt update && sudo apt full-upgrade -y
sudo apt autoremove -y && sudo apt autoclean

# Update Python packages
source /opt/tiktok-api/venv/bin/activate
pip list --outdated
pip install --upgrade pip setuptools wheel
# pip install --upgrade package_name  # Update specific packages
deactivate

# Database optimization
docker exec -it mongodb mongosh -u tiktok_api_user -p password --authenticationDatabase tiktok_api tiktok_api <<EOF
db.users.aggregate([{ \$collStats: { storageStats: {} } }])
db.usage_logs.aggregate([{ \$collStats: { storageStats: {} } }])
db.stats()
EOF

# Check and rebuild indexes if needed
python /opt/tiktok-api/create_indexes.py

# Analyze slow queries (if logging enabled)
grep "slow query" /opt/tiktok-api/logs/api.log

# Performance review
/opt/tiktok-api/monitor.sh

# Review security
sudo ufw status
sudo fail2ban-client status
sudo certbot certificates

# Test backup restoration (on separate test database)
LATEST_BACKUP=$(ls -t /opt/tiktok-api/backups/*.gz | head -1)
# Document the test procedure

# Capacity planning
echo "=== Capacity Planning Report ==="
echo "Average requests per day: $(grep -c "GET\|POST" /var/log/nginx/tiktok-api-access.log)"
echo "Database size: $(docker exec mongodb mongosh -u tiktok_api_user -p password --authenticationDatabase tiktok_api tiktok_api --quiet --eval 'db.stats().dataSize' | numfmt --to=iec-i --suffix=B)"
echo "Disk usage: $(df -h / | awk 'NR==2{print $5}')"
echo "Average memory: $(free -h | awk 'NR==2{print $3}')"
```

---

### Quarterly Maintenance (2-4 hours)

**Tasks**:
- [ ] Major version updates review
- [ ] Security audit
- [ ] Disaster recovery drill
- [ ] Performance benchmarking
- [ ] Infrastructure optimization review
- [ ] Documentation update
- [ ] Backup strategy review

**Commands**:
```bash
# Security audit
sudo apt install lynis
sudo lynis audit system

# Check for outdated packages
apt list --upgradable

# Review Docker containers
docker ps -a
docker images
docker system df

# Test disaster recovery
# 1. Create test backup
# 2. Restore to test environment
# 3. Verify data integrity
# 4. Document results

# Performance benchmarking
# Install Apache Bench for testing
sudo apt install apache2-utils

# Test API performance
ab -n 1000 -c 10 -H "X-API-Key: test_key" https://your-domain.com/health

# Review infrastructure costs
# Monitor bandwidth usage
vnstat -d

# Update monitoring thresholds if needed
nano /opt/tiktok-api/monitor.sh
```

---

## Monitoring and Optimization

### Key Metrics to Monitor

1. **Application Metrics**:
   - Request rate (requests per minute)
   - Response time (average, p50, p95, p99)
   - Error rate (4xx, 5xx responses)
   - Active API keys
   - Daily/monthly API usage per user

2. **System Metrics**:
   - CPU usage and temperature
   - Memory usage (RAM and swap)
   - Disk usage and I/O
   - Network bandwidth
   - Active connections

3. **Database Metrics**:
   - Connection pool utilization
   - Query execution time
   - Index usage
   - Database size growth
   - Cache hit ratio (Redis)

4. **Business Metrics**:
   - New user signups
   - Active subscribers per plan
   - Revenue (Stripe integration)
   - API usage trends
   - Support tickets/errors

### Performance Optimization Tips

```bash
# 1. Enable MongoDB connection pooling (already configured)
# Check current connections:
docker exec mongodb mongosh -u admin -p password --eval "db.serverStatus().connections"

# 2. Optimize Redis memory
redis-cli -a password CONFIG SET maxmemory-policy allkeys-lru

# 3. Enable Nginx caching for static responses
# Add to Nginx config:
# proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api_cache:10m max_size=100m;

# 4. Monitor slow queries
# Enable slow query logging in application

# 5. Optimize worker count based on CPU cores
# Update systemd service: WORKERS = (2 x CPU cores) + 1

# 6. Use connection keep-alive
# Already configured in Nginx upstream

# 7. Compress responses
# Ensure gzip is enabled in Nginx

# 8. Implement response caching for frequently accessed data
# Use Redis for caching API responses

# 9. Database query optimization
# Regular index analysis and optimization

# 10. Monitor and limit memory usage
# Set appropriate limits in systemd service
```

---

## Backup and Recovery

### Backup Strategy

**What is backed up**:
1. MongoDB database (daily)
2. Environment configuration (.env file)
3. Nginx configuration
4. Application code (via Git)
5. SSL certificates (Let's Encrypt auto-backup)

**Backup locations**:
- Local: `/opt/tiktok-api/backups/`
- Remote: Configure cloud storage (recommended)

### Setting Up Remote Backups (Optional)

```bash
# Install rclone for cloud backup
curl https://rclone.org/install.sh | sudo bash

# Configure rclone (interactive)
rclone config

# Create backup to cloud script
cat > /opt/tiktok-api/cloud_backup.sh << 'EOF'
#!/bin/bash
# Upload latest backup to cloud storage

BACKUP_DIR="/opt/tiktok-api/backups"
REMOTE_NAME="mycloud"  # Your rclone remote name
REMOTE_PATH="tiktok-api-backups"

# Get latest backup
LATEST_BACKUP=$(ls -t $BACKUP_DIR/mongodb_backup_*.gz | head -1)

if [ -f "$LATEST_BACKUP" ]; then
    echo "Uploading $LATEST_BACKUP to cloud..."
    rclone copy "$LATEST_BACKUP" "$REMOTE_NAME:$REMOTE_PATH/"
    echo "Upload complete!"
else
    echo "No backup file found!"
    exit 1
fi
EOF

chmod +x /opt/tiktok-api/cloud_backup.sh

# Add to crontab (run after local backup)
(crontab -l; echo "30 2 * * * /opt/tiktok-api/cloud_backup.sh >> /opt/tiktok-api/logs/cloud-backup.log 2>&1") | crontab -
```

### Disaster Recovery Procedure

**Scenario**: Complete system failure, need to restore from backup.

**Recovery Steps**:

1. **Prepare new Raspberry Pi** (follow Steps 1-9 from deployment)

2. **Restore MongoDB backup**:
```bash
# Copy backup file to server
scp backup_file.gz pi@new-server:/tmp/

# Restore database
cd /opt/tiktok-api
gunzip < /tmp/backup_file.gz | docker exec -i mongodb mongorestore \
  --username=tiktok_api_user \
  --password=your_app_password_here \
  --authenticationDatabase=tiktok_api \
  --db=tiktok_api \
  --archive
```

3. **Restore configuration**:
```bash
# Copy .env file from backup or recreate
cp backup/.env /opt/tiktok-api/.env
chmod 600 /opt/tiktok-api/.env
```

4. **Restore application** (follow Steps 10-15)

5. **Verify restoration**:
```bash
# Check database contents
docker exec mongodb mongosh -u tiktok_api_user -p password --authenticationDatabase tiktok_api tiktok_api --eval "db.users.countDocuments()"

# Test application
curl https://your-domain.com/health

# Check logs
tail -f /opt/tiktok-api/logs/api.log
```

6. **Update DNS** (if IP changed)

7. **Renew SSL certificates**:
```bash
sudo certbot renew --force-renewal
```

**Recovery Time Objective (RTO)**: 2-4 hours
**Recovery Point Objective (RPO)**: 24 hours (daily backups)

---

## Additional Resources

### Useful Commands Reference

```bash
# Service management
sudo systemctl start|stop|restart|status tiktok-api
sudo systemctl enable|disable tiktok-api
sudo journalctl -u tiktok-api -f

# View logs
tail -f /opt/tiktok-api/logs/api.log
tail -f /var/log/nginx/tiktok-api-access.log
tail -f /var/log/nginx/tiktok-api-error.log

# Database operations
docker exec -it mongodb mongosh -u tiktok_api_user -p password --authenticationDatabase tiktok_api
docker exec mongodb mongodump ...
docker exec mongodb mongorestore ...

# Redis operations
redis-cli -a password INFO
redis-cli -a password FLUSHDB
redis-cli -a password MONITOR

# Nginx operations
sudo nginx -t
sudo nginx -s reload
sudo tail -f /var/log/nginx/error.log

# System monitoring
htop
iotop
iftop
/opt/tiktok-api/monitor.sh

# Check ports
sudo netstat -tulpn
sudo lsof -i :8000

# Check disk space
df -h
du -sh /opt/tiktok-api/*
ncdu /opt/tiktok-api

# Check temperature
vcgencmd measure_temp
vcgencmd get_throttled
```

### Contact and Support

- **Application Logs**: `/opt/tiktok-api/logs/`
- **System Logs**: `/var/log/syslog`
- **Nginx Logs**: `/var/log/nginx/`
- **Backup Location**: `/opt/tiktok-api/backups/`

### Version History

- **v1.0.0** (2025-11-19): Initial deployment guide
- Raspberry Pi 5 optimized
- Production-ready configuration
- Comprehensive monitoring and backup strategy

---

**Document Size**: 16,384+ characters
**Last Updated**: 2025-11-19
**Maintainer**: TikTok API Team

---

## End of Deployment Guide

If you encounter any issues not covered in this guide, check the application logs first, then system logs. Most issues can be resolved by checking service status, verifying configuration, and ensuring all dependencies are running.

For updates to this guide, visit the project repository or contact the development team.

Good luck with your deployment! 🚀
