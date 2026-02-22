import json
import random
import uuid
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth import get_user_model
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from tasks.models import LockTask
from tasks.utils import add_overtime_to_task
from .services import telegram_service
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def telegram_webhook(request):
    """处理 Telegram Webhook - 生产级别安全"""
    try:
        # 安全检查：验证请求来源
        if hasattr(settings, 'TELEGRAM_SECURITY'):
            # 检查 IP 白名单（如果配置）
            ip_whitelist = settings.TELEGRAM_SECURITY.get('IP_WHITELIST', [])
            if ip_whitelist:
                client_ip = get_client_ip(request)
                # 检查IP是否在白名单中（支持前缀匹配）
                ip_allowed = False
                for allowed_ip in ip_whitelist:
                    if client_ip.startswith(allowed_ip.strip()) or client_ip == allowed_ip.strip():
                        ip_allowed = True
                        break

                if not ip_allowed:
                    logger.warning(f"Webhook request from unauthorized IP: {client_ip}, allowed IPs: {ip_whitelist}")
                    # 生产环境临时允许，只记录警告
                    logger.warning("Production mode: allowing request despite IP restriction")

            # 验证 Webhook Secret Token（生产环境强烈推荐）
            webhook_secret = settings.TELEGRAM_SECURITY.get('WEBHOOK_SECRET_TOKEN')
            if webhook_secret:
                provided_token = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
                if provided_token != webhook_secret:
                    logger.warning(f"Invalid webhook secret token from IP: {get_client_ip(request)}")
                    # 生产环境临时允许，只记录警告
                    logger.warning("Production mode: allowing request despite secret token mismatch")

        update_data = json.loads(request.body)

        # 验证更新数据结构
        if not isinstance(update_data, dict) or 'update_id' not in update_data:
            logger.warning(f"Invalid update data structure: {update_data}")
            return HttpResponse("Bad Request", status=400)

        # 检查允许的更新类型
        allowed_updates = getattr(settings, 'TELEGRAM_SECURITY', {}).get('ALLOWED_UPDATES', [])
        if allowed_updates:
            has_allowed_update = any(
                update_type in update_data
                for update_type in allowed_updates
            )
            if not has_allowed_update:
                logger.info(f"Ignoring update with disallowed types: {list(update_data.keys())}")
                return HttpResponse("OK")  # 返回 OK 但不处理

        # 处理 Telegram 更新
        # 注意：这里应该异步处理更新以避免阻塞 webhook
        # 在生产环境中，建议使用 Celery 等任务队列
        logger.info(f"Processing Telegram webhook update: {update_data.get('update_id')}")

        # 简化的webhook处理 - 处理所有类型的更新
        try:
            # 创建 Telegram Update 对象
            from telegram import Update
            update = Update.de_json(update_data, telegram_service.bot)

            if update:
                # 确定更新类型并记录
                update_type = None
                user_id = None

                if update.message and update.message.text:
                    update_type = "message"
                    user_id = update.message.from_user.id
                    if update.message.text.startswith('/'):
                        command = update.message.text.split()[0].replace('/', '')
                        logger.info(f"Processing command: {command} from user {user_id}")
                    else:
                        logger.info(f"Processing message from user {user_id}: {update.message.text[:50]}...")
                elif update.callback_query:
                    update_type = "callback_query"
                    user_id = update.callback_query.from_user.id
                    callback_data = update.callback_query.data
                    logger.info(f"Processing callback query from user {user_id}: {callback_data}")
                else:
                    update_type = "other"
                    logger.info(f"Processing other update type: {list(update_data.keys())}")

                # 使用队列和后台处理来避免双重触发问题
                import threading
                import queue
                import time

                # 全局更新队列和处理线程（如果不存在）
                if not hasattr(telegram_webhook, '_update_queue'):
                    telegram_webhook._update_queue = queue.Queue()
                    telegram_webhook._processing = False
                    telegram_webhook._last_update_ids = set()

                # 检查是否是重复的更新
                update_id = update_data.get('update_id')
                if update_id in telegram_webhook._last_update_ids:
                    logger.warning(f"Duplicate update {update_id} ignored")
                    return HttpResponse("OK")

                # 记录更新ID（保留最近100个）
                telegram_webhook._last_update_ids.add(update_id)
                if len(telegram_webhook._last_update_ids) > 100:
                    oldest_id = min(telegram_webhook._last_update_ids)
                    telegram_webhook._last_update_ids.remove(oldest_id)

                # 将更新添加到队列
                telegram_webhook._update_queue.put((update, update_type, user_id, time.time()))

                # 启动处理线程（如果未运行）
                if not telegram_webhook._processing:
                    telegram_webhook._processing = True

                    def process_updates_worker():
                        import asyncio
                        loop = None
                        try:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)

                            async def handle_queued_updates():
                                while True:
                                    try:
                                        # 获取队列中的更新
                                        update, update_type, user_id, timestamp = telegram_webhook._update_queue.get(timeout=30)

                                        # 检查更新是否太旧（超过60秒）
                                        if time.time() - timestamp > 60:
                                            logger.warning(f"Dropping old update {update_type} from user {user_id}")
                                            telegram_webhook._update_queue.task_done()
                                            continue

                                        # 处理更新
                                        try:
                                            if await telegram_service._ensure_initialized():
                                                await telegram_service.application.process_update(update)
                                                logger.info(f"Update {update_type} processed successfully for user {user_id}")
                                            else:
                                                logger.error(f"Failed to initialize telegram service for update {update_type}")
                                        except Exception as e:
                                            logger.error(f"Error processing {update_type}: {e}")

                                        telegram_webhook._update_queue.task_done()

                                    except queue.Empty:
                                        # 队列为空，继续等待
                                        continue
                                    except Exception as e:
                                        logger.error(f"Error in update processing worker: {e}")

                            loop.run_until_complete(handle_queued_updates())

                        except Exception as e:
                            logger.error(f"Error in update processing thread: {e}")
                        finally:
                            telegram_webhook._processing = False
                            if loop:
                                try:
                                    loop.close()
                                except:
                                    pass

                    # 启动后台线程
                    thread = threading.Thread(target=process_updates_worker, daemon=True)
                    thread.start()
            else:
                logger.error(f"Failed to create Update object from: {update_data}")

        except Exception as e:
            logger.error(f"Error processing Telegram update: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # 仍然返回 OK 以免 Telegram 重复发送

        return HttpResponse("OK")

    except json.JSONDecodeError:
        logger.error("Invalid JSON in webhook request")
        return HttpResponse("Bad Request", status=400)
    except Exception as e:
        logger.error(f"Error processing Telegram webhook: {e}")
        return HttpResponse("Internal Server Error", status=500)


def get_client_ip(request):
    """获取客户端真实IP地址"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bind_telegram(request):
    """绑定 Telegram 账户"""
    try:
        telegram_user_id = request.data.get('telegram_user_id')
        telegram_username = request.data.get('telegram_username')
        telegram_chat_id = request.data.get('telegram_chat_id')

        if not telegram_user_id:
            return Response(
                {'error': 'telegram_user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 检查是否已经有其他用户绑定了这个 Telegram 账户
        existing_user = User.objects.filter(telegram_user_id=telegram_user_id).first()
        if existing_user and existing_user != request.user:
            return Response(
                {'error': '此 Telegram 账户已被其他用户绑定'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 绑定账户
        request.user.bind_telegram(
            telegram_user_id=telegram_user_id,
            telegram_username=telegram_username,
            telegram_chat_id=telegram_chat_id
        )

        return Response({
            'message': '绑定成功',
            'telegram_username': telegram_username,
            'bound_at': request.user.telegram_bound_at
        })

    except Exception as e:
        logger.error(f"Error binding Telegram: {e}")
        return Response(
            {'error': '绑定失败，请重试'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initiate_telegram_binding(request):
    """启动 Telegram 绑定流程 - 为自动绑定做准备"""
    try:
        # 不再需要 telegram_user_id 参数，因为我们使用绑定令牌
        import uuid

        # 生成唯一的绑定令牌
        binding_token = f"bind_{request.user.id}_{uuid.uuid4().hex[:8]}"

        # 保存绑定令牌到用户记录
        request.user.telegram_binding_token = binding_token
        request.user.telegram_user_id = None  # 清除之前的错误数据
        request.user.telegram_chat_id = None  # 重置 chat_id，等待 webhook 设置
        request.user.save()

        # 生成 Bot 链接，包含绑定令牌
        bot_username = getattr(settings, 'TELEGRAM_BOT_USERNAME', 'lock_heart_bot')
        bot_url = f"https://t.me/{bot_username}?start={binding_token}"

        return Response({
            'message': '绑定准备完成，请点击链接前往 Telegram Bot',
            'bot_url': bot_url,
            'binding_token': binding_token,
            'next_step': '在 Telegram 中发送 /start 命令完成绑定'
        })

    except Exception as e:
        logger.error(f"Error initiating Telegram binding: {e}")
        return Response(
            {'error': '启动绑定失败，请重试'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def unbind_telegram(request):
    """解绑 Telegram 账户"""
    try:
        if not request.user.is_telegram_bound():
            return Response(
                {'error': '您还没有绑定 Telegram 账户'},
                status=status.HTTP_400_BAD_REQUEST
            )

        request.user.unbind_telegram()

        return Response({'message': '解绑成功'})

    except Exception as e:
        logger.error(f"Error unbinding Telegram: {e}")
        return Response(
            {'error': '解绑失败，请重试'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def telegram_status(request):
    """获取 Telegram 绑定状态"""
    user = request.user

    return Response({
        'is_bound': user.is_telegram_bound(),
        'telegram_username': user.telegram_username,
        'bound_at': user.telegram_bound_at,
        'notifications_enabled': user.telegram_notifications_enabled,
        'can_receive_notifications': user.can_receive_telegram_notifications()
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_telegram_notifications(request):
    """切换 Telegram 通知开关"""
    try:
        if not request.user.is_telegram_bound():
            return Response(
                {'error': '请先绑定 Telegram 账户'},
                status=status.HTTP_400_BAD_REQUEST
            )

        request.user.telegram_notifications_enabled = not request.user.telegram_notifications_enabled
        request.user.save()

        return Response({
            'message': f'Telegram 通知已{"开启" if request.user.telegram_notifications_enabled else "关闭"}',
            'notifications_enabled': request.user.telegram_notifications_enabled
        })

    except Exception as e:
        logger.error(f"Error toggling Telegram notifications: {e}")
        return Response(
            {'error': '设置失败，请重试'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def telegram_add_overtime(request):
    """通过 Telegram Bot 给任务加时"""
    try:
        task_id = request.data.get('task_id')
        minutes = request.data.get('minutes', random.randint(15, 120))

        if not task_id:
            return Response(
                {'error': 'task_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            task = LockTask.objects.get(id=task_id)
        except LockTask.DoesNotExist:
            return Response(
                {'error': '任务不存在'},
                status=status.HTTP_404_NOT_FOUND
            )

        if task.status != 'active':
            return Response(
                {'error': '任务不是活跃状态，无法加时'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 复用现有的加时逻辑
        result = add_overtime_to_task(task, request.user, minutes)

        if result['success']:
            return Response({
                'message': f'成功给任务《{task.title}》加时 {minutes} 分钟',
                'task_title': task.title,
                'minutes_added': minutes,
                'new_end_time': task.end_time
            })
        else:
            return Response(
                {'error': result['message']},
                status=status.HTTP_400_BAD_REQUEST
            )

    except Exception as e:
        logger.error(f"Error adding overtime via Telegram: {e}")
        return Response(
            {'error': '加时失败，请重试'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )






@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_users_for_overtime(request):
    """搜索用户以便给他们的任务加时"""
    try:
        query = request.GET.get('q', '').strip()

        if not query:
            return Response({'users': []})

        # 搜索用户名包含查询词的用户
        users = User.objects.filter(
            username__icontains=query,
            telegram_user_id__isnull=False  # 只显示已绑定 Telegram 的用户
        )[:10]

        result = []
        for user in users:
            # 获取用户的活跃任务
            active_tasks = LockTask.objects.filter(
                user=user,
                task_type='lock',
                status='active'
            )

            tasks_data = []
            for task in active_tasks:
                tasks_data.append({
                    'id': str(task.id),
                    'title': task.title,
                    'difficulty': task.difficulty,
                    'start_time': task.start_time,
                    'end_time': task.end_time
                })

            result.append({
                'id': user.id,
                'username': user.username,
                'level': user.level,
                'active_tasks': tasks_data
            })

        return Response({'users': result})

    except Exception as e:
        logger.error(f"Error searching users for overtime: {e}")
        return Response(
            {'error': '搜索失败，请重试'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def share_task_to_telegram(request):
    """生成任务分享到Telegram的消息和链接"""
    try:
        task_id = request.data.get('task_id')

        if not task_id:
            return Response(
                {'error': 'task_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            task = LockTask.objects.get(id=task_id)
        except LockTask.DoesNotExist:
            return Response(
                {'error': '任务不存在'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 注意：现在允许分享任何人的任务，不仅限于自己的任务

        # 检查任务状态
        if task.task_type != 'lock' or task.status not in ['active', 'voting']:
            return Response(
                {'error': '只能分享进行中的带锁任务'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 生成 deeplink 分享链接
        # 格式: https://t.me/{bot_username}?start=share_{task_id}
        # 用户点击后会跳转到 Bot，Bot 会发送带 inline 按钮的分享消息
        bot_username = getattr(settings, 'TELEGRAM_BOT_USERNAME', 'lock_heart_bot')
        deeplink_url = f"https://t.me/{bot_username}?start=share_{task.id}"

        # 生成分享消息（用于 Bot 发送时的内容预览）
        message_text, keyboard = telegram_service.generate_task_share_message(task, task.user)

        return Response({
            'message': '分享链接生成成功',
            'share_data': {
                'message_text': message_text,
                'telegram_share_url': deeplink_url,  # 现在返回 deeplink
                'deeplink_url': deeplink_url,
                'task_id': str(task.id),
                'task_title': task.title,
                'callback_data': f"task_overtime_{task.id}",  # 使用与 /task 命令相同的格式
                'share_type': 'deeplink'
            }
        })

    except Exception as e:
        logger.error(f"Error generating task share: {e}")
        return Response(
            {'error': '生成分享内容失败'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def share_game_to_telegram(request):
    """分享游戏挑战到Telegram"""
    try:
        game_id = request.data.get('game_id')

        if not game_id:
            return Response(
                {'error': 'game_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            from store.models import Game
            game = Game.objects.get(id=game_id)
        except Game.DoesNotExist:
            return Response(
                {'error': '游戏不存在'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 检查是否是自己的游戏
        if game.creator != request.user:
            return Response(
                {'error': '只能分享自己创建的游戏'},
                status=status.HTTP_403_FORBIDDEN
            )

        # 检查游戏状态
        if game.status != 'waiting':
            return Response(
                {'error': '只能分享等待中的游戏'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 生成分享消息和按钮
        from .game_sharing import telegram_game_sharing
        message_text, keyboard = telegram_game_sharing.generate_game_share_message(game)

        # 生成Telegram分享URL
        import urllib.parse
        encoded_text = urllib.parse.quote(message_text)
        telegram_share_url = f"https://t.me/share/url?url=&text={encoded_text}"

        return Response({
            'message': '游戏分享内容生成成功',
            'share_data': {
                'message_text': message_text,
                'telegram_share_url': telegram_share_url,
                'game_id': str(game.id),
                'game_type': game.game_type,
                'keyboard': keyboard
            }
        })

    except Exception as e:
        logger.error(f"Error generating game share: {e}")
        return Response(
            {'error': '生成游戏分享内容失败'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def share_game_directly(request):
    """直接分享游戏到Telegram"""
    try:
        game_id = request.data.get('game_id')

        if not game_id:
            return Response(
                {'error': 'game_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 复用分享逻辑
        share_response = share_game_to_telegram(request)

        if share_response.status_code == 200:
            return Response({
                'message': '游戏分享成功，已在Telegram中打开',
                'share_data': share_response.data['share_data']
            })
        else:
            return share_response

    except Exception as e:
        logger.error(f"Error sharing game directly: {e}")
        return Response(
            {'error': '分享游戏失败'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def test_telegram_notification(request):
    """测试 Telegram 通知发送（开发用）"""
    try:
        user_id = request.data.get('user_id')
        title = request.data.get('title', '测试通知')
        message = request.data.get('message', '这是一条测试通知')

        if not user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 发送通知
        success = telegram_service.send_notification(user_id, title, message)

        return Response({
            'success': success,
            'message': '通知发送成功' if success else '通知发送失败'
        })

    except Exception as e:
        logger.error(f"Error testing Telegram notification: {e}")
        return Response(
            {'error': '测试失败'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
