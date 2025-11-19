# 🎬 TikTok Video Intelligence API

Professional REST API for extracting TikTok videos and metadata. Built for developers, marketers, and businesses.

## ✨ Features

- **📹 Video Download**: Extract TikTok videos without watermark
- **📊 Rich Metadata**: Views, likes, comments, hashtags, music, and more
- **🌍 Country Detection**: Identify video origin (Premium feature)
- **⚡ Smart Caching**: Fast responses with Redis caching
- **🔒 Secure**: API key authentication with rate limiting
- **📈 Usage Tracking**: Detailed analytics and monitoring
- **🤖 Telegram Bot**: Real-time notifications and management
- **💰 Multiple Plans**: Free, Basic, Pro, and Business tiers

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/Bot-Rasperrypi.git
cd Bot-Rasperrypi

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your configuration

# Start MongoDB and Redis
sudo systemctl start mongodb redis

# Run the application
python -m app.main
```

### Docker Quick Start

```bash
docker-compose up -d
```

## 📖 API Usage

### Authentication

All API requests require an API key in the header:

```bash
curl -X POST "http://localhost:8000/api/v1/video/extract" \
  -H "X-API-Key: tk_your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.tiktok.com/@username/video/1234567890",
    "extract_metadata": true
  }'
```

### Response

```json
{
  "success": true,
  "video_url": "https://direct-download-link.com/video.mp4",
  "metadata": {
    "video_id": "1234567890",
    "title": "Amazing video title",
    "author": "Username",
    "views": 1000000,
    "likes": 50000,
    "comments": 1000,
    "hashtags": ["viral", "fyp"],
    "duration": 15
  },
  "cached": false,
  "requests_remaining": 950,
  "process_time_ms": 1234
}
```

## 📋 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | System health check |
| `/api/v1/video/extract` | POST | Extract video and metadata |
| `/api/v1/user/register` | POST | Register new user |
| `/api/v1/user/me` | GET | Get user info |
| `/api/v1/user/usage` | GET | Get usage statistics |

## 💎 Subscription Plans

| Plan | Price | Requests/Month | Rate Limit | Country Detection |
|------|-------|----------------|------------|-------------------|
| **Free** | $0 | 50 | 10/min | ❌ |
| **Basic** | $5 | 1,000 | 30/min | ❌ |
| **Pro** | $20 | 10,000 | 100/min | ✅ |
| **Business** | $100 | 100,000 | 500/min | ✅ |

## 🤖 Telegram Bot Commands

The owner can manage the API via Telegram:

- `/stats` - Get system statistics
- `/users` - List recent subscribers
- `/revenue` - View revenue metrics
- `/health` - Check server status
- `/block <email>` - Block a user
- `/unblock <email>` - Unblock a user

## 🛠️ Configuration

Key environment variables (see `.env.example`):

```env
# MongoDB
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=tiktok_api

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_OWNER_CHAT_ID=your_chat_id

# Stripe (optional)
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
```

## 📊 Monitoring

Access the health endpoint to monitor system status:

```bash
curl http://localhost:8000/health
```

## 📚 Documentation

- [API Documentation](API_DOCUMENTATION.md) - Complete API reference
- [Deployment Guide](DEPLOYMENT.md) - Production deployment instructions
- [Owner Guide](OWNER_GUIDE.md) - Management and operations guide

## 🔒 Security

- ✅ API key authentication
- ✅ Rate limiting per plan
- ✅ Input validation
- ✅ Secure secrets management
- ✅ HTTPS required (via Cloudflare)

## 🧪 Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html
```

## 📈 Performance

- Response time: < 2 seconds (95th percentile)
- Cache hit rate: > 30%
- Uptime target: 99.5%

## 🤝 Support

- **Email**: support@yourdomain.com
- **Telegram**: @your_support_bot
- **Documentation**: https://docs.yourdomain.com

## 📄 License

Copyright © 2024. All rights reserved.

## 🙏 Credits

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - Video extraction
- [MongoDB](https://www.mongodb.com/) - Database
- [Redis](https://redis.io/) - Caching
- [python-telegram-bot](https://python-telegram-bot.org/) - Telegram integration

---

**Made with ❤️ for developers**
