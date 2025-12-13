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

            # 注册处理器
            self._register_handlers()

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

    def _register_handlers(self):
        """注册命令和消息处理器"""
        if not self.application:
            return

        # 检查是否已经注册过处理器，避免重复注册
        if hasattr(self, '_handlers_registered') and self._handlers_registered:
            logger.info("Handlers already registered, skipping registration")
            return

        # 清除现有的处理器（如果有）
        self.application.handlers.clear()

        # 命令处理器
        self.application.add_handler(CommandHandler("start", self._handle_start))
        self.application.add_handler(CommandHandler("bind", self._handle_bind))
        self.application.add_handler(CommandHandler("unbind", self._handle_unbind))
        self.application.add_handler(CommandHandler("status", self._handle_status))
        self.application.add_handler(CommandHandler("task", self._handle_task))
        self.application.add_handler(CommandHandler("share_item", self._handle_share_item))
        self.application.add_handler(CommandHandler("help", self._handle_help))

        # 回调查询处理器（处理按钮点击）
        self.application.add_handler(CallbackQueryHandler(self._handle_callback_query))

        # 消息处理器
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))

        # 标记已注册
        self._handlers_registered = True
        logger.info("Telegram bot handlers registered successfully")

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

        # 自动绑定逻辑已移到 _process_binding 方法中
        # 这里不再需要查找等待绑定的用户

        # 检查用户是否已经绑定
        try:
            existing_user = await sync_to_async(User.objects.filter)(telegram_user_id=user_id)
            existing_user = await sync_to_async(existing_user.first)()

            if existing_user:
                already_bound_text = f"""
👋 欢迎回来，{existing_user.username}！

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
                await update.message.reply_text(
                    f"您已经绑定了账户：{user.username}\n\n"
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

                await update.message.reply_text(
                    f"✅ 已成功解绑账户：{user.username}\n\n"
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
            if chat_type == 'private':
                status_text = f"""👤 **用户状态**
用户名：{user.username}
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
用户名：{user.username}
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
                if chat_type == 'private':
                    message_text = f"""🔓 **当前任务状态**

您目前没有正在进行的带锁任务。

💡 前往应用创建新的带锁任务，挑战自己的意志力！"""
                else:
                    message_text = f"""🔓 **@{user.username} 的任务状态**

{user.username} 目前没有正在进行的带锁任务。

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
            if chat_type == 'private':
                task_text = f"""🔒 **您的带锁任务**

📋 **任务标题**：{task.title}
📊 **难度**：{difficulty_map.get(task.difficulty, task.difficulty)}
⏰ **剩余时间**：{time_left}
📅 **状态**：{'🔄 进行中' if task.status == 'active' else '🗳️ 投票期' if task.status == 'voting' else task.status}

💡 **描述**：{task.description[:100] + '...' if len(task.description) > 100 else task.description}

💪 坚持完成任务，挑战自己的意志力！"""
            else:
                task_text = f"""🔒 **@{user.username} 的带锁任务**

📋 **任务标题**：{task.title}
👤 **任务者**：{user.username}
📊 **难度**：{difficulty_map.get(task.difficulty, task.difficulty)}
⏰ **剩余时间**：{time_left}
📅 **状态**：{'🔄 进行中' if task.status == 'active' else '🗳️ 投票期' if task.status == 'voting' else task.status}

💡 **描述**：{task.description[:100] + '...' if len(task.description) > 100 else task.description}

💪 帮助 {user.username} 坚持完成任务！"""

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
/share_item - 分享背包中的物品
/help - 显示此帮助
通知功能：
绑定后会自动接收应用内的重要通知"""

        await update.message.reply_text(help_text)

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

            # 获取可分享的物品（photo, note, key 且状态为 available）
            shareable_items_query = await sync_to_async(Item.objects.filter)(
                owner=user,
                inventory=inventory,
                status='available',
                item_type__name__in=['photo', 'note', 'key']
            )
            shareable_items = await sync_to_async(list)(shareable_items_query.select_related('item_type'))

            if not shareable_items:
                # 用户没有可分享的物品
                if chat_type == 'private':
                    message_text = f"""🎒 **您的背包**

您目前没有可分享的物品。

💡 可分享的物品类型：
📷 照片 (photo)
📝 笔记 (note)
🗝️ 钥匙 (key)

前往应用购买或获得这些物品后，就可以在这里分享给朋友了！"""
                else:
                    message_text = f"""🎒 **@{user.username} 的背包**

{user.username} 目前没有可分享的物品。

💡 可分享的物品类型：📷 照片、📝 笔记、🗝️ 钥匙"""

                await self._safe_send_message(
                    update.message.reply_text,
                    message_text,
                    parse_mode='Markdown'
                )
                return

            # 构建物品选择界面
            if chat_type == 'private':
                items_text = f"""🎒 **您的可分享物品**

请选择要分享的物品：

"""
            else:
                items_text = f"""🎒 **@{user.username} 的可分享物品**

@{user.username} 请选择要分享的物品：

"""

            # 添加物品列表信息
            for i, item in enumerate(shareable_items[:5], 1):  # 最多显示5个物品
                item_icon = getattr(item.item_type, 'icon', '📦')
                items_text += f"{i}. {item_icon} {item.item_type.display_name}\n"

            items_text += f"\n💡 选择后将生成分享链接，其他人点击即可获得物品！"

            # 创建物品选择按钮（只有分享者可以点击）
            keyboard_buttons = []
            for i, item in enumerate(shareable_items[:5]):  # 最多显示5个物品
                item_icon = getattr(item.item_type, 'icon', '📦')
                button_text = f"{item_icon} {item.item_type.display_name}"
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

            # 处理游戏参与回调
            elif callback_data.startswith('game_'):
                await self._handle_game_callback(query, callback_data, current_user)

            else:
                await self._safe_callback_response(query, "❌ 无效的操作")

        except User.DoesNotExist:
            await self._safe_callback_response(query, "❌ 用户不存在", show_alert=True)
            logger.error(f"User not found for telegram_user_id: {user_id}")
        except Exception as e:
            await self._safe_callback_response(query, "❌ 操作失败，请稍后重试", show_alert=True)
            logger.error(f"Unexpected error in callback query: {e}")

    async def _handle_task_overtime_callback(self, query, callback_data, clicker_user_id):
        """处理 /task 命令的任务加时回调"""
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

            # 检查任务状态
            if task.status != 'active':
                await self._safe_callback_response(query, "❌ 任务已结束，无法加时", show_alert=True)
                logger.warning(f"Task {task_id} is not active, status: {task.status}")
                return

            # 生成随机加时时间（15-120分钟）
            random_minutes = random.randint(15, 120)
            logger.info(f"Generated random minutes: {random_minutes}")

            # 执行加时操作（使用 sync_to_async 包装同步函数）
            overtime_result = await sync_to_async(add_overtime_to_task)(task, clicker_user, random_minutes)
            logger.info(f"Overtime result: {overtime_result}")

            if overtime_result['success']:
                # 加时成功，更新消息
                original_text = query.message.text
                updated_text = f"{original_text}\n\n🎯 @{clicker_user.username} 给这个任务加了 {random_minutes} 分钟！"

                # 更新消息，移除按钮（防止重复点击）
                edit_success = await self._safe_edit_message(
                    query,
                    updated_text,
                    reply_markup=None,
                    parse_mode='Markdown'
                )

                # 发送确认消息
                response_success = await self._safe_callback_response(
                    query,
                    f"✅ 成功给任务加时 {random_minutes} 分钟！",
                    show_alert=True
                )

                if edit_success and response_success:
                    logger.info(f"Task overtime successful: user {clicker_user.username} added {random_minutes} minutes to task {task.title}")
                else:
                    logger.warning(f"Task overtime successful but message update failed: edit={edit_success}, response={response_success}")

            else:
                # 加时失败
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
                await query.edit_message_text(
                    text=f"{query.message.text}\n\n"
                         f"🎯 @{current_user.username} 给这个任务加了 {random_minutes} 分钟！",
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
            if item.item_type.name not in ['photo', 'note', 'key']:
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

            if chat_type == 'private':
                updated_text = f"""🎁 **您选择分享的物品**

{item_icon} **{item.item_type.display_name}**
📝 描述：{item.item_type.description}

🔗 分享链接已生成，其他人点击下方按钮即可获取此物品！

⚠️ 注意：只有第一个点击的人能获得物品"""
            else:
                updated_text = f"""🎁 **@{current_user.username} 分享的物品**

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

        try:
            # 导入必要的模型
            from store.models import SharedItem

            # 查找分享记录
            shared_item_query = await sync_to_async(SharedItem.objects.filter)(
                share_token=share_token,
                status='active'
            )
            shared_item = await sync_to_async(shared_item_query.select_related('sharer', 'item', 'item__item_type').first)()

            if not shared_item:
                await self._safe_callback_response(query, "❌ 分享链接无效或已过期", show_alert=True)
                return

            # 检查是否是分享者自己
            if shared_item.sharer.id == current_user.id:
                await self._safe_callback_response(query, "❌ 不能获取自己分享的物品", show_alert=True)
                return

            # 检查是否已被其他人获取
            if shared_item.claimer:
                await self._safe_callback_response(query, f"❌ 物品已被 {shared_item.claimer.username} 获取", show_alert=True)
                return

            # 检查获取者的背包空间
            claimer_inventory_query = await sync_to_async(UserInventory.objects.filter)(user=current_user)
            claimer_inventory = await sync_to_async(claimer_inventory_query.first)()

            if not claimer_inventory:
                await self._safe_callback_response(query, "❌ 您还没有背包，请先前往应用购买背包", show_alert=True)
                return

            if claimer_inventory.available_slots <= 0:
                await self._safe_callback_response(query, "❌ 您的背包空间不足，请先清理背包", show_alert=True)
                return

            # 执行物品转移
            try:
                # 更新物品所有者和背包
                item = shared_item.item
                item.owner = current_user
                item.inventory = claimer_inventory
                await sync_to_async(item.save)()

                # 更新分享记录
                shared_item.claimer = current_user
                shared_item.status = 'claimed'
                shared_item.claimed_at = timezone.now()
                await sync_to_async(shared_item.save)()

                # 更新背包容量
                await sync_to_async(claimer_inventory.update_slots)()

                # 创建通知给分享者（与web API保持一致）
                from users.models import Notification
                await sync_to_async(Notification.create_notification)(
                    recipient=shared_item.sharer,
                    notification_type='item_shared',
                    actor=current_user,
                    title='物品被领取',
                    message=f'{current_user.username} 领取了您分享的 {item.item_type.display_name}',
                    related_object_type='shared_item',
                    related_object_id=shared_item.id,
                    extra_data={
                        'item_type': item.item_type.name,
                        'item_display_name': item.item_type.display_name,
                        'claimer_id': current_user.id,
                        'claimer_username': current_user.username,
                        'claimed_at': shared_item.claimed_at.isoformat()
                    }
                )

                # 更新消息显示获取成功
                original_text = query.message.text
                updated_text = f"{original_text}\n\n🎉 @{current_user.username} 已成功获取此物品！"

                # 移除按钮
                edit_success = await self._safe_edit_message(
                    query,
                    updated_text,
                    reply_markup=None,
                    parse_mode='Markdown'
                )

                # 发送成功消息
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
                logger.error(f"Failed to transfer item: {e}")
                await self._safe_callback_response(query, "❌ 物品转移失败，请稍后重试", show_alert=True)

        except Exception as e:
            logger.error(f"Error in share claim callback: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            await self._safe_callback_response(query, "❌ 获取物品失败，请稍后重试", show_alert=True)

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

        message_text = f"""
🔒 **带锁任务分享**

📋 **任务标题**：{task.title}
👤 **任务者**：{share_user.username}
📊 **难度**：{difficulty_map.get(task.difficulty, task.difficulty)}
⏰ **剩余时间**：{time_left}
📅 **状态**：{'🔄 进行中' if task.status == 'active' else '🗳️ 投票期' if task.status == 'voting' else task.status}

💡 **描述**：{task.description[:100] + '...' if len(task.description) > 100 else task.description}

💪 帮助 {share_user.username} 坚持完成任务！
        """

        # 创建加时按钮
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⏰ 给TA加时", callback_data=f"overtime_{task.id}")]
        ])

        return message_text.strip(), keyboard

    async def _handle_message(self, update, context):
        """处理普通消息"""
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
                await update.message.reply_text(
                    f"❌ 此 Telegram 账户已被用户 {existing_user.username} 绑定。"
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

            success_text = f"""
✅ 绑定成功！

您的 Lockup 账户 **{pending_user.username}** 已成功绑定到 Telegram！

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
        if not self.bot:
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

            await self.bot.send_message(
                chat_id=user.telegram_chat_id,
                text=notification_text,
                parse_mode='Markdown'
            )

            return True

        except Exception as e:
            logger.error(f"Failed to send Telegram notification to user {user_id}: {e}")
            return False


# 全局实例
telegram_service = TelegramBotService()
