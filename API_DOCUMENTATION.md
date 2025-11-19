# 📚 TikTok Video Intelligence API - Complete Documentation

**Version:** 1.0.0
**Last Updated:** January 2025
**Base URL:** `https://api.yourdomain.com`

---

## 📖 Table of Contents

1. [Introduction](#introduction)
2. [Authentication](#authentication)
3. [Rate Limiting](#rate-limiting)
4. [Endpoints](#endpoints)
5. [Error Codes](#error-codes)
6. [Code Examples](#code-examples)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

---

## 1. Introduction

The TikTok Video Intelligence API provides developers with powerful tools to extract TikTok videos and comprehensive metadata. Our API is designed for:

- **Content Creators & Marketers**: Analyze TikTok content performance
- **Social Media Tools**: Build video downloaders and analytics platforms
- **Research & Analytics**: Study TikTok trends and user behavior
- **Automation**: Integrate TikTok data into your workflows

### Key Features

✨ **Video Extraction**: Download TikTok videos without watermarks
📊 **Rich Metadata**: Get views, likes, comments, hashtags, music details
🌍 **Country Detection**: Identify video origin (Premium plans)
⚡ **Fast & Reliable**: Response times < 2 seconds
🔒 **Secure**: HTTPS-only with API key authentication
📈 **Scalable**: Rate limits from 10/min to 500/min

### Base URL

```
https://api.yourdomain.com
```

**Important:** All requests must use HTTPS. HTTP requests will be automatically redirected.

---

## 2. Authentication

All API requests require authentication using an API key.

### Getting Your API Key

1. **Sign up** at https://rapidapi.com/yourusername/api/tiktok-video-intelligence
2. **Subscribe** to a plan (Free to get started)
3. **Copy your API key** from the dashboard

### Using Your API Key

Include your API key in the request header:

```http
X-API-Key: tk_your_api_key_here
```

**Example Request:**

```bash
curl -X POST "https://api.yourdomain.com/api/v1/video/extract" \
  -H "X-API-Key: tk_your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.tiktok.com/@user/video/123"}'
```

### Security Best Practices

🔒 **Never expose your API key** in client-side code
🔒 **Use environment variables** to store keys
🔒 **Rotate keys regularly** for production apps
🔒 **Monitor usage** to detect unauthorized access

---

## 3. Rate Limiting

Rate limits prevent abuse and ensure fair usage for all users.

### Rate Limits by Plan

| Plan | Requests/Month | Rate Limit | Country Detection |
|------|----------------|------------|-------------------|
| **Free** | 50 | 10/minute | ❌ No |
| **Basic** | 1,000 | 30/minute | ❌ No |
| **Pro** | 10,000 | 100/minute | ✅ Yes |
| **Business** | 100,000 | 500/minute | ✅ Yes |

### Rate Limit Headers

Every response includes rate limit information:

```http
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 28
X-RateLimit-Reset: 1704067200
```

### Handling Rate Limits

When you exceed the rate limit, you'll receive a `429 Too Many Requests` response:

```json
{
  "success": false,
  "error": "Rate limit exceeded",
  "detail": "Maximum 30 requests per minute for Basic plan",
  "retry_after": 45,
  "reset_at": "2024-01-01T10:01:00Z"
}
```

**Recommended approach:**

```python
import time

def make_request_with_retry(url, headers, data, max_retries=3):
    for attempt in range(max_retries):
        response = requests.post(url, headers=headers, json=data)

        if response.status_code == 429:
            retry_after = response.json().get('retry_after', 60)
            print(f"Rate limited. Waiting {retry_after} seconds...")
            time.sleep(retry_after)
            continue

        return response

    raise Exception("Max retries exceeded")
```

---

## 4. Endpoints

### 4.1 Extract TikTok Video

Extract video URL and metadata from a TikTok video link.

**Endpoint:** `POST /api/v1/video/extract`

**Request Headers:**

```http
X-API-Key: string (required)
Content-Type: application/json
```

**Request Body:**

```json
{
  "url": "string (required) - TikTok video URL",
  "extract_metadata": "boolean (optional, default: true)",
  "extract_country": "boolean (optional, default: false, Pro+ only)"
}
```

**Example Request:**

```bash
curl -X POST "https://api.yourdomain.com/api/v1/video/extract" \
  -H "X-API-Key: tk_your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.tiktok.com/@username/video/1234567890",
    "extract_metadata": true,
    "extract_country": false
  }'
```

**Success Response (200 OK):**

```json
{
  "success": true,
  "video_url": "https://download-url.com/video.mp4",
  "metadata": {
    "video_id": "1234567890",
    "title": "Amazing dance video! 🔥",
    "description": "Check out my new dance moves #fyp #viral",
    "author": {
      "username": "username",
      "nickname": "Display Name",
      "verified": true,
      "follower_count": 1000000,
      "avatar": "https://avatar-url.com/image.jpg"
    },
    "statistics": {
      "views": 1000000,
      "likes": 50000,
      "comments": 1000,
      "shares": 500,
      "saves": 2000
    },
    "music": {
      "title": "Original Sound",
      "author": "username",
      "duration": 15,
      "url": "https://music-url.com/sound.mp3"
    },
    "hashtags": ["fyp", "viral", "dance", "trending"],
    "mentions": ["@user1", "@user2"],
    "duration": 15,
    "resolution": "1080x1920",
    "thumbnail": "https://thumbnail-url.com/image.jpg",
    "created_at": "2024-01-15T10:30:00Z",
    "country": "US",
    "region": "California"
  },
  "cached": false,
  "requests_remaining": 949,
  "process_time_ms": 1234
}
```

**Error Responses:**

**400 Bad Request:**
```json
{
  "success": false,
  "error": "Invalid TikTok URL",
  "detail": "The URL format is incorrect. Expected format: https://www.tiktok.com/@username/video/id",
  "requests_remaining": 950
}
```

**401 Unauthorized:**
```json
{
  "success": false,
  "error": "Invalid API Key",
  "detail": "The API key provided is invalid or expired"
}
```

**403 Forbidden:**
```json
{
  "success": false,
  "error": "Country detection not available",
  "detail": "Country detection requires Pro or Business plan",
  "current_plan": "basic",
  "upgrade_url": "https://rapidapi.com/yourusername/api/tiktok-video-intelligence/pricing"
}
```

**404 Not Found:**
```json
{
  "success": false,
  "error": "Video not found",
  "detail": "The video may have been deleted or is private",
  "requests_remaining": 949
}
```

**429 Too Many Requests:**
```json
{
  "success": false,
  "error": "Rate limit exceeded",
  "detail": "Maximum 30 requests per minute for Basic plan",
  "retry_after": 45,
  "reset_at": "2024-01-01T10:01:00Z"
}
```

**500 Internal Server Error:**
```json
{
  "success": false,
  "error": "Internal server error",
  "detail": "An unexpected error occurred. Please try again or contact support.",
  "request_id": "req_abc123xyz"
}
```

---

### 4.2 Get User Information

Get information about your account and current usage.

**Endpoint:** `GET /api/v1/user/me`

**Request Headers:**

```http
X-API-Key: string (required)
```

**Example Request:**

```bash
curl -X GET "https://api.yourdomain.com/api/v1/user/me" \
  -H "X-API-Key: tk_your_api_key_here"
```

**Success Response (200 OK):**

```json
{
  "email": "user@example.com",
  "plan": "pro",
  "status": "active",
  "requests_used": 500,
  "requests_limit": 10000,
  "requests_remaining": 9500,
  "usage_percent": 5.0,
  "rate_limit": "100 per minute",
  "features": {
    "video_extraction": true,
    "metadata_extraction": true,
    "country_detection": true,
    "priority_support": true
  },
  "billing": {
    "current_period_start": "2024-01-01T00:00:00Z",
    "current_period_end": "2024-02-01T00:00:00Z",
    "next_billing_date": "2024-02-01T00:00:00Z"
  },
  "created_at": "2024-01-01T00:00:00Z",
  "last_request_at": "2024-01-15T10:30:00Z"
}
```

---

### 4.3 Get Usage Statistics

Get detailed usage statistics for your account.

**Endpoint:** `GET /api/v1/user/usage`

**Request Headers:**

```http
X-API-Key: string (required)
```

**Query Parameters:**

- `period` (optional): `today`, `week`, `month`, `all` (default: `month`)

**Example Request:**

```bash
curl -X GET "https://api.yourdomain.com/api/v1/user/usage?period=week" \
  -H "X-API-Key: tk_your_api_key_here"
```

**Success Response (200 OK):**

```json
{
  "period": "week",
  "total_requests": 150,
  "successful_requests": 145,
  "failed_requests": 5,
  "cached_requests": 30,
  "cache_hit_rate": 20.0,
  "average_response_time_ms": 1234,
  "requests_by_day": [
    {"date": "2024-01-08", "count": 20},
    {"date": "2024-01-09", "count": 25},
    {"date": "2024-01-10", "count": 30},
    {"date": "2024-01-11", "count": 22},
    {"date": "2024-01-12", "count": 18},
    {"date": "2024-01-13", "count": 15},
    {"date": "2024-01-14", "count": 20}
  ],
  "top_videos": [
    {
      "video_id": "1234567890",
      "requests": 5,
      "last_requested": "2024-01-14T10:30:00Z"
    }
  ]
}
```

---

### 4.4 Health Check

Check API health status (no authentication required).

**Endpoint:** `GET /health`

**Example Request:**

```bash
curl -X GET "https://api.yourdomain.com/health"
```

**Success Response (200 OK):**

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime": 99.8,
  "services": {
    "mongodb": "healthy",
    "redis": "healthy",
    "tiktok_api": "operational"
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

## 5. Error Codes Reference

Complete reference of all possible error codes.

| HTTP Code | Error | Description | Solution |
|-----------|-------|-------------|----------|
| **400** | Invalid URL | TikTok URL format incorrect | Use format: `https://www.tiktok.com/@user/video/id` |
| **400** | Missing parameter | Required parameter not provided | Check request body for required fields |
| **400** | Invalid parameter | Parameter value is invalid | Verify parameter types and formats |
| **401** | Unauthorized | API key missing or invalid | Include valid `X-API-Key` header |
| **401** | Expired API key | API key has expired | Generate new API key from dashboard |
| **403** | Forbidden | Feature not available in current plan | Upgrade to Pro or Business plan |
| **403** | Account suspended | Account has been suspended | Contact support@yourdomain.com |
| **404** | Video not found | Video doesn't exist or is private | Verify video URL is accessible |
| **404** | Endpoint not found | API endpoint doesn't exist | Check endpoint URL and method |
| **429** | Rate limit exceeded | Too many requests | Wait and retry after `retry_after` seconds |
| **500** | Internal server error | Unexpected server error | Try again or contact support |
| **503** | Service unavailable | API temporarily unavailable | Check status page or try again later |

---

## 6. Code Examples

Complete, working code examples in multiple languages.

### 6.1 Python Example

```python
import requests
import json
import time

class TikTokAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.yourdomain.com"
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }

    def extract_video(self, tiktok_url, extract_metadata=True, extract_country=False):
        """
        Extract TikTok video and metadata

        Args:
            tiktok_url: Full TikTok video URL
            extract_metadata: Whether to extract metadata (default: True)
            extract_country: Whether to extract country (Pro+ only, default: False)

        Returns:
            dict: Response data or None if failed
        """
        endpoint = f"{self.base_url}/api/v1/video/extract"

        payload = {
            "url": tiktok_url,
            "extract_metadata": extract_metadata,
            "extract_country": extract_country
        }

        try:
            response = requests.post(endpoint, headers=self.headers, json=payload)

            # Handle rate limiting with retry
            if response.status_code == 429:
                retry_after = response.json().get('retry_after', 60)
                print(f"⚠️  Rate limited. Waiting {retry_after} seconds...")
                time.sleep(retry_after)
                return self.extract_video(tiktok_url, extract_metadata, extract_country)

            if response.status_code == 200:
                data = response.json()
                print("✅ Success!")
                print(f"📹 Video URL: {data['video_url']}")

                if 'metadata' in data:
                    meta = data['metadata']
                    print(f"👤 Author: @{meta['author']['username']}")
                    print(f"👀 Views: {meta['statistics']['views']:,}")
                    print(f"❤️  Likes: {meta['statistics']['likes']:,}")
                    print(f"💬 Comments: {meta['statistics']['comments']:,}")

                print(f"📊 Requests remaining: {data['requests_remaining']}")
                return data
            else:
                error_data = response.json()
                print(f"❌ Error {response.status_code}: {error_data.get('error', 'Unknown error')}")
                print(f"📝 Detail: {error_data.get('detail', 'No details')}")
                return None

        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {str(e)}")
            return None
        except json.JSONDecodeError:
            print("❌ Failed to parse response")
            return None

    def get_account_info(self):
        """Get account information and usage"""
        endpoint = f"{self.base_url}/api/v1/user/me"

        try:
            response = requests.get(endpoint, headers=self.headers)

            if response.status_code == 200:
                data = response.json()
                print("📊 Account Information:")
                print(f"📧 Email: {data['email']}")
                print(f"📦 Plan: {data['plan'].upper()}")
                print(f"📈 Usage: {data['requests_used']}/{data['requests_limit']} ({data['usage_percent']:.1f}%)")
                print(f"⏱️  Rate limit: {data['rate_limit']}")
                return data
            else:
                print(f"❌ Error: {response.status_code}")
                return None

        except Exception as e:
            print(f"❌ Failed: {str(e)}")
            return None

    def get_usage_stats(self, period='week'):
        """Get usage statistics"""
        endpoint = f"{self.base_url}/api/v1/user/usage"
        params = {"period": period}

        try:
            response = requests.get(endpoint, headers=self.headers, params=params)

            if response.status_code == 200:
                data = response.json()
                print(f"📊 Usage Statistics ({period}):")
                print(f"✅ Successful: {data['successful_requests']}")
                print(f"❌ Failed: {data['failed_requests']}")
                print(f"⚡ Cached: {data['cached_requests']} ({data['cache_hit_rate']:.1f}%)")
                print(f"⏱️  Avg response time: {data['average_response_time_ms']}ms")
                return data
            else:
                print(f"❌ Error: {response.status_code}")
                return None

        except Exception as e:
            print(f"❌ Failed: {str(e)}")
            return None


# Usage Example
if __name__ == "__main__":
    # Initialize API client
    api_key = "tk_your_api_key_here"
    client = TikTokAPI(api_key)

    # Extract video
    video_url = "https://www.tiktok.com/@username/video/1234567890"
    result = client.extract_video(video_url)

    if result:
        # Download video (optional)
        video_download_url = result['video_url']
        print(f"\n💾 Download video: {video_download_url}")

        # You can now download the video using requests
        # video_response = requests.get(video_download_url)
        # with open('tiktok_video.mp4', 'wb') as f:
        #     f.write(video_response.content)

    # Get account info
    print("\n" + "="*50)
    client.get_account_info()

    # Get usage stats
    print("\n" + "="*50)
    client.get_usage_stats(period='week')
```

---

### 6.2 JavaScript (Node.js) Example

```javascript
const axios = require('axios');

class TikTokAPI {
    constructor(apiKey) {
        this.apiKey = apiKey;
        this.baseUrl = 'https://api.yourdomain.com';
        this.headers = {
            'X-API-Key': apiKey,
            'Content-Type': 'application/json'
        };
    }

    /**
     * Extract TikTok video and metadata
     * @param {string} tiktokUrl - Full TikTok video URL
     * @param {boolean} extractMetadata - Whether to extract metadata
     * @param {boolean} extractCountry - Whether to extract country (Pro+ only)
     * @returns {Promise<object|null>} Response data or null if failed
     */
    async extractVideo(tiktokUrl, extractMetadata = true, extractCountry = false) {
        const endpoint = `${this.baseUrl}/api/v1/video/extract`;

        const payload = {
            url: tiktokUrl,
            extract_metadata: extractMetadata,
            extract_country: extractCountry
        };

        try {
            const response = await axios.post(endpoint, payload, { headers: this.headers });

            if (response.status === 200) {
                const data = response.data;
                console.log('✅ Success!');
                console.log(`📹 Video URL: ${data.video_url}`);

                if (data.metadata) {
                    const meta = data.metadata;
                    console.log(`👤 Author: @${meta.author.username}`);
                    console.log(`👀 Views: ${meta.statistics.views.toLocaleString()}`);
                    console.log(`❤️  Likes: ${meta.statistics.likes.toLocaleString()}`);
                    console.log(`💬 Comments: ${meta.statistics.comments.toLocaleString()}`);
                }

                console.log(`📊 Requests remaining: ${data.requests_remaining}`);
                return data;
            }
        } catch (error) {
            if (error.response) {
                // Handle rate limiting
                if (error.response.status === 429) {
                    const retryAfter = error.response.data.retry_after || 60;
                    console.log(`⚠️  Rate limited. Waiting ${retryAfter} seconds...`);
                    await new Promise(resolve => setTimeout(resolve, retryAfter * 1000));
                    return this.extractVideo(tiktokUrl, extractMetadata, extractCountry);
                }

                console.error(`❌ Error ${error.response.status}: ${error.response.data.error}`);
                console.error(`📝 Detail: ${error.response.data.detail}`);
            } else {
                console.error(`❌ Request failed: ${error.message}`);
            }
            return null;
        }
    }

    /**
     * Get account information and usage
     * @returns {Promise<object|null>} Account data or null if failed
     */
    async getAccountInfo() {
        const endpoint = `${this.baseUrl}/api/v1/user/me`;

        try {
            const response = await axios.get(endpoint, { headers: this.headers });

            if (response.status === 200) {
                const data = response.data;
                console.log('📊 Account Information:');
                console.log(`📧 Email: ${data.email}`);
                console.log(`📦 Plan: ${data.plan.toUpperCase()}`);
                console.log(`📈 Usage: ${data.requests_used}/${data.requests_limit} (${data.usage_percent.toFixed(1)}%)`);
                console.log(`⏱️  Rate limit: ${data.rate_limit}`);
                return data;
            }
        } catch (error) {
            if (error.response) {
                console.error(`❌ Error: ${error.response.status}`);
            } else {
                console.error(`❌ Failed: ${error.message}`);
            }
            return null;
        }
    }

    /**
     * Get usage statistics
     * @param {string} period - 'today', 'week', 'month', or 'all'
     * @returns {Promise<object|null>} Usage stats or null if failed
     */
    async getUsageStats(period = 'week') {
        const endpoint = `${this.baseUrl}/api/v1/user/usage`;

        try {
            const response = await axios.get(endpoint, {
                headers: this.headers,
                params: { period }
            });

            if (response.status === 200) {
                const data = response.data;
                console.log(`📊 Usage Statistics (${period}):`);
                console.log(`✅ Successful: ${data.successful_requests}`);
                console.log(`❌ Failed: ${data.failed_requests}`);
                console.log(`⚡ Cached: ${data.cached_requests} (${data.cache_hit_rate.toFixed(1)}%)`);
                console.log(`⏱️  Avg response time: ${data.average_response_time_ms}ms`);
                return data;
            }
        } catch (error) {
            if (error.response) {
                console.error(`❌ Error: ${error.response.status}`);
            } else {
                console.error(`❌ Failed: ${error.message}`);
            }
            return null;
        }
    }
}

// Usage Example
(async () => {
    // Initialize API client
    const apiKey = 'tk_your_api_key_here';
    const client = new TikTokAPI(apiKey);

    // Extract video
    const videoUrl = 'https://www.tiktok.com/@username/video/1234567890';
    const result = await client.extractVideo(videoUrl);

    if (result) {
        console.log(`\n💾 Download video: ${result.video_url}`);
    }

    // Get account info
    console.log('\n' + '='.repeat(50));
    await client.getAccountInfo();

    // Get usage stats
    console.log('\n' + '='.repeat(50));
    await client.getUsageStats('week');
})();
```

---

### 6.3 PHP Example

```php
<?php

class TikTokAPI {
    private $apiKey;
    private $baseUrl;
    private $headers;

    public function __construct($apiKey) {
        $this->apiKey = $apiKey;
        $this->baseUrl = 'https://api.yourdomain.com';
        $this->headers = [
            'X-API-Key: ' . $apiKey,
            'Content-Type: application/json'
        ];
    }

    /**
     * Extract TikTok video and metadata
     *
     * @param string $tiktokUrl Full TikTok video URL
     * @param bool $extractMetadata Whether to extract metadata
     * @param bool $extractCountry Whether to extract country (Pro+ only)
     * @return array|null Response data or null if failed
     */
    public function extractVideo($tiktokUrl, $extractMetadata = true, $extractCountry = false) {
        $endpoint = $this->baseUrl . '/api/v1/video/extract';

        $payload = [
            'url' => $tiktokUrl,
            'extract_metadata' => $extractMetadata,
            'extract_country' => $extractCountry
        ];

        $ch = curl_init($endpoint);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($payload));
        curl_setopt($ch, CURLOPT_HTTPHEADER, $this->headers);

        $response = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);

        if ($httpCode === 200) {
            $data = json_decode($response, true);
            echo "✅ Success!\n";
            echo "📹 Video URL: " . $data['video_url'] . "\n";

            if (isset($data['metadata'])) {
                $meta = $data['metadata'];
                echo "👤 Author: @" . $meta['author']['username'] . "\n";
                echo "👀 Views: " . number_format($meta['statistics']['views']) . "\n";
                echo "❤️  Likes: " . number_format($meta['statistics']['likes']) . "\n";
                echo "💬 Comments: " . number_format($meta['statistics']['comments']) . "\n";
            }

            echo "📊 Requests remaining: " . $data['requests_remaining'] . "\n";
            return $data;
        } elseif ($httpCode === 429) {
            $data = json_decode($response, true);
            $retryAfter = $data['retry_after'] ?? 60;
            echo "⚠️  Rate limited. Waiting $retryAfter seconds...\n";
            sleep($retryAfter);
            return $this->extractVideo($tiktokUrl, $extractMetadata, $extractCountry);
        } else {
            $data = json_decode($response, true);
            echo "❌ Error $httpCode: " . ($data['error'] ?? 'Unknown error') . "\n";
            echo "📝 Detail: " . ($data['detail'] ?? 'No details') . "\n";
            return null;
        }
    }

    /**
     * Get account information and usage
     *
     * @return array|null Account data or null if failed
     */
    public function getAccountInfo() {
        $endpoint = $this->baseUrl . '/api/v1/user/me';

        $ch = curl_init($endpoint);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_HTTPHEADER, $this->headers);

        $response = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);

        if ($httpCode === 200) {
            $data = json_decode($response, true);
            echo "📊 Account Information:\n";
            echo "📧 Email: " . $data['email'] . "\n";
            echo "📦 Plan: " . strtoupper($data['plan']) . "\n";
            echo "📈 Usage: {$data['requests_used']}/{$data['requests_limit']} ({$data['usage_percent']}%)\n";
            echo "⏱️  Rate limit: " . $data['rate_limit'] . "\n";
            return $data;
        } else {
            echo "❌ Error: $httpCode\n";
            return null;
        }
    }

    /**
     * Get usage statistics
     *
     * @param string $period 'today', 'week', 'month', or 'all'
     * @return array|null Usage stats or null if failed
     */
    public function getUsageStats($period = 'week') {
        $endpoint = $this->baseUrl . '/api/v1/user/usage?period=' . $period;

        $ch = curl_init($endpoint);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_HTTPHEADER, $this->headers);

        $response = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);

        if ($httpCode === 200) {
            $data = json_decode($response, true);
            echo "📊 Usage Statistics ($period):\n";
            echo "✅ Successful: " . $data['successful_requests'] . "\n";
            echo "❌ Failed: " . $data['failed_requests'] . "\n";
            echo "⚡ Cached: {$data['cached_requests']} ({$data['cache_hit_rate']}%)\n";
            echo "⏱️  Avg response time: {$data['average_response_time_ms']}ms\n";
            return $data;
        } else {
            echo "❌ Error: $httpCode\n";
            return null;
        }
    }
}

// Usage Example
$apiKey = 'tk_your_api_key_here';
$client = new TikTokAPI($apiKey);

// Extract video
$videoUrl = 'https://www.tiktok.com/@username/video/1234567890';
$result = $client->extractVideo($videoUrl);

if ($result) {
    echo "\n💾 Download video: " . $result['video_url'] . "\n";
}

// Get account info
echo "\n" . str_repeat('=', 50) . "\n";
$client->getAccountInfo();

// Get usage stats
echo "\n" . str_repeat('=', 50) . "\n";
$client->getUsageStats('week');

?>
```

---

### 6.4 cURL Example

```bash
#!/bin/bash

# Configuration
API_KEY="tk_your_api_key_here"
BASE_URL="https://api.yourdomain.com"

# Extract video
echo "📹 Extracting TikTok video..."
curl -X POST "$BASE_URL/api/v1/video/extract" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.tiktok.com/@username/video/1234567890",
    "extract_metadata": true,
    "extract_country": false
  }' \
  | python -m json.tool

echo -e "\n$(printf '=%.0s' {1..50})\n"

# Get account info
echo "📊 Getting account information..."
curl -X GET "$BASE_URL/api/v1/user/me" \
  -H "X-API-Key: $API_KEY" \
  | python -m json.tool

echo -e "\n$(printf '=%.0s' {1..50})\n"

# Get usage stats
echo "📈 Getting usage statistics..."
curl -X GET "$BASE_URL/api/v1/user/usage?period=week" \
  -H "X-API-Key: $API_KEY" \
  | python -m json.tool
```

---

## 7. Best Practices

### 7.1 Error Handling

Always implement proper error handling:

```python
try:
    response = client.extract_video(url)
    if response:
        # Process success
        pass
    else:
        # Handle failure
        pass
except Exception as e:
    # Log error and notify monitoring system
    logger.error(f"API request failed: {str(e)}")
```

### 7.2 Rate Limiting Strategy

Implement exponential backoff for rate limiting:

```python
import time

def make_request_with_backoff(func, *args, max_retries=5):
    for i in range(max_retries):
        try:
            return func(*args)
        except RateLimitError as e:
            if i == max_retries - 1:
                raise
            wait_time = min(2 ** i, 60)  # Max 60 seconds
            time.sleep(wait_time)
```

### 7.3 Caching

Cache responses to reduce API calls:

```python
import hashlib
import pickle
from datetime import datetime, timedelta

class ResponseCache:
    def __init__(self, ttl=3600):
        self.cache = {}
        self.ttl = ttl

    def get(self, url):
        key = hashlib.md5(url.encode()).hexdigest()
        if key in self.cache:
            data, timestamp = self.cache[key]
            if datetime.now() - timestamp < timedelta(seconds=self.ttl):
                return data
        return None

    def set(self, url, data):
        key = hashlib.md5(url.encode()).hexdigest()
        self.cache[key] = (data, datetime.now())
```

### 7.4 Security

- ✅ **Never expose API keys** in client-side code
- ✅ **Use environment variables** for API keys
- ✅ **Implement IP whitelisting** for production
- ✅ **Rotate API keys** regularly
- ✅ **Monitor usage** for anomalies

### 7.5 Performance

- ✅ Use connection pooling for multiple requests
- ✅ Implement request queuing for bulk operations
- ✅ Cache frequently accessed videos
- ✅ Use async/await for concurrent requests

---

## 8. Troubleshooting

### Problem: "Invalid API Key"

**Cause:** API key is incorrect, expired, or missing

**Solution:**
1. Verify API key is correct (copy from dashboard)
2. Check that `X-API-Key` header is included
3. Ensure no extra spaces or characters in key
4. Generate new API key if expired

---

### Problem: "Rate limit exceeded"

**Cause:** Too many requests in short time

**Solution:**
1. Check `retry_after` value in response
2. Implement exponential backoff
3. Upgrade to higher plan for more requests
4. Distribute requests over time

---

### Problem: "Video not found"

**Cause:** Video doesn't exist, is private, or was deleted

**Solution:**
1. Verify URL is correct
2. Check if video is accessible in browser
3. Try different video URL
4. Contact support if persistent

---

### Problem: "Country detection not available"

**Cause:** Feature requires Pro or Business plan

**Solution:**
1. Upgrade to Pro plan ($20/month)
2. Remove `extract_country: true` from request
3. Contact sales for Enterprise plan

---

### Problem: Slow response times

**Cause:** Network issues, API load, or video size

**Solution:**
1. Check your internet connection
2. Try during off-peak hours
3. Implement caching for repeated requests
4. Contact support if consistent

---

## Support & Resources

### Documentation
- **API Docs:** https://docs.yourdomain.com
- **Getting Started:** https://docs.yourdomain.com/quickstart
- **FAQ:** https://docs.yourdomain.com/faq

### Support
- **Email:** support@yourdomain.com
- **Response time:** < 24 hours
- **Priority support:** Pro & Business plans

### Community
- **Discord:** https://discord.gg/yourdiscord
- **GitHub:** https://github.com/yourusername/tiktok-api-examples

### Updates
- **Changelog:** https://docs.yourdomain.com/changelog
- **Status Page:** https://status.yourdomain.com

---

**Last Updated:** January 2025
**API Version:** 1.0.0

---

*Built with ❤️ for developers*
