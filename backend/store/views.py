from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import random
import json
import logging
import os
from datetime import timedelta

logger = logging.getLogger(__name__)

from .models import (
    ItemType, UserInventory, Item, StoreItem, Purchase,
    Game, GameParticipant, DriftBottle, BuriedTreasure, GameSession, SharedItem,
    UserEffect, SharedTaskAccess, TaskSnapshot, UserZoneExploration
)
from users.models import Notification
from .serializers import (
    ItemTypeSerializer, UserInventorySerializer, ItemSerializer,
    StoreItemSerializer, PurchaseSerializer, GameSerializer,
    DriftBottleSerializer, BuriedTreasureSerializer, GameSessionSerializer,
    PurchaseItemSerializer, TimeWheelPlaySerializer, JoinGameSerializer,
    CreateDriftBottleSerializer, UploadPhotoSerializer, BuryItemSerializer,
    ExploreZoneSerializer, FindTreasureSerializer
)
from tasks.models import LockTask, TaskTimelineEvent
from tasks.validators import validate_task_completion_conditions


def getDifficultyText(difficulty: str) -> str:
    """获取难度显示文本"""
    difficulties = {
        'easy': '简单',
        'normal': '普通',
        'hard': '困难'
    }
    return difficulties.get(difficulty, difficulty)


def get_fibonacci_cost(n):
    """获取第n次探索的费用（斐波那契数列）"""
    if n <= 0:
        return 1
    if n <= 2:
        return 1
    a, b = 1, 1
    for _ in range(3, n + 1):
        a, b = b, a + b
    return b


COOLDOWN_SECONDS = 30  # 探索冷却时间（秒）


class StoreItemListView(generics.ListAPIView):
    """商店商品列表"""
    queryset = StoreItem.objects.filter(is_available=True)
    serializer_class = StoreItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        # 根据用户等级过滤
        if hasattr(user, 'level'):
            queryset = queryset.filter(level_requirement__lte=user.level)

        return queryset


class UserInventoryView(generics.RetrieveAPIView):
    """用户背包"""
    serializer_class = UserInventorySerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        inventory, created = UserInventory.objects.get_or_create(user=self.request.user)
        return inventory


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def purchase_item(request):
    """购买商品"""
    serializer = PurchaseItemSerializer(data=request.data)
    if serializer.is_valid():
        store_item_id = serializer.validated_data['store_item_id']
        quantity = serializer.validated_data.get('quantity', 1)

        try:
            with transaction.atomic():
                store_item = get_object_or_404(StoreItem, id=store_item_id, is_available=True)
                user = request.user

                # 检查用户等级要求
                if hasattr(user, 'level') and user.level < store_item.level_requirement:
                    return Response({
                        'error': f'需要等级 {store_item.level_requirement} 才能购买此商品'
                    }, status=status.HTTP_403_FORBIDDEN)

                # 检查库存
                if store_item.stock is not None and store_item.stock < quantity:
                    return Response({
                        'error': '库存不足'
                    }, status=status.HTTP_400_BAD_REQUEST)

                # 检查每日购买限制
                if store_item.daily_limit:
                    # 使用日期范围查询避免timezone问题
                    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
                    today_end = today_start + timedelta(days=1)

                    today_purchases = Purchase.objects.filter(
                        user=user,
                        store_item=store_item,
                        created_at__gte=today_start,
                        created_at__lt=today_end
                    ).count()

                    if today_purchases + quantity > store_item.daily_limit:
                        return Response({
                            'error': f'今日购买限制：{store_item.daily_limit}个，已购买{today_purchases}个'
                        }, status=status.HTTP_400_BAD_REQUEST)


                # 检查用户积分
                total_cost = store_item.price * quantity
                if hasattr(user, 'coins') and user.coins < total_cost:
                    return Response({
                        'error': '积分不足'
                    }, status=status.HTTP_400_BAD_REQUEST)

                # 检查背包容量
                inventory, _ = UserInventory.objects.get_or_create(user=user)
                if inventory.available_slots < quantity:
                    return Response({
                        'error': f'背包空间不足，剩余{inventory.available_slots}格'
                    }, status=status.HTTP_400_BAD_REQUEST)

                # 扣除积分
                if hasattr(user, 'coins'):
                    user.deduct_coins(
                        amount=total_cost,
                        change_type='store_purchase',
                        description=f'购买 {store_item.name} x{quantity}',
                        metadata={
                            'store_item_id': str(store_item.id),
                            'store_item_name': store_item.name,
                            'quantity': quantity,
                            'unit_price': store_item.price,
                            'total_cost': total_cost
                        }
                    )

                # 减少库存
                if store_item.stock is not None:
                    store_item.stock -= quantity
                    store_item.save()

                # 创建购买记录和物品
                items_created = []
                for _ in range(quantity):
                    # 先创建物品实例
                    item = Item.objects.create(
                        item_type=store_item.item_type,
                        owner=user,
                        original_owner=user,  # 设置原始拥有者为购买者
                        inventory=inventory
                    )

                    # 然后创建购买记录，关联到物品
                    purchase = Purchase.objects.create(
                        user=user,
                        store_item=store_item,
                        item=item,
                        price_paid=store_item.price
                    )
                    items_created.append(item)


                # 返回购买结果
                return Response({
                    'message': f'成功购买 {quantity} 个 {store_item.name}',
                    'items': [{'id': str(item.id), 'type': item.item_type.name} for item in items_created],
                    'remaining_coins': getattr(user, 'coins', 0),
                    'remaining_slots': inventory.available_slots
                }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({
                'error': f'购买失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_photo_to_paper(request):
    """上传照片到相纸"""
    serializer = UploadPhotoSerializer(data=request.data)
    if serializer.is_valid():
        paper_item_id = serializer.validated_data['paper_item_id']
        photo = serializer.validated_data['photo']

        try:
            with transaction.atomic():
                # 获取相纸道具
                paper_item = get_object_or_404(
                    Item,
                    id=paper_item_id,
                    owner=request.user,
                    item_type__name='photo_paper',
                    status='available'
                )

                # 保存照片文件
                file_name = f"photos/{timezone.now().strftime('%Y%m%d_%H%M%S')}_{photo.name}"
                file_path = default_storage.save(file_name, ContentFile(photo.read()))

                # 更新相纸道具为照片道具
                paper_item.item_type = ItemType.objects.get(name='photo')
                paper_item.properties = {
                    'photo_path': file_path,
                    'upload_time': timezone.now().isoformat(),
                    'burn_after_reading': True
                }
                paper_item.save()

                return Response({
                    'message': '照片上传成功',
                    'photo_item_id': str(paper_item.id)
                }, status=status.HTTP_200_OK)

        except ItemType.DoesNotExist:
            return Response({
                'error': '照片道具类型不存在'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({
                'error': f'上传失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def view_photo(request, photo_id):
    """查看照片（阅后即焚）"""
    try:
        with transaction.atomic():
            photo_item = get_object_or_404(
                Item,
                id=photo_id,
                item_type__name='photo',
                status='available'
            )

            # 检查权限（拥有者或漂流瓶接收者）
            can_view = False
            if photo_item.owner == request.user:
                can_view = True
            else:
                # 检查是否是漂流瓶中的照片
                drift_bottles = DriftBottle.objects.filter(
                    items__id=photo_id,
                    finder=request.user,
                    status='found'
                )
                if drift_bottles.exists():
                    can_view = True

            if not can_view:
                return Response({
                    'error': '无权查看此照片'
                }, status=status.HTTP_403_FORBIDDEN)

            # 获取照片路径
            photo_path = photo_item.properties.get('photo_path')
            if not photo_path or not default_storage.exists(photo_path):
                return Response({
                    'error': '照片文件不存在'
                }, status=status.HTTP_404_NOT_FOUND)

            # 读取照片文件
            with default_storage.open(photo_path, 'rb') as f:
                photo_data = f.read()

            # 阅后即焚：删除照片文件和标记道具为已使用
            if photo_item.properties.get('burn_after_reading', True):
                default_storage.delete(photo_path)
                photo_item.status = 'used'
                photo_item.used_at = timezone.now()
                photo_item.inventory = None  # 从背包中移除
                photo_item.save()

                # 创建照片查看通知（如果不是自己的照片）
                if photo_item.owner != request.user:
                    Notification.create_notification(
                        recipient=photo_item.owner,
                        notification_type='photo_viewed',
                        actor=request.user,
                        related_object_type='item',
                        related_object_id=photo_item.id,
                        extra_data={
                            'photo_path': photo_path,
                            'view_time': timezone.now().isoformat(),
                            'burn_after_reading': True
                        },
                        priority='low'
                    )

            from django.http import HttpResponse
            return HttpResponse(photo_data, content_type='image/jpeg')

    except Exception as e:
        return Response({
            'error': f'查看照片失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def play_time_wheel(request):
    """时间转盘游戏 - 新版本：接受前端计算的时间变更"""
    try:
        # 获取前端传递的参数
        task_id = request.data.get('task_id')
        bet_amount = request.data.get('bet_amount')
        is_increase = request.data.get('is_increase')
        time_change_minutes = request.data.get('time_change_minutes')
        base_time = request.data.get('base_time')

        # 验证必要参数
        if not all([task_id, bet_amount, time_change_minutes is not None, base_time]):
            return Response({
                'error': '缺少必要参数：task_id, bet_amount, is_increase, time_change_minutes, base_time'
            }, status=status.HTTP_400_BAD_REQUEST)

        # 验证数据类型和合理性
        try:
            bet_amount = int(bet_amount)
            time_change_minutes = int(time_change_minutes)
            base_time = int(base_time)
            is_increase = bool(is_increase)
        except (ValueError, TypeError):
            return Response({
                'error': '参数类型错误'
            }, status=status.HTTP_400_BAD_REQUEST)

        # 验证数据合理性
        if bet_amount <= 0:
            return Response({
                'error': '投注金额必须大于0'
            }, status=status.HTTP_400_BAD_REQUEST)

        if base_time not in [5, 15, 30, 60]:
            return Response({
                'error': '基础时间必须是5、15、30或60分钟'
            }, status=status.HTTP_400_BAD_REQUEST)

        if time_change_minutes != base_time * bet_amount:
            return Response({
                'error': '时间变更计算错误'
            }, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            user = request.user

            # 检查指定的锁任务是否存在且属于当前用户且是活跃状态
            try:
                lock_task = LockTask.objects.get(
                    id=task_id,
                    user=user,
                    task_type='lock',
                    status='active'
                )
            except LockTask.DoesNotExist:
                # 提供更详细的错误信息帮助调试
                task_exists = LockTask.objects.filter(id=task_id).first()
                if not task_exists:
                    return Response({
                        'error': f'任务 {task_id} 不存在'
                    }, status=status.HTTP_400_BAD_REQUEST)
                elif task_exists.user != user:
                    return Response({
                        'error': f'任务 {task_id} 不属于当前用户'
                    }, status=status.HTTP_400_BAD_REQUEST)
                elif task_exists.task_type != 'lock':
                    return Response({
                        'error': f'任务 {task_id} 不是带锁任务类型'
                    }, status=status.HTTP_400_BAD_REQUEST)
                elif task_exists.status != 'active':
                    return Response({
                        'error': f'任务 {task_id} 状态为 {task_exists.status}，不是活跃状态'
                    }, status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response({
                        'error': '指定的锁任务不存在、不属于您或不是活跃状态'
                    }, status=status.HTTP_400_BAD_REQUEST)

            # 检查积分
            if hasattr(user, 'coins') and user.coins < bet_amount:
                return Response({
                    'error': '积分不足'
                }, status=status.HTTP_400_BAD_REQUEST)

            # 扣除积分
            if hasattr(user, 'coins'):
                user.deduct_coins(
                    amount=bet_amount,
                    change_type='time_wheel_adjustment',
                    description='时间转盘调整任务时间费用',
                    metadata={'task_id': str(lock_task.id), 'time_change_minutes': time_change_minutes, 'is_increase': is_increase}
                )

            # 记录时间变化前的状态
            previous_end_time = lock_task.end_time

            # 更新指定锁任务的时间
            if is_increase:
                # 增加锁时间
                if lock_task.end_time:
                    lock_task.end_time += timedelta(minutes=time_change_minutes)
                else:
                    lock_task.end_time = timezone.now() + timedelta(minutes=time_change_minutes)
            else:
                # 减少锁时间
                if lock_task.end_time:
                    new_time = lock_task.end_time - timedelta(minutes=time_change_minutes)
                    # 不能减少到当前时间之前
                    lock_task.end_time = max(new_time, timezone.now())
                else:
                    # 如果任务没有结束时间，设置为当前时间（表示立即可以完成）
                    lock_task.end_time = timezone.now()

            lock_task.save()

            # 创建时间线事件记录
            event_type = 'time_wheel_increase' if is_increase else 'time_wheel_decrease'
            actual_change = time_change_minutes if is_increase else -time_change_minutes

            TaskTimelineEvent.objects.create(
                task=lock_task,
                event_type=event_type,
                user=user,
                time_change_minutes=actual_change,
                previous_end_time=previous_end_time,
                new_end_time=lock_task.end_time,
                description=f'时间转盘游戏: 投入{bet_amount}积分，转出{base_time}分钟{"增加" if is_increase else "减少"}时间（总计{time_change_minutes}分钟）',
                metadata={
                    'bet_amount': bet_amount,
                    'base_time_minutes': base_time,
                    'final_time_change': time_change_minutes,
                    'wheel_result': 'increase' if is_increase else 'decrease',
                    'frontend_calculated': True
                }
            )

            # 创建游戏会话记录
            GameSession.objects.create(
                user=user,
                game_type='time_wheel',
                bet_amount=bet_amount
            )

            # 小游戏活跃度奖励
            request.user.update_activity(points=1)

            return Response({
                'success': True,
                'result': 'increase' if is_increase else 'decrease',
                'time_change_minutes': time_change_minutes,
                'new_end_time': lock_task.end_time.isoformat() if lock_task.end_time else None,
                'message': f'{"增加" if is_increase else "减少"}了 {time_change_minutes} 分钟锁时间',
                'remaining_coins': getattr(user, 'coins', 0)
            }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'error': f'游戏失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_drift_bottle(request):
    """创建漂流瓶"""
    serializer = CreateDriftBottleSerializer(data=request.data)
    if serializer.is_valid():
        message = serializer.validated_data['message']
        item_ids = serializer.validated_data.get('item_ids', [])

        try:
            with transaction.atomic():
                user = request.user

                # 检查物品所有权
                items = []
                if item_ids:
                    items = list(Item.objects.filter(
                        id__in=item_ids,
                        owner=user,
                        status='available'
                    ))

                    if len(items) != len(item_ids):
                        return Response({
                            'error': '部分物品不存在或不可用'
                        }, status=status.HTTP_400_BAD_REQUEST)

                # 创建漂流瓶
                drift_bottle = DriftBottle.objects.create(
                    sender=user,
                    message=message,
                    expires_at=timezone.now() + timedelta(days=7)  # 7天后过期
                )

                # 添加物品到漂流瓶
                for item in items:
                    drift_bottle.items.add(item)
                    item.status = 'in_drift_bottle'
                    item.inventory = None  # 从背包中移除
                    item.save()

                return Response({
                    'message': '漂流瓶创建成功',
                    'drift_bottle_id': str(drift_bottle.id),
                    'expires_at': drift_bottle.expires_at.isoformat()
                }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({
                'error': f'创建漂流瓶失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GameListCreateView(generics.ListCreateAPIView):
    """游戏列表和创建"""
    serializer_class = GameSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Game.objects.filter(status__in=['waiting', 'active']).order_by('-created_at')

    def perform_create(self, serializer):
        from rest_framework.exceptions import ValidationError

        # 处理掷骰子游戏的特殊逻辑
        game_type = serializer.validated_data.get('game_type')

        # 只对非掷骰子游戏检查带锁任务限制
        if game_type != 'dice':
            # 检查用户是否有正在进行的锁任务
            active_lock_tasks = LockTask.objects.filter(
                user=self.request.user,
                status='active'
            )

            if not active_lock_tasks.exists():
                raise ValidationError('只有正在进行锁任务时才能创建游戏')
        if game_type == 'dice':
            # 预先掷骰子 (1-6)
            dice_result = random.randint(1, 6)

            # 获取可选的物品奖励
            item_reward_id = self.request.data.get('item_reward_id')
            item_reward_details = None

            if item_reward_id:
                try:
                    # 验证物品是否属于创建者且可用
                    item = Item.objects.get(
                        id=item_reward_id,
                        owner=self.request.user,
                        status='available'
                    )

                    # 缓存物品信息用于显示
                    item_reward_details = {
                        'name': item.item_type.name,
                        'display_name': item.item_type.display_name,
                        'icon': item.item_type.icon,
                        'description': item.item_type.description
                    }

                    # 锁定物品，防止创建者在游戏结束前处置
                    item.status = 'in_game'
                    item.save()

                except Item.DoesNotExist:
                    raise ValidationError('选择的奖励物品不存在或不可用')

            # 设置游戏数据
            game_data = {
                'dice_result': dice_result,
                'item_reward_id': item_reward_id,
                'item_reward_details': item_reward_details
            }

            # 掷骰子游戏固定为一对一（创建者 vs 第一个参与者）
            serializer.validated_data['max_players'] = 1
            serializer.validated_data['game_data'] = game_data

        serializer.save(creator=self.request.user)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def join_game(request, game_id):
    """加入游戏"""
    # Ensure Notification is available in local scope to prevent scoping issues
    from users.models import Notification as NotificationModel

    serializer = JoinGameSerializer(data=request.data)
    if serializer.is_valid():
        try:
            with transaction.atomic():
                game = get_object_or_404(Game, id=game_id, status='waiting')
                user = request.user

                # 只对非掷骰子游戏检查带锁任务限制
                if game.game_type != 'dice':
                    # 检查用户是否有正在进行的锁任务
                    active_lock_tasks = LockTask.objects.filter(
                        user=user,
                        status='active'
                    )

                    if not active_lock_tasks.exists():
                        return Response({
                            'error': '只有正在进行锁任务时才能参与游戏'
                        }, status=status.HTTP_400_BAD_REQUEST)

                # 检查是否已经参与
                if GameParticipant.objects.filter(game=game, user=user).exists():
                    return Response({
                        'error': '您已经参与了这个游戏'
                    }, status=status.HTTP_400_BAD_REQUEST)

                # 检查积分
                if hasattr(user, 'coins') and user.coins < game.bet_amount:
                    return Response({
                        'error': '积分不足'
                    }, status=status.HTTP_400_BAD_REQUEST)

                # 对于掷骰子游戏，如果有物品奖励，需要检查参与者背包空间
                if game.game_type == 'dice' and game.game_data.get('item_reward_id'):
                    from .models import UserInventory
                    inventory, _ = UserInventory.objects.get_or_create(user=user)
                    if inventory.available_slots < 1:
                        return Response({
                            'error': f'背包空间不足，剩余{inventory.available_slots}格，无法参与有奖励物品的游戏'
                        }, status=status.HTTP_400_BAD_REQUEST)

                # 扣除积分
                if hasattr(user, 'coins'):
                    user.deduct_coins(
                        amount=game.bet_amount,
                        change_type='game_participation',
                        description=f'参与{game.get_game_type_display()}游戏消耗',
                        metadata={'game_id': str(game.id), 'game_type': game.game_type}
                    )

                # 获取玩家的行动选择
                action_data = serializer.validated_data.get('action', {})

                # 创建参与记录，存储玩家的选择
                GameParticipant.objects.create(
                    game=game,
                    user=user,
                    action=action_data
                )

                # 小游戏活跃度奖励
                request.user.update_activity(points=1)

                # 检查是否可以开始游戏
                participant_count = game.participants.count()
                print(f"DEBUG: Game {game.id}, type: {game.game_type}, participant_count: {participant_count}, max_players: {game.max_players}")
                if participant_count >= game.max_players:
                    game.status = 'active'
                    game.save()

                    # 开始游戏逻辑（简单的猜拳游戏）
                    if game.game_type == 'rock_paper_scissors':
                        participants = list(GameParticipant.objects.filter(game=game))
                        valid_choices = ['rock', 'paper', 'scissors']

                        # 收集玩家选择并验证
                        results = []
                        valid_participants = []

                        for participant in participants:
                            player_choice = participant.action.get('choice')

                            # 如果玩家没有提供有效选择，随机分配一个
                            if not player_choice or player_choice not in valid_choices:
                                player_choice = random.choice(valid_choices)
                                # 更新参与者的action记录
                                participant.action = {'choice': player_choice}
                                participant.save()

                            valid_participants.append(participant)
                            results.append({
                                'player': participant.user.username,
                                'choice': player_choice
                            })

                        # 确定赢家
                        if len(valid_participants) == 2:
                            p1, p2 = valid_participants
                            choice1 = p1.action['choice']
                            choice2 = p2.action['choice']

                            winner = None
                            if choice1 == choice2:
                                # 平局，重新开始
                                game.status = 'waiting'
                                game.save()

                                # 平局时返还发起人（游戏创建者）的积分
                                creator = game.creator
                                if hasattr(creator, 'coins'):
                                    creator.add_coins(
                                        amount=game.bet_amount,
                                        change_type='game_refund',
                                        description='石头剪刀布游戏平局返还',
                                        metadata={'game_id': str(game.id), 'result': 'tie'}
                                    )

                                # 给双方发送平局通知
                                for participant in valid_participants:
                                    opponent = valid_participants[1] if participant == valid_participants[0] else valid_participants[0]
                                    is_creator = participant.user == creator
                                    message = f'与 {opponent.user.username} 的石头剪刀布游戏平局，游戏重新开始'
                                    if is_creator:
                                        message += f'，已返还 {game.bet_amount} 积分'

                                    NotificationModel.create_notification(
                                        recipient=participant.user,
                                        notification_type='game_result',
                                        actor=opponent.user,
                                        title='石头剪刀布平局',
                                        message=message,
                                        related_object_type='game',
                                        related_object_id=game.id,
                                        extra_data={
                                            'game_type': 'rock_paper_scissors',
                                            'result': 'tie',
                                            'your_choice': participant.action['choice'],
                                            'opponent_choice': opponent.action['choice'],
                                            'opponent_username': opponent.user.username,
                                            'opponent_id': opponent.user.id,
                                            'bet_amount': game.bet_amount,
                                            'coins_refunded': game.bet_amount if is_creator else 0
                                        },
                                        priority='normal'
                                    )

                                return Response({
                                    'message': '平局！游戏重新开始，发起人积分已返还',
                                    'results': results,
                                    'coins_refunded': game.bet_amount
                                })
                            elif (choice1 == 'rock' and choice2 == 'scissors') or \
                                 (choice1 == 'paper' and choice2 == 'rock') or \
                                 (choice1 == 'scissors' and choice2 == 'paper'):
                                winner = p1.user
                                loser = p2.user
                            else:
                                winner = p2.user
                                loser = p1.user

                            # 处理结果 - 存储在result字段中，因为Game模型没有winner字段
                            game.result = {
                                'winner': winner.username,
                                'loser': loser.username,
                                'winner_choice': choice1 if winner == p1.user else choice2,
                                'loser_choice': choice2 if winner == p1.user else choice1,
                                'game_results': results
                            }
                            game.status = 'completed'
                            game.completed_at = timezone.now()
                            game.save()

                            # 输家加时30分钟
                            loser_lock_tasks = LockTask.objects.filter(
                                user=loser,
                                status='active'
                            )
                            for task in loser_lock_tasks:
                                previous_end_time = task.end_time
                                if task.end_time:
                                    task.end_time += timedelta(minutes=30)
                                else:
                                    task.end_time = timezone.now() + timedelta(minutes=30)
                                task.save()

                                # 创建时间线事件记录游戏加时
                                TaskTimelineEvent.objects.create(
                                    task=task,
                                    event_type='overtime_added',
                                    user=None,  # 系统操作
                                    time_change_minutes=30,
                                    previous_end_time=previous_end_time,
                                    new_end_time=task.end_time,
                                    description=f'游戏失败加时: {loser.username} 在{game.game_type}游戏中败给 {winner.username}，增加30分钟锁时间',
                                    metadata={
                                        'game_id': str(game.id),
                                        'game_type': game.game_type,
                                        'winner': winner.username,
                                        'loser': loser.username,
                                        'penalty_minutes': 30
                                    }
                                )

                            # 给获胜者发送胜利通知
                            NotificationModel.create_notification(
                                recipient=winner,
                                notification_type='game_result',
                                actor=loser,
                                title='石头剪刀布获胜',
                                message=f'恭喜！您在与 {loser.username} 的石头剪刀布游戏中获胜，获得 {game.bet_amount} 积分',
                                related_object_type='game',
                                related_object_id=game.id,
                                extra_data={
                                    'game_type': 'rock_paper_scissors',
                                    'result': 'win',
                                    'your_choice': game.result['winner_choice'],
                                    'opponent_choice': game.result['loser_choice'],
                                    'opponent_username': loser.username,
                                    'opponent_id': loser.id,
                                    'bet_amount': game.bet_amount,
                                    'coins_change': game.bet_amount  # 获胜者得到积分
                                },
                                priority='normal'
                            )

                            # 给失败者发送失败通知
                            NotificationModel.create_notification(
                                recipient=loser,
                                notification_type='game_result',
                                actor=winner,
                                title='石头剪刀布失败',
                                message=f'很遗憾，您在与 {winner.username} 的石头剪刀布游戏中失败，锁时间增加30分钟',
                                related_object_type='game',
                                related_object_id=game.id,
                                extra_data={
                                    'game_type': 'rock_paper_scissors',
                                    'result': 'lose',
                                    'your_choice': game.result['loser_choice'],
                                    'opponent_choice': game.result['winner_choice'],
                                    'opponent_username': winner.username,
                                    'opponent_id': winner.id,
                                    'bet_amount': game.bet_amount,
                                    'time_penalty_minutes': 30  # 失败者增加锁时间
                                },
                                priority='normal'
                            )

                            return Response({
                                'message': f'{winner.username} 获胜！{loser.username} 增加30分钟锁时间',
                                'winner': winner.username,
                                'loser': loser.username,
                                'results': results,
                                'coins_change': game.bet_amount,  # 为前端显示积分变化
                                'remaining_coins': getattr(winner, 'coins', 0)  # 获胜者的剩余积分
                            })

                    # 掷骰子游戏逻辑
                    elif game.game_type == 'dice':
                        print(f"DEBUG: Starting dice game logic for game {game.id}")
                        participant = GameParticipant.objects.get(game=game, user=user)
                        participant_guess = participant.action.get('guess', 'big')

                        # 获取预先掷好的骰子结果
                        dice_result = game.game_data.get('dice_result', 1)
                        print(f"DEBUG: Dice result: {dice_result}, participant guess: {participant_guess}")

                        # 判断大小 (4,5,6为大，1,2,3为小)
                        is_big = dice_result >= 4
                        is_correct = (participant_guess == 'big' and is_big) or (participant_guess == 'small' and not is_big)
                        print(f"DEBUG: is_big: {is_big}, is_correct: {is_correct}")

                        # 创建者总是获得参与费用
                        creator = game.creator
                        creator.coins += game.bet_amount
                        creator.save()

                        # 处理物品奖励转移
                        item_transferred = False
                        item_reward_details = None

                        if is_correct and game.game_data.get('item_reward_id'):
                            try:
                                # 验证物品仍然存在且在游戏中
                                reward_item = Item.objects.get(
                                    id=game.game_data['item_reward_id'],
                                    owner=creator,
                                    status='in_game'
                                )

                                # 获取参与者背包
                                participant_inventory, _ = UserInventory.objects.get_or_create(user=user)

                                # 转移物品给获胜者
                                reward_item.owner = user
                                reward_item.inventory = participant_inventory
                                reward_item.status = 'available'
                                reward_item.save()
                                item_transferred = True
                                item_reward_details = game.game_data.get('item_reward_details')

                                # 记录物品转移到游戏会话中
                                GameSession.objects.create(
                                    user=user,
                                    game_type='dice',
                                    bet_amount=game.bet_amount,
                                    result_data={
                                        'dice_result': dice_result,
                                        'guess': participant_guess,
                                        'is_correct': is_correct,
                                        'item_received': item_reward_details,
                                        'creator': creator.username
                                    }
                                )

                            except Item.DoesNotExist:
                                # 物品不再可用，只给积分奖励
                                pass

                        # 如果有奖励物品但参与者没猜中，归还物品给创建者
                        if not is_correct and game.game_data.get('item_reward_id'):
                            try:
                                reward_item = Item.objects.get(
                                    id=game.game_data['item_reward_id'],
                                    owner=creator,
                                    status='in_game'
                                )
                                # 归还给创建者
                                creator_inventory, _ = UserInventory.objects.get_or_create(user=creator)
                                reward_item.inventory = creator_inventory
                                reward_item.status = 'available'
                                reward_item.save()
                            except Item.DoesNotExist:
                                pass

                        # 记录创建者的游戏会话
                        GameSession.objects.create(
                            user=creator,
                            game_type='dice',
                            bet_amount=game.bet_amount,
                            result_data={
                                'dice_result': dice_result,
                                'participant_guess': participant_guess,
                                'participant_won': is_correct,
                                'coins_earned': game.bet_amount,
                                'item_given': item_transferred,
                                'participant': user.username
                            }
                        )

                        # 完成游戏
                        game.status = 'completed'
                        game.completed_at = timezone.now()
                        game.result = {
                            'dice_result': dice_result,
                            'participant_guess': participant_guess,
                            'is_correct': is_correct,
                            'creator': creator.username,
                            'participant': user.username,
                            'item_transferred': item_transferred,
                            'item_details': item_reward_details
                        }
                        game.save()

                        # 发送通知给参与者
                        if is_correct:
                            title = '掷骰子获胜'
                            message = f'恭喜！您猜{participant_guess}，骰子结果是{dice_result}，猜中了！'
                            if item_transferred:
                                message += f'获得奖励物品：{item_reward_details["display_name"]}'
                        else:
                            title = '掷骰子失败'
                            message = f'很遗憾，您猜{participant_guess}，骰子结果是{dice_result}，没有猜中。'

                        NotificationModel.create_notification(
                            recipient=user,
                            notification_type='game_result',
                            actor=creator,
                            title=title,
                            message=message,
                            related_object_type='game',
                            related_object_id=game.id,
                            extra_data={
                                'game_type': 'dice',
                                'dice_result': dice_result,
                                'guess': participant_guess,
                                'is_correct': is_correct,
                                'item_received': item_reward_details if item_transferred else None,
                                'creator_username': creator.username,
                                'creator_id': creator.id,
                                'bet_amount': game.bet_amount
                            },
                            priority='normal'
                        )

                        # 发送通知给创建者
                        creator_message = f'{user.username} 参与了您的掷骰子游戏，猜{participant_guess}，'
                        creator_message += f'骰子结果{dice_result}，{"猜中了" if is_correct else "没猜中"}，'
                        creator_message += f'您获得了 {game.bet_amount} 积分'
                        if item_transferred:
                            creator_message += f'，奖励物品已转移给对方'

                        NotificationModel.create_notification(
                            recipient=creator,
                            notification_type='game_result',
                            actor=user,
                            title='掷骰子游戏完成',
                            message=creator_message,
                            related_object_type='game',
                            related_object_id=game.id,
                            extra_data={
                                'game_type': 'dice',
                                'dice_result': dice_result,
                                'participant_guess': participant_guess,
                                'participant_won': is_correct,
                                'coins_earned': game.bet_amount,
                                'item_given': item_transferred,
                                'participant_username': user.username,
                                'participant_id': user.id,
                                'bet_amount': game.bet_amount
                            },
                            priority='normal'
                        )

                        # 刷新用户对象以获取最新的积分
                        user.refresh_from_db()
                        print(f"DEBUG: Final user coins: {getattr(user, 'coins', 0)}")

                        return Response({
                            'message': f'掷骰子结果：{dice_result}，您猜{participant_guess}，{"猜中了！" if is_correct else "没猜中"}',
                            'dice_result': dice_result,
                            'guess': participant_guess,
                            'is_correct': is_correct,
                            'item_received': item_reward_details if item_transferred else None,
                            'creator_coins_change': game.bet_amount,
                            'remaining_coins': getattr(user, 'coins', 0)
                        })

                return Response({
                    'message': '成功加入游戏',
                    'participants': participant_count + 1,
                    'max_participants': game.max_players
                })

        except Exception as e:
            return Response({
                'error': f'加入游戏失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def get_zone_display_name(zone_name: str) -> str:
    """获取区域显示名称"""
    zone_names = {
        'beach': '月光海滩',
        'forest': '神秘森林',
        'mountain': '雾山',
        'desert': '沙漠绿洲',
        'cave': '深邃洞穴'
    }
    return zone_names.get(zone_name, zone_name)


def get_zone_difficulty(zone_name: str) -> str:
    """根据区域获取难度"""
    zone_difficulty = {
        'beach': 'easy',
        'forest': 'normal',
        'mountain': 'hard',
        'desert': 'normal',
        'cave': 'hard'
    }
    return zone_difficulty.get(zone_name, 'normal')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bury_item(request):
    """掩埋物品 - 新版本：根据区域自动确定难度"""
    serializer = BuryItemSerializer(data=request.data)
    if serializer.is_valid():
        item_id = serializer.validated_data['item_id']
        location_zone = serializer.validated_data['location_zone']
        location_hint = serializer.validated_data['location_hint']
        # 根据区域自动确定难度
        difficulty = get_zone_difficulty(location_zone)

        try:
            with transaction.atomic():
                user = request.user

                # 首先检查物品是否存在
                try:
                    item = Item.objects.get(id=item_id)
                except Item.DoesNotExist:
                    return Response({
                        'error': '物品不存在'
                    }, status=status.HTTP_404_NOT_FOUND)

                # 检查物品是否属于当前用户（只检查当前所属者 owner，不检查原始所属者 original_owner）
                if item.owner_id != user.id:
                    return Response({
                        'error': f'该物品不属于您，无法掩埋。物品当前所属者ID: {item.owner_id}，您的ID: {user.id}'
                    }, status=status.HTTP_403_FORBIDDEN)

                # 检查物品状态
                if item.status != 'available':
                    status_display = dict(Item.STATUS_CHOICES).get(item.status, item.status)
                    return Response({
                        'error': f'物品当前状态为"{status_display}"，无法掩埋。只有状态为"可用"的物品才能掩埋。'
                    }, status=status.HTTP_400_BAD_REQUEST)

                # 创建掩埋宝物记录
                buried_treasure = BuriedTreasure.objects.create(
                    burier=user,
                    item=item,
                    location_zone=location_zone,
                    location_hint=location_hint,
                    difficulty=difficulty,
                    expires_at=timezone.now() + timedelta(days=30)  # 30天后过期
                )

                # 更新物品状态
                item.status = 'buried'
                item.inventory = None  # 从背包中移除
                item.save()

                # 掩埋活跃度奖励
                request.user.update_activity(points=1)

                return Response({
                    'message': f'物品已掩埋到 {get_zone_display_name(location_zone)} ({getDifficultyText(difficulty)})',
                    'treasure_id': str(buried_treasure.id),
                    'location_zone': location_zone,
                    'difficulty': difficulty,
                    'expires_at': buried_treasure.expires_at.isoformat()
                }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f" bury_item error: {e}", exc_info=True)
            return Response({
                'error': f'掩埋失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def explore_zone(request):
    """探索区域寻找宝物 - 带冷却时间和斐波那契费用递增"""
    serializer = ExploreZoneSerializer(data=request.data)
    if serializer.is_valid():
        zone_name = serializer.validated_data['zone_name']
        card_position = serializer.validated_data.get('card_position', 0)  # 用户选择的卡牌位置

        try:
            with transaction.atomic():
                user = request.user
                today = timezone.now().date()

                # 获取或创建今日探索记录
                exploration_record, created = UserZoneExploration.objects.get_or_create(
                    user=user,
                    zone_name=zone_name,
                    exploration_date=today,
                    defaults={
                        'daily_count': 0,
                        'last_exploration_at': timezone.now() - timedelta(seconds=COOLDOWN_SECONDS + 1)
                    }
                )

                # 检查冷却时间
                time_since_last = timezone.now() - exploration_record.last_exploration_at
                cooldown_remaining = max(0, COOLDOWN_SECONDS - int(time_since_last.total_seconds()))

                if cooldown_remaining > 0:
                    retry_after = timezone.now() + timedelta(seconds=cooldown_remaining)
                    return Response({
                        'error': '探索冷却中',
                        'cooldown_seconds': cooldown_remaining,
                        'retry_after': retry_after.isoformat()
                    }, status=status.HTTP_429_TOO_MANY_REQUESTS)

                # 计算本次探索费用（基于今日探索次数，斐波那契递增）
                next_exploration_number = exploration_record.daily_count + 1
                exploration_cost = get_fibonacci_cost(next_exploration_number)

                # 检查用户积分
                if hasattr(user, 'coins') and user.coins < exploration_cost:
                    return Response({
                        'error': '积分不足',
                        'required': exploration_cost,
                        'current': user.coins
                    }, status=status.HTTP_400_BAD_REQUEST)

                # 扣除探索费用
                if hasattr(user, 'coins'):
                    user.deduct_coins(
                        amount=exploration_cost,
                        change_type='exploration',
                        description='探索消耗',
                        metadata={'zone': zone_name, 'exploration_number': next_exploration_number}
                    )

                # 更新探索记录
                exploration_record.daily_count = next_exploration_number
                exploration_record.last_exploration_at = timezone.now()
                exploration_record.save()

                # 计算下次探索费用
                next_cost = get_fibonacci_cost(next_exploration_number + 1)

                # 探索活跃度奖励
                request.user.update_activity(points=1)

                # 查找该区域的可发现宝物
                available_treasures = BuriedTreasure.objects.filter(
                    location_zone=zone_name,
                    status='buried',
                    expires_at__gt=timezone.now()
                ).exclude(burier=user)  # 不能发现自己埋的宝物

                # 根据区域确定难度和卡牌数量
                zone_config = {
                    'beach': {'difficulty': 'easy', 'card_count': 3},
                    'forest': {'difficulty': 'normal', 'card_count': 6},
                    'mountain': {'difficulty': 'hard', 'card_count': 9},
                    'desert': {'difficulty': 'normal', 'card_count': 6},
                    'cave': {'difficulty': 'hard', 'card_count': 9}
                }

                config = zone_config.get(zone_name, {'difficulty': 'normal', 'card_count': 6})
                card_count = config['card_count']

                # 生成卡牌并处理翻牌结果
                cards = []
                treasure_positions = set()
                selected_treasure = None
                found_item = None
                selected_treasures = []
                position_to_treasure = {}

                if available_treasures.exists():
                    # 随机选择一些宝物放入卡牌中
                    treasure_list = list(available_treasures)
                    # 最多放置卡数量-1个宝物，确保至少有一个空卡
                    max_treasures = min(len(treasure_list), card_count - 1)
                    selected_treasures = random.sample(treasure_list, max_treasures)

                    # 随机分配位置 - 将宝物分配到随机位置
                    possible_positions = list(range(card_count))
                    # 随机选择位置（保持列表顺序用于映射）
                    selected_positions = random.sample(possible_positions, len(selected_treasures))
                    treasure_positions = set(selected_positions)

                    # 创建位置到宝物的映射
                    # selected_positions[i] 位置对应 selected_treasures[i] 宝物
                    position_to_treasure = {pos: treasure for pos, treasure in zip(selected_positions, selected_treasures)}

                    # 检查用户选择的卡牌是否有宝物
                    if card_position in treasure_positions:
                        selected_treasure = position_to_treasure[card_position]

                        # 检查背包容量
                        inventory, _ = UserInventory.objects.get_or_create(user=user)
                        if inventory.available_slots < 1:
                            return Response({
                                'error': '背包空间不足，无法获得宝物'
                            }, status=status.HTTP_400_BAD_REQUEST)

                        # 转移物品所有权
                        item = selected_treasure.item
                        item.owner = user
                        item.inventory = inventory
                        item.status = 'available'
                        item.save()

                        # 更新宝物状态
                        selected_treasure.finder = user
                        selected_treasure.status = 'found'
                        selected_treasure.found_at = timezone.now()
                        selected_treasure.save()

                        # 给掩埋者一些积分奖励
                        reward_amount = 0
                        if hasattr(selected_treasure.burier, 'coins'):
                            reward_amount = {
                                'easy': 5,
                                'normal': 10,
                                'hard': 20
                            }.get(selected_treasure.difficulty, 10)
                            selected_treasure.burier.add_coins(
                                amount=reward_amount,
                                change_type='treasure_discovered',
                                description='宝物被发现奖励',
                                metadata={
                                    'treasure_id': str(selected_treasure.id),
                                    'finder': user.username,
                                    'difficulty': selected_treasure.difficulty
                                }
                            )

                        # 创建宝物发现通知
                        Notification.create_notification(
                            recipient=selected_treasure.burier,
                            notification_type='treasure_found',
                            actor=user,
                            related_object_type='buried_treasure',
                            related_object_id=selected_treasure.id,
                            extra_data={
                                'item_type': item.item_type.display_name,
                                'location_zone': selected_treasure.location_zone,
                                'difficulty': selected_treasure.difficulty,
                                'reward_amount': reward_amount,
                                'finder': user.username,
                                'found_at': selected_treasure.found_at.isoformat()
                            },
                            priority='normal'
                        )

                        found_item = {
                            'id': str(item.id),
                            'type': item.item_type.display_name,
                            'properties': item.properties
                        }

                # 创建所有卡牌（展示完整结果）
                # position_to_treasure 已在上方创建，直接使用

                for i in range(card_count):
                    if i in treasure_positions:
                        treasure = position_to_treasure[i]

                        # 如果这个宝物已经被找到，标记为已找到
                        is_found = treasure == selected_treasure

                        cards.append({
                            'position': i,
                            'has_treasure': True,
                            'treasure_id': str(treasure.id),
                            'location_hint': treasure.location_hint,
                            'difficulty': treasure.difficulty,
                            'item_type': treasure.item.item_type.display_name,
                            'burier': treasure.burier.username,
                            'is_found': is_found
                        })
                    else:
                        cards.append({
                            'position': i,
                            'has_treasure': False
                        })

                # 不打乱卡牌顺序，保持位置一致性

                return Response({
                    'message': f'在 {get_zone_display_name(zone_name)} 区域探索完成！花费{exploration_cost}积分',
                    'zone': zone_name,
                    'exploration_cost': exploration_cost,
                    'today_count': exploration_record.daily_count,
                    'cooldown_remaining': COOLDOWN_SECONDS,
                    'next_cost': next_cost,
                    'difficulty': config['difficulty'],
                    'card_count': card_count,
                    'cards': cards,
                    'selected_position': card_position,
                    'found_item': found_item,
                    'treasure_count': len([c for c in cards if c['has_treasure']]),
                    'cost': exploration_cost,
                    'success': found_item is not None
                }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'error': f'探索失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def find_treasure(request):
    """挖掘发现的宝物"""
    serializer = FindTreasureSerializer(data=request.data)
    if serializer.is_valid():
        treasure_id = serializer.validated_data['treasure_id']

        try:
            with transaction.atomic():
                user = request.user

                # 获取宝物
                treasure = get_object_or_404(
                    BuriedTreasure,
                    id=treasure_id,
                    status='buried'
                )

                # 检查是否可以挖掘（不能挖掘自己埋的）
                if treasure.burier == user:
                    return Response({
                        'error': '不能挖掘自己埋藏的宝物'
                    }, status=status.HTTP_400_BAD_REQUEST)

                # 检查背包容量
                inventory, _ = UserInventory.objects.get_or_create(user=user)
                if inventory.available_slots < 1:
                    return Response({
                        'error': '背包空间不足'
                    }, status=status.HTTP_400_BAD_REQUEST)

                # 转移物品所有权
                item = treasure.item
                item.owner = user
                item.inventory = inventory
                item.status = 'available'
                item.save()

                # 更新宝物状态
                treasure.finder = user
                treasure.status = 'found'
                treasure.found_at = timezone.now()
                treasure.save()

                # 给掩埋者一些积分奖励
                reward_amount = 0
                if hasattr(treasure.burier, 'coins'):
                    reward_amount = {
                        'easy': 5,
                        'normal': 10,
                        'hard': 20
                    }.get(treasure.difficulty, 10)

                    treasure.burier.coins += reward_amount
                    treasure.burier.save()

                # 创建宝物发现通知
                Notification.create_notification(
                    recipient=treasure.burier,
                    notification_type='treasure_found',
                    actor=user,
                    related_object_type='buried_treasure',
                    related_object_id=treasure.id,
                    extra_data={
                        'item_type': item.item_type.display_name,
                        'location_zone': treasure.location_zone,
                        'difficulty': treasure.difficulty,
                        'reward_amount': reward_amount,
                        'finder': user.username,
                        'found_at': treasure.found_at.isoformat()
                    },
                    priority='normal'
                )

                return Response({
                    'message': '成功挖掘到宝物！',
                    'item': {
                        'id': str(item.id),
                        'type': item.item_type.display_name,
                        'properties': item.properties
                    },
                    'reward_to_burier': reward_amount,
                    'remaining_slots': inventory.available_slots
                }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'error': f'挖掘失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BuriedTreasureListView(generics.ListAPIView):
    """掩埋宝物列表"""
    serializer_class = BuriedTreasureSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        status_filter = self.request.query_params.get('status', 'buried')

        queryset = BuriedTreasure.objects.filter(burier=user)

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset.order_by('-created_at')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_available_zones(request):
    """获取可探索的区域列表（包含冷却状态和费用信息）"""
    zones = [
        {
            'name': 'forest',
            'display_name': '神秘森林',
            'description': '古老的森林，充满了未知的秘密',
            'difficulty': 'normal'
        },
        {
            'name': 'mountain',
            'display_name': '雾山',
            'description': '云雾缭绕的高山，隐藏着珍贵的宝物',
            'difficulty': 'hard'
        },
        {
            'name': 'beach',
            'display_name': '月光海滩',
            'description': '月光下的海滩，经常有意外收获',
            'difficulty': 'easy'
        },
        {
            'name': 'desert',
            'display_name': '沙漠绿洲',
            'description': '干燥的沙漠中的生命之源',
            'difficulty': 'normal'
        },
        {
            'name': 'cave',
            'display_name': '深邃洞穴',
            'description': '黑暗的洞穴深处藏着最珍贵的财宝',
            'difficulty': 'hard'
        }
    ]

    user = request.user
    today = timezone.now().date()

    # 统计每个区域的宝物数量和冷却状态
    for zone in zones:
        zone_name = zone['name']

        # 宝物数量
        treasure_count = BuriedTreasure.objects.filter(
            location_zone=zone_name,
            status='buried',
            expires_at__gt=timezone.now()
        ).count()
        zone['treasure_count'] = treasure_count

        # 获取或创建今日探索记录
        exploration_record, _ = UserZoneExploration.objects.get_or_create(
            user=user,
            zone_name=zone_name,
            exploration_date=today,
            defaults={
                'daily_count': 0,
                'last_exploration_at': timezone.now() - timedelta(seconds=COOLDOWN_SECONDS + 1)
            }
        )

        # 计算冷却状态
        time_since_last = timezone.now() - exploration_record.last_exploration_at
        cooldown_remaining = max(0, COOLDOWN_SECONDS - int(time_since_last.total_seconds()))

        # 添加冷却和费用信息
        zone['cooldown_seconds'] = cooldown_remaining
        zone['is_cooldown'] = cooldown_remaining > 0
        zone['today_count'] = exploration_record.daily_count
        zone['next_cost'] = get_fibonacci_cost(exploration_record.daily_count + 1)

    return Response({
        'zones': zones
    }, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def cancel_game(request, game_id):
    """取消游戏"""
    try:
        with transaction.atomic():
            game = get_object_or_404(Game, id=game_id)
            user = request.user

            # 检查权限：只能取消自己创建的且状态为waiting的游戏
            if game.creator != user:
                return Response({
                    'error': '只能取消自己创建的游戏'
                }, status=status.HTTP_403_FORBIDDEN)

            if game.status != 'waiting':
                return Response({
                    'error': '只能取消等待中的游戏'
                }, status=status.HTTP_400_BAD_REQUEST)

            # 检查是否已有其他参与者（除了创建者自己）
            other_participants = GameParticipant.objects.filter(game=game).exclude(user=user)
            if other_participants.exists():
                return Response({
                    'error': '已有其他玩家参与，无法取消游戏'
                }, status=status.HTTP_400_BAD_REQUEST)

            # 返还积分给创建者
            if hasattr(user, 'coins'):
                user.coins += game.bet_amount
                user.save()

            # 返还物品奖励给创建者（如果有的话）
            item_returned = False
            if game.game_type == 'dice' and game.game_data.get('item_reward_id'):
                try:
                    # 获取物品并返还给创建者
                    reward_item = Item.objects.get(
                        id=game.game_data['item_reward_id'],
                        owner=user,
                        status='in_game'
                    )

                    # 确保物品回到创建者的背包
                    inventory, _ = UserInventory.objects.get_or_create(user=user)
                    reward_item.inventory = inventory
                    reward_item.status = 'available'  # 解锁物品
                    reward_item.save()
                    item_returned = True

                except Item.DoesNotExist:
                    # 物品已经不存在或状态异常，忽略
                    pass

            # 删除游戏
            game.delete()

            message = '游戏已取消，积分已返还'
            if item_returned:
                message += '，奖励物品已返还'

            return Response({
                'message': message,
                'refunded_amount': game.bet_amount,
                'remaining_coins': getattr(user, 'coins', 0),
                'item_returned': item_returned
            }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'error': f'取消游戏失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def revoke_item_prize(request, item_id):
    """
    撤销物品的奖品预留状态
    1. 验证物品状态为 in_game
    2. 验证用户是物品拥有者
    3. 查找并取消关联的游戏
    4. 返还物品到背包
    """
    try:
        with transaction.atomic():
            user = request.user

            # 获取物品并验证
            item = get_object_or_404(
                Item,
                id=item_id,
                owner=user
            )

            # 验证物品状态为 in_game
            if item.status != 'in_game':
                return Response({
                    'error': '该物品未被预留为游戏奖品，无法撤销'
                }, status=status.HTTP_400_BAD_REQUEST)

            # 查找关联的游戏
            # 游戏通过 game_data.item_reward_id 引用物品
            game = Game.objects.filter(
                game_data__item_reward_id=str(item_id),
                status='waiting'
            ).first()

            if not game:
                return Response({
                    'error': '未找到关联的等待中游戏，可能游戏已开始或已结束'
                }, status=status.HTTP_400_BAD_REQUEST)

            # 验证游戏创建者是当前用户
            if game.creator != user:
                return Response({
                    'error': '只能撤销自己创建的游戏奖品'
                }, status=status.HTTP_403_FORBIDDEN)

            # 检查是否已有其他参与者
            other_participants = GameParticipant.objects.filter(game=game).exclude(user=user)
            if other_participants.exists():
                return Response({
                    'error': '已有其他玩家参与，无法撤销游戏'
                }, status=status.HTTP_400_BAD_REQUEST)

            # 返还积分给创建者
            refunded_amount = 0
            if hasattr(user, 'coins'):
                user.coins += game.bet_amount
                user.save()
                refunded_amount = game.bet_amount

            # 返还物品到背包
            inventory, _ = UserInventory.objects.get_or_create(user=user)
            item.inventory = inventory
            item.status = 'available'
            item.save()

            # 删除游戏
            game.delete()

            # 创建通知
            try:
                Notification.objects.create(
                    user=user,
                    notification_type='game_cancelled',
                    title='游戏已取消',
                    message=f'您取消了掷骰子游戏，{game.bet_amount}积分和奖品{item.item_type.display_name}已返还到您的背包'
                )
            except Exception:
                # 通知创建失败不影响主流程
                pass

            return Response({
                'message': '奖品预留已撤销，游戏已取消',
                'refunded_amount': refunded_amount,
                'remaining_coins': getattr(user, 'coins', 0),
                'item_returned': True,
                'item_name': item.item_type.display_name
            }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'error': f'撤销奖品预留失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def discard_item(request):
    """丢弃物品"""
    try:
        item_id = request.data.get('item_id')
        if not item_id:
            return Response({
                'error': '缺少物品ID'
            }, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            user = request.user

            # 获取要丢弃的物品
            item = get_object_or_404(
                Item,
                id=item_id,
                owner=user,
                status='available'
            )

            # 删除物品（设置状态为已丢弃并从背包中移除）
            item.status = 'discarded'
            item.inventory = None  # 从背包中移除
            item.save()

            return Response({
                'message': f'成功丢弃 {item.item_type.display_name}'
            }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'error': f'丢弃物品失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def return_item_to_original_owner(request):
    """归还物品给原始拥有者"""
    try:
        item_id = request.data.get('item_id')
        if not item_id:
            return Response({
                'error': '缺少物品ID'
            }, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            user = request.user

            # 获取物品
            item = get_object_or_404(
                Item,
                id=item_id,
                owner=user,  # 当前拥有者必须是请求用户
                status='available'
            )

            # 检查是否有原始拥有者
            if not item.original_owner:
                return Response({
                    'error': '此物品没有原始拥有者，无法归还'
                }, status=status.HTTP_400_BAD_REQUEST)

            # 检查原始拥有者不是当前拥有者
            if item.original_owner == user:
                return Response({
                    'error': '您已经是此物品的原始拥有者'
                }, status=status.HTTP_400_BAD_REQUEST)

            # 获取原始拥有者的背包
            original_inventory, _ = UserInventory.objects.get_or_create(user=item.original_owner)

            # 检查原始拥有者背包容量
            if original_inventory.available_slots < 1:
                return Response({
                    'error': f'归还失败：{item.original_owner.username} 的背包已满（{original_inventory.used_slots}/{original_inventory.max_slots}）'
                }, status=status.HTTP_400_BAD_REQUEST)

            # 从当前用户背包中移除
            current_inventory = item.inventory
            if current_inventory:
                item.inventory = None

            # 归还给原始拥有者
            item.owner = item.original_owner
            item.inventory = original_inventory
            item.save()

            # 创建通知给原始拥有者
            Notification.create_notification(
                recipient=item.original_owner,
                notification_type='item_received',
                actor=user,
                title='物品归还',
                message=f'{user.username} 将 {item.item_type.display_name} 归还给您',
                related_object_type='item',
                related_object_id=item.id,
                extra_data={
                    'item_type': item.item_type.name,
                    'item_display_name': item.item_type.display_name,
                    'returned_by': user.username
                }
            )

            return Response({
                'message': f'成功将 {item.item_type.display_name} 归还给 {item.original_owner.username}',
                'item_id': str(item.id),
                'original_owner': item.original_owner.username
            }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'error': f'归还物品失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_share_link(request):
    """创建分享链接"""
    try:
        item_id = request.data.get('item_id')
        if not item_id:
            return Response({
                'error': '缺少物品ID'
            }, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            user = request.user

            # 获取要分享的物品
            item = get_object_or_404(
                Item,
                id=item_id,
                owner=user,
                status='available'
            )

            # 检查物品类型是否可分享 (photo, note, key, little_treasury, detection_radar, blizzard_bottle, sun_bottle, time_hourglass, lucky_charm, energy_potion, time_anchor, exploration_compass, influence_crown, small_campfire)
            if item.item_type.name not in ['photo', 'note', 'key', 'little_treasury', 'detection_radar', 'blizzard_bottle', 'sun_bottle', 'time_hourglass', 'lucky_charm', 'energy_potion', 'time_anchor', 'exploration_compass', 'influence_crown', 'small_campfire']:
                return Response({
                    'error': f'{item.item_type.display_name} 不支持分享'
                }, status=status.HTTP_400_BAD_REQUEST)

            # 检查该物品是否已有活跃的分享链接
            existing_share = SharedItem.objects.filter(
                sharer=user,
                item=item,
                status='active',
                expires_at__gt=timezone.now()
            ).first()

            if existing_share:
                # 如果已有活跃分享链接，重用现有的
                shared_item = existing_share
                share_token = existing_share.share_token
            else:
                # 生成新的分享token
                import secrets
                share_token = secrets.token_urlsafe(32)

                # 创建分享记录
                shared_item = SharedItem.objects.create(
                    sharer=user,
                    item=item,
                    share_token=share_token,
                    expires_at=timezone.now() + timedelta(hours=24)  # 24小时后过期
                )

            # 物品保持在背包中，不改变状态，只有被成功领取后才转移

            # 生成分享链接URL
            from django.conf import settings
            base_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
            share_url = f"{base_url}/claim/{share_token}"

            return Response({
                'message': f'成功创建 {item.item_type.display_name} 的分享链接',
                'share_url': share_url,
                'share_id': str(shared_item.id),
                'expires_at': shared_item.expires_at.isoformat()
            }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({
            'error': f'创建分享链接失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def claim_shared_item(request, share_token):
    """领取分享的物品"""
    try:
        with transaction.atomic():
            user = request.user

            # 获取分享记录
            shared_item = get_object_or_404(
                SharedItem,
                share_token=share_token,
                status='active',
                expires_at__gt=timezone.now()
            )

            # 检查不能领取自己分享的物品
            if shared_item.sharer == user:
                return Response({
                    'error': '不能领取自己分享的物品'
                }, status=status.HTTP_400_BAD_REQUEST)

            # 验证物品仍然属于原分享者且状态为可用
            item = shared_item.item
            if item.owner != shared_item.sharer:
                return Response({
                    'error': '物品已不属于原分享者，无法领取'
                }, status=status.HTTP_400_BAD_REQUEST)

            if item.status != 'available':
                return Response({
                    'error': f'物品状态异常（{item.status}），无法领取'
                }, status=status.HTTP_400_BAD_REQUEST)

            # 检查背包容量
            inventory, _ = UserInventory.objects.get_or_create(user=user)
            if inventory.available_slots < 1:
                return Response({
                    'error': f'背包空间不足，剩余{inventory.available_slots}格'
                }, status=status.HTTP_400_BAD_REQUEST)

            # 转移物品所有权（从原主人背包转移到领取者背包）
            item.owner = user
            item.inventory = inventory  # 移到领取者背包
            item.status = 'available'
            item.save()

            # 更新分享状态
            shared_item.claimer = user
            shared_item.status = 'claimed'
            shared_item.claimed_at = timezone.now()
            shared_item.save()

            # 创建通知给分享者
            Notification.create_notification(
                recipient=shared_item.sharer,
                notification_type='item_shared',
                actor=user,
                title='物品被领取',
                message=f'{user.username} 领取了您分享的 {item.item_type.display_name}',
                related_object_type='shared_item',
                related_object_id=shared_item.id,
                extra_data={
                    'item_type': item.item_type.name,
                    'item_display_name': item.item_type.display_name,
                    'claimed_by': user.username,
                    'claimed_at': shared_item.claimed_at.isoformat()
                }
            )

            # 给分享者增加活跃度
            shared_item.sharer.update_activity(points=1)

            return Response({
                'message': f'成功领取 {item.item_type.display_name}！',
                'item': {
                    'id': str(item.id),
                    'type': item.item_type.display_name,
                    'properties': item.properties
                },
                'sharer': shared_item.sharer.username,
                'remaining_slots': inventory.available_slots
            }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'error': f'领取物品失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def use_universal_key(request):
    """使用万能钥匙直接完成带锁任务"""
    try:
        task_id = request.data.get('task_id')
        universal_key_id = request.data.get('universal_key_id')

        if not task_id or not universal_key_id:
            return Response({
                'error': '缺少必要参数：task_id 和 universal_key_id'
            }, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            user = request.user

            # 验证万能钥匙
            try:
                universal_key = Item.objects.get(
                    id=universal_key_id,
                    owner=user,
                    item_type__name='key',
                    status='available'
                )

                # 检查是否为万能钥匙（通过商店物品名称判断）
                purchase_record = Purchase.objects.filter(
                    item=universal_key,
                    store_item__name='通用钥匙'
                ).first()

                if not purchase_record:
                    return Response({
                        'error': '指定的物品不是万能钥匙'
                    }, status=status.HTTP_400_BAD_REQUEST)

            except Item.DoesNotExist:
                return Response({
                    'error': '万能钥匙不存在或不可用'
                }, status=status.HTTP_400_BAD_REQUEST)

            # 验证带锁任务
            try:
                lock_task = LockTask.objects.get(
                    id=task_id,
                    user=user,
                    task_type='lock'
                )
            except LockTask.DoesNotExist:
                return Response({
                    'error': '指定的带锁任务不存在或不属于您'
                }, status=status.HTTP_400_BAD_REQUEST)

            # 检查任务状态是否可以使用万能钥匙
            if lock_task.status not in ['active', 'voting', 'voting_passed']:
                return Response({
                    'error': f'任务状态为 {lock_task.status}，任务不在可完成状态'
                }, status=status.HTTP_400_BAD_REQUEST)

            can_complete, reason_response = validate_task_completion_conditions(lock_task, user, require_has_key=False)
            if not can_complete:
                return reason_response

            # 记录使用前状态
            previous_status = lock_task.status
            previous_end_time = lock_task.end_time

            # 直接完成任务
            lock_task.status = 'completed'
            lock_task.completed_at = timezone.now()
            lock_task.save()

            # 销毁万能钥匙
            universal_key.status = 'used'
            universal_key.used_at = timezone.now()
            universal_key.inventory = None  # 从背包中移除
            universal_key.save()

            # 销毁任务相关的所有钥匙道具（原始钥匙等）
            from tasks.utils import destroy_task_keys
            destroy_result = destroy_task_keys(lock_task, reason="universal_key_used", user=user, metadata={
                'universal_key_id': str(universal_key.id),
                'completion_method': 'universal_key'
            })

            # 使用与正常完成任务相同的奖励机制（时间奖励）
            # 1. 处理所有未发放的小时奖励
            from tasks.views import _process_task_hourly_rewards, _calculate_completion_bonus
            hourly_rewards_processed = _process_task_hourly_rewards(lock_task)

            # 2. 计算并发放完成奖励（基于难度的一次性奖励）
            completion_bonus = _calculate_completion_bonus(lock_task)
            total_reward_coins = completion_bonus
            if completion_bonus > 0:
                user.coins += completion_bonus
                user.save()

            # 创建任务完成时间线事件
            completion_metadata = {
                'completion_method': 'universal_key',
                'universal_key_id': str(universal_key.id),
                'previous_status': previous_status,
                'hourly_rewards_processed': hourly_rewards_processed,
                'completion_bonus': completion_bonus,
                'total_reward_coins': total_reward_coins,
                'key_used': True,
                'reward_system': 'hourly_plus_completion_bonus'
            }

            # 添加钥匙销毁信息到元数据中
            if destroy_result['success']:
                completion_metadata.update({
                    'keys_destroyed': destroy_result['keys_destroyed'],
                    'destroyed_key_details': destroy_result['destroyed_keys']
                })

            TaskTimelineEvent.objects.create(
                task=lock_task,
                event_type='task_completed',
                user=user,
                time_change_minutes=0,
                previous_end_time=previous_end_time,
                new_end_time=lock_task.end_time,
                description=f'使用万能钥匙直接完成任务，获得 {hourly_rewards_processed} 小时奖励积分 + {completion_bonus} 完成奖励积分{"，已销毁 " + str(destroy_result["keys_destroyed"]) + " 个相关钥匙" if destroy_result["success"] and destroy_result["keys_destroyed"] > 0 else ""}',
                metadata=completion_metadata
            )

            # 创建万能钥匙使用通知
            Notification.create_notification(
                recipient=user,
                notification_type='coins_earned_task_reward',
                title='万能钥匙使用成功',
                message=f'使用万能钥匙完成任务《{lock_task.title}》，获得 {hourly_rewards_processed} 小时奖励积分 + {completion_bonus} 完成奖励积分',
                related_object_type='lock_task',
                related_object_id=lock_task.id,
                extra_data={
                    'task_title': lock_task.title,
                    'task_difficulty': lock_task.difficulty,
                    'completion_method': 'universal_key',
                    'hourly_rewards_processed': hourly_rewards_processed,
                    'completion_bonus': completion_bonus,
                    'total_reward_coins': total_reward_coins,
                    'previous_status': previous_status
                },
                priority='normal'
            )

            return Response({
                'message': f'成功使用万能钥匙完成任务《{lock_task.title}》！',
                'task_id': str(lock_task.id),
                'task_title': lock_task.title,
                'previous_status': previous_status,
                'new_status': 'completed',
                'reward_coins': total_reward_coins,
                'remaining_coins': getattr(user, 'coins', 0),
                'completion_time': lock_task.completed_at.isoformat()
            }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'error': f'使用万能钥匙失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_task_key_ownership(request):
    """检查用户是否拥有指定任务的原始钥匙"""
    try:
        task_ids = request.data.get('task_ids', [])
        if not task_ids:
            return Response({
                'error': '缺少任务ID列表'
            }, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        results = []

        for task_id in task_ids:
            try:
                # 查找该任务对应的钥匙
                task_key_item = Item.objects.filter(
                    item_type__name='key',
                    owner=user,  # 当前持有者必须是请求用户
                    status='available',
                    properties__task_id=str(task_id)
                ).first()

                has_original_key = task_key_item is not None

                results.append({
                    'task_id': task_id,
                    'has_original_key': has_original_key,
                    'key_holder': user.username if has_original_key else None
                })

            except Exception as e:
                results.append({
                    'task_id': task_id,
                    'has_original_key': False,
                    'error': str(e)
                })

        return Response({
            'results': results
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'error': f'检查钥匙所有权失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_task_key_holder(request, task_id):
    """获取指定任务的当前钥匙持有者信息"""
    try:
        # 查找该任务对应的钥匙
        task_key_item = Item.objects.filter(
            item_type__name='key',
            status='available',
            properties__task_id=str(task_id)
        ).first()

        if not task_key_item:
            return Response({
                'task_id': task_id,
                'has_key': False,
                'key_holder': None,
                'message': '该任务没有可用的钥匙'
            }, status=status.HTTP_200_OK)

        # 返回当前钥匙持有者信息
        key_holder = task_key_item.owner
        return Response({
            'task_id': task_id,
            'has_key': True,
            'key_holder': {
                'id': key_holder.id,
                'username': key_holder.username,
                'is_current_user': key_holder == request.user
            },
            'original_owner': {
                'id': task_key_item.original_owner.id if task_key_item.original_owner else None,
                'username': task_key_item.original_owner.username if task_key_item.original_owner else None
            } if task_key_item.original_owner else None
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'error': f'获取钥匙持有者信息失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def deposit_treasury_coins(request, item_id):
    """存入积分到小金库"""
    try:
        amount = request.data.get('amount', 0)

        # 验证输入
        if not isinstance(amount, int) or amount <= 0:
            return Response({
                'error': '存入数量必须是正整数'
            }, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            user = request.user

            # 获取小金库道具
            try:
                treasury_item = Item.objects.get(
                    id=item_id,
                    owner=user,
                    item_type__name='little_treasury',
                    status='available'
                )
            except Item.DoesNotExist:
                return Response({
                    'error': '小金库道具不存在或不可用'
                }, status=status.HTTP_404_NOT_FOUND)

            # 检查用户积分是否足够
            if not hasattr(user, 'coins') or user.coins < amount:
                return Response({
                    'error': f'积分不足，您当前有 {getattr(user, "coins", 0)} 积分'
                }, status=status.HTTP_400_BAD_REQUEST)

            # 检查小金库是否已有积分
            current_stored = treasury_item.properties.get('stored_coins', 0)
            if current_stored > 0:
                return Response({
                    'error': '小金库已经存储了积分，无法再次存入'
                }, status=status.HTTP_400_BAD_REQUEST)

            # 扣除用户积分
            user.coins -= amount
            user.save(update_fields=['coins'])

            # 更新小金库属性
            treasury_item.properties.update({
                'stored_coins': amount,
                'depositor_username': user.username,
                'deposit_time': timezone.now().isoformat()
            })
            treasury_item.save(update_fields=['properties'])

            return Response({
                'success': True,
                'message': f'成功存入 {amount} 积分到小金库',
                'stored_coins': amount,
                'user_remaining_coins': user.coins
            }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'error': f'存入积分失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def withdraw_treasury_coins(request, item_id):
    """从小金库提取积分（销毁道具）"""
    try:
        with transaction.atomic():
            user = request.user

            # 获取小金库道具
            try:
                treasury_item = Item.objects.get(
                    id=item_id,
                    owner=user,
                    item_type__name='little_treasury',
                    status='available'
                )
            except Item.DoesNotExist:
                return Response({
                    'error': '小金库道具不存在或不可用'
                }, status=status.HTTP_404_NOT_FOUND)

            # 获取存储的积分数量
            stored_coins = treasury_item.properties.get('stored_coins', 0)

            if stored_coins <= 0:
                return Response({
                    'error': '小金库中没有积分可以提取'
                }, status=status.HTTP_400_BAD_REQUEST)

            # 将积分添加到用户账户
            user.add_coins(
                amount=stored_coins,
                change_type='treasury_withdrawal',
                description='小金库提取',
                metadata={
                    'depositor_username': treasury_item.properties.get('depositor_username'),
                    'deposit_time': treasury_item.properties.get('deposit_time')
                }
            )

            # 记录存入者信息（用于通知）
            depositor_username = treasury_item.properties.get('depositor_username')
            deposit_time = treasury_item.properties.get('deposit_time')

            # 销毁小金库道具（标记为已使用）
            treasury_item.status = 'used'
            treasury_item.used_at = timezone.now()
            treasury_item.inventory = None  # 从背包中移除
            treasury_item.save(update_fields=['status', 'used_at', 'inventory'])

            # 创建使用记录（如果有ItemUsageRecord模型的话）
            # 这里暂时省略，因为没有看到该模型的定义

            return Response({
                'success': True,
                'message': f'成功提取 {stored_coins} 积分，小金库已销毁',
                'withdrawn_coins': stored_coins,
                'user_total_coins': user.coins,
                'depositor_info': {
                    'username': depositor_username,
                    'deposit_time': deposit_time
                } if depositor_username else None
            }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'error': f'提取积分失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def view_note(request, note_id):
    """查看纸条（阅后即焚）"""
    try:
        with transaction.atomic():
            note_item = get_object_or_404(
                Item,
                id=note_id,
                item_type__name='note',
                status='available'
            )

            # 检查权限（拥有者或漂流瓶接收者或分享链接接收者）
            can_view = False
            if note_item.owner == request.user:
                can_view = True
            else:
                # 检查是否是漂流瓶中的纸条
                drift_bottles = DriftBottle.objects.filter(
                    items__id=note_id,
                    finder=request.user,
                    status='found'
                )
                if drift_bottles.exists():
                    can_view = True

                # 检查是否是分享链接中的纸条
                shared_items = SharedItem.objects.filter(
                    item_id=note_id,
                    is_claimed=False,
                    expires_at__gt=timezone.now()
                )
                if shared_items.exists():
                    can_view = True

            if not can_view:
                return Response({
                    'error': '无权查看此纸条'
                }, status=status.HTTP_403_FORBIDDEN)

            # 获取纸条内容
            note_content = note_item.properties.get('content', '')
            if not note_content:
                return Response({
                    'error': '纸条内容为空'
                }, status=status.HTTP_404_NOT_FOUND)

            # 准备返回数据
            response_data = {
                'content': note_content,
                'created_at': note_item.properties.get('created_at'),
                'editor': note_item.properties.get('editor'),
                'burn_after_reading': note_item.properties.get('burn_after_reading', True),
                'view_time': timezone.now().isoformat()
            }

            # 阅后即焚：标记道具为已使用
            if note_item.properties.get('burn_after_reading', True):
                note_item.status = 'used'
                note_item.used_at = timezone.now()
                note_item.inventory = None  # 从背包中移除
                note_item.save()

                # 创建纸条查看通知（如果不是自己的纸条）
                if note_item.owner != request.user:
                    Notification.create_notification(
                        recipient=note_item.owner,
                        notification_type='note_viewed',
                        actor=request.user,
                        related_object_type='item',
                        related_object_id=note_item.id,
                        extra_data={
                            'content_preview': note_content[:10] + ('...' if len(note_content) > 10 else ''),
                            'view_time': timezone.now().isoformat(),
                            'burn_after_reading': True
                        },
                        priority='low'
                    )

            return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'error': f'查看纸条失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def use_lucky_charm(request):
    """使用幸运符 - 为下一个带锁任务提供+20%小时奖励概率"""
    try:
        item_id = request.data.get('item_id')
        if not item_id:
            return Response({
                'error': '缺少道具ID'
            }, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            user = request.user

            # 获取幸运符道具
            try:
                lucky_charm = Item.objects.get(
                    id=item_id,
                    owner=user,
                    item_type__name='lucky_charm',
                    status='available'
                )
            except Item.DoesNotExist:
                return Response({
                    'error': '幸运符道具不存在或不可用'
                }, status=status.HTTP_404_NOT_FOUND)

            # 检查是否已有活跃的幸运符效果
            existing_effect = UserEffect.objects.filter(
                user=user,
                effect_type='lucky_charm',
                is_active=True
            ).first()

            if existing_effect:
                return Response({
                    'error': '您已经有活跃的幸运符效果，无法重复使用'
                }, status=status.HTTP_400_BAD_REQUEST)

            # 创建幸运符效果
            UserEffect.objects.create(
                user=user,
                effect_type='lucky_charm',
                item=lucky_charm,
                properties={
                    'luck_boost': 0.2,  # +20% 概率加成
                    'used_at': timezone.now().isoformat(),
                    'description': '下一个带锁任务的小时奖励概率+20%'
                },
                is_active=True
            )

            # 销毁幸运符道具
            lucky_charm.status = 'used'
            lucky_charm.used_at = timezone.now()
            lucky_charm.inventory = None  # 从背包中移除
            lucky_charm.save()

            return Response({
                'success': True,
                'message': '幸运符使用成功！下一个带锁任务的小时奖励概率将提高20%',
                'effect_description': '下一个带锁任务的小时奖励概率+20%',
                'boost_percentage': 20
            }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'error': f'使用幸运符失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def use_energy_potion(request):
    """使用活力药水 - 在24小时内将活跃度衰减减少50%"""
    try:
        item_id = request.data.get('item_id')
        if not item_id:
            return Response({
                'error': '缺少道具ID'
            }, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            user = request.user

            # 获取活力药水道具
            try:
                energy_potion = Item.objects.get(
                    id=item_id,
                    owner=user,
                    item_type__name='energy_potion',
                    status='available'
                )
            except Item.DoesNotExist:
                return Response({
                    'error': '活力药水道具不存在或不可用'
                }, status=status.HTTP_404_NOT_FOUND)

            # 检查是否已有活跃的活力药水效果
            existing_effect = UserEffect.objects.filter(
                user=user,
                effect_type='energy_potion',
                is_active=True,
                expires_at__gt=timezone.now()
            ).first()

            if existing_effect:
                remaining_time = existing_effect.expires_at - timezone.now()
                remaining_hours = int(remaining_time.total_seconds() / 3600)
                return Response({
                    'error': f'您已经有活跃的活力药水效果，剩余时间：{remaining_hours}小时'
                }, status=status.HTTP_400_BAD_REQUEST)

            # 计算过期时间（24小时后）
            expires_at = timezone.now() + timedelta(hours=24)

            # 创建活力药水效果
            UserEffect.objects.create(
                user=user,
                effect_type='energy_potion',
                item=energy_potion,
                properties={
                    'decay_reduction': 0.5,  # 50% 衰减减少
                    'duration_hours': 24,
                    'used_at': timezone.now().isoformat(),
                    'description': '24小时内活跃度衰减减少50%'
                },
                expires_at=expires_at,
                is_active=True
            )

            # 销毁活力药水道具
            energy_potion.status = 'used'
            energy_potion.used_at = timezone.now()
            energy_potion.inventory = None  # 从背包中移除
            energy_potion.save()

            return Response({
                'success': True,
                'message': '活力药水使用成功！在接下来的24小时内，您的活跃度衰减将减少50%',
                'effect_description': '24小时内活跃度衰减减少50%',
                'decay_reduction_percentage': 50,
                'duration_hours': 24,
                'expires_at': expires_at.isoformat()
            }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'error': f'使用活力药水失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_shared_tasks(request):
    """获取朋友分享给我的任务列表"""
    try:
        user = request.user

        # 获取所有分享给我的活跃任务
        shared_accesses = SharedTaskAccess.objects.filter(
            viewer=user,
            is_active=True,
            expires_at__gt=timezone.now()
        ).select_related('item').order_by('-created_at')

        shared_tasks = []
        for access in shared_accesses:
            # 通过task_id获取任务
            try:
                from tasks.models import LockTask
                task = LockTask.objects.get(id=access.task_id)
            except LockTask.DoesNotExist:
                continue

            # 只显示仍然活跃的任务
            if task.status in ['active', 'voting', 'voting_passed']:
                shared_tasks.append({
                    'access_id': str(access.id),
                    'task': {
                        'id': str(task.id),
                        'title': task.title,
                        'description': task.description,
                        'difficulty': task.difficulty,
                        'status': task.status,
                        'start_time': task.start_time.isoformat() if task.start_time else None,
                        'end_time': task.end_time.isoformat() if task.end_time else None,
                        'is_frozen': task.is_frozen,
                        'time_display_hidden': task.time_display_hidden,
                        'total_hourly_rewards': task.total_hourly_rewards,
                        'last_hourly_reward_at': task.last_hourly_reward_at.isoformat() if task.last_hourly_reward_at else None
                    },
                    'shared_by': {
                        'username': access.sharer.username,
                        'id': access.sharer.id
                    },
                    'shared_at': access.created_at.isoformat(),
                    'expires_at': access.expires_at.isoformat(),
                    'item_used': access.item.item_type.name if access.item else 'unknown'
                })

        return Response({
            'shared_tasks': shared_tasks,
            'count': len(shared_tasks)
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'error': f'获取分享任务失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def use_time_anchor(request):
    """使用时间锚点 - 保存任务状态或恢复任务状态"""
    try:
        item_id = request.data.get('item_id')
        task_id = request.data.get('task_id')
        action = request.data.get('action')  # 'save' 或 'restore'
        recreate_key = request.data.get('recreate_key', False)  # 是否重新创建钥匙

        if not all([item_id, task_id, action]):
            return Response({
                'error': '缺少必要参数：item_id、task_id、action'
            }, status=status.HTTP_400_BAD_REQUEST)

        if action not in ['save', 'restore']:
            return Response({
                'error': 'action 参数必须是 "save" 或 "restore"'
            }, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            user = request.user

            # 获取时间锚点道具
            try:
                anchor_item = Item.objects.get(
                    id=item_id,
                    owner=user,
                    item_type__name='time_anchor',
                    status='available'
                )
            except Item.DoesNotExist:
                return Response({
                    'error': '时间锚点道具不存在或不可用'
                }, status=status.HTTP_404_NOT_FOUND)

            # 获取要操作的任务
            try:
                from tasks.models import LockTask
                lock_task = LockTask.objects.get(
                    id=task_id,
                    user=user,
                    task_type='lock'
                )
            except LockTask.DoesNotExist:
                return Response({
                    'error': '指定的带锁任务不存在或不属于您'
                }, status=status.HTTP_400_BAD_REQUEST)

            if action == 'save':
                # 保存任务状态
                if lock_task.status not in ['active', 'voting', 'voting_passed']:
                    return Response({
                        'error': '只能保存活跃状态或投票期的任务状态'
                    }, status=status.HTTP_400_BAD_REQUEST)

                # 检查是否已经有保存的状态，如果有则删除旧的快照
                existing_snapshot = TaskSnapshot.objects.filter(
                    task_id=lock_task.id,
                    item=anchor_item,
                    used_at__isnull=True
                ).first()

                is_overwrite = existing_snapshot is not None
                if existing_snapshot:
                    # 删除旧的快照，允许覆盖保存
                    existing_snapshot.delete()

                # 创建任务快照
                TaskSnapshot.objects.create(
                    user=user,
                    item=anchor_item,
                    task_id=lock_task.id,
                    snapshot_data={
                        'status': lock_task.status,
                        'start_time': lock_task.start_time.isoformat() if lock_task.start_time else None,
                        'end_time': lock_task.end_time.isoformat() if lock_task.end_time else None,
                        'is_frozen': lock_task.is_frozen,
                        'frozen_at': lock_task.frozen_at.isoformat() if lock_task.frozen_at else None,
                        'frozen_end_time': lock_task.frozen_end_time.isoformat() if lock_task.frozen_end_time else None,
                        'total_frozen_duration': lock_task.total_frozen_duration.total_seconds() if lock_task.total_frozen_duration else 0,
                        'last_hourly_reward_at': lock_task.last_hourly_reward_at.isoformat() if lock_task.last_hourly_reward_at else None,
                        'total_hourly_rewards': lock_task.total_hourly_rewards,
                        'time_display_hidden': lock_task.time_display_hidden,
                        'shield_active': getattr(lock_task, 'shield_active', False),
                        'shield_activated_at': getattr(lock_task, 'shield_activated_at', None),
                        'shield_activated_by_id': getattr(lock_task, 'shield_activated_by', None)
                    }
                )

                # 更新道具属性，标记已使用保存功能
                anchor_item.properties.update({
                    'saved_task_id': str(lock_task.id),
                    'saved_at': timezone.now().isoformat(),
                    'can_restore': True
                })
                anchor_item.save()

                # 创建时间线事件
                TaskTimelineEvent.objects.create(
                    task=lock_task,
                    event_type='item_effect_applied',
                    user=user,
                    description='使用时间锚点保存任务状态',
                    metadata={
                        'item_type': 'time_anchor',
                        'action': 'save',
                        'saved_status': lock_task.status,
                        'saved_end_time': lock_task.end_time.isoformat() if lock_task.end_time else None,
                        'anchor_item_id': str(anchor_item.id)
                    }
                )

                save_message = '任务状态已重新保存！如果任务失败，可以使用恢复功能' if is_overwrite else '任务状态已保存！如果任务失败，可以使用恢复功能'

                return Response({
                    'success': True,
                    'message': save_message,
                    'task_title': lock_task.title,
                    'saved_status': lock_task.status,
                    'saved_at': timezone.now().isoformat(),
                    'can_restore': True
                }, status=status.HTTP_200_OK)

            elif action == 'restore':
                # 恢复任务状态
                if lock_task.status != 'failed':
                    return Response({
                        'error': '只能恢复失败状态的任务'
                    }, status=status.HTTP_400_BAD_REQUEST)

                # 检查是否可以恢复
                if not anchor_item.properties.get('can_restore', False):
                    return Response({
                        'error': '此时间锚点无法恢复任务，请先保存任务状态'
                    }, status=status.HTTP_400_BAD_REQUEST)

                # 获取保存的快照
                snapshot = TaskSnapshot.objects.filter(
                    task_id=lock_task.id,
                    item=anchor_item,
                    used_at__isnull=True
                ).first()

                if not snapshot:
                    return Response({
                        'error': '未找到保存的任务状态'
                    }, status=status.HTTP_400_BAD_REQUEST)

                # 恢复任务状态
                old_status = lock_task.status
                saved_data = snapshot.snapshot_data

                lock_task.status = saved_data.get('status')
                if saved_data.get('start_time'):
                    lock_task.start_time = timezone.datetime.fromisoformat(saved_data['start_time'])
                if saved_data.get('end_time'):
                    lock_task.end_time = timezone.datetime.fromisoformat(saved_data['end_time'])
                lock_task.is_frozen = saved_data.get('is_frozen', False)
                if saved_data.get('frozen_at'):
                    lock_task.frozen_at = timezone.datetime.fromisoformat(saved_data['frozen_at'])
                if saved_data.get('frozen_end_time'):
                    lock_task.frozen_end_time = timezone.datetime.fromisoformat(saved_data['frozen_end_time'])
                total_seconds = saved_data.get('total_frozen_duration', 0)
                lock_task.total_frozen_duration = timedelta(seconds=total_seconds)
                if saved_data.get('last_hourly_reward_at'):
                    lock_task.last_hourly_reward_at = timezone.datetime.fromisoformat(saved_data['last_hourly_reward_at'])
                lock_task.total_hourly_rewards = saved_data.get('total_hourly_rewards', 0)
                lock_task.time_display_hidden = saved_data.get('time_display_hidden', False)

                lock_task.save()

                # 标记快照为已使用
                snapshot.used_at = timezone.now()
                snapshot.save()

                # 钥匙重新创建和返还逻辑
                key_returned = False
                returned_key_id = None
                key_return_message = None
                key_recreated = False

                # 检查任务是否有钥匙
                existing_key = Item.objects.filter(
                    item_type__name='key',
                    properties__task_id=str(lock_task.id),
                    status='available'
                ).first()

                if not existing_key and recreate_key:
                    # 重新创建任务钥匙
                    try:
                        # 获取钥匙物品类型
                        key_item_type = ItemType.objects.get(name='key')

                        # 获取用户背包
                        user_inventory, created = UserInventory.objects.get_or_create(
                            user=user,
                            defaults={'max_slots': 6}
                        )

                        # 检查背包是否有空间
                        current_items_count = user_inventory.items.filter(status='available').count()
                        if current_items_count >= user_inventory.max_slots:
                            key_return_message = '背包空间不足，无法返还钥匙'
                        else:
                            # 创建新的钥匙
                            new_key = Item.objects.create(
                                item_type=key_item_type,
                                owner=user,
                                inventory=user_inventory,
                                status='available',
                                properties={
                                    'task_id': str(lock_task.id),
                                    'task_title': lock_task.title,
                                    'created_by_time_anchor': True,
                                    'original_task_creator': user.id
                                },
                                original_owner=user
                            )

                            key_returned = True
                            returned_key_id = str(new_key.id)
                            key_return_message = '任务钥匙已重新创建并返还到背包'
                            key_recreated = True

                    except ItemType.DoesNotExist:
                        key_return_message = '钥匙物品类型不存在，无法创建钥匙'
                    except Exception as e:
                        key_return_message = f'创建钥匙失败：{str(e)}'

                elif existing_key:
                    # 钥匙已存在，确保在用户背包中
                    if existing_key.owner == user and existing_key.status == 'available':
                        key_returned = True
                        returned_key_id = str(existing_key.id)
                        key_return_message = '任务钥匙已存在于背包中'
                    else:
                        key_return_message = '钥匙存在但状态异常'
                else:
                    key_return_message = '未请求钥匙重新创建'

                # 销毁时间锚点道具
                anchor_item.status = 'used'
                anchor_item.used_at = timezone.now()
                anchor_item.inventory = None  # 从背包中移除
                anchor_item.save()

                # 创建时间线事件
                timeline_event = TaskTimelineEvent.objects.create(
                    task=lock_task,
                    event_type='item_effect_applied',
                    user=user,
                    description=f'使用时间锚点恢复任务状态：{old_status} → {lock_task.status}',
                    metadata={
                        'item_type': 'time_anchor',
                        'action': 'restore',
                        'old_status': old_status,
                        'restored_status': lock_task.status,
                        'restored_end_time': lock_task.end_time.isoformat() if lock_task.end_time else None,
                        'anchor_item_id': str(anchor_item.id),
                        'key_returned': key_returned,
                        'key_recreated': key_recreated,
                        'returned_key_id': returned_key_id
                    }
                )

                response_data = {
                    'success': True,
                    'message': '任务状态已恢复！时间锚点已销毁',
                    'task_title': lock_task.title,
                    'old_status': old_status,
                    'restored_status': lock_task.status,
                    'restored_end_time': lock_task.end_time.isoformat() if lock_task.end_time else None,
                    'key_returned': key_returned,
                    'returned_key_id': returned_key_id,
                    'key_return_message': key_return_message,
                    'key_recreated': key_recreated,
                    'timeline_event_created': True,
                    'timeline_event_id': str(timeline_event.id)
                }

                return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'error': f'使用时间锚点失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def use_exploration_compass(request):
    """使用探索指南针 - 显示指定区域的所有埋藏宝物相关信息（物品类型、难度、埋藏者）"""
    try:
        item_id = request.data.get('item_id')
        zone_name = request.data.get('zone_name')

        if not all([item_id, zone_name]):
            return Response({
                'error': '缺少必要参数：item_id、zone_name'
            }, status=status.HTTP_400_BAD_REQUEST)

        # 验证区域名称
        valid_zones = ['beach', 'forest', 'mountain', 'desert', 'cave']
        if zone_name not in valid_zones:
            return Response({
                'error': f'无效的区域名称，有效区域：{", ".join(valid_zones)}'
            }, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            user = request.user

            # 获取探索指南针道具
            try:
                compass_item = Item.objects.get(
                    id=item_id,
                    owner=user,
                    item_type__name='exploration_compass',
                    status='available'
                )
            except Item.DoesNotExist:
                return Response({
                    'error': '探索指南针道具不存在或不可用'
                }, status=status.HTTP_404_NOT_FOUND)

            # 查找指定区域的所有埋藏宝物（包括用户自己埋藏的）
            buried_treasures = BuriedTreasure.objects.filter(
                location_zone=zone_name,
                status='buried',
                expires_at__gt=timezone.now()
            ).select_related('burier', 'item__item_type')

            if not buried_treasures.exists():
                # 即使没有宝物也要销毁道具
                compass_item.status = 'used'
                compass_item.used_at = timezone.now()
                compass_item.inventory = None
                compass_item.save()

                return Response({
                    'success': True,
                    'message': f'{get_zone_display_name(zone_name)} 区域当前没有埋藏的宝物',
                    'zone_name': zone_name,
                    'zone_display_name': get_zone_display_name(zone_name),
                    'treasures': [],
                    'treasure_count': 0
                }, status=status.HTTP_200_OK)

            # 构建宝物信息 - 显示物品类型、难度、埋藏者，包括用户自己埋藏的宝物
            treasures_info = []
            for treasure in buried_treasures:
                is_own_treasure = treasure.burier == user
                burier_display = treasure.burier.username
                if is_own_treasure:
                    burier_display += " (您)"

                treasures_info.append({
                    'treasure_id': str(treasure.id),
                    'difficulty': treasure.difficulty,
                    'difficulty_display': getDifficultyText(treasure.difficulty),
                    'item_type': treasure.item.item_type.name,
                    'item_display_name': treasure.item.item_type.display_name,
                    'item_icon': treasure.item.item_type.icon,
                    'burier': {
                        'username': treasure.burier.username,
                        'id': treasure.burier.id
                    },
                    'is_own_treasure': is_own_treasure,
                    'buried_at': treasure.created_at.isoformat(),
                    'expires_at': treasure.expires_at.isoformat(),
                    # 显示宝物相关信息而非位置信息，标识自己埋藏的宝物
                    'treasure_info': f'🎁 物品：{treasure.item.item_type.display_name}\n⚡ 难度：{getDifficultyText(treasure.difficulty)}\n👤 埋藏者：{burier_display}'
                })

            # 销毁探索指南针道具
            compass_item.status = 'used'
            compass_item.used_at = timezone.now()
            compass_item.inventory = None  # 从背包中移除
            compass_item.save()

            # 记录使用日志（不涉及特定任务，所以不创建时间线事件）
            # 可以创建一个通用的道具使用记录
            try:
                from users.models import ActivityLog
                ActivityLog.objects.create(
                    user=user,
                    action_type='item_used',
                    points_change=0,
                    new_total=user.activity_score,
                    metadata={
                        'item_type': 'exploration_compass',
                        'item_id': str(compass_item.id),
                        'zone_explored': zone_name,
                        'treasures_found': len(treasures_info),
                        'used_at': timezone.now().isoformat()
                    }
                )
            except Exception:
                # 如果ActivityLog模型还不存在，忽略错误
                pass

            return Response({
                'success': True,
                'message': f'探索指南针揭示了 {get_zone_display_name(zone_name)} 区域的 {len(treasures_info)} 个宝物信息！',
                'zone_name': zone_name,
                'zone_display_name': get_zone_display_name(zone_name),
                'treasures': treasures_info,
                'treasure_count': len(treasures_info),
                'compass_used_at': timezone.now().isoformat(),
                'description': '探索指南针显示了区域内所有宝物的相关信息（物品类型、难度、埋藏者），但不显示具体位置'
            }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'error': f'使用探索指南针失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




@api_view(['POST'])
@permission_classes([IsAuthenticated])
def use_influence_crown(request):
    """使用影响力皇冠 - 在48小时内所有投票权重变为3倍"""
    try:
        item_id = request.data.get('item_id')

        if not item_id:
            return Response({
                'error': '缺少必要参数：item_id'
            }, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            user = request.user

            # 获取影响力皇冠道具
            try:
                crown_item = Item.objects.get(
                    id=item_id,
                    owner=user,
                    item_type__name='influence_crown',
                    status='available'
                )
            except Item.DoesNotExist:
                return Response({
                    'error': '影响力皇冠道具不存在或不可用'
                }, status=status.HTTP_404_NOT_FOUND)

            # 检查是否已有活跃的影响力皇冠效果
            existing_effect = UserEffect.objects.filter(
                user=user,
                effect_type='influence_crown',
                is_active=True,
                expires_at__gt=timezone.now()
            ).first()

            if existing_effect:
                remaining_time = existing_effect.expires_at - timezone.now()
                remaining_hours = int(remaining_time.total_seconds() / 3600)
                return Response({
                    'error': f'您已经有活跃的影响力皇冠效果，剩余时间：{remaining_hours}小时'
                }, status=status.HTTP_400_BAD_REQUEST)

            # 计算过期时间（48小时后）
            expires_at = timezone.now() + timedelta(hours=48)

            # 创建影响力皇冠效果
            UserEffect.objects.create(
                user=user,
                effect_type='influence_crown',
                item=crown_item,
                properties={
                    'vote_multiplier': 3,  # 3倍投票权重
                    'duration_hours': 48,
                    'used_at': timezone.now().isoformat(),
                    'description': '48小时内所有投票权重变为3倍'
                },
                expires_at=expires_at,
                is_active=True
            )

            # 销毁影响力皇冠道具
            crown_item.status = 'used'
            crown_item.used_at = timezone.now()
            crown_item.inventory = None  # 从背包中移除
            crown_item.save()

            # 创建通知
            Notification.create_notification(
                recipient=user,
                notification_type='item_effect_activated',
                title='影响力皇冠激活',
                message=f'影响力皇冠已激活！在接下来的48小时内，您的所有投票权重将变为3倍',
                related_object_type='item',
                related_object_id=crown_item.id,
                extra_data={
                    'item_type': 'influence_crown',
                    'effect_duration_hours': 48,
                    'vote_multiplier': 3,
                    'expires_at': expires_at.isoformat(),
                    'activated_at': timezone.now().isoformat()
                },
                priority='high'
            )

            return Response({
                'success': True,
                'message': '影响力皇冠激活成功！在接下来的48小时内，您的所有投票权重将变为3倍',
                'effect_description': '48小时内所有投票权重变为3倍',
                'vote_multiplier': 3,
                'duration_hours': 48,
                'expires_at': expires_at.isoformat(),
                'activated_at': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'error': f'使用影响力皇冠失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def edit_note(request, note_id):
    """编辑纸条内容"""
    try:
        with transaction.atomic():
            note_item = get_object_or_404(
                Item,
                id=note_id,
                item_type__name='note',
                status='available',
                owner=request.user  # 只有所有者可以编辑
            )

            content = request.data.get('content', '').strip()

            # 验证内容长度
            if not content:
                return Response({
                    'error': '纸条内容不能为空'
                }, status=status.HTTP_400_BAD_REQUEST)

            if len(content) > 30:
                return Response({
                    'error': '纸条内容不能超过30个字符'
                }, status=status.HTTP_400_BAD_REQUEST)

            # 更新纸条内容
            note_item.properties.update({
                'content': content,
                'edited_at': timezone.now().isoformat(),
                'burn_after_reading': True,
                'editor': request.user.username
            })

            # 如果是第一次编辑，添加创建时间
            if 'created_at' not in note_item.properties:
                note_item.properties['created_at'] = timezone.now().isoformat()

            note_item.save()

            return Response({
                'success': True,
                'message': '纸条内容已更新',
                'content': content,
                'edited_at': note_item.properties['edited_at']
            }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'error': f'编辑纸条失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def use_small_campfire(request):
    """使用小火堆解冻被冻结的任务"""
    from tasks.models import LockTask
    from tasks.timeline import TaskTimelineEvent
    from notifications.models import Notification
    from django.utils import timezone
    from datetime import timedelta

    user = request.user
    small_campfire_id = request.data.get('small_campfire_id')
    task_id = request.data.get('task_id')

    if not small_campfire_id or not task_id:
        return Response({
            'error': '请提供小火堆ID和任务ID'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        # 验证小火堆
        small_campfire = Item.objects.get(
            id=small_campfire_id,
            owner=user,
            item_type__name='small_campfire',
            status='available'
        )
    except Item.DoesNotExist:
        return Response({
            'error': '小火堆不存在或已被使用'
        }, status=status.HTTP_404_NOT_FOUND)

    try:
        # 验证任务
        lock_task = LockTask.objects.get(id=task_id, user=user)
    except LockTask.DoesNotExist:
        return Response({
            'error': '任务不存在或不属于您'
        }, status=status.HTTP_404_NOT_FOUND)

    # 验证任务是否被冻结
    if not lock_task.is_frozen:
        return Response({
            'error': '任务未被冻结，无需使用小火堆'
        }, status=status.HTTP_400_BAD_REQUEST)

    # 验证任务状态
    if lock_task.status not in ['active', 'voting_passed']:
        return Response({
            'error': '只能对进行中的任务使用小火堆'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        with transaction.atomic():
            # 计算剩余时间
            now = timezone.now()
            if lock_task.frozen_end_time and lock_task.frozen_at:
                remaining_time = lock_task.frozen_end_time - lock_task.frozen_at
                # 恢复任务时间
                lock_task.end_time = now + remaining_time

            # 累计冻结时长
            if lock_task.frozen_at:
                frozen_duration = now - lock_task.frozen_at
                lock_task.total_frozen_duration += frozen_duration

            # 解冻任务
            lock_task.is_frozen = False
            lock_task.frozen_at = None
            lock_task.frozen_end_time = None
            lock_task.save()

            # 消耗小火堆
            small_campfire.status = 'used'
            small_campfire.used_at = now
            small_campfire.inventory = None
            small_campfire.save()

            # 创建时间线事件
            TaskTimelineEvent.objects.create(
                task=lock_task,
                event_type='item_effect_applied',
                user=user,
                metadata={
                    'item_type': 'small_campfire',
                    'action': 'task_unfrozen',
                    'unfrozen_at': now.isoformat(),
                    'remaining_time_restored': str(remaining_time) if 'remaining_time' in locals() else None,
                    'item_id': str(small_campfire.id)
                }
            )

            # 创建通知
            Notification.create_notification(
                recipient=user,
                notification_type='item_effect_applied',
                title='小火堆使用成功',
                message=f'您的任务"{lock_task.title}"已成功解冻！',
                priority='normal',
                extra_data={
                    'item_type': 'small_campfire',
                    'task_id': str(lock_task.id),
                    'task_title': lock_task.title,
                    'unfrozen_at': now.isoformat()
                }
            )

            return Response({
                'success': True,
                'message': '小火堆使用成功，任务已解冻！',
                'task': {
                    'id': str(lock_task.id),
                    'title': lock_task.title,
                    'is_frozen': lock_task.is_frozen,
                    'end_time': lock_task.end_time.isoformat() if lock_task.end_time else None
                }
            }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'error': f'解冻任务时发生错误: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def use_small_campfire_on_task(request):
    """使用小火堆选择并解冻被冻结的任务 - 类似万能钥匙的选择机制"""
    from tasks.models import LockTask, TaskTimelineEvent
    from users.models import Notification
    from django.utils import timezone
    from datetime import timedelta

    try:
        item_id = request.data.get('item_id')
        task_id = request.data.get('task_id')

        if not item_id or not task_id:
            return Response({
                'error': '缺少必要参数：item_id 和 task_id'
            }, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            user = request.user

            # 验证小火堆道具
            try:
                small_campfire = Item.objects.get(
                    id=item_id,
                    owner=user,
                    item_type__name='small_campfire',
                    status='available'
                )
            except Item.DoesNotExist:
                return Response({
                    'error': '小火堆道具不存在或不可用'
                }, status=status.HTTP_404_NOT_FOUND)

            # 验证任务
            try:
                lock_task = LockTask.objects.get(
                    id=task_id,
                    user=user,
                    task_type='lock'
                )
            except LockTask.DoesNotExist:
                return Response({
                    'error': '指定的带锁任务不存在或不属于您'
                }, status=status.HTTP_400_BAD_REQUEST)

            # 验证任务是否被冻结
            if not lock_task.is_frozen:
                return Response({
                    'error': '任务未被冻结，无需使用小火堆'
                }, status=status.HTTP_400_BAD_REQUEST)

            # 验证任务状态
            if lock_task.status not in ['active', 'voting_passed']:
                return Response({
                    'error': '只能对进行中的任务使用小火堆'
                }, status=status.HTTP_400_BAD_REQUEST)

            # 计算剩余时间
            now = timezone.now()
            if lock_task.frozen_end_time and lock_task.frozen_at:
                remaining_time = lock_task.frozen_end_time - lock_task.frozen_at
                # 恢复任务时间
                lock_task.end_time = now + remaining_time

            # 累计冻结时长
            if lock_task.frozen_at:
                frozen_duration = now - lock_task.frozen_at
                lock_task.total_frozen_duration += frozen_duration

            # 解冻任务
            lock_task.is_frozen = False
            lock_task.frozen_at = None
            lock_task.frozen_end_time = None
            lock_task.save()

            # 消耗小火堆
            small_campfire.status = 'used'
            small_campfire.used_at = now
            small_campfire.inventory = None
            small_campfire.save()

            # 创建时间线事件
            TaskTimelineEvent.objects.create(
                task=lock_task,
                event_type='item_effect_applied',
                user=user,
                description=f'使用小火堆解冻任务：{lock_task.title}',
                metadata={
                    'item_type': 'small_campfire',
                    'action': 'task_unfrozen',
                    'unfrozen_at': now.isoformat(),
                    'remaining_time_restored': str(remaining_time) if 'remaining_time' in locals() else None,
                    'item_id': str(small_campfire.id),
                    'selection_method': 'task_selection'
                }
            )

            # 创建通知
            Notification.create_notification(
                recipient=user,
                notification_type='item_effect_applied',
                title='小火堆使用成功',
                message=f'您使用小火堆成功解冻了任务「{lock_task.title}」！',
                related_object_type='lock_task',
                related_object_id=lock_task.id,
                extra_data={
                    'item_type': 'small_campfire',
                    'task_id': str(lock_task.id),
                    'task_title': lock_task.title,
                    'unfrozen_at': now.isoformat(),
                    'selection_method': 'task_selection'
                },
                priority='normal'
            )

            return Response({
                'success': True,
                'message': f'小火堆使用成功！任务「{lock_task.title}」已解冻',
                'task_id': str(lock_task.id),
                'task_title': lock_task.title,
                'task': {
                    'id': str(lock_task.id),
                    'title': lock_task.title,
                    'is_frozen': lock_task.is_frozen,
                    'end_time': lock_task.end_time.isoformat() if lock_task.end_time else None,
                    'status': lock_task.status
                }
            }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'error': f'使用小火堆失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_frozen_tasks(request):
    """获取用户的冻结任务列表，用于小火堆选择"""
    from tasks.models import LockTask

    try:
        user = request.user

        # 获取所有被冻结的带锁任务
        frozen_tasks = LockTask.objects.filter(
            user=user,
            task_type='lock',
            is_frozen=True,
            status__in=['active', 'voting_passed']
        ).order_by('-frozen_at')

        tasks_data = []
        for task in frozen_tasks:
            # 计算冻结时长
            frozen_duration_seconds = 0
            if task.frozen_at:
                frozen_duration = timezone.now() - task.frozen_at
                frozen_duration_seconds = int(frozen_duration.total_seconds())

            # 计算预计解冻后的剩余时间
            remaining_time_after_unfreeze = None
            if task.frozen_end_time and task.frozen_at:
                remaining_time = task.frozen_end_time - task.frozen_at
                remaining_time_after_unfreeze = int(remaining_time.total_seconds())

            tasks_data.append({
                'id': str(task.id),
                'title': task.title,
                'description': task.description,
                'difficulty': task.difficulty,
                'status': task.status,
                'frozen_at': task.frozen_at.isoformat() if task.frozen_at else None,
                'frozen_end_time': task.frozen_end_time.isoformat() if task.frozen_end_time else None,
                'frozen_duration_seconds': frozen_duration_seconds,
                'remaining_time_after_unfreeze_seconds': remaining_time_after_unfreeze,
                'start_time': task.start_time.isoformat() if task.start_time else None,
                'end_time': task.end_time.isoformat() if task.end_time else None
            })

        return Response({
            'frozen_tasks': tasks_data,
            'count': len(tasks_data),
            'message': f'找到 {len(tasks_data)} 个冻结的任务' if tasks_data else '当前没有冻结的任务'
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'error': f'获取冻结任务列表失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# 角斗场游戏 (Arena Game)
# ============================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_arena_game(request):
    """创建角斗场游戏"""
    try:
        with transaction.atomic():
            user = request.user

            # 获取请求参数并转换为整数
            try:
                bet_amount = int(request.data.get('bet_amount', 10))
                audience_ticket_price = int(request.data.get('audience_ticket_price', 5))
                max_audience = int(request.data.get('max_audience', 20))
                deadline_hours = int(request.data.get('deadline_hours', 12))
                winner_reward_percentage = int(request.data.get('winner_reward_percentage', 80))
            except (ValueError, TypeError):
                return Response({'error': '参数格式错误，请输入有效的数字'}, status=status.HTTP_400_BAD_REQUEST)

            # 验证参数
            if bet_amount < 1:
                return Response({'error': '投注金额至少为1积分'}, status=status.HTTP_400_BAD_REQUEST)
            if audience_ticket_price < 1:
                return Response({'error': '门票价格至少为1积分'}, status=status.HTTP_400_BAD_REQUEST)
            if max_audience < 5 or max_audience > 100:
                return Response({'error': '观众人数上限必须在5-100之间'}, status=status.HTTP_400_BAD_REQUEST)
            if deadline_hours < 1 or deadline_hours > 72:
                return Response({'error': '截止时间必须在1-72小时之间'}, status=status.HTTP_400_BAD_REQUEST)
            if winner_reward_percentage < 50 or winner_reward_percentage > 95:
                return Response({'error': '胜者奖励比例必须在50%-95%之间'}, status=status.HTTP_400_BAD_REQUEST)

            # 检查用户积分
            if hasattr(user, 'coins') and user.coins < bet_amount:
                return Response({'error': '积分不足'}, status=status.HTTP_400_BAD_REQUEST)

            # 处理照片上传
            creator_photo = request.FILES.get('photo')
            if not creator_photo:
                return Response({'error': '请上传照片'}, status=status.HTTP_400_BAD_REQUEST)

            # 验证文件类型
            import os
            _, ext = os.path.splitext(creator_photo.name.lower())
            if ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                return Response({'error': '不支持的图片格式'}, status=status.HTTP_400_BAD_REQUEST)

            # 生成时间戳命名格式: YYYYMMDD_HHMMSS_milliseconds.jpg (与发布动态相同)
            now = timezone.now()
            timestamp = now.strftime('%Y%m%d_%H%M%S')
            milliseconds = f"{now.microsecond // 1000:03d}"
            date_path = now.strftime('%Y/%m/%d')
            secure_filename = f"{timestamp}_{milliseconds}{ext}"

            # 保存照片文件
            file_name = f"arena/{date_path}/{secure_filename}"

            # 确保文件指针在开头并读取内容
            creator_photo.seek(0)
            file_content = creator_photo.read()
            if not file_content:
                return Response({'error': '照片文件内容为空'}, status=status.HTTP_400_BAD_REQUEST)

            file_path = default_storage.save(file_name, ContentFile(file_content))
            logger.info(f"Arena game creator photo saved: {file_path}")

            # 扣除发起者赌注
            if hasattr(user, 'coins'):
                user.deduct_coins(
                    amount=bet_amount,
                    change_type='arena_game_bet',
                    description='创建角斗场游戏赌注',
                    metadata={'game_type': 'arena'}
                )

            # 计算截止时间
            deadline = timezone.now() + timedelta(hours=deadline_hours)

            # 创建游戏
            game = Game.objects.create(
                game_type='arena',
                creator=user,
                bet_amount=bet_amount,
                max_players=max_audience + 2,  # 发起者 + 挑战者 + 观众
                status='waiting',
                game_data={
                    'creator_photo': {
                        'path': file_path,
                        'uploaded_at': timezone.now().isoformat()
                    },
                    'challenger_photo': None,
                    'config': {
                        'audience_ticket_price': audience_ticket_price,
                        'max_audience': max_audience,
                        'deadline': deadline.isoformat(),
                        'winner_reward_percentage': winner_reward_percentage
                    },
                    'audience': [],
                    'votes': {
                        'creator': 0,
                        'challenger': 0
                    }
                },
                result={}
            )

            # 创建发起者参与记录
            GameParticipant.objects.create(
                game=game,
                user=user,
                action={'role': 'creator', 'photo_uploaded': True}
            )

            return Response({
                'message': '角斗场游戏创建成功',
                'game': {
                    'id': str(game.id),
                    'bet_amount': bet_amount,
                    'audience_ticket_price': audience_ticket_price,
                    'max_audience': max_audience,
                    'deadline': deadline.isoformat(),
                    'status': 'waiting'
                },
                'remaining_coins': getattr(user, 'coins', 0)
            }, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"create_arena_game error: {e}", exc_info=True)
        return Response({
            'error': f'创建游戏失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def join_arena_game(request, game_id):
    """挑战者加入角斗场游戏"""
    try:
        with transaction.atomic():
            user = request.user
            game = get_object_or_404(Game, id=game_id, game_type='arena')

            # 检查游戏状态
            if game.status != 'waiting':
                return Response({'error': '游戏已经开始或已结束'}, status=status.HTTP_400_BAD_REQUEST)

            # 检查是否已经是参与者
            if GameParticipant.objects.filter(game=game, user=user).exists():
                return Response({'error': '您已经参与了此游戏'}, status=status.HTTP_400_BAD_REQUEST)

            # 不能挑战自己的游戏
            if game.creator == user:
                return Response({'error': '不能挑战自己创建的游戏'}, status=status.HTTP_400_BAD_REQUEST)

            # 检查是否已有挑战者
            existing_participants = GameParticipant.objects.filter(game=game).count()
            if existing_participants >= 2:
                return Response({'error': '此游戏已有挑战者'}, status=status.HTTP_400_BAD_REQUEST)

            # 检查用户积分
            if hasattr(user, 'coins') and user.coins < game.bet_amount:
                return Response({'error': '积分不足'}, status=status.HTTP_400_BAD_REQUEST)

            # 处理照片上传
            challenger_photo = request.FILES.get('photo')
            if not challenger_photo:
                return Response({'error': '请上传照片'}, status=status.HTTP_400_BAD_REQUEST)

            # 验证文件类型
            _, ext = os.path.splitext(challenger_photo.name.lower())
            if ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                return Response({'error': '不支持的图片格式'}, status=status.HTTP_400_BAD_REQUEST)

            # 生成时间戳命名格式: YYYYMMDD_HHMMSS_milliseconds.jpg (与发布动态相同)
            now = timezone.now()
            timestamp = now.strftime('%Y%m%d_%H%M%S')
            milliseconds = f"{now.microsecond // 1000:03d}"
            date_path = now.strftime('%Y/%m/%d')
            secure_filename = f"{timestamp}_{milliseconds}{ext}"

            # 保存照片文件
            file_name = f"arena/{date_path}/{secure_filename}"

            # 确保文件指针在开头并读取内容
            challenger_photo.seek(0)
            file_content = challenger_photo.read()
            if not file_content:
                return Response({'error': '照片文件内容为空'}, status=status.HTTP_400_BAD_REQUEST)

            file_path = default_storage.save(file_name, ContentFile(file_content))
            logger.info(f"Arena game challenger photo saved: {file_path}")

            # 扣除挑战者赌注
            if hasattr(user, 'coins'):
                user.deduct_coins(
                    amount=game.bet_amount,
                    change_type='arena_game_bet',
                    description='加入角斗场游戏赌注',
                    metadata={'game_id': str(game.id)}
                )

            # 更新游戏数据
            game.game_data['challenger_photo'] = {
                'path': file_path,
                'uploaded_at': timezone.now().isoformat()
            }
            game.status = 'active'
            game.started_at = timezone.now()
            game.save()

            # 创建挑战者参与记录
            GameParticipant.objects.create(
                game=game,
                user=user,
                action={'role': 'challenger', 'photo_uploaded': True}
            )

            # 发送通知给发起者
            from users.models import Notification as NotificationModel
            NotificationModel.create_notification(
                recipient=game.creator,
                notification_type='game_update',
                actor=user,
                title='角斗场挑战者已加入',
                message=f'{user.username} 接受了您的角斗场挑战！游戏现在开始，等待观众入场投票。',
                related_object_type='game',
                related_object_id=game.id,
                extra_data={
                    'game_type': 'arena',
                    'action': 'challenger_joined',
                    'challenger_id': user.id,
                    'challenger_username': user.username
                },
                priority='normal'
            )

            return Response({
                'message': '成功加入角斗场游戏',
                'game': {
                    'id': str(game.id),
                    'status': 'active',
                    'bet_amount': game.bet_amount
                },
                'remaining_coins': getattr(user, 'coins', 0)
            }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"join_arena_game error: {e}", exc_info=True)
        return Response({
            'error': f'加入游戏失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def enter_arena_audience(request, game_id):
    """观众入场"""
    try:
        with transaction.atomic():
            user = request.user
            game = get_object_or_404(Game, id=game_id, game_type='arena')

            # 检查游戏状态
            if game.status != 'active':
                return Response({'error': '游戏不在进行中'}, status=status.HTTP_400_BAD_REQUEST)

            # 检查是否是发起者或挑战者
            participant = GameParticipant.objects.filter(game=game, user=user).first()
            if participant:
                role = participant.action.get('role')
                if role in ['creator', 'challenger']:
                    return Response({
                        'error': '发起者和挑战者不能以观众身份入场',
                        'has_access': True,
                        'role': role
                    }, status=status.HTTP_400_BAD_REQUEST)

            # 检查是否已经在观众列表中
            audience_list = game.game_data.get('audience', [])
            existing_audience = [a for a in audience_list if a.get('user_id') == user.id]
            if existing_audience:
                return Response({
                    'message': '您已经是观众',
                    'has_access': True,
                    'remaining_coins': getattr(user, 'coins', 0)
                })

            # 检查观众人数上限
            if len(audience_list) >= game.game_data['config']['max_audience']:
                return Response({'error': '观众人数已满'}, status=status.HTTP_400_BAD_REQUEST)

            # 检查截止时间
            from django.utils.dateparse import parse_datetime
            deadline = parse_datetime(game.game_data['config']['deadline'])
            if deadline and timezone.now() > deadline:
                return Response({'error': '游戏已截止'}, status=status.HTTP_400_BAD_REQUEST)

            # 获取门票价格
            ticket_price = game.game_data['config']['audience_ticket_price']

            # 检查用户积分
            if hasattr(user, 'coins') and user.coins < ticket_price:
                return Response({'error': '积分不足'}, status=status.HTTP_400_BAD_REQUEST)

            # 扣除门票费用
            if hasattr(user, 'coins'):
                user.deduct_coins(
                    amount=ticket_price,
                    change_type='arena_ticket',
                    description='角斗场观众门票',
                    metadata={'game_id': str(game.id)}
                )

            # 添加观众到列表
            new_audience = {
                'user_id': user.id,
                'username': user.username,
                'joined_at': timezone.now().isoformat(),
                'has_voted': False,
                'vote_for': None
            }
            game.game_data['audience'].append(new_audience)
            game.save()

            # 创建观众参与记录
            GameParticipant.objects.get_or_create(
                game=game,
                user=user,
                defaults={'action': {'role': 'audience'}}
            )

            return Response({
                'message': '入场成功，现在可以查看照片并投票',
                'has_access': True,
                'remaining_coins': getattr(user, 'coins', 0),
                'ticket_price': ticket_price
            }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"enter_arena_audience error: {e}", exc_info=True)
        return Response({
            'error': f'入场失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def vote_arena_game(request, game_id):
    """观众投票"""
    try:
        with transaction.atomic():
            user = request.user
            game = get_object_or_404(Game, id=game_id, game_type='arena')

            # 检查游戏状态
            if game.status != 'active':
                return Response({'error': '游戏不在进行中'}, status=status.HTTP_400_BAD_REQUEST)

            # 获取投票选择
            vote_for = request.data.get('vote_for')
            if vote_for not in ['creator', 'challenger']:
                return Response({'error': '投票选择无效'}, status=status.HTTP_400_BAD_REQUEST)

            # 检查用户是否是观众
            audience_list = game.game_data.get('audience', [])
            audience_entry = None
            for a in audience_list:
                if a.get('user_id') == user.id:
                    audience_entry = a
                    break

            if not audience_entry:
                return Response({'error': '您不是此游戏的观众'}, status=status.HTTP_403_FORBIDDEN)

            # 检查是否已经投票
            if audience_entry.get('has_voted'):
                return Response({'error': '您已经投过票了'}, status=status.HTTP_400_BAD_REQUEST)

            # 记录投票
            audience_entry['has_voted'] = True
            audience_entry['vote_for'] = vote_for
            audience_entry['voted_at'] = timezone.now().isoformat()

            # 更新票数统计
            game.game_data['votes'][vote_for] += 1
            game.save()

            # 检查是否所有观众都已投票
            all_voted = all(a.get('has_voted', False) for a in audience_list)
            total_audience = len(audience_list)
            max_audience = game.game_data.get('config', {}).get('max_audience', 20)

            # 只有当达到最大观众数且全部投票后才自动结算
            # 否则等待截止时间到达后手动结算
            if all_voted and total_audience >= max_audience:
                result = settle_arena_game_internal(game)
                return Response({
                    'message': '投票成功！所有观众已投票，游戏已结算',
                    'vote_for': vote_for,
                    'current_votes': game.game_data['votes'],
                    'is_completed': True,
                    'result': result
                })

            return Response({
                'message': '投票成功',
                'vote_for': vote_for,
                'current_votes': game.game_data['votes'],
                'is_completed': False,
                'total_audience': total_audience,
                'voted_count': sum(1 for a in audience_list if a.get('has_voted', False))
            }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"vote_arena_game error: {e}", exc_info=True)
        return Response({
            'error': f'投票失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def settle_arena_game(request, game_id):
    """手动结算角斗场游戏（用于截止时间到达）"""
    try:
        game = get_object_or_404(Game, id=game_id, game_type='arena')

        # 检查权限（只有发起者或管理员可以手动结算）
        if game.creator != request.user and not request.user.is_staff:
            return Response({'error': '无权结算此游戏'}, status=status.HTTP_403_FORBIDDEN)

        # 检查游戏状态
        if game.status == 'completed':
            return Response({'error': '游戏已经结算过了'}, status=status.HTTP_400_BAD_REQUEST)

        if game.status != 'active':
            return Response({'error': '游戏尚未开始'}, status=status.HTTP_400_BAD_REQUEST)

        result = settle_arena_game_internal(game)

        return Response({
            'message': '游戏结算成功',
            'result': result
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"settle_arena_game error: {e}", exc_info=True)
        return Response({
            'error': f'结算失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def settle_arena_game_internal(game):
    """内部结算函数"""
    from users.models import Notification as NotificationModel

    with transaction.atomic():
        votes = game.game_data.get('votes', {'creator': 0, 'challenger': 0})
        audience_list = game.game_data.get('audience', [])
        config = game.game_data.get('config', {})
        winner_reward_percentage = config.get('winner_reward_percentage', 80)

        # 确定胜者
        if votes['creator'] > votes['challenger']:
            winner = 'creator'
        elif votes['challenger'] > votes['creator']:
            winner = 'challenger'
        else:
            # 平局 - 按总票数比例分配（各50%）
            winner = 'tie'

        # 计算总奖池
        total_bet = game.bet_amount * 2  # 发起者 + 挑战者
        total_tickets = sum(config.get('audience_ticket_price', 5) for _ in audience_list)
        total_pot = total_bet + total_tickets

        # 计算奖励分配
        if winner == 'creator':
            winner_reward = int(total_pot * winner_reward_percentage / 100)
            loser_reward = total_pot - winner_reward
        elif winner == 'challenger':
            winner_reward = int(total_pot * winner_reward_percentage / 100)
            loser_reward = total_pot - winner_reward
        else:
            # 平局 - 平分
            winner_reward = total_pot // 2
            loser_reward = total_pot - winner_reward

        # 获取参与用户
        participants = GameParticipant.objects.filter(game=game)
        creator_user = None
        challenger_user = None

        for p in participants:
            role = p.action.get('role')
            if role == 'creator':
                creator_user = p.user
            elif role == 'challenger':
                challenger_user = p.user

        # 发放奖励
        if creator_user and hasattr(creator_user, 'coins'):
            if winner == 'creator':
                creator_user.add_coins(
                    amount=winner_reward,
                    change_type='arena_game_reward',
                    description='角斗场游戏获胜奖励',
                    metadata={'game_id': str(game.id), 'votes': votes}
                )
            else:
                creator_user.add_coins(
                    amount=loser_reward,
                    change_type='arena_game_reward',
                    description='角斗场游戏参与奖励',
                    metadata={'game_id': str(game.id), 'votes': votes}
                )

        if challenger_user and hasattr(challenger_user, 'coins'):
            if winner == 'challenger':
                challenger_user.add_coins(
                    amount=winner_reward,
                    change_type='arena_game_reward',
                    description='角斗场游戏获胜奖励',
                    metadata={'game_id': str(game.id), 'votes': votes}
                )
            else:
                challenger_user.add_coins(
                    amount=loser_reward,
                    change_type='arena_game_reward',
                    description='角斗场游戏参与奖励',
                    metadata={'game_id': str(game.id), 'votes': votes}
                )

        # 更新游戏状态
        game.status = 'completed'
        game.completed_at = timezone.now()
        game.result = {
            'winner': winner,
            'total_pot': total_pot,
            'creator_reward': winner_reward if winner == 'creator' else loser_reward,
            'challenger_reward': winner_reward if winner == 'challenger' else loser_reward,
            'final_votes': votes,
            'audience_count': len(audience_list),
            'completed_at': timezone.now().isoformat()
        }
        game.save()

        # 发送通知
        if creator_user:
            title = '角斗场游戏结束'
            if winner == 'creator':
                message = f'恭喜！您在角斗场游戏中获胜，获得 {winner_reward} 积分奖励！'
            elif winner == 'tie':
                message = f'角斗场游戏平局，您获得 {winner_reward if winner == "creator" else loser_reward} 积分。'
            else:
                message = f'角斗场游戏结束，您获得 {loser_reward} 积分参与奖励。'

            NotificationModel.create_notification(
                recipient=creator_user,
                notification_type='game_result',
                actor=challenger_user or creator_user,
                title=title,
                message=message,
                related_object_type='game',
                related_object_id=game.id,
                extra_data={
                    'game_type': 'arena',
                    'result': game.result
                },
                priority='normal'
            )

        if challenger_user:
            title = '角斗场游戏结束'
            if winner == 'challenger':
                message = f'恭喜！您在角斗场游戏中获胜，获得 {winner_reward} 积分奖励！'
            elif winner == 'tie':
                message = f'角斗场游戏平局，您获得 {winner_reward if winner == "challenger" else loser_reward} 积分。'
            else:
                message = f'角斗场游戏结束，您获得 {loser_reward} 积分参与奖励。'

            NotificationModel.create_notification(
                recipient=challenger_user,
                notification_type='game_result',
                actor=creator_user or challenger_user,
                title=title,
                message=message,
                related_object_type='game',
                related_object_id=game.id,
                extra_data={
                    'game_type': 'arena',
                    'result': game.result
                },
                priority='normal'
            )

        # 发送通知给所有观众
        from users.models import User
        for audience_member in audience_list:
            try:
                audience_user = User.objects.get(id=audience_member['user_id'])
                voted_for = audience_member.get('vote_for', 'unknown')
                vote_result = '猜中了！' if (voted_for == winner or (voted_for == 'creator' and winner == 'creator') or (voted_for == 'challenger' and winner == 'challenger')) else '很遗憾，您支持的一方没有获胜。'

                NotificationModel.create_notification(
                    recipient=audience_user,
                    notification_type='game_result',
                    actor=creator_user or challenger_user,
                    title='角斗场游戏结束',
                    message=f'您参与的角斗场对决已结束！最终投票：发起者 {votes["creator"]} 票 vs 挑战者 {votes["challenger"]} 票。{vote_result}',
                    related_object_type='game',
                    related_object_id=game.id,
                    extra_data={
                        'game_type': 'arena',
                        'result': game.result,
                        'your_vote': voted_for
                    },
                    priority='normal'
                )
            except User.DoesNotExist:
                continue

        return game.result


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_arena_game_status(request, game_id):
    """获取角斗场游戏状态"""
    try:
        game = get_object_or_404(Game, id=game_id, game_type='arena')
        user = request.user

        # 检查用户权限
        is_creator = game.creator == user
        is_challenger = False
        is_audience = False
        has_access = False

        participant = GameParticipant.objects.filter(game=game, user=user).first()
        if participant:
            role = participant.action.get('role')
            if role == 'challenger':
                is_challenger = True
                has_access = True
            elif role == 'creator':
                has_access = True
            elif role == 'audience':
                is_audience = True
                # 检查是否在观众列表中且已支付
                for a in game.game_data.get('audience', []):
                    if a.get('user_id') == user.id:
                        has_access = True
                        break

        # 检查截止时间
        from django.utils.dateparse import parse_datetime
        deadline = parse_datetime(game.game_data['config']['deadline'])
        is_expired = deadline and timezone.now() > deadline

        # 如果游戏已截止但未结算，自动结算
        if is_expired and game.status == 'active':
            result = settle_arena_game_internal(game)
            return Response({
                'game': {
                    'id': str(game.id),
                    'status': 'completed',
                    'result': result
                }
            })

        # 构建响应数据
        response_data = {
            'id': str(game.id),
            'status': game.status,
            'bet_amount': game.bet_amount,
            'creator': {
                'id': game.creator.id,
                'username': game.creator.username
            },
            'config': game.game_data.get('config', {}),
            'votes': game.game_data.get('votes', {'creator': 0, 'challenger': 0}),
            'audience_count': len(game.game_data.get('audience', [])),
            'is_expired': is_expired,
            'user_role': 'creator' if is_creator else ('challenger' if is_challenger else ('audience' if is_audience else 'none')),
            'has_access': has_access
        }

        # 如果有权限，添加照片信息
        if has_access or game.status == 'completed':
            response_data['creator_photo'] = game.game_data.get('creator_photo')
            response_data['challenger_photo'] = game.game_data.get('challenger_photo')

        # 如果游戏已完成，添加结果
        if game.status == 'completed':
            response_data['result'] = game.result

        return Response(response_data)

    except Exception as e:
        logger.error(f"get_arena_game_status error: {e}", exc_info=True)
        return Response({
            'error': f'获取游戏状态失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_arena_games(request):
    """获取角斗场游戏列表"""
    try:
        status_filter = request.query_params.get('status', 'all')

        games = Game.objects.filter(game_type='arena')

        if status_filter != 'all':
            games = games.filter(status=status_filter)

        games = games.order_by('-created_at')[:50]

        result = []
        for game in games:
            # 获取挑战者信息
            challenger = None
            for p in GameParticipant.objects.filter(game=game):
                if p.action.get('role') == 'challenger':
                    challenger = p.user
                    break

            result.append({
                'id': str(game.id),
                'creator': {
                    'id': game.creator.id,
                    'username': game.creator.username
                },
                'challenger': {
                    'id': challenger.id,
                    'username': challenger.username
                } if challenger else None,
                'bet_amount': game.bet_amount,
                'status': game.status,
                'config': {
                    'audience_ticket_price': game.game_data.get('config', {}).get('audience_ticket_price', 5),
                    'max_audience': game.game_data.get('config', {}).get('max_audience', 20)
                },
                'audience_count': len(game.game_data.get('audience', [])),
                'audience': game.game_data.get('audience', []),
                'votes': game.game_data.get('votes', {'creator': 0, 'challenger': 0}),
                'result': game.result,
                'created_at': game.created_at.isoformat()
            })

        return Response({
            'games': result,
            'count': len(result)
        })

    except Exception as e:
        logger.error(f"list_arena_games error: {e}", exc_info=True)
        return Response({
            'error': f'获取游戏列表失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
