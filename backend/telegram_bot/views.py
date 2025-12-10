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
                if client_ip not in ip_whitelist:
                    logger.warning(f"Webhook request from unauthorized IP: {client_ip}")
                    return HttpResponse("Forbidden", status=403)

            # 验证 Webhook Secret Token（生产环境强烈推荐）
            webhook_secret = settings.TELEGRAM_SECURITY.get('WEBHOOK_SECRET_TOKEN')
            if webhook_secret:
                provided_token = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
                if provided_token != webhook_secret:
                    logger.warning(f"Invalid webhook secret token from IP: {get_client_ip(request)}")
                    return HttpResponse("Unauthorized", status=401)

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

        # 调用 telegram_service 处理更新
        try:
            from telegram import Update
            import asyncio
            import threading
            from concurrent.futures import ThreadPoolExecutor

            # 创建 Update 对象
            update = Update.de_json(update_data, telegram_service.bot)

            if update:
                # 使用线程池来处理更新，避免事件循环问题
                def process_update_sync():
                    try:
                        # 在新线程中创建独立的事件循环
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)

                        try:
                            # 确保Bot已经初始化
                            if loop.run_until_complete(telegram_service._ensure_initialized()):
                                # 运行异步处理
                                loop.run_until_complete(
                                    telegram_service.application.process_update(update)
                                )
                                logger.info(f"Successfully processed update {update_data.get('update_id')}")
                            else:
                                logger.error("Failed to initialize Telegram Bot")
                        finally:
                            # 确保正确关闭循环
                            try:
                                # 取消所有待处理的任务
                                pending_tasks = asyncio.all_tasks(loop)
                                for task in pending_tasks:
                                    task.cancel()
                                # 等待任务完成
                                if pending_tasks:
                                    loop.run_until_complete(
                                        asyncio.gather(*pending_tasks, return_exceptions=True)
                                    )
                            except Exception:
                                pass
                            finally:
                                loop.close()

                    except Exception as e:
                        logger.error(f"Error in background thread: {e}")

                # 使用守护线程处理，不阻塞webhook响应
                thread = threading.Thread(target=process_update_sync, daemon=True)
                thread.start()
            else:
                logger.warning(f"Failed to create Update object from data: {update_data}")

        except Exception as e:
            logger.error(f"Error processing Telegram update: {e}")
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
        telegram_user_id = request.data.get('telegram_user_id')

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

        # 预设置用户的 telegram_user_id，但不设置 chat_id（等待 /start 命令完成绑定）
        request.user.telegram_user_id = telegram_user_id
        request.user.telegram_chat_id = None  # 重置 chat_id，等待 webhook 设置
        request.user.save()

        # 生成 Bot 链接
        bot_username = getattr(settings, 'TELEGRAM_BOT_USERNAME', 'lock_up_bot')
        bot_url = f"https://t.me/{bot_username}"

        return Response({
            'message': '绑定准备完成，请点击链接前往 Telegram Bot',
            'bot_url': bot_url,
            'telegram_user_id': telegram_user_id,
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

        # 检查是否是自己的任务
        if task.user != request.user:
            return Response(
                {'error': '只能分享自己的任务'},
                status=status.HTTP_403_FORBIDDEN
            )

        # 检查任务状态
        if task.task_type != 'lock' or task.status not in ['active', 'voting']:
            return Response(
                {'error': '只能分享进行中的带锁任务'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 生成分享消息和按钮
        message_text, keyboard = telegram_service.generate_task_share_message(task, request.user)

        # 生成Telegram分享URL
        import urllib.parse
        encoded_text = urllib.parse.quote(message_text)
        telegram_share_url = f"https://t.me/share/url?url=&text={encoded_text}"

        return Response({
            'message': '分享内容生成成功',
            'share_data': {
                'message_text': message_text,
                'telegram_share_url': telegram_share_url,
                'task_id': str(task.id),
                'task_title': task.title,
                'callback_data': f"overtime_{task.id}"
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
