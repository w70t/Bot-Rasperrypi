"""
Telegram Bot for Owner Management
Provides notifications and management commands for the API owner
"""

import asyncio
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from app.config import get_settings
from app.database import Collections
from app.services.auth_service import auth_service
from app.services.usage_service import usage_service

settings = get_settings()
logger = logging.getLogger(__name__)


class TelegramBotManager:
    """
    Telegram Bot Manager for API Owner
    """

    def __init__(self):
        self.application = None
        self.owner_chat_id = settings.TELEGRAM_OWNER_CHAT_ID

    async def start(self):
        """Start the Telegram bot"""
        if not settings.TELEGRAM_BOT_TOKEN:
            logger.warning("Telegram bot token not configured, skipping bot")
            return

        try:
            self.application = Application.builder().token(
                settings.TELEGRAM_BOT_TOKEN
            ).build()

            # Add command handlers
            self.application.add_handler(CommandHandler("start", self.cmd_start))
            self.application.add_handler(CommandHandler("stats", self.cmd_stats))
            self.application.add_handler(CommandHandler("users", self.cmd_users))
            self.application.add_handler(CommandHandler("revenue", self.cmd_revenue))
            self.application.add_handler(CommandHandler("health", self.cmd_health))
            self.application.add_handler(CommandHandler("logs", self.cmd_logs))
            self.application.add_handler(CommandHandler("backup", self.cmd_backup))
            self.application.add_handler(CommandHandler("adduser", self.cmd_adduser))
            self.application.add_handler(CommandHandler("upgrade", self.cmd_upgrade))
            self.application.add_handler(CommandHandler("search", self.cmd_search))
            self.application.add_handler(CommandHandler("block", self.cmd_block))
            self.application.add_handler(CommandHandler("unblock", self.cmd_unblock))
            self.application.add_handler(CommandHandler("help", self.cmd_help))

            # Start polling
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()

            logger.info("✓ Telegram bot started successfully")

        except Exception as e:
            logger.error(f"Failed to start Telegram bot: {str(e)}", exc_info=True)

    async def stop(self):
        """Stop the Telegram bot"""
        if self.application:
            try:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
                logger.info("✓ Telegram bot stopped")
            except Exception as e:
                logger.error(f"Error stopping bot: {str(e)}")

    def _is_owner(self, update: Update) -> bool:
        """Check if message is from owner"""
        if not self.owner_chat_id:
            return False

        return str(update.effective_chat.id) == str(self.owner_chat_id)

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        if not self._is_owner(update):
            await update.message.reply_text("⛔ Unauthorized")
            return

        welcome_msg = """
👋 مرحباً! أنا بوت مراقبة TikTok API

🎯 الأوامر المتاحة:
• /stats - إحصائيات عامة
• /users - قائمة المشتركين
• /revenue - تقرير الأرباح
• /health - حالة السيرفر
• /logs - آخر الأخطاء
• /backup - نسخ احتياطي فوري
• /adduser <email> <plan> - إضافة مشترك
• /upgrade <email> <plan> - ترقية باقة
• /search <email> - البحث عن مستخدم
• /block <email> - حظر مستخدم
• /unblock <email> - رفع الحظر
• /help - قائمة الأوامر

✨ الإشعارات التلقائية مفعّلة
📊 التقرير اليومي: 9:00 صباحاً
        """

        await update.message.reply_text(welcome_msg)

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        if not self._is_owner(update):
            return

        help_msg = """
📚 دليل الأوامر:

📊 /stats
احصل على إحصائيات سريعة:
- طلبات آخر ساعة
- مشتركين نشطين
- معدل الأداء

👥 /users
قائمة بآخر 5 مشتركين:
- البريد الإلكتروني
- الباقة
- الحالة

💰 /revenue
تقرير الأرباح:
- اليوم
- هذا الشهر
- النمو

⚡ /health
حالة السيرفر:
- MongoDB
- Redis
- استخدام الذاكرة
- المساحة المتاحة

🚫 /block email@example.com
حظر مستخدم من استخدام API

✅ /unblock email@example.com
رفع الحظر عن مستخدم
        """

        await update.message.reply_text(help_msg)

    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        if not self._is_owner(update):
            return

        try:
            # Get system stats
            stats = await usage_service.get_system_stats(days=1)

            # Get user counts
            total_users = await auth_service.get_user_count()
            active_users = stats.get("active_users", 0)

            # Get plan breakdown
            free_users = await auth_service.get_user_count(plan="free")
            basic_users = await auth_service.get_user_count(plan="basic")
            pro_users = await auth_service.get_user_count(plan="pro")
            business_users = await auth_service.get_user_count(plan="business")

            msg = f"""
📊 إحصائيات النظام

👥 المستخدمين:
• إجمالي: {total_users}
• نشط اليوم: {active_users}
• Free: {free_users}
• Basic: {basic_users}
• Pro: {pro_users}
• Business: {business_users}

📈 الطلبات (آخر 24 ساعة):
• إجمالي: {stats.get('total_requests', 0)}
• ناجح: {stats.get('successful_requests', 0)}
• فاشل: {stats.get('failed_requests', 0)}
• من الكاش: {stats.get('cached_requests', 0)}

⚡ الأداء:
• متوسط الاستجابة: {stats.get('avg_response_time', 0):.0f}ms
            """

            await update.message.reply_text(msg)

        except Exception as e:
            logger.error(f"Error in /stats: {str(e)}", exc_info=True)
            await update.message.reply_text(f"❌ خطأ: {str(e)}")

    async def cmd_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /users command"""
        if not self._is_owner(update):
            return

        try:
            # Get last 5 users
            users = await auth_service.get_all_users(limit=5)

            if not users:
                await update.message.reply_text("لا يوجد مستخدمين")
                return

            msg = "👥 آخر 5 مشتركين:\n\n"

            for i, user in enumerate(users, 1):
                status_emoji = "✅" if user.status == "active" else "❌"
                msg += f"{i}. {status_emoji} {user.email}\n"
                msg += f"   Bahقة: {user.plan}\n"
                msg += f"   الطلبات: {user.requests_used}/{user.requests_limit}\n\n"

            await update.message.reply_text(msg)

        except Exception as e:
            logger.error(f"Error in /users: {str(e)}", exc_info=True)
            await update.message.reply_text(f"❌ خطأ: {str(e)}")

    async def cmd_revenue(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /revenue command"""
        if not self._is_owner(update):
            return

        try:
            # Calculate MRR
            free_users = await auth_service.get_user_count(plan="free", status="active")
            basic_users = await auth_service.get_user_count(plan="basic", status="active")
            pro_users = await auth_service.get_user_count(plan="pro", status="active")
            business_users = await auth_service.get_user_count(plan="business", status="active")

            mrr = (
                basic_users * settings.PRICE_BASIC +
                pro_users * settings.PRICE_PRO +
                business_users * settings.PRICE_BUSINESS
            )

            arr = mrr * 12

            msg = f"""
💰 تقرير الأرباح

📊 الاشتراكات النشطة:
• Free: {free_users} (${0})
• Basic: {basic_users} (${basic_users * settings.PRICE_BASIC:.0f})
• Pro: {pro_users} (${pro_users * settings.PRICE_PRO:.0f})
• Business: {business_users} (${business_users * settings.PRICE_BUSINESS:.0f})

💵 الإيرادات:
• MRR: ${mrr:.2f}/شهر
• ARR: ${arr:.2f}/سنة

📈 متوسط الإيراد لكل مستخدم:
${mrr / max(basic_users + pro_users + business_users, 1):.2f}/شهر
            """

            await update.message.reply_text(msg)

        except Exception as e:
            logger.error(f"Error in /revenue: {str(e)}", exc_info=True)
            await update.message.reply_text(f"❌ خطأ: {str(e)}")

    async def cmd_health(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /health command"""
        if not self._is_owner(update):
            return

        try:
            from app.database import Database
            from app.services.cache_service import cache_service
            import psutil

            # Check services
            mongodb_healthy = await Database.check_health()
            redis_stats = await cache_service.get_stats()
            redis_healthy = redis_stats.get("connected", False)

            # System resources
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            mongodb_emoji = "✅" if mongodb_healthy else "❌"
            redis_emoji = "✅" if redis_healthy else "❌"

            msg = f"""
⚡ حالة السيرفر

🔧 الخدمات:
• MongoDB: {mongodb_emoji}
• Redis: {redis_emoji}

💻 الموارد:
• الذاكرة: {memory.percent:.1f}% مستخدمة
• المساحة: {disk.percent:.1f}% مستخدمة
• متاح: {disk.free / (1024**3):.1f} GB

⏱️ الوقت: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
            """

            await update.message.reply_text(msg)

        except Exception as e:
            logger.error(f"Error in /health: {str(e)}", exc_info=True)
            await update.message.reply_text(f"❌ خطأ: {str(e)}")

    async def cmd_block(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /block command"""
        if not self._is_owner(update):
            return

        if not context.args or len(context.args) < 1:
            await update.message.reply_text("❌ استخدام: /block email@example.com")
            return

        email = context.args[0]
        reason = " ".join(context.args[1:]) if len(context.args) > 1 else "Blocked by admin"

        try:
            success, error = await auth_service.block_user(email, reason)

            if success:
                await update.message.reply_text(f"✅ تم حظر: {email}")
            else:
                await update.message.reply_text(f"❌ فشل: {error}")

        except Exception as e:
            logger.error(f"Error in /block: {str(e)}", exc_info=True)
            await update.message.reply_text(f"❌ خطأ: {str(e)}")

    async def cmd_unblock(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /unblock command"""
        if not self._is_owner(update):
            return

        if not context.args or len(context.args) < 1:
            await update.message.reply_text("❌ استخدام: /unblock email@example.com")
            return

        email = context.args[0]

        try:
            success, error = await auth_service.unblock_user(email)

            if success:
                await update.message.reply_text(f"✅ تم رفع الحظر: {email}")
            else:
                await update.message.reply_text(f"❌ فشل: {error}")

        except Exception as e:
            logger.error(f"Error in /unblock: {str(e)}", exc_info=True)
            await update.message.reply_text(f"❌ خطأ: {str(e)}")

    async def cmd_logs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /logs command - Show last 10 errors"""
        if not self._is_owner(update):
            return

        try:
            import os
            from pathlib import Path

            error_log_path = Path(settings.ERROR_LOG_FILE_PATH)

            if not error_log_path.exists():
                await update.message.reply_text("📝 لا توجد أخطاء مسجلة")
                return

            # Read last 20 lines from error log
            with open(error_log_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                last_errors = lines[-20:] if len(lines) > 20 else lines

            if not last_errors:
                await update.message.reply_text("📝 لا توجد أخطاء مسجلة")
                return

            error_msg = "🔴 آخر الأخطاء:\n\n"
            error_msg += "".join(last_errors[-10:])  # Last 10 lines

            # Split if too long (Telegram limit is 4096 chars)
            if len(error_msg) > 4000:
                error_msg = error_msg[-4000:]
                error_msg = "..." + error_msg

            await update.message.reply_text(error_msg)

        except Exception as e:
            logger.error(f"Error in /logs: {str(e)}", exc_info=True)
            await update.message.reply_text(f"❌ خطأ: {str(e)}")

    async def cmd_backup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /backup command - Create immediate backup"""
        if not self._is_owner(update):
            return

        try:
            await update.message.reply_text("⏳ جاري إنشاء النسخة الاحتياطية...")

            from app.services.backup_service import backup_service
            backup_file = await backup_service.create_backup()

            if backup_file:
                # Send backup file
                with open(backup_file, 'rb') as f:
                    await update.message.reply_document(
                        document=f,
                        caption=f"✅ النسخة الاحتياطية جاهزة\n📅 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
                    )
            else:
                await update.message.reply_text("❌ فشل إنشاء النسخة الاحتياطية")

        except Exception as e:
            logger.error(f"Error in /backup: {str(e)}", exc_info=True)
            await update.message.reply_text(f"❌ خطأ: {str(e)}")

    async def cmd_adduser(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /adduser command - Add user manually"""
        if not self._is_owner(update):
            return

        if not context.args or len(context.args) < 2:
            await update.message.reply_text(
                "❌ استخدام: /adduser email@example.com <plan>\n"
                "Plans: free, basic, pro, business"
            )
            return

        email = context.args[0]
        plan = context.args[1].lower()

        if plan not in ["free", "basic", "pro", "business"]:
            await update.message.reply_text("❌ الباقة غير صحيحة. استخدم: free, basic, pro, business")
            return

        try:
            # Create user
            user = await auth_service.create_user(email=email, plan=plan)

            if user:
                await update.message.reply_text(
                    f"✅ تم إضافة المستخدم:\n"
                    f"📧 Email: {email}\n"
                    f"📦 Plan: {plan}\n"
                    f"🔑 API Key: {user.api_key}"
                )
            else:
                await update.message.reply_text("❌ فشل إضافة المستخدم")

        except Exception as e:
            logger.error(f"Error in /adduser: {str(e)}", exc_info=True)
            await update.message.reply_text(f"❌ خطأ: {str(e)}")

    async def cmd_upgrade(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /upgrade command - Upgrade user plan"""
        if not self._is_owner(update):
            return

        if not context.args or len(context.args) < 2:
            await update.message.reply_text(
                "❌ استخدام: /upgrade email@example.com <new_plan>\n"
                "Plans: basic, pro, business"
            )
            return

        email = context.args[0]
        new_plan = context.args[1].lower()

        if new_plan not in ["basic", "pro", "business"]:
            await update.message.reply_text("❌ الباقة غير صحيحة. استخدم: basic, pro, business")
            return

        try:
            success = await auth_service.update_user_plan(email, new_plan)

            if success:
                await update.message.reply_text(
                    f"✅ تم ترقية المستخدم:\n"
                    f"📧 Email: {email}\n"
                    f"🆙 New Plan: {new_plan}"
                )
            else:
                await update.message.reply_text("❌ فشل ترقية المستخدم (المستخدم غير موجود)")

        except Exception as e:
            logger.error(f"Error in /upgrade: {str(e)}", exc_info=True)
            await update.message.reply_text(f"❌ خطأ: {str(e)}")

    async def cmd_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /search command - Search for user"""
        if not self._is_owner(update):
            return

        if not context.args or len(context.args) < 1:
            await update.message.reply_text("❌ استخدام: /search email@example.com")
            return

        email = context.args[0]

        try:
            user = await auth_service.get_user_by_email(email)

            if not user:
                await update.message.reply_text(f"❌ المستخدم غير موجود: {email}")
                return

            status_emoji = "✅" if user.status == "active" else "❌"

            msg = f"""
👤 معلومات المستخدم:

📧 Email: {user.email}
{status_emoji} Status: {user.status}
📦 Plan: {user.plan}
🔑 API Key: {user.api_key[:20]}...

📊 الاستخدام:
• الطلبات: {user.requests_used}/{user.requests_limit}
• المتبقي: {user.requests_limit - user.requests_used}
• نسبة الاستخدام: {(user.requests_used/user.requests_limit*100):.1f}%

📅 التواريخ:
• التسجيل: {user.created_at.strftime('%Y-%m-%d')}
• آخر استخدام: {user.last_used_at.strftime('%Y-%m-%d') if user.last_used_at else 'لم يستخدم بعد'}
            """

            await update.message.reply_text(msg)

        except Exception as e:
            logger.error(f"Error in /search: {str(e)}", exc_info=True)
            await update.message.reply_text(f"❌ خطأ: {str(e)}")

    async def send_notification(self, message: str):
        """
        Send notification to owner

        Args:
            message: Notification message
        """
        if not self.application or not self.owner_chat_id:
            return

        try:
            await self.application.bot.send_message(
                chat_id=self.owner_chat_id,
                text=message
            )
        except Exception as e:
            logger.error(f"Failed to send notification: {str(e)}")

    # ==================== AUTO NOTIFICATIONS ====================

    async def notify_new_subscriber(self, user_email: str, plan: str, price: float):
        """
        Send notification when new user subscribes

        Args:
            user_email: User's email
            plan: Subscription plan
            price: Monthly price
        """
        if not settings.NOTIFY_NEW_SUBSCRIBER:
            return

        try:
            # Get total subscriber count
            total_users = await auth_service.get_user_count()

            # Calculate MRR
            basic_users = await auth_service.get_user_count(plan="basic", status="active")
            pro_users = await auth_service.get_user_count(plan="pro", status="active")
            business_users = await auth_service.get_user_count(plan="business", status="active")

            mrr = (
                basic_users * settings.PRICE_BASIC +
                pro_users * settings.PRICE_PRO +
                business_users * settings.PRICE_BUSINESS
            )

            msg = f"""
🎉 اشتراك جديد!

📧 Email: {user_email}
📦 Plan: {plan.upper()}
💰 Price: ${price}/month

📊 الإحصائيات:
• إجمالي المشتركين: {total_users}
• MRR الحالي: ${mrr:.2f}/month

⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
            """

            await self.send_notification(msg)

        except Exception as e:
            logger.error(f"Failed to send new subscriber notification: {str(e)}")

    async def notify_error(self, error_type: str, error_msg: str, traceback_str: str = None):
        """
        Send notification when technical error occurs

        Args:
            error_type: Type of error
            error_msg: Error message
            traceback_str: Stack trace (optional)
        """
        if not settings.NOTIFY_ERRORS:
            return

        try:
            from app.database import Database
            from app.services.cache_service import cache_service

            # Check system health
            mongodb_healthy = await Database.check_health()
            redis_stats = await cache_service.get_stats()
            redis_healthy = redis_stats.get("connected", False)

            msg = f"""
🔴 خطأ تقني!

❌ Type: {error_type}
📝 Message: {error_msg}

🔧 System Status:
• MongoDB: {"✅" if mongodb_healthy else "❌"}
• Redis: {"✅" if redis_healthy else "❌"}

⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
            """

            if traceback_str and len(traceback_str) < 500:
                msg += f"\n\n📋 Traceback:\n{traceback_str}"

            await self.send_notification(msg)

        except Exception as e:
            logger.error(f"Failed to send error notification: {str(e)}")

    async def notify_rate_limit_exceeded(self, user_email: str, plan: str, current_usage: int, limit: int):
        """
        Send notification when user exceeds rate limit

        Args:
            user_email: User's email
            plan: Current plan
            current_usage: Current usage count
            limit: Plan limit
        """
        try:
            usage_percent = (current_usage / limit * 100) if limit > 0 else 0

            msg = f"""
⚠️ تجاوز حد الطلبات

📧 User: {user_email}
📦 Plan: {plan.upper()}
📊 Usage: {current_usage}/{limit} ({usage_percent:.0f}%)

💡 توصية: اقترح عليهم الترقية للباقة الأعلى

⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
            """

            await self.send_notification(msg)

        except Exception as e:
            logger.error(f"Failed to send rate limit notification: {str(e)}")

    async def notify_milestone(self, milestone_type: str, value: int):
        """
        Send notification when reaching milestones

        Args:
            milestone_type: Type of milestone (users or revenue)
            value: Milestone value
        """
        if not settings.NOTIFY_MILESTONES:
            return

        try:
            if milestone_type == "users":
                emoji = "👥"
                text = f"{value} مشترك"
            elif milestone_type == "mrr":
                emoji = "💰"
                text = f"${value} MRR"
            else:
                return

            msg = f"""
🎯 إنجاز جديد!

{emoji} وصلت إلى: {text}

🎉 مبروك! استمر في التقدم!

⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
            """

            await self.send_notification(msg)

        except Exception as e:
            logger.error(f"Failed to send milestone notification: {str(e)}")

    async def send_daily_report(self):
        """
        Send automated daily report at 9:00 AM
        """
        if not settings.NOTIFY_DAILY_REPORT:
            return

        try:
            from app.database import Database
            from app.services.cache_service import cache_service
            import psutil

            # Get yesterday's stats
            stats = await usage_service.get_system_stats(days=1)

            # Get user counts
            total_users = await auth_service.get_user_count()
            active_users = stats.get("active_users", 0)

            # Get new users today
            from datetime import timedelta
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            new_users_today = await auth_service.get_user_count(created_after=today_start)

            # Calculate MRR
            basic_users = await auth_service.get_user_count(plan="basic", status="active")
            pro_users = await auth_service.get_user_count(plan="pro", status="active")
            business_users = await auth_service.get_user_count(plan="business", status="active")

            mrr = (
                basic_users * settings.PRICE_BASIC +
                pro_users * settings.PRICE_PRO +
                business_users * settings.PRICE_BUSINESS
            )

            arr = mrr * 12

            # System health
            mongodb_healthy = await Database.check_health()
            redis_stats = await cache_service.get_stats()
            redis_healthy = redis_stats.get("connected", False)

            # Get cache hit rate
            cache_hit_rate = redis_stats.get("hit_rate", 0)

            # System resources
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            msg = f"""
📊 التقرير اليومي - {datetime.utcnow().strftime('%Y-%m-%d')}

💰 الأرباح:
• MRR: ${mrr:.2f}/month
• ARR: ${arr:.2f}/year
• أمس: ${(mrr/30):.2f}

👥 المستخدمين:
• إجمالي: {total_users}
• نشط: {active_users}
• جديد اليوم: {new_users_today}
• Basic: {basic_users} | Pro: {pro_users} | Business: {business_users}

📈 الطلبات (آخر 24 ساعة):
• إجمالي: {stats.get('total_requests', 0)}
• ناجح: {stats.get('successful_requests', 0)}
• متوسط الوقت: {stats.get('avg_response_time', 0):.0f}ms

⚡ الأداء:
• Cache Hit Rate: {cache_hit_rate:.1f}%
• Error Rate: {stats.get('error_rate', 0):.1f}%
• Uptime: {stats.get('uptime', 'N/A')}

🔧 النظام:
• MongoDB: {"✅" if mongodb_healthy else "❌"}
• Redis: {"✅" if redis_healthy else "❌"}
• Memory: {memory.percent:.1f}% used
• Disk: {disk.percent:.1f}% used ({disk.free / (1024**3):.1f} GB free)

⏰ {datetime.utcnow().strftime('%H:%M:%S')} UTC
            """

            await self.send_notification(msg)

        except Exception as e:
            logger.error(f"Failed to send daily report: {str(e)}")

    async def schedule_daily_report(self):
        """
        Schedule daily report to be sent at configured time
        """
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger

        if not settings.NOTIFY_DAILY_REPORT:
            return

        try:
            # Parse time from settings (format: "HH:MM")
            hour, minute = map(int, settings.DAILY_REPORT_TIME.split(':'))

            scheduler = AsyncIOScheduler()
            scheduler.add_job(
                self.send_daily_report,
                trigger=CronTrigger(hour=hour, minute=minute),
                id='daily_report',
                replace_existing=True
            )
            scheduler.start()

            logger.info(f"✓ Daily report scheduled at {settings.DAILY_REPORT_TIME} UTC")

        except Exception as e:
            logger.error(f"Failed to schedule daily report: {str(e)}")


# Singleton instance
telegram_bot = TelegramBotManager()
