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
        if not settings.TELEGRAM_BOT_TOKEN or settings.TELEGRAM_BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
            logger.warning("Telegram Bot Token not configured")
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
            return False

        if not getattr(self, '_initialized', False):
            try:
                await self.bot.initialize()
                await self.application.initialize()
                self._initialized = True
                logger.info("Telegram Bot initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Telegram Bot: {e}")
                return False

        return True

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
                    await update.message.reply_text(
                        "❌ 您还没有绑定任何账户\n\n"
                        "使用 /bind 开始绑定"
                    )
                else:
                    await update.message.reply_text(
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

            await update.message.reply_text(status_text, parse_mode='Markdown')
            logger.info(f"Status command processed successfully for user {user.username} in {chat_type} chat")

        except Exception as e:
            logger.error(f"Error in status handler for user {user_id}: {e}")
            await update.message.reply_text(
                "❌ 获取状态信息时发生错误，请稍后重试"
            )

    async def _handle_help(self, update, context):
        """处理 /help 命令"""
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type

        # 安全检查：验证更新和频率限制
        if not self._validate_update(update) or not self._check_rate_limit(user_id):
            logger.warning(f"Security check failed for user {user_id} in _handle_help")
            return

        if chat_type == 'private':
            help_text = """🤖 **Lockup Bot 帮助**

**基础命令：**
/start - 开始使用
/bind - 绑定 Lockup 账户
/unbind - 解绑账户
/status - 查看账户状态
/help - 显示此帮助

**Inline Mode：**
在任何聊天中输入 `@lock_up_bot` 然后输入朋友的用户名，可以给他们的活跃任务加时

**游戏功能：**
• 猜拳游戏：发送 "猜拳" 或 "rock paper scissors"
• 时间转盘：发送 "转盘" 或 "wheel"

**通知功能：**
绑定后会自动接收应用内的重要通知

需要帮助？联系开发者或查看应用内说明。"""
        else:
            help_text = """🤖 **Lockup Bot 群聊帮助**

**可用命令：**
/status - 查看您的账户状态
/help - 显示此帮助

**注意：**
• 绑定账户请私聊机器人使用 /start
• 群聊中只显示基础状态信息
• 完整功能请私聊使用"""

        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def _handle_callback_query(self, update, context):
        """处理回调查询 - 用于处理分享任务的加时按钮"""
        query = update.callback_query
        user_id = update.effective_user.id

        # 安全检查：验证更新和频率限制
        if not self._validate_update(update) or not self._check_rate_limit(user_id):
            logger.warning(f"Security check failed for user {user_id} in _handle_callback_query")
            await query.answer("❌ 请求过于频繁，请稍后再试")
            return

        # 检查用户是否已绑定
        if not await self._is_user_authorized(user_id):
            await query.answer("❌ 请先绑定您的 Lockup 账户", show_alert=True)
            return

        try:
            callback_data = query.data
            user_query = await sync_to_async(User.objects.filter)(telegram_user_id=user_id)
            current_user = await sync_to_async(user_query.first)()

            # 处理任务加时回调
            if callback_data.startswith('overtime_'):
                await self._handle_overtime_callback(query, callback_data, current_user)

            # 处理游戏参与回调
            elif callback_data.startswith('game_'):
                await self._handle_game_callback(query, callback_data, current_user)

            else:
                await query.answer("❌ 无效的操作")

        except User.DoesNotExist:
            await query.answer("❌ 用户不存在", show_alert=True)
            logger.error(f"User not found for telegram_user_id: {user_id}")
        except Exception as e:
            await query.answer("❌ 操作失败，请稍后重试", show_alert=True)
            logger.error(f"Unexpected error in callback query: {e}")

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
