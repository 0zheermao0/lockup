import asyncio
import json
import random
import time
from typing import Optional, Dict, Any
from collections import defaultdict
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from asgiref.sync import sync_to_async
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from tasks.models import LockTask
from users.models import Notification
from tasks.utils import add_overtime_to_task
from store.models import Item, UserInventory
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class TelegramBotService:
    """Telegram Bot 核心服务类 - 生产级别安全"""

    def __init__(self):
        self.bot = None
        self.application = None

        # 安全功能：请求频率限制
        self.rate_limiter = defaultdict(list)  # user_id -> [timestamp, ...]
        self.max_requests_per_minute = getattr(settings, 'TELEGRAM_SECURITY', {}).get('MAX_REQUESTS_PER_MINUTE', 60)

        # 安全功能：IP白名单（如果配置）
        self.ip_whitelist = getattr(settings, 'TELEGRAM_SECURITY', {}).get('IP_WHITELIST', [])

        # 安全功能：允许的更新类型
        self.allowed_updates = getattr(settings, 'TELEGRAM_SECURITY', {}).get('ALLOWED_UPDATES', ['message', 'inline_query', 'callback_query'])

        self._setup_bot()

    def _setup_bot(self):
        """初始化 Bot"""
        # 检查Token是否正确配置
        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        if not token or token == 'YOUR_BOT_TOKEN_HERE' or len(token) < 40:
            logger.warning(f"Telegram Bot Token not configured or invalid. Token: {token[:20] if token else 'None'}...")
            return

        try:
            self.bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
            self.application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

            # 不在这里注册处理器，而是在确保初始化完成后注册
            # 延迟初始化：只在第一次使用时初始化
            self._initialized = False

            logger.info("Telegram Bot service configured successfully")
        except Exception as e:
            logger.error(f"Failed to setup Telegram Bot: {e}")
            self.bot = None
            self.application = None

    async def _ensure_initialized(self):
        """确保Bot和Application已经初始化"""
        if not self.bot or not self.application:
            logger.warning("Bot or Application not configured")
            return False

        # 如果已经初始化，直接返回
        if getattr(self, '_initialized', False):
            return True

        try:
            # 初始化 Bot
            if not getattr(self.bot, '_initialized', False):
                logger.info("Initializing Bot...")
                await self.bot.initialize()
                self.bot._initialized = True
                logger.info("Bot initialized successfully")

            # 初始化 Application
            if not getattr(self.application, '_initialized', False):
                logger.info("Initializing Application...")
                await self.application.initialize()
                self.application._initialized = True
                logger.info("Application initialized successfully")

            # 确保处理器已注册
            if not getattr(self, '_handlers_registered', False):
                logger.info("Registering handlers...")
                self._register_handlers()

            self._initialized = True
            logger.info("Telegram service fully initialized")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Telegram Bot: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    async def _safe_send_message(self, message_func, *args, **kwargs):
        """安全地发送Telegram消息，处理事件循环关闭等错误"""
        try:
            return await message_func(*args, **kwargs)
        except Exception as e:
            # 检查是否是事件循环关闭错误
            if "Event loop is closed" in str(e) or "RuntimeError" in str(e):
                logger.warning(f"Event loop error when sending message: {e}")
                # 不抛出异常，只是记录日志
                return None
            else:
                # 其他错误重新抛出
                raise e

    async def _safe_callback_response(self, query, message, show_alert=False):
        """安全地回应回调查询"""
        try:
            await query.answer(message, show_alert=show_alert)
            return True
        except Exception as e:
            if "Event loop is closed" in str(e) or "RuntimeError" in str(e):
                logger.warning(f"Event loop error in callback response: {e}")
                return False
            else:
                logger.error(f"Error in callback response: {e}")
                return False

    async def _safe_edit_message(self, query, text, reply_markup=None, parse_mode=None):
        """安全地编辑消息"""
        try:
            await query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
            return True
        except Exception as e:
            if "Event loop is closed" in str(e) or "RuntimeError" in str(e):
                logger.warning(f"Event loop error in message edit: {e}")
                return False
            else:
                logger.error(f"Error in message edit: {e}")
                return False

    def _check_rate_limit(self, user_id: int) -> bool:
        """检查用户请求频率限制"""
        if not getattr(settings, 'TELEGRAM_SECURITY', {}).get('RATE_LIMITING_ENABLED', True):
            return True

        now = time.time()
        user_requests = self.rate_limiter[user_id]

        # 清理60秒前的请求记录
        user_requests[:] = [req_time for req_time in user_requests if now - req_time < 60]

        # 检查是否超过限制
        if len(user_requests) >= self.max_requests_per_minute:
            logger.warning(f"Rate limit exceeded for user {user_id}: {len(user_requests)} requests in last minute")
            return False

        # 记录当前请求
        user_requests.append(now)
        return True

    def _validate_update(self, update) -> bool:
        """验证更新是否符合安全要求"""
        # 检查更新类型是否在允许列表中
        if hasattr(update, 'message') and update.message and 'message' not in self.allowed_updates:
            return False
        if hasattr(update, 'inline_query') and update.inline_query and 'inline_query' not in self.allowed_updates:
            return False
        if hasattr(update, 'callback_query') and update.callback_query and 'callback_query' not in self.allowed_updates:
            return False

        return True

    async def _is_user_authorized(self, user_id: int) -> bool:
        """检查用户是否已绑定并授权使用Bot"""
        try:
            user_query = await sync_to_async(User.objects.filter)(telegram_user_id=user_id)
            user = await sync_to_async(user_query.first)()
            if user:
                return await sync_to_async(user.is_telegram_bound)()
            return False
        except Exception:
            return False

    def _get_telegram_display_name(self, user, effective_user=None) -> str:
        """获取用户的Telegram显示名称

        优先级：
        1. update.effective_user.username（当前Telegram用户的用户名）
        2. user.telegram_username（存储的Telegram用户名）
        3. user.username（应用用户名）
        """
        if effective_user and effective_user.username:
            return effective_user.username
        if user.telegram_username:
            return user.telegram_username
        return user.username

    def _register_handlers(self):
        """注册命令和消息处理器"""
        if not self.application:
            logger.warning("Application not available for handler registration")
            return

        # 检查是否已经注册过处理器，避免重复注册
        if hasattr(self, '_handlers_registered') and self._handlers_registered:
            logger.info("Handlers already registered, skipping registration")
            return

        try:
            # 清除现有的处理器（如果有）
            self.application.handlers.clear()

            # 命令处理器
            self.application.add_handler(CommandHandler("start", self._handle_start))
            self.application.add_handler(CommandHandler("bind", self._handle_bind))
            self.application.add_handler(CommandHandler("unbind", self._handle_unbind))
            self.application.add_handler(CommandHandler("status", self._handle_status))
            self.application.add_handler(CommandHandler("task", self._handle_task))
            self.application.add_handler(CommandHandler("share_item", self._handle_share_item))
            self.application.add_handler(CommandHandler("share_games", self._handle_share_games))
            self.application.add_handler(CommandHandler("board", self._handle_board))
            self.application.add_handler(CommandHandler("help", self._handle_help))

            # 回调查询处理器（处理按钮点击）
            self.application.add_handler(CallbackQueryHandler(self._handle_callback_query))

            # 消息处理器
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))

            # 标记已注册
            self._handlers_registered = True
            logger.info("Telegram bot handlers registered successfully")
        except Exception as e:
            logger.error(f"Failed to register handlers: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            self._handlers_registered = False

    async def _handle_start(self, update, context):
        """处理 /start 命令"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        chat_type = update.effective_chat.type
        username = update.effective_user.username

        # 安全检查：验证更新和频率限制
        if not self._validate_update(update) or not self._check_rate_limit(user_id):
            logger.warning(f"Security check failed for user {user_id} in _handle_start")
            return

        # 群聊中不处理 /start 命令
        if chat_type != 'private':
            await update.message.reply_text(
                "🤖 请在私聊中使用 /start 命令来绑定您的账户"
            )
            return

        # 检查是否是深度链接绑定
        if context.args and len(context.args) > 0:
            bind_token = context.args[0]
            if bind_token.startswith('bind_'):
                # 处理绑定请求
                await self._process_binding(update, context, bind_token, user_id, chat_id, username)
                return
            elif bind_token.startswith('share_'):
                # 处理任务分享 deeplink
                await self._handle_share_deeplink(update, context, bind_token, user_id, chat_id)
                return
            elif bind_token.startswith('reg_'):
                # 处理新用户注册
                await self._handle_registration_start(update, context, bind_token, user_id, chat_id, username)
                return

        # 自动绑定逻辑已移到 _process_binding 方法中
        # 这里不再需要查找等待绑定的用户

        # 检查用户是否已经绑定
        try:
            existing_user = await sync_to_async(User.objects.filter)(telegram_user_id=user_id)
            existing_user = await sync_to_async(existing_user.first)()

            if existing_user:
                # 使用 Telegram 用户名（如果可用）
                tg_display_name = update.effective_user.username or update.effective_user.first_name or existing_user.telegram_username or existing_user.username
                already_bound_text = f"""
👋 欢迎回来，{tg_display_name}！

您的账户已经绑定成功。

使用 /help 查看所有可用命令
                """
                try:
                    await update.message.reply_text(already_bound_text)
                    logger.info(f"User {existing_user.username} already bound, sent welcome back message")
                    return
                except Exception as e:
                    logger.error(f"Failed to send welcome back message: {e}")
                    return

        except Exception as e:
            logger.error(f"Error checking existing user binding: {e}")

        # 默认欢迎消息（未绑定的用户）
        welcome_text = """
🔒 欢迎使用 Lockup Telegram Bot！

这个 Bot 可以帮助您：
• 🔗 绑定您的 Lockup 账户
• ⏰ 通过 Inline Mode 给朋友的任务加时
• 🔔 接收应用通知
• 🎮 玩猜拳和时间转盘游戏

使用 /help 查看所有命令
使用 /bind 开始绑定您的账户
        """

        try:
            await update.message.reply_text(welcome_text)
            logger.info(f"Sent welcome message to new user {user_id}")
        except Exception as e:
            logger.error(f"Failed to send welcome message to user {user_id}: {e}")
            # In case of failure, we still continue processing

    async def _handle_registration_start(self, update, context, reg_token, user_id, chat_id, username):
        """Handle new user registration via bot"""
        from django.core.cache import cache

        # Get stored Telegram data from cache
        tg_data = cache.get(f"tg_reg:{reg_token}")
        if not tg_data:
            await update.message.reply_text(
                "❌ 注册链接已过期，请重新尝试登录。"
            )
            return

        # Verify the Telegram user ID matches
        if str(tg_data.get('telegram_user_id')) != str(user_id):
            await update.message.reply_text(
                "❌ 注册信息与当前Telegram账号不匹配，请重新尝试登录。"
            )
            return

        # Store in user context for conversation
        context.user_data['registration'] = {
            'token': reg_token,
            'telegram_data': tg_data,
            'step': 'email'  # Waiting for email
        }

        await update.message.reply_text(
            "👋 欢迎！我来帮您创建Lockup账号。\n\n"
            "请发送您的邮箱地址："
        )
        logger.info(f"Started registration flow for Telegram user {user_id}")

    async def _handle_registration_message(self, update, context):
        """Handle messages during registration flow"""
        from django.core.cache import cache
        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError

        reg_data = context.user_data.get('registration')
        if not reg_data:
            return False  # Not in registration flow

        step = reg_data['step']
        text = update.message.text.strip()

        if step == 'email':
            # Validate email
            try:
                validate_email(text)
            except ValidationError:
                await update.message.reply_text("❌ 邮箱格式不正确，请重新发送：")
                return True

            # Check if email exists
            email_exists = await sync_to_async(User.objects.filter(email=text).exists)()
            if email_exists:
                await update.message.reply_text("❌ 该邮箱已被注册，请使用其他邮箱：")
                return True

            reg_data['email'] = text
            reg_data['step'] = 'password'
            await update.message.reply_text("✅ 邮箱已记录。\n\n请设置您的密码（至少6位）：")
            return True

        elif step == 'password':
            if len(text) < 6:
                await update.message.reply_text("❌ 密码太短，请至少输入6位字符：")
                return True

            # Create user
            tg_data = reg_data['telegram_data']
            try:
                user = await self._create_user_from_telegram(
                    email=reg_data['email'],
                    password=text,
                    telegram_user_id=tg_data['telegram_user_id'],
                    telegram_username=tg_data['telegram_username'],
                    first_name=tg_data.get('first_name', ''),
                    last_name=tg_data.get('last_name', '')
                )

                # Clear registration data
                del context.user_data['registration']
                cache.delete(f"tg_reg:{reg_data['token']}")

                # Send success message with web app link
                # 使用 Telegram 用户名（如果可用）
                tg_display_name = user.telegram_username or user.username
                await update.message.reply_text(
                    f"✅ 账号创建成功！\n\n"
                    f"邮箱：{user.email}\n"
                    f"用户名：{tg_display_name}\n"
                    f"Telegram已自动绑定。\n\n"
                    f"现在您可以直接通过Telegram登录，或点击以下链接访问：\n"
                    f"https://lock-up.zheermao.top"
                )
                logger.info(f"Successfully created user {user.username} from Telegram registration")
                return True

            except Exception as e:
                logger.error(f"Error creating user from Telegram registration: {e}")
                await update.message.reply_text(
                    "❌ 创建账号时发生错误，请稍后重试或联系客服。"
                )
                return True

        return False

    async def _create_user_from_telegram(self, email, password, telegram_user_id, telegram_username, first_name, last_name):
        """Create a new user from Telegram registration data"""
        from django.contrib.auth.hashers import make_password

        # Generate username from Telegram username or first_name
        if telegram_username:
            base_username = telegram_username
        elif first_name:
            base_username = first_name
        else:
            base_username = "user"

        # Make sure username is unique
        username = base_username
        counter = 1
        while await sync_to_async(User.objects.filter(username=username).exists)():
            username = f"{base_username}_{counter}"
            counter += 1

        # Create user
        user = User(
            username=username,
            email=email,
            password=make_password(password),
            telegram_user_id=telegram_user_id,
            telegram_username=telegram_username or '',
            telegram_chat_id=telegram_user_id,  # Use user_id as chat_id for private chats
            telegram_bound_at=timezone.now(),
            telegram_notifications_enabled=True,
            is_active=True,  # Skip email verification
        )
        await sync_to_async(user.save)()

        return user

    async def _handle_share_deeplink(self, update, context, share_token, user_id, chat_id):
        """处理任务分享 deeplink - 生成带 inline 按钮的分享消息"""
        try:
            # 解析任务 ID
            # share_token 格式: share_{task_id}
            task_id = share_token.replace('share_', '')

            if not task_id:
                await update.message.reply_text("❌ 无效的任务分享链接")
                return

            # 获取任务信息
            from tasks.models import LockTask
            try:
                task = await sync_to_async(LockTask.objects.get)(id=task_id)
            except LockTask.DoesNotExist:
                await update.message.reply_text("❌ 任务不存在或已被删除")
                return

            # 检查任务状态
            if task.task_type != 'lock' or task.status not in ['active', 'voting']:
                await update.message.reply_text("❌ 该任务已结束或不是带锁任务，无法分享")
                return

            # 获取任务创建者信息
            task_creator = await sync_to_async(lambda: task.user)()
            creator_username = self._get_telegram_display_name(task_creator, None)

            # 计算剩余时间
            from django.utils import timezone
            from datetime import timedelta

            now = timezone.now()
            if task.end_time:
                remaining = task.end_time - now
                if remaining.total_seconds() > 0:
                    hours = int(remaining.total_seconds() // 3600)
                    minutes = int((remaining.total_seconds() % 3600) // 60)
                    time_left = f"{hours}小时{minutes}分钟" if hours > 0 else f"{minutes}分钟"
                else:
                    time_left = "已截止"
            else:
                time_left = "未知"

            # 难度映射
            difficulty_map = {
                'easy': '⭐ 简单',
                'normal': '⭐⭐ 普通',
                'hard': '⭐⭐⭐ 困难',
                'hell': '💀 地狱'
            }

            # 构建分享消息
            share_text = f"""🔒 **带锁任务分享**

📋 **任务标题**：{task.title}
👤 **任务者**：{creator_username}
📊 **难度**：{difficulty_map.get(task.difficulty, task.difficulty)}
⏰ **剩余时间**：{time_left}
📅 **状态**：{'🔄 进行中' if task.status == 'active' else '🗳️ 投票期'}

💡 **描述**：{task.description[:100] + '...' if len(task.description) > 100 else task.description}

💪 帮助 {creator_username} 坚持完成任务！"""

            # 创建 inline 按钮 - 使用与 /task 命令相同的格式
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("⏰ 给TA加时", callback_data=f"task_overtime_{task.id}")]
            ])

            # 发送分享消息给用户
            await update.message.reply_text(
                share_text,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )

            logger.info(f"Generated share message for task {task_id} to user {user_id}")

            # 提示用户转发消息给朋友
            hint_text = """
✅ **分享消息已生成！**

👉 **下一步**：点击上方的 "转发" 按钮，选择要分享的聊天或群组

您的朋友点击 "⏰ 给TA加时" 按钮即可为任务加时！
            """
            await update.message.reply_text(hint_text, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Error handling share deeplink: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            await update.message.reply_text("❌ 处理分享链接时出错，请重试")

    async def _handle_bind(self, update, context):
        """处理 /bind 命令"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        chat_type = update.effective_chat.type

        # 安全检查：验证更新和频率限制
        if not self._validate_update(update) or not self._check_rate_limit(user_id):
            logger.warning(f"Security check failed for user {user_id} in _handle_bind")
            return

        # 群聊中不处理 /bind 命令
        if chat_type != 'private':
            await update.message.reply_text(
                "🤖 请在私聊中使用 /bind 命令来绑定您的账户"
            )
            return

        # 检查用户是否已经绑定
        try:
            user_query = await sync_to_async(User.objects.filter)(telegram_chat_id=chat_id)
            user = await sync_to_async(user_query.first)()

            if user:
                display_name = self._get_telegram_display_name(user, update.effective_user)
                await update.message.reply_text(
                    f"您已经绑定了账户：{display_name}\n\n"
                    "如需重新绑定，请先使用 /unbind 解绑"
                )
                return
        except Exception as e:
            logger.error(f"Error checking existing binding: {e}")

        frontend_url = getattr(settings, 'TELEGRAM_APP_CONFIG', {}).get('FRONTEND_URL', 'https://lock-up.zheermao.top')
        profile_url = f"{frontend_url}/profile"

        await update.message.reply_text(
            "🔗 请前往 Lockup 系统完成绑定：\n\n"
            f"{profile_url}\n\n"
            "在个人资料页面中点击「打开 Telegram Bot」按钮即可完成绑定！"
        )

    async def _handle_unbind(self, update, context):
        """处理 /unbind 命令"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        chat_type = update.effective_chat.type

        # 安全检查：验证更新和频率限制
        if not self._validate_update(update) or not self._check_rate_limit(user_id):
            logger.warning(f"Security check failed for user {user_id} in _handle_unbind")
            return

        # 群聊中不处理 /unbind 命令
        if chat_type != 'private':
            await update.message.reply_text(
                "🤖 请在私聊中使用 /unbind 命令来解绑您的账户"
            )
            return

        try:
            user_query = await sync_to_async(User.objects.filter)(telegram_chat_id=chat_id)
            user = await sync_to_async(user_query.first)()

            if user:
                await sync_to_async(user.unbind_telegram)()
                display_name = self._get_telegram_display_name(user, update.effective_user)
                await update.message.reply_text(
                    f"✅ 已成功解绑账户：{display_name}\n\n"
                    "您可以随时使用 /bind 重新绑定"
                )
            else:
                await update.message.reply_text(
                    "❌ 您还没有绑定任何账户\n\n"
                    "使用 /bind 开始绑定"
                )
        except Exception as e:
            logger.error(f"Error in unbind handler: {e}")
            await update.message.reply_text(
                "❌ 解绑过程中发生错误，请稍后重试"
            )

    async def _handle_status(self, update, context):
        """处理 /status 命令"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        chat_type = update.effective_chat.type

        # 安全检查：验证更新和频率限制
        if not self._validate_update(update) or not self._check_rate_limit(user_id):
            logger.warning(f"Security check failed for user {user_id} in _handle_status")
            return

        try:
            # 根据聊天类型确定如何查找用户
            if chat_type == 'private':
                # 私聊：使用 chat_id 查找
                user_query = await sync_to_async(User.objects.filter)(telegram_chat_id=chat_id)
            else:
                # 群聊：使用 user_id 查找
                user_query = await sync_to_async(User.objects.filter)(telegram_user_id=user_id)

            user = await sync_to_async(user_query.first)()

            if not user:
                if chat_type == 'private':
                    await self._safe_send_message(
                        update.message.reply_text,
                        "❌ 您还没有绑定任何账户\n\n"
                        "使用 /bind 开始绑定"
                    )
                else:
                    await self._safe_send_message(
                        update.message.reply_text,
                        f"❌ @{update.effective_user.username or update.effective_user.first_name} 还没有绑定账户"
                    )
                return

            # 获取用户活跃任务
            active_tasks_query = await sync_to_async(LockTask.objects.filter)(
                user=user,
                task_type='lock',
                status='active'
            )
            active_tasks_count = await sync_to_async(active_tasks_query.count)()

            # 构建状态消息
            display_name = self._get_telegram_display_name(user, update.effective_user)
            if chat_type == 'private':
                status_text = f"""👤 **用户状态**
用户名：{display_name}
等级：Level {user.level}
积分：{user.coins}
活跃任务：{active_tasks_count} 个

🔔 **通知设置**
Telegram 通知：{'✅ 已开启' if user.telegram_notifications_enabled else '❌ 已关闭'}

📊 **统计信息**
发布动态：{user.total_posts}
收到点赞：{user.total_likes_received}
完成任务：{user.total_tasks_completed}"""
            else:
                # 群聊中显示简化信息，使用profile URL
                frontend_url = getattr(settings, 'TELEGRAM_APP_CONFIG', {}).get('FRONTEND_URL', 'https://lock-up.zheermao.top')
                profile_url = f"{frontend_url}/profile/{user.id}"
                status_text = f"""👤 **{profile_url} 的状态**
用户名：{display_name}
等级：Level {user.level}
积分：{user.coins}
活跃任务：{active_tasks_count} 个"""

            # 发送状态消息
            await self._safe_send_message(
                update.message.reply_text,
                status_text,
                parse_mode='Markdown'
            )

            logger.info(f"Status command processed successfully for user {user.username} in {chat_type} chat")

        except Exception as e:
            logger.error(f"Error in status handler for user {user_id}: {e}")
            await self._safe_send_message(
                update.message.reply_text,
                "❌ 获取状态信息时发生错误，请稍后重试"
            )

    async def _handle_task(self, update, context):
        """处理 /task 命令 - 显示用户的带锁任务情况"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        chat_type = update.effective_chat.type

        # 安全检查：验证更新和频率限制
        if not self._validate_update(update) or not self._check_rate_limit(user_id):
            logger.warning(f"Security check failed for user {user_id} in _handle_task")
            return

        try:
            # 根据聊天类型确定如何查找用户
            if chat_type == 'private':
                # 私聊：使用 chat_id 查找
                user_query = await sync_to_async(User.objects.filter)(telegram_chat_id=chat_id)
            else:
                # 群聊：使用 user_id 查找
                user_query = await sync_to_async(User.objects.filter)(telegram_user_id=user_id)

            user = await sync_to_async(user_query.first)()

            if not user:
                if chat_type == 'private':
                    await self._safe_send_message(
                        update.message.reply_text,
                        "❌ 您还没有绑定任何账户\n\n"
                        "使用 /bind 开始绑定"
                    )
                else:
                    await self._safe_send_message(
                        update.message.reply_text,
                        f"❌ @{update.effective_user.username or update.effective_user.first_name} 还没有绑定账户\n\n"
                        "请私聊机器人使用 /start 进行绑定"
                    )
                return

            # 获取用户当前活跃的带锁任务
            active_tasks_query = await sync_to_async(LockTask.objects.filter)(
                user=user,
                task_type='lock',
                status='active'
            )
            active_tasks = await sync_to_async(list)(active_tasks_query)

            if not active_tasks:
                # 用户没有活跃的带锁任务
                display_name = self._get_telegram_display_name(user, update.effective_user)
                if chat_type == 'private':
                    message_text = f"""🔓 **当前任务状态**

您目前没有正在进行的带锁任务。

💡 前往应用创建新的带锁任务，挑战自己的意志力！"""
                else:
                    message_text = f"""🔓 **@{display_name} 的任务状态**

{display_name} 目前没有正在进行的带锁任务。

💡 可以前往应用创建新的带锁任务！"""

                await self._safe_send_message(
                    update.message.reply_text,
                    message_text,
                    parse_mode='Markdown'
                )
                return

            # 显示第一个活跃任务（如果有多个，显示最新的）
            task = active_tasks[0]

            # 计算剩余时间
            if task.end_time:
                from django.utils import timezone
                remaining = task.end_time - timezone.now()
                if remaining.total_seconds() > 0:
                    hours = int(remaining.total_seconds() // 3600)
                    minutes = int((remaining.total_seconds() % 3600) // 60)
                    time_left = f"{hours}小时{minutes}分钟" if hours > 0 else f"{minutes}分钟"
                else:
                    time_left = "已到期"
            else:
                time_left = "无限制"

            # 难度映射
            difficulty_map = {
                'easy': '🟢 简单',
                'normal': '🟡 普通',
                'hard': '🔴 困难',
                'hell': '🔥 地狱'
            }

            # 构建任务信息
            display_name = self._get_telegram_display_name(user, update.effective_user)
            if chat_type == 'private':
                task_text = f"""🔒 **您的带锁任务**

📋 **任务标题**：{task.title}
📊 **难度**：{difficulty_map.get(task.difficulty, task.difficulty)}
⏰ **剩余时间**：{time_left}
📅 **状态**：{'🔄 进行中' if task.status == 'active' else '🗳️ 投票期' if task.status == 'voting' else task.status}

💡 **描述**：{task.description[:100] + '...' if len(task.description) > 100 else task.description}

💪 坚持完成任务，挑战自己的意志力！"""
            else:
                task_text = f"""🔒 **@{display_name} 的带锁任务**

📋 **任务标题**：{task.title}
👤 **任务者**：{display_name}
📊 **难度**：{difficulty_map.get(task.difficulty, task.difficulty)}
⏰ **剩余时间**：{time_left}
📅 **状态**：{'🔄 进行中' if task.status == 'active' else '🗳️ 投票期' if task.status == 'voting' else task.status}

💡 **描述**：{task.description[:100] + '...' if len(task.description) > 100 else task.description}

💪 帮助 {display_name} 坚持完成任务！"""

            # 创建加时按钮
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("⏰ 给TA加时", callback_data=f"task_overtime_{task.id}")]
            ])

            await self._safe_send_message(
                update.message.reply_text,
                task_text,
                parse_mode='Markdown',
                reply_markup=keyboard
            )

            logger.info(f"Task command processed successfully for user {user.username} in {chat_type} chat, task: {task.title}")

        except Exception as e:
            logger.error(f"Error in task handler for user {user_id}: {e}")
            await self._safe_send_message(
                update.message.reply_text,
                "❌ 获取任务信息时发生错误，请稍后重试"
            )

    async def _handle_help(self, update, context):
        """处理 /help 命令"""
        user_id = update.effective_user.id

        # 安全检查：验证更新和频率限制
        if not self._validate_update(update) or not self._check_rate_limit(user_id):
            logger.warning(f"Security check failed for user {user_id} in _handle_help")
            return

        help_text = """🤖 Lockup Bot 帮助

基础命令：
/start - 开始使用
/bind - 绑定 Lockup 账户
/unbind - 解绑账户
/status - 查看账户状态
/task - 查看您的带锁任务
/board - 查看您的任务板
/share_item - 分享背包中的物品
/share_games - 分享您的游戏
/help - 显示此帮助
通知功能：
绑定后会自动接收应用内的重要通知"""

        await update.message.reply_text(help_text)

    async def _handle_board(self, update, context):
        """处理 /board 命令 - 显示用户创建的可接取任务板任务"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        chat_type = update.effective_chat.type

        # 安全检查：验证更新和频率限制
        if not self._validate_update(update) or not self._check_rate_limit(user_id):
            logger.warning(f"Security check failed for user {user_id} in _handle_board")
            return

        try:
            # 根据聊天类型确定如何查找用户
            if chat_type == 'private':
                # 私聊：使用 chat_id 查找
                user_query = await sync_to_async(User.objects.filter)(telegram_chat_id=chat_id)
            else:
                # 群聊：使用 user_id 查找
                user_query = await sync_to_async(User.objects.filter)(telegram_user_id=user_id)

            user = await sync_to_async(user_query.first)()

            if not user:
                if chat_type == 'private':
                    await self._safe_send_message(
                        update.message.reply_text,
                        "❌ 您还没有绑定任何账户\n\n"
                        "使用 /bind 开始绑定"
                    )
                else:
                    await self._safe_send_message(
                        update.message.reply_text,
                        f"❌ @{update.effective_user.username or update.effective_user.first_name} 还没有绑定账户\n\n"
                        "请私聊机器人使用 /start 进行绑定"
                    )
                return

            # 查询可接取的任务板任务
            available_tasks = await self._get_user_available_board_tasks(user)

            if not available_tasks:
                # 用户没有可接取的任务板任务
                display_name = self._get_telegram_display_name(user, update.effective_user)
                if chat_type == 'private':
                    message_text = f"""🏆 **您的任务板**

您目前没有可接取的任务板任务。

💡 可接取的任务需要满足以下条件：
• 📋 您创建的任务板任务
• 🔄 状态为可接取（已发布）
• 👥 未满员（还有空位）
• ⏰ 在有效期内（未过期）

前往应用创建新的任务板任务，邀请朋友参与！"""
                else:
                    message_text = f"""🏆 **@{display_name} 的任务板**

{display_name} 目前没有可接取的任务板任务。

💡 可以前往应用创建新的任务板任务！"""

                await self._safe_send_message(
                    update.message.reply_text,
                    message_text,
                    parse_mode='Markdown'
                )
                return

            # 显示任务选择界面
            await self._send_task_selection_interface(update, user, available_tasks, chat_type)

            logger.info(f"Board command processed successfully for user {user.username} in {chat_type} chat, {len(available_tasks)} tasks found")

        except Exception as e:
            logger.error(f"Error in board handler for user {user_id}: {e}")
            await self._safe_send_message(
                update.message.reply_text,
                "❌ 获取任务板信息时发生错误，请稍后重试"
            )

    async def _handle_share_item(self, update, context):
        """处理 /share_item 命令 - 显示用户背包中可分享的物品"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        chat_type = update.effective_chat.type

        # 安全检查：验证更新和频率限制
        if not self._validate_update(update) or not self._check_rate_limit(user_id):
            logger.warning(f"Security check failed for user {user_id} in _handle_share_item")
            return

        try:
            # 根据聊天类型确定如何查找用户
            if chat_type == 'private':
                # 私聊：使用 chat_id 查找
                user_query = await sync_to_async(User.objects.filter)(telegram_chat_id=chat_id)
            else:
                # 群聊：使用 user_id 查找
                user_query = await sync_to_async(User.objects.filter)(telegram_user_id=user_id)

            user = await sync_to_async(user_query.first)()

            if not user:
                if chat_type == 'private':
                    await self._safe_send_message(
                        update.message.reply_text,
                        "❌ 您还没有绑定任何账户\n\n"
                        "使用 /bind 开始绑定"
                    )
                else:
                    await self._safe_send_message(
                        update.message.reply_text,
                        f"❌ @{update.effective_user.username or update.effective_user.first_name} 还没有绑定账户\n\n"
                        "请私聊机器人使用 /start 进行绑定"
                    )
                return

            # 获取用户背包
            inventory_query = await sync_to_async(UserInventory.objects.filter)(user=user)
            inventory = await sync_to_async(inventory_query.first)()

            if not inventory:
                await self._safe_send_message(
                    update.message.reply_text,
                    "❌ 您还没有背包，请先前往应用购买物品"
                )
                return

            # 获取可分享的物品（支持多种类型且状态为 available）
            shareable_items_query = await sync_to_async(Item.objects.filter)(
                owner=user,
                inventory=inventory,
                status='available',
                item_type__name__in=['photo', 'note', 'key', 'little_treasury', 'detection_radar', 'blizzard_bottle', 'sun_bottle', 'time_hourglass', 'small_campfire']
            )
            shareable_items = await sync_to_async(list)(shareable_items_query.select_related('item_type', 'original_owner'))

            if not shareable_items:
                # 用户没有可分享的物品
                display_name = self._get_telegram_display_name(user, update.effective_user)
                if chat_type == 'private':
                    message_text = f"""🎒 **您的背包**

您目前没有可分享的物品。

💡 可分享的物品类型：
📷 照片 (photo)
📝 笔记 (note)
🗝️ 钥匙 (key)

前往应用购买或获得这些物品后，就可以在这里分享给朋友了！"""
                else:
                    message_text = f"""🎒 **@{display_name} 的背包**

{display_name} 目前没有可分享的物品。

💡 可分享的物品类型：📷 照片、📝 笔记、🗝️ 钥匙"""

                await self._safe_send_message(
                    update.message.reply_text,
                    message_text,
                    parse_mode='Markdown'
                )
                return

            # 构建物品选择界面
            display_name = self._get_telegram_display_name(user, update.effective_user)
            if chat_type == 'private':
                items_text = f"""🎒 **您的可分享物品**

请选择要分享的物品：

"""
            else:
                items_text = f"""🎒 **@{display_name} 的可分享物品**

@{display_name} 请选择要分享的物品：

"""

            # 添加物品列表信息
            for i, item in enumerate(shareable_items[:5], 1):  # 最多显示5个物品
                item_icon = getattr(item.item_type, 'icon', '📦')
                # 添加原始所有者信息以辅助区分相同物品
                if item.original_owner:
                    owner_display = self._get_telegram_display_name(item.original_owner, None)
                    items_text += f"{i}. {item_icon} {item.item_type.display_name} - {owner_display}\n"
                else:
                    owner_display = self._get_telegram_display_name(item.owner, None)
                    items_text += f"{i}. {item_icon} {item.item_type.display_name} - {owner_display}\n"

            items_text += f"\n💡 选择后将生成分享链接，其他人点击即可获得物品！"

            # 创建物品选择按钮（只有分享者可以点击）
            keyboard_buttons = []
            for i, item in enumerate(shareable_items[:5]):  # 最多显示5个物品
                item_icon = getattr(item.item_type, 'icon', '📦')
                # 添加原始所有者信息以辅助区分相同物品
                if item.original_owner:
                    owner_display = self._get_telegram_display_name(item.original_owner, None)
                    button_text = f"{item_icon} {item.item_type.display_name} - {owner_display}"
                else:
                    owner_display = self._get_telegram_display_name(item.owner, None)
                    button_text = f"{item_icon} {item.item_type.display_name} - {owner_display}"
                callback_data = f"share_select_{item.id}_{user.id}"  # 包含用户ID用于权限验证
                keyboard_buttons.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

            keyboard = InlineKeyboardMarkup(keyboard_buttons)

            await self._safe_send_message(
                update.message.reply_text,
                items_text,
                parse_mode='Markdown',
                reply_markup=keyboard
            )

            logger.info(f"Share item command processed successfully for user {user.username} in {chat_type} chat, {len(shareable_items)} shareable items found")

        except Exception as e:
            logger.error(f"Error in share_item handler for user {user_id}: {e}")
            await self._safe_send_message(
                update.message.reply_text,
                "❌ 获取物品信息时发生错误，请稍后重试"
            )

    async def _handle_share_games(self, update, context):
        """处理 /share_games 命令 - 显示用户可分享的游戏"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        chat_type = update.effective_chat.type

        # 安全检查：验证更新和频率限制
        if not self._validate_update(update) or not self._check_rate_limit(user_id):
            logger.warning(f"Security check failed for user {user_id} in _handle_share_games")
            return

        try:
            # 根据聊天类型确定如何查找用户
            if chat_type == 'private':
                user_query = await sync_to_async(User.objects.filter)(telegram_chat_id=chat_id)
            else:
                user_query = await sync_to_async(User.objects.filter)(telegram_user_id=user_id)

            user = await sync_to_async(user_query.first)()

            if not user:
                if chat_type == 'private':
                    await self._safe_send_message(
                        update.message.reply_text,
                        "❌ 您还没有绑定任何账户\n\n"
                        "使用 /bind 开始绑定"
                    )
                else:
                    await self._safe_send_message(
                        update.message.reply_text,
                        f"❌ @{update.effective_user.username or update.effective_user.first_name} 还没有绑定账户\n\n"
                        "请私聊机器人使用 /start 进行绑定"
                    )
                return

            # 获取用户等待中的游戏（掷骰子和石头剪刀布）
            from store.models import Game
            from django.utils import timezone

            waiting_games_query = await sync_to_async(Game.objects.filter)(
                creator=user,
                status='waiting',
                game_type__in=['dice', 'rock_paper_scissors']
            )
            waiting_games = await sync_to_async(list)(waiting_games_query.order_by('-created_at')[:10])

            if not waiting_games:
                await self._safe_send_message(
                    update.message.reply_text,
                    "🎮 **您没有可分享的游戏**\n\n"
                    "您目前没有等待参与者的游戏。\n\n"
                    "💡 前往应用创建新的游戏：\n"
                    "• 🎲 掷骰子（猜大小）\n"
                    "• ✂️ 石头剪刀布",
                    parse_mode='Markdown'
                )
                return

            # 构建游戏选择界面
            display_name = self._get_telegram_display_name(user, update.effective_user)
            if chat_type == 'private':
                games_text = f"""🎮 **分享游戏**

您有 {len(waiting_games)} 个等待参与者的游戏：

"""
            else:
                games_text = f"""🎮 **@{display_name} 的游戏**

@{display_name} 有 {len(waiting_games)} 个等待参与者的游戏：

"""

            # 游戏类型映射
            game_type_map = {
                'dice': {'emoji': '🎲', 'name': '掷骰子'},
                'rock_paper_scissors': {'emoji': '✂️', 'name': '石头剪刀布'}
            }

            # 添加游戏列表
            for i, game in enumerate(waiting_games, 1):
                game_info = game_type_map.get(game.game_type, {'emoji': '🎮', 'name': game.game_type})

                games_text += f"""{i}. {game_info['emoji']} **{game_info['name']}**
   💰 赌注: {game.bet_amount}积分 | 👥 {game.participants.count()}/{game.max_players}人

"""

            games_text += "💡 选择一个游戏来分享："

            # 创建选择按钮（只有游戏创建者可以点击）
            keyboard_buttons = []
            for game in waiting_games:
                game_info = game_type_map.get(game.game_type, {'emoji': '🎮', 'name': game.game_type})
                button_text = f"{game_info['emoji']} {game_info['name']} - {game.bet_amount}积分"
                callback_data = f"share_game_select_{game.id}_{user.id}"
                keyboard_buttons.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

            keyboard = InlineKeyboardMarkup(keyboard_buttons)

            await self._safe_send_message(
                update.message.reply_text,
                games_text,
                parse_mode='Markdown',
                reply_markup=keyboard
            )

            logger.info(f"Share games command processed successfully for user {user.username}, {len(waiting_games)} games found")

        except Exception as e:
            logger.error(f"Error in share_games handler for user {user_id}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            await self._safe_send_message(
                update.message.reply_text,
                "❌ 获取游戏信息时发生错误，请稍后重试"
            )

    async def _handle_share_game_select_callback(self, query, callback_data, current_user):
        """处理游戏选择回调 - 只有游戏创建者可以选择"""
        try:
            # 解析回调数据：share_game_select_{game_id}_{creator_user_id}
            parts = callback_data.replace('share_game_select_', '').split('_')
            if len(parts) != 2:
                await self._safe_callback_response(query, "❌ 无效的操作", show_alert=True)
                return

            game_id, creator_user_id = parts
            creator_user_id = int(creator_user_id)

            # 验证只有游戏创建者可以选择
            if current_user.id != creator_user_id:
                await self._safe_callback_response(query, "❌ 只有游戏创建者才能分享游戏", show_alert=True)
                return

            # 获取游戏信息
            from store.models import Game
            from .game_sharing import telegram_game_sharing

            game_query = await sync_to_async(Game.objects.filter)(
                id=game_id,
                creator=current_user,
                status='waiting'
            )
            game = await sync_to_async(game_query.first)()

            if not game:
                await self._safe_callback_response(query, "❌ 游戏不存在或已开始", show_alert=True)
                return

            # 生成分享消息
            message_text, keyboard = telegram_game_sharing.generate_game_share_message(game)

            # 更新消息为分享界面
            await self._safe_edit_message(
                query,
                message_text,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )

            await self._safe_callback_response(query, "✅ 游戏分享消息已生成！", show_alert=True)
            logger.info(f"User {current_user.username} selected game {game_id} for sharing")

        except ValueError:
            await self._safe_callback_response(query, "❌ 无效的用户ID", show_alert=True)
        except Exception as e:
            logger.error(f"Error in share game select callback: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            await self._safe_callback_response(query, "❌ 操作失败，请稍后重试", show_alert=True)

    async def _handle_sharegame_join_callback(self, query, callback_data, current_user):
        """处理分享游戏参与回调"""
        from .game_sharing import telegram_game_sharing
        from store.models import Game

        # 解析回调数据：sharegame_join_{game_id}_{choice}
        try:
            parts = callback_data.replace('sharegame_join_', '').split('_', 1)
            if len(parts) != 2:
                await self._safe_callback_response(query, "❌ 无效的游戏操作", show_alert=True)
                return

            game_id, choice = parts

            # 获取游戏
            game_query = await sync_to_async(Game.objects.filter)(id=game_id)
            game = await sync_to_async(game_query.first)()

            if not game:
                await self._safe_callback_response(query, "❌ 游戏不存在", show_alert=True)
                return

            # 处理游戏参与
            result = await telegram_game_sharing.handle_game_participation(
                current_user, game_id, choice
            )

            if result['success']:
                # 获取最新的参与者信息
                participant_count = await sync_to_async(game.participants.count)()

                # 构建更新后的消息
                if game.status == 'completed':
                    # 游戏已完成，显示结果
                    await self._safe_edit_message(
                        query,
                        result.get('new_message', query.message.text),
                        reply_markup=None,
                        parse_mode='Markdown'
                    )
                else:
                    # 游戏仍在等待，更新参与者列表
                    original_text = query.message.text
                    current_user_display = self._get_telegram_display_name(current_user, None)

                    # 检查是否已有参与者记录
                    if "👥 **参与者：**" in original_text:
                        # 已有参与者记录，追加
                        updated_text = f"{original_text}\n• @{current_user_display}"
                    else:
                        # 首次有参与者
                        updated_text = f"{original_text}\n\n👥 **参与者：**\n• @{current_user_display}"

                    # 保持原有的按钮
                    await self._safe_edit_message(
                        query,
                        updated_text,
                        reply_markup=query.message.reply_markup,
                        parse_mode='Markdown'
                    )

                await self._safe_callback_response(query, result['message'], show_alert=True)
            else:
                await self._safe_callback_response(query, result['message'], show_alert=True)

        except Exception as e:
            logger.error(f"Error in sharegame join callback: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            await self._safe_callback_response(query, "❌ 参与游戏时出错，请稍后重试", show_alert=True)

    async def _handle_callback_query(self, update, context):
        """处理回调查询 - 用于处理分享任务的加时按钮"""
        query = update.callback_query
        user_id = update.effective_user.id

        # 安全检查：验证更新和频率限制
        if not self._validate_update(update) or not self._check_rate_limit(user_id):
            logger.warning(f"Security check failed for user {user_id} in _handle_callback_query")
            await self._safe_callback_response(query, "❌ 请求过于频繁，请稍后再试")
            return

        try:
            callback_data = query.data

            # 处理 /task 命令的加时按钮
            if callback_data.startswith('task_overtime_'):
                await self._handle_task_overtime_callback(query, callback_data, user_id)
                return

            # 检查用户是否已绑定（只对其他类型的回调检查）
            if not await self._is_user_authorized(user_id):
                await self._safe_callback_response(query, "❌ 请先绑定您的 Lockup 账户", show_alert=True)
                return

            user_query = await sync_to_async(User.objects.filter)(telegram_user_id=user_id)
            current_user = await sync_to_async(user_query.first)()

            # 处理任务加时回调（原有的分享任务功能）
            if callback_data.startswith('overtime_'):
                await self._handle_overtime_callback(query, callback_data, current_user)

            # 处理物品分享回调
            elif callback_data.startswith('share_select_'):
                await self._handle_share_select_callback(query, callback_data, current_user)

            elif callback_data.startswith('share_claim_'):
                await self._handle_share_claim_callback(query, callback_data, current_user)

            # 处理任务板相关回调
            elif callback_data.startswith('board_select_'):
                await self._handle_board_select_callback(query, callback_data, current_user)

            elif callback_data.startswith('board_take_'):
                await self._handle_board_take_callback(query, callback_data, current_user)

            # 处理游戏参与回调
            elif callback_data.startswith('game_'):
                await self._handle_game_callback(query, callback_data, current_user)

            # 处理分享游戏选择回调
            elif callback_data.startswith('share_game_select_'):
                await self._handle_share_game_select_callback(query, callback_data, current_user)

            # 处理分享游戏参与回调
            elif callback_data.startswith('sharegame_join_'):
                await self._handle_sharegame_join_callback(query, callback_data, current_user)

            else:
                await self._safe_callback_response(query, "❌ 无效的操作")

        except User.DoesNotExist:
            await self._safe_callback_response(query, "❌ 用户不存在", show_alert=True)
            logger.error(f"User not found for telegram_user_id: {user_id}")
        except Exception as e:
            await self._safe_callback_response(query, "❌ 操作失败，请稍后重试", show_alert=True)
            logger.error(f"Unexpected error in callback query: {e}")

    async def _handle_task_overtime_callback(self, query, callback_data, clicker_user_id):
        """处理 /task 命令的任务加时回调 - 持续存在的按钮"""
        task_id = callback_data.replace('task_overtime_', '')
        logger.info(f"Processing task overtime callback: task_id={task_id}, user_id={clicker_user_id}")

        try:
            # 检查点击加时按钮的用户是否已绑定
            clicker_query = await sync_to_async(User.objects.filter)(telegram_user_id=clicker_user_id)
            clicker_user = await sync_to_async(clicker_query.first)()

            if not clicker_user:
                # 用户未绑定，引导绑定
                frontend_url = getattr(settings, 'TELEGRAM_APP_CONFIG', {}).get('FRONTEND_URL', 'https://lock-up.zheermao.top')
                profile_url = f"{frontend_url}/profile"

                message = (
                    f"❌ 您还没有绑定 Lockup 账户，无法进行加时操作\n\n"
                    f"请前往 {profile_url} 绑定您的账户，然后就可以给朋友的任务加时了！"
                )

                await self._safe_callback_response(query, message, show_alert=True)
                logger.info(f"User {clicker_user_id} not bound, sent binding guidance")
                return

            # 获取任务信息
            task_query = await sync_to_async(LockTask.objects.filter)(id=task_id)
            task = await sync_to_async(task_query.first)()

            if not task:
                await self._safe_callback_response(query, "❌ 任务不存在", show_alert=True)
                logger.warning(f"Task {task_id} not found")
                return

            # 检查任务状态 - 允许active和voting状态
            if task.status not in ['active', 'voting']:
                await self._safe_callback_response(query, "❌ 任务已结束，无法加时", show_alert=True)
                logger.warning(f"Task {task_id} is not active, status: {task.status}")
                return

            # 使用 add_overtime_to_task 的逻辑来生成基于难度的随机时间
            # 根据难度等级确定加时范围（分钟）
            difficulty_overtime_map = {
                'easy': 10,     # 简单：10分钟
                'normal': 20,   # 普通：20分钟
                'hard': 30,     # 困难：30分钟
                'hell': 60      # 地狱：60分钟
            }

            base_overtime = difficulty_overtime_map.get(task.difficulty, 20)  # 默认20分钟

            # 随机加时（在基础时间的50%-150%之间）
            min_overtime = int(base_overtime * 0.5)
            max_overtime = int(base_overtime * 1.5)
            random_minutes = random.randint(min_overtime, max_overtime)

            logger.info(f"Generated difficulty-based random minutes for {task.difficulty}: {random_minutes} (range: {min_overtime}-{max_overtime})")

            # 执行加时操作（不传入minutes参数，让函数自己计算）
            overtime_result = await sync_to_async(add_overtime_to_task)(task, clicker_user)
            logger.info(f"Overtime result: {overtime_result}")

            if overtime_result['success']:
                # 加时成功，在消息末尾追加加时记录，但保持按钮
                original_text = query.message.text

                # 检查是否已有加时记录，如果有则追加
                clicker_display = self._get_telegram_display_name(clicker_user, None)
                if "🎯 加时记录：" in original_text:
                    # 已有加时记录，在现有记录后追加
                    updated_text = f"{original_text}\n• @{clicker_display} +{overtime_result['overtime_minutes']}分钟"
                else:
                    # 首次加时，添加加时记录区域
                    updated_text = f"{original_text}\n\n🎯 **加时记录：**\n• @{clicker_display} +{overtime_result['overtime_minutes']}分钟"

                # 保持原有的加时按钮（持续存在）
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("⏰ 给TA加时", callback_data=f"task_overtime_{task.id}")]
                ])

                # 更新消息，保持按钮
                edit_success = await self._safe_edit_message(
                    query,
                    updated_text,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )

                # 发送确认消息
                response_success = await self._safe_callback_response(
                    query,
                    f"✅ 成功给任务加时 {overtime_result['overtime_minutes']} 分钟！",
                    show_alert=True
                )

                if edit_success and response_success:
                    logger.info(f"Task overtime successful: user {clicker_user.username} added {overtime_result['overtime_minutes']} minutes to task {task.title}")
                else:
                    logger.warning(f"Task overtime successful but message update failed: edit={edit_success}, response={response_success}")

            else:
                # 加时失败，显示具体原因（包括两小时冷却等）
                await self._safe_callback_response(
                    query,
                    f"❌ 加时失败：{overtime_result['message']}",
                    show_alert=True
                )
                logger.warning(f"Task overtime failed: {overtime_result['message']}")

        except Exception as e:
            logger.error(f"Error in task overtime callback: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            await self._safe_callback_response(query, "❌ 加时操作失败，请稍后重试", show_alert=True)

    async def _handle_overtime_callback(self, query, callback_data, current_user):
        """处理任务加时回调"""
        task_id = callback_data.replace('overtime_', '')

        try:
            task = LockTask.objects.get(id=task_id)

            # 生成随机加时时间（15-120分钟）
            random_minutes = random.randint(15, 120)

            # 执行加时操作
            overtime_result = add_overtime_to_task(task, current_user, random_minutes)

            if overtime_result['success']:
                # 加时成功
                # 更新消息，移除按钮（防止重复点击）
                current_user_display = self._get_telegram_display_name(current_user, None)
                await query.edit_message_text(
                    text=f"{query.message.text}\n\n"
                         f"🎯 @{current_user_display} 给这个任务加了 {random_minutes} 分钟！",
                    reply_markup=None
                )

                # 发送确认消息
                await query.answer(f"✅ 成功加时 {random_minutes} 分钟！", show_alert=True)

            else:
                # 加时失败
                await query.answer(f"❌ 加时失败：{overtime_result['message']}", show_alert=True)

        except LockTask.DoesNotExist:
            await query.answer("❌ 任务不存在", show_alert=True)

    async def _handle_game_callback(self, query, callback_data, current_user):
        """处理游戏参与回调"""
        from .game_sharing import telegram_game_sharing

        # 解析回调数据：game_id_choice 或 game_id_join
        parts = callback_data.replace('game_', '').split('_', 1)
        if len(parts) != 2:
            await query.answer("❌ 无效的游戏操作")
            return

        game_id, action = parts

        # 处理游戏参与
        result = await telegram_game_sharing.handle_game_participation(
            current_user, game_id, action if action in ['rock', 'paper', 'scissors'] else None
        )

        if result['success']:
            # 如果需要更新消息
            if result.get('should_edit_message'):
                await query.edit_message_text(
                    text=result['new_message'],
                    reply_markup=None if 'new_message' in result else query.message.reply_markup
                )

            await query.answer(result['message'], show_alert=True)
        else:
            await query.answer(result['message'], show_alert=True)

    async def _handle_share_select_callback(self, query, callback_data, current_user):
        """处理物品选择回调 - 只有分享者可以选择物品"""
        # 解析回调数据：share_select_{item_id}_{sharer_user_id}
        try:
            parts = callback_data.replace('share_select_', '').split('_')
            if len(parts) != 2:
                await self._safe_callback_response(query, "❌ 无效的操作", show_alert=True)
                return

            item_id, sharer_user_id = parts
            sharer_user_id = int(sharer_user_id)

            # 验证只有分享者可以选择物品
            if current_user.id != sharer_user_id:
                await self._safe_callback_response(query, "❌ 只有物品分享者才能选择物品", show_alert=True)
                return

            # 获取物品信息
            item_query = await sync_to_async(Item.objects.filter)(id=item_id, owner=current_user, status='available')
            item = await sync_to_async(item_query.select_related('item_type').first)()

            if not item:
                await self._safe_callback_response(query, "❌ 物品不存在或已被使用", show_alert=True)
                return

            # 检查物品是否可分享
            if item.item_type.name not in ['photo', 'note', 'key', 'little_treasury', 'detection_radar', 'blizzard_bottle', 'sun_bottle', 'time_hourglass', 'small_campfire']:
                await self._safe_callback_response(query, "❌ 该物品无法分享", show_alert=True)
                return

            # 创建分享链接
            try:
                share_result = await sync_to_async(self._create_telegram_share_link)(item, current_user)
            except Exception as e:
                logger.error(f"Failed to create share link for item {item_id}: {e}")
                await self._safe_callback_response(query, "❌ 创建分享链接失败，请稍后重试", show_alert=True)
                return

            # 更新消息显示选中的物品和获取按钮
            chat_type = query.message.chat.type
            item_icon = getattr(item.item_type, 'icon', '📦')

            current_user_display = self._get_telegram_display_name(current_user, None)
            if chat_type == 'private':
                updated_text = f"""🎁 **您选择分享的物品**

{item_icon} **{item.item_type.display_name}**
📝 描述：{item.item_type.description}

🔗 分享链接已生成，其他人点击下方按钮即可获取此物品！

⚠️ 注意：只有第一个点击的人能获得物品"""
            else:
                updated_text = f"""🎁 **@{current_user_display} 分享的物品**

{item_icon} **{item.item_type.display_name}**
📝 描述：{item.item_type.description}

💡 点击下方按钮即可获取此物品！

⚠️ 注意：只有第一个点击的人能获得物品"""

            # 创建获取按钮（所有人都可以点击）
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🎁 获取物品", callback_data=f"share_claim_{share_result['share_token']}")]
            ])

            # 更新消息
            edit_success = await self._safe_edit_message(
                query,
                updated_text,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )

            if edit_success:
                await self._safe_callback_response(query, f"✅ 已选择分享 {item.item_type.display_name}！", show_alert=True)
                logger.info(f"User {current_user.username} selected item {item.item_type.display_name} for sharing")
            else:
                await self._safe_callback_response(query, "❌ 更新消息失败，请稍后重试", show_alert=True)

        except ValueError:
            await self._safe_callback_response(query, "❌ 无效的用户ID", show_alert=True)
        except Exception as e:
            logger.error(f"Error in share select callback: {e}")
            await self._safe_callback_response(query, "❌ 操作失败，请稍后重试", show_alert=True)

    async def _handle_share_claim_callback(self, query, callback_data, current_user):
        """处理物品获取回调 - 任何绑定用户都可以获取物品"""
        # 解析回调数据：share_claim_{share_token}
        share_token = callback_data.replace('share_claim_', '')
        logger.info(f"Processing share claim callback: share_token={share_token}, user_id={current_user.id}")

        # Phase 1: Validate and transfer (wrapped in try-except for actual errors)
        try:
            from store.models import SharedItem
            from django.db import transaction

            def get_shared_item_with_lock(token):
                with transaction.atomic():
                    return SharedItem.objects.select_for_update().filter(
                        share_token=token,
                        status='active'
                    ).select_related('sharer', 'item', 'item__item_type').first()

            shared_item = await sync_to_async(get_shared_item_with_lock)(share_token)

            if not shared_item:
                await self._safe_callback_response(query, "❌ 分享链接无效或已过期", show_alert=True)
                return

            if shared_item.sharer.id == current_user.id:
                await self._safe_callback_response(query, "❌ 不能获取自己分享的物品", show_alert=True)
                return

            if shared_item.claimer:
                claimer_display = self._get_telegram_display_name(shared_item.claimer, None)
                await self._safe_callback_response(query, f"❌ 物品已被 {claimer_display} 获取", show_alert=True)
                return

            # Check inventory space
            claimer_inventory_query = await sync_to_async(UserInventory.objects.filter)(user=current_user)
            claimer_inventory = await sync_to_async(claimer_inventory_query.first)()

            if not claimer_inventory:
                await self._safe_callback_response(query, "❌ 您还没有背包，请先前往应用购买背包", show_alert=True)
                return

            available_slots = await sync_to_async(lambda: claimer_inventory.available_slots)()
            if available_slots <= 0:
                await self._safe_callback_response(query, "❌ 您的背包空间不足，请先清理背包", show_alert=True)
                return

            # Transfer item
            def transfer_item_and_update_record():
                with transaction.atomic():
                    item = Item.objects.select_for_update().get(id=shared_item.item.id)
                    item.owner = current_user
                    item.inventory = claimer_inventory
                    item.status = 'available'
                    item.save()

                    shared_item_record = SharedItem.objects.select_for_update().get(id=shared_item.id)
                    shared_item_record.claimer = current_user
                    shared_item_record.status = 'claimed'
                    shared_item_record.claimed_at = timezone.now()
                    shared_item_record.save()

                    return item, shared_item_record

            item, shared_item_record = await sync_to_async(transfer_item_and_update_record)()

        except Exception as e:
            logger.error(f"Error in item transfer: {e}", exc_info=True)
            error_msg = "❌ 获取物品失败，请稍后重试"
            if "does not exist" in str(e):
                error_msg = "❌ 物品已被领取或不存在"
            elif "space" in str(e).lower() or "slot" in str(e).lower():
                error_msg = "❌ 背包空间不足"
            elif "inventory" in str(e).lower():
                error_msg = "❌ 背包系统错误"
            await self._safe_callback_response(query, error_msg, show_alert=True)
            return  # Exit early on transfer failure

        # Phase 2: Post-transfer operations (notification, message updates)
        # These failures should NOT show error to user since item was already transferred
        current_user_display = self._get_telegram_display_name(current_user, None)
        try:
            from users.models import Notification
            await sync_to_async(Notification.create_notification)(
                recipient=shared_item.sharer,
                notification_type='item_shared',
                actor=current_user,
                title='物品被领取',
                message=f'{current_user_display} 领取了您分享的 {item.item_type.display_name}',
                related_object_type='shared_item',
                related_object_id=shared_item.id,
                extra_data={
                    'item_type': item.item_type.name,
                    'item_display_name': item.item_type.display_name,
                    'claimer_id': current_user.id,
                    'claimer_username': current_user_display,
                    'claimed_at': shared_item_record.claimed_at.isoformat()
                }
            )
        except Exception as e:
            logger.error(f"Notification creation failed after successful item transfer: {e}", exc_info=True)
            # Don't show error to user - item was already transferred

        # Update message and send success response
        try:
            original_text = query.message.text
            updated_text = f"{original_text}\n\n🎉 @{current_user_display} 已成功获取此物品！"

            edit_success = await self._safe_edit_message(
                query,
                updated_text,
                reply_markup=None,
                parse_mode='Markdown'
            )

            success_message = f"🎉 成功获取 {item.item_type.icon} {item.item_type.display_name}！\n\n物品已添加到您的背包中。"
            response_success = await self._safe_callback_response(
                query,
                success_message,
                show_alert=True
            )

            if edit_success and response_success:
                logger.info(f"Item {item.item_type.display_name} successfully transferred from {shared_item.sharer.username} to {current_user.username}")
            else:
                logger.warning(f"Item transfer successful but message update failed: edit={edit_success}, response={response_success}")
        except Exception as e:
            logger.error(f"Message update failed after successful item transfer: {e}", exc_info=True)
            # Still try to send success callback even if message edit failed
            try:
                success_message = f"🎉 成功获取 {item.item_type.icon} {item.item_type.display_name}！\n\n物品已添加到您的背包中。"
                await self._safe_callback_response(query, success_message, show_alert=True)
            except Exception as e2:
                logger.error(f"Failed to send success callback: {e2}", exc_info=True)

    def _create_telegram_share_link(self, item, sharer_user):
        """创建Telegram分享链接（同步方法）"""
        from store.models import SharedItem
        import uuid
        from django.utils import timezone
        from datetime import timedelta

        # 生成唯一的分享令牌
        share_token = str(uuid.uuid4())

        # 创建分享记录
        shared_item = SharedItem.objects.create(
            sharer=sharer_user,
            item=item,
            share_token=share_token,
            expires_at=timezone.now() + timedelta(hours=24),  # 24小时后过期
            status='active'
        )

        return {
            'share_token': share_token,
            'expires_at': shared_item.expires_at.isoformat()
        }

    def generate_task_share_message(self, task, share_user):
        """生成任务分享消息"""
        # 计算剩余时间
        if task.end_time:
            from django.utils import timezone
            remaining = task.end_time - timezone.now()
            if remaining.total_seconds() > 0:
                hours = int(remaining.total_seconds() // 3600)
                minutes = int((remaining.total_seconds() % 3600) // 60)
                time_left = f"{hours}小时{minutes}分钟" if hours > 0 else f"{minutes}分钟"
            else:
                time_left = "已到期"
        else:
            time_left = "无限制"

        # 难度映射
        difficulty_map = {
            'easy': '🟢 简单',
            'normal': '🟡 普通',
            'hard': '🔴 困难',
            'hell': '🔥 地狱'
        }

        share_user_display = self._get_telegram_display_name(share_user, None)

        message_text = f"""
🔒 **带锁任务分享**

📋 **任务标题**：{task.title}
👤 **任务者**：{share_user_display}
📊 **难度**：{difficulty_map.get(task.difficulty, task.difficulty)}
⏰ **剩余时间**：{time_left}
📅 **状态**：{'🔄 进行中' if task.status == 'active' else '🗳️ 投票期' if task.status == 'voting' else task.status}

💡 **描述**：{task.description[:100] + '...' if len(task.description) > 100 else task.description}

💪 帮助 {share_user_display} 坚持完成任务！
        """

        # 创建加时按钮
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⏰ 给TA加时", callback_data=f"overtime_{task.id}")]
        ])

        return message_text.strip(), keyboard

    async def _handle_message(self, update, context):
        """处理普通消息"""
        # Check if user is in registration flow
        if await self._handle_registration_message(update, context):
            return

        message_text = update.message.text.lower()

        # 猜拳游戏
        if any(keyword in message_text for keyword in ['猜拳', 'rock paper scissors', '石头剪刀布']):
            await self._handle_rock_paper_scissors(update, context)
            return

        # 时间转盘游戏
        if any(keyword in message_text for keyword in ['转盘', 'wheel', '轮盘']):
            await self._handle_time_wheel(update, context)
            return

        # 默认回复
        await update.message.reply_text(
            "🤖 我不太明白您的意思。使用 /help 查看可用命令。"
        )

    async def _handle_rock_paper_scissors(self, update, context):
        """处理猜拳游戏"""
        choices = ['✊ 石头', '✋ 布', '✌️ 剪刀']
        bot_choice = random.choice(choices)

        await update.message.reply_text(
            f"🎮 **猜拳游戏**\n\n"
            f"我的选择：{bot_choice}\n\n"
            f"请选择您的出招：",
            reply_markup={
                'inline_keyboard': [
                    [
                        {'text': '✊ 石头', 'callback_data': 'rps_rock'},
                        {'text': '✋ 布', 'callback_data': 'rps_paper'},
                        {'text': '✌️ 剪刀', 'callback_data': 'rps_scissors'}
                    ]
                ]
            },
            parse_mode='Markdown'
        )

    async def _handle_time_wheel(self, update, context):
        """处理时间转盘游戏"""
        # 时间选项（分钟）
        time_options = [15, 30, 45, 60, 90, 120, 180, 240]
        selected_time = random.choice(time_options)

        # 创建转盘动画效果
        animation_frames = [
            "🎯 转盘转动中...",
            "🌀 转盘转动中...",
            "💫 转盘转动中...",
            "⭐ 转盘转动中...",
        ]

        # 发送动画
        message = await update.message.reply_text(animation_frames[0])

        for frame in animation_frames[1:]:
            await asyncio.sleep(0.5)
            await message.edit_text(frame)

        await asyncio.sleep(1)

        # 显示结果
        result_text = f"""
🎊 **时间转盘结果**

🎯 转盘停在：**{selected_time} 分钟**

{'🎉 恭喜！这是一个不错的时间！' if selected_time >= 60 else '😅 时间有点短，不过也很有挑战性！'}
        """

        await message.edit_text(result_text, parse_mode='Markdown')

    async def _process_binding(self, update, context, bind_token, user_id, chat_id, username):
        """处理深度链接绑定"""
        try:
            # 根据绑定令牌查找等待绑定的用户
            pending_user = await sync_to_async(User.objects.filter)(
                telegram_binding_token=bind_token
            )
            pending_user = await sync_to_async(pending_user.first)()

            if not pending_user:
                await update.message.reply_text(
                    "❌ 绑定令牌无效或已过期，请重新在系统中点击绑定按钮。"
                )
                return

            # 检查是否已经有其他用户绑定了这个 Telegram 账户
            existing_user = await sync_to_async(User.objects.filter)(telegram_user_id=user_id)
            existing_user = await sync_to_async(existing_user.first)()

            if existing_user and existing_user != pending_user:
                existing_display = self._get_telegram_display_name(existing_user, update.effective_user)
                await update.message.reply_text(
                    f"❌ 此 Telegram 账户已被用户 {existing_display} 绑定。"
                )
                return

            # 完成绑定：设置 Telegram 信息并清除绑定令牌
            pending_user.telegram_user_id = user_id
            pending_user.telegram_chat_id = chat_id
            if username:
                pending_user.telegram_username = username
            pending_user.telegram_bound_at = timezone.now()
            pending_user.telegram_binding_token = None  # 清除绑定令牌
            await sync_to_async(pending_user.save)()

            pending_display = self._get_telegram_display_name(pending_user, update.effective_user)
            success_text = f"""
✅ 绑定成功！

您的 Lockup 账户 **{pending_display}** 已成功绑定到 Telegram！

现在您可以：
• 🔔 接收任务通知
• ⏰ 通过 Bot 给朋友的任务加时
• 🎮 玩各种小游戏

使用 /help 查看所有可用命令
            """

            try:
                await update.message.reply_text(success_text, parse_mode='Markdown')
                logger.info(f"Successfully bound user {pending_user.username} (ID: {pending_user.id}) to Telegram user {user_id}")
            except Exception as e:
                logger.error(f"Failed to send binding success message: {e}")

        except Exception as e:
            logger.error(f"Error during binding process: {e}")
            await update.message.reply_text(
                "❌ 绑定过程中发生错误，请稍后重试。"
            )

    async def send_notification(self, user_id: int, title: str, message: str, extra_data: Dict[Any, Any] = None):
        """发送通知给指定用户"""
        # 确保 Bot 已经初始化
        if not await self._ensure_initialized():
            logger.warning("Bot not initialized, cannot send notification")
            return False

        try:
            user_query = await sync_to_async(User.objects.filter)(id=user_id)
            user = await sync_to_async(user_query.first)()
            if not user or not await sync_to_async(user.can_receive_telegram_notifications)():
                return False

            notification_text = f"🔔 **{title}**\n\n{message}"

            # 添加相关链接（如果有）
            if extra_data and extra_data.get('related_object_type'):
                # 这里可以添加深度链接到应用
                pass

            # 使用安全的消息发送方法
            result = await self._safe_send_message(
                self.bot.send_message,
                chat_id=user.telegram_chat_id,
                text=notification_text,
                parse_mode='Markdown'
            )

            if result is not None:
                logger.info(f"Successfully sent Telegram notification to user {user_id}")
                return True
            else:
                logger.warning(f"Failed to send Telegram notification to user {user_id} - message send returned None")
                return False

        except Exception as e:
            logger.error(f"Failed to send Telegram notification to user {user_id}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    async def _get_user_available_board_tasks(self, user):
        """查询用户创建的可接取任务板任务"""
        from django.utils import timezone
        from django.db.models import Count, F, Q

        now = timezone.now()

        # 查询条件：
        # 1. 用户创建的任务板任务
        # 2. 状态为可接取 (open, taken, submitted)
        # 3. 未满员 (current_participants < max_participants)
        # 4. 在有效期内 (deadline > now)
        tasks_query = await sync_to_async(LockTask.objects.filter)(
            user=user,  # 修正：使用 user 而不是 creator
            task_type='board',
            status__in=['open', 'taken', 'submitted'],  # 修正：可接取的状态
            deadline__gt=now
        )

        # 使用注解查询参与者数量，过滤未满员的任务
        tasks_query = tasks_query.annotate(
            participant_count=Count('participants', filter=Q(participants__status='joined'))  # 修正：使用正确的关系名称和状态
        ).filter(
            participant_count__lt=F('max_participants')
        )

        return await sync_to_async(list)(
            tasks_query.select_related().order_by('-created_at')[:10]
        )

    async def _send_task_selection_interface(self, update, user, tasks, chat_type):
        """发送任务选择界面"""

        # 构建消息文本
        display_name = self._get_telegram_display_name(user, update.effective_user)
        if chat_type == 'private':
            message_text = f"""🏆 **您的任务板**

您有 {len(tasks)} 个可接取的任务：

"""
        else:
            message_text = f"""🏆 **@{display_name} 的任务板**

@{display_name} 有 {len(tasks)} 个可接取的任务：

"""

        # 添加任务列表
        for i, task in enumerate(tasks, 1):
            # 计算剩余时间
            remaining_time = self._format_remaining_time(task.deadline)

            # 获取详细参与者信息
            from tasks.models import TaskParticipant
            participants = TaskParticipant.objects.filter(task=task)
            current_count = participants.count()

            # 构建参与者预览（显示前3个参与者）
            participant_preview = ""
            if participants.exists():
                preview_participants = participants[:3]
                names = [self._get_telegram_display_name(p.participant, None) for p in preview_participants]
                participant_preview = f" ({', '.join(names)}{'...' if current_count > 3 else ''})"

            participant_info = f"{current_count}/{task.max_participants}人{participant_preview}"

            # 根据任务类型决定是否显示难度
            difficulty_info = ""
            if task.task_type == 'lock' and task.difficulty:
                difficulty_map = {
                    'easy': '🟢 简单',
                    'normal': '🟡 普通',
                    'hard': '🔴 困难',
                    'hell': '🔥 地狱'
                }
                difficulty = difficulty_map.get(task.difficulty, task.difficulty)
                difficulty_info = f"📊 {difficulty} | "

            message_text += f"""{i}. **{task.title}**
   {difficulty_info}👥 {participant_info} | ⏰ {remaining_time}
   💰 奖励: {task.reward}积分

"""

        message_text += "💡 选择一个任务来开放接取："

        # 创建选择按钮（只有任务创建者可以点击）
        keyboard_buttons = []
        for task in tasks:
            button_text = f"🎯 {task.title[:20]}{'...' if len(task.title) > 20 else ''}"
            callback_data = f"board_select_{task.id}_{user.id}"
            keyboard_buttons.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

        keyboard = InlineKeyboardMarkup(keyboard_buttons)

        await self._safe_send_message(
            update.message.reply_text,
            message_text,
            parse_mode='Markdown',
            reply_markup=keyboard
        )

    async def _handle_board_select_callback(self, query, callback_data, current_user):
        """处理任务选择回调 - 只有任务创建者可以选择"""

        # 解析回调数据：board_select_{task_id}_{creator_user_id}
        try:
            parts = callback_data.replace('board_select_', '').split('_')
            if len(parts) != 2:
                return await self._safe_callback_response(query, "❌ 无效的操作", show_alert=True)

            task_id, creator_user_id = parts
            creator_user_id = int(creator_user_id)

            # 验证只有任务创建者可以选择
            if current_user.id != creator_user_id:
                return await self._safe_callback_response(query, "❌ 只有任务创建者才能开放任务接取", show_alert=True)

            # 获取任务信息
            task_query = await sync_to_async(LockTask.objects.filter)(
                id=task_id,
                user=current_user,  # 修正：使用 user 而不是 creator
                task_type='board'
            )
            task = await sync_to_async(task_query.select_related().first)()

            if not task:
                return await self._safe_callback_response(query, "❌ 任务不存在或无权限", show_alert=True)

            # 检查任务状态
            if task.status not in ['open', 'taken', 'submitted']:
                return await self._safe_callback_response(query, "❌ 任务已结束或不可接取", show_alert=True)

            # 更新消息为接取界面
            await self._update_to_take_interface(query, task, current_user)

        except ValueError:
            await self._safe_callback_response(query, "❌ 无效的用户ID", show_alert=True)
        except Exception as e:
            logger.error(f"Error in board select callback: {e}")
            await self._safe_callback_response(query, "❌ 操作失败", show_alert=True)

    async def _handle_board_take_callback(self, query, callback_data, current_user):
        """处理任务接取回调 - 所有绑定用户都可以接取"""

        # 解析回调数据：board_take_{task_id}
        task_id = callback_data.replace('board_take_', '')

        try:
            # 获取任务信息
            task_query = await sync_to_async(LockTask.objects.filter)(
                id=task_id,
                task_type='board'
            )
            task = await sync_to_async(task_query.select_related('user').first)()

            if not task:
                return await self._safe_callback_response(query, "❌ 任务不存在或已结束", show_alert=True)

            # 检查任务状态
            if task.status not in ['open', 'taken', 'submitted']:
                return await self._safe_callback_response(query, "❌ 任务已结束或不可接取", show_alert=True)

            # 执行任务接取逻辑（所有验证都在_take_board_task中进行）
            success, message = await self._take_board_task(task, current_user)

            if success:
                # 更新消息显示接取成功
                await self._update_message_with_participant(query, task, current_user)

                # 发送成功消息和截止时间提醒
                remaining_time = self._format_remaining_time(task.deadline)
                success_message = f"🎉 成功接取任务《{task.title}》！\n\n⏰ 截止时间：{remaining_time}\n💡 请及时提交完成！"

                await self._safe_callback_response(query, success_message, show_alert=True)

                # 创建截止时间提醒通知
                await self._create_deadline_reminder_notification(task, current_user)

                logger.info(f"User {current_user.username} successfully took board task {task.title}")
            else:
                # 改进错误消息显示
                error_messages = {
                    "任务已满员": "😔 任务已满员，请尝试其他任务",
                    "您已经参与了这个任务": "ℹ️ 您已经参与了这个任务",
                    "不能接取自己发布的任务": "⚠️ 不能接取自己发布的任务",
                    "任务已过期": "⏰ 任务已过期，无法接取",
                    "任务不可接取": "❌ 任务当前状态不允许接取",
                    "任务不是开放状态": "❌ 任务不是开放状态"
                }

                # 检查是否是完成率限制错误
                if "完成率" in message:
                    display_message = f"📊 {message}"
                else:
                    display_message = error_messages.get(message, f"❌ {message}")

                await self._safe_callback_response(query, display_message, show_alert=True)

        except Exception as e:
            logger.error(f"Error in board take callback: {e}")
            await self._safe_callback_response(query, "❌ 接取任务失败，请稍后重试", show_alert=True)

    async def _take_board_task(self, task, user):
        """执行任务接取逻辑 - 与Web应用验证保持一致"""
        try:
            from django.utils import timezone
            from tasks.models import TaskParticipant

            # 验证1: 检查是否是任务板
            if task.task_type != 'board':
                return False, "只能接取任务板任务"

            # 验证2: 检查是否是自己发布的任务
            if task.user == user:
                return False, "不能接取自己发布的任务"

            # 验证3: 检查是否已经参与过
            existing_participant = await sync_to_async(
                TaskParticipant.objects.filter(task=task, participant=user).exists
            )()
            if existing_participant:
                return False, "您已经参与了这个任务"

            # 验证4: 检查完成率门槛（新增）
            if task.completion_rate_threshold and task.completion_rate_threshold > 0:
                user_completion_rate = await sync_to_async(user.get_task_completion_rate)()
                if user_completion_rate < task.completion_rate_threshold:
                    return False, f"您的任务完成率为{user_completion_rate:.1f}%，需要达到{task.completion_rate_threshold}%才能接取此任务"

            # 验证5: 检查截止时间（新增）
            if task.deadline and timezone.now() > task.deadline:
                return False, "任务已过期"

            # 判断是单人还是多人任务
            is_multi_person = task.max_participants and task.max_participants > 1

            if is_multi_person:
                # 验证6: 多人任务状态检查
                if task.status not in ['open', 'taken', 'submitted']:
                    return False, "任务不可接取"

                # 验证7: 检查是否已满员
                current_participants = await sync_to_async(
                    TaskParticipant.objects.filter(task=task).count
                )()
                if current_participants >= task.max_participants:
                    return False, "任务已满员"

                # 创建参与记录
                participant = await sync_to_async(TaskParticipant.objects.create)(
                    task=task,
                    participant=user
                )

                # 多人任务状态更新逻辑
                if current_participants == 0 and task.status == 'open':
                    task.status = 'taken'
                    task.taker = user
                    task.taken_at = timezone.now()

                    # 设置截止时间
                    if task.max_duration:
                        task.deadline = task.taken_at + timezone.timedelta(hours=task.max_duration)

                    await sync_to_async(task.save)()

            else:
                # 单人任务状态检查
                if task.status != 'open':
                    return False, "任务不是开放状态"

                # 创建参与记录
                await sync_to_async(TaskParticipant.objects.create)(
                    task=task,
                    participant=user
                )

                # 单人任务状态更新
                task.status = 'taken'
                task.taker = user
                task.taken_at = timezone.now()

                if task.max_duration:
                    task.deadline = task.taken_at + timezone.timedelta(hours=task.max_duration)

                await sync_to_async(task.save)()

            return True, "任务接取成功"

        except Exception as e:
            logger.error(f"Error in _take_board_task: {e}")
            return False, f"接取任务时发生错误: {str(e)}"

    async def _update_to_take_interface(self, query, task, creator):
        """更新消息为接取界面"""
        chat_type = query.message.chat.type

        # 构建任务详情消息
        message_text = self._build_task_detail_message(task, creator, chat_type)

        # 创建接取按钮（持久化，所有人可点击）
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎯 接取任务", callback_data=f"board_take_{task.id}")]
        ])

        await self._safe_edit_message(
            query,
            message_text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

        await self._safe_callback_response(query, f"✅ 已开放《{task.title}》的接取", show_alert=True)

    def _build_task_detail_message(self, task, creator, chat_type):
        """构建任务详情消息"""
        # 计算剩余时间
        remaining_time = self._format_remaining_time(task.deadline)

        # 根据任务类型决定是否显示难度
        difficulty_line = ""
        if task.task_type == 'lock' and task.difficulty:
            difficulty_map = {
                'easy': '🟢 简单',
                'normal': '🟡 普通',
                'hard': '🔴 困难',
                'hell': '🔥 地狱'
            }
            difficulty = difficulty_map.get(task.difficulty, task.difficulty)
            difficulty_line = f"📊 **难度**：{difficulty}\n"

        # 获取参与者信息
        participants_info = self._get_participants_info(task)

        creator_display = self._get_telegram_display_name(creator, None)

        if chat_type == 'private':
            message_text = f"""🎯 **任务详情**

📋 **任务标题**：{task.title}
👤 **创建者**：{creator_display}
{difficulty_line}{participants_info}
⏰ **截止时间**：{remaining_time}
💰 **奖励**：{task.reward}积分

💡 **描述**：
{task.description[:200] + '...' if len(task.description) > 200 else task.description}

🎯 点击下方按钮接取任务！"""
        else:
            message_text = f"""🎯 **@{creator_display} 开放的任务**

📋 **任务标题**：{task.title}
👤 **创建者**：{creator_display}
{difficulty_line}{participants_info}
⏰ **截止时间**：{remaining_time}
💰 **奖励**：{task.reward}积分

💡 **描述**：
{task.description[:200] + '...' if len(task.description) > 200 else task.description}

🎯 点击下方按钮接取任务！"""

        return message_text

    def _get_participants_info(self, task):
        """获取参与者详细信息"""
        from tasks.models import TaskParticipant

        participants = TaskParticipant.objects.filter(task=task).select_related('participant')
        current_count = participants.count()

        if current_count == 0:
            return f"👥 **参与者**：0/{task.max_participants}人"

        # 状态图标映射
        status_emojis = {
            'joined': '✅',
            'submitted': '📋',
            'approved': '🎉',
            'rejected': '❌'
        }

        participant_lines = []
        for participant in participants[:5]:  # 最多显示5个参与者
            emoji = status_emojis.get(participant.status, '❓')
            participant_display = self._get_telegram_display_name(participant.participant, None)
            participant_lines.append(f"  {emoji} {participant_display}")

        # 如果参与者超过5个，显示省略号
        if current_count > 5:
            participant_lines.append(f"  ... 还有{current_count - 5}人")

        participants_text = "\n".join(participant_lines)

        return f"""👥 **参与者**：{current_count}/{task.max_participants}人
{participants_text}"""

    async def _update_message_with_participant(self, query, task, new_participant):
        """更新消息显示新参与者"""
        # 获取当前参与者数量
        current_participants = await sync_to_async(
            task.participants.filter(status='joined').count  # 修正：使用正确的关系名称和状态
        )()

        # 在原消息基础上添加参与者信息
        original_text = query.message.text
        new_participant_display = self._get_telegram_display_name(new_participant, None)

        # 检查是否已有参与者记录
        if "🎯 **参与者：**" in original_text:
            # 已有参与者记录，在现有记录后追加
            updated_text = f"{original_text}\n• @{new_participant_display}"
        else:
            # 首次有参与者，添加参与者记录区域
            updated_text = f"{original_text}\n\n🎯 **参与者：**\n• @{new_participant_display}"

        # 如果满员，移除按钮
        if current_participants >= task.max_participants:
            updated_text += f"\n\n✅ **任务已满员，自动开始！**"
            keyboard = None
        else:
            # 保持接取按钮
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🎯 接取任务", callback_data=f"board_take_{task.id}")]
            ])

        # 更新消息
        await self._safe_edit_message(
            query,
            updated_text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

    async def _create_deadline_reminder_notification(self, task, user):
        """创建截止时间提醒通知"""
        from users.models import Notification

        # 计算截止时间
        remaining_time = self._format_remaining_time(task.deadline)

        # 创建通知
        await sync_to_async(Notification.create_notification)(
            recipient=user,
            notification_type='task_deadline_reminder',
            actor=None,
            title='任务截止时间提醒',
            message=f'您参与的任务板任务《{task.title}》将在{remaining_time}后截止，请及时提交完成！',
            related_object_type='lock_task',
            related_object_id=task.id,
            extra_data={
                'task_type': 'board',
                'task_title': task.title,
                'deadline': task.deadline.isoformat(),
                'remaining_time': remaining_time
            },
            priority='high'
        )

    def _format_remaining_time(self, deadline):
        """格式化剩余时间显示"""
        from django.utils import timezone

        remaining = deadline - timezone.now()
        if remaining.total_seconds() <= 0:
            return "已过期"

        days = remaining.days
        hours = remaining.seconds // 3600
        minutes = (remaining.seconds % 3600) // 60

        if days > 0:
            return f"{days}天{hours}小时"
        elif hours > 0:
            return f"{hours}小时{minutes}分钟"
        else:
            return f"{minutes}分钟"


# 全局实例
telegram_service = TelegramBotService()
