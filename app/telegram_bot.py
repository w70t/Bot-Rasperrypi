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
• /block <email> - حظر مستخدم
• /unblock <email> - رفع الحظر
• /help - قائمة الأوامر

✨ الإشعارات التلقائية مفعّلة
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


# Singleton instance
telegram_bot = TelegramBotManager()
