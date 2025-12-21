from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q, Count, F
from datetime import timedelta
import random
import logging

logger = logging.getLogger(__name__)

from .models import LockTask, TaskKey, TaskVote, OvertimeAction, TaskTimelineEvent, HourlyReward, TaskParticipant, PinnedUser
from store.models import ItemType, UserInventory, Item
from users.models import Notification
from .utils import destroy_task_keys
from .pinning_service import PinningQueueManager
from .pagination import DynamicPageNumberPagination
from .serializers import (
    LockTaskSerializer, LockTaskCreateSerializer,
    TaskKeySerializer, TaskVoteSerializer, TaskVoteCreateSerializer,
    TaskTimelineEventSerializer
)


class IsOwnerOrAdmin(permissions.BasePermission):
    """只有拥有者或管理员可以操作"""

    def has_object_permission(self, request, view, obj):
        # 对于删除操作，只允许工作人员和超级用户
        if request.method == 'DELETE':
            return request.user.is_staff or request.user.is_superuser
        # 对于其他操作（GET, PUT, PATCH），保持原有逻辑
        return obj.user == request.user or request.user.is_superuser


class LockTaskListCreateView(generics.ListCreateAPIView):
    """任务列表和创建"""
    permission_classes = [IsAuthenticated]
    pagination_class = DynamicPageNumberPagination

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return LockTaskCreateSerializer
        return LockTaskSerializer

    def get_queryset(self):
        # 在获取任务列表时，自动处理过期的投票
        try:
            _process_voting_results_internal()
        except Exception as e:
            # 不让投票处理错误影响任务列表获取
            print(f"Warning: Failed to process voting results: {e}")

        queryset = LockTask.objects.all()

        # 按任务类型筛选
        task_type = self.request.query_params.get('task_type')
        if task_type:
            queryset = queryset.filter(task_type=task_type)

        # 按状态筛选
        status = self.request.query_params.get('status')
        if status:
            if status == 'available':  # "可接取" - 新的筛选逻辑
                # 只包括开放中的单人任务和未满员未到期的多人任务
                from django.utils import timezone

                # 筛选任务板类型
                queryset = queryset.filter(task_type='board')

                # 添加参与者数量注释
                queryset = queryset.annotate(
                    current_participants=Count('participants')
                )

                # 时间条件：未过期
                time_condition = Q(deadline__isnull=True) | Q(deadline__gt=timezone.now())

                # 分别处理单人和多人任务的状态条件
                single_person_condition = (
                    (Q(max_participants__isnull=True) | Q(max_participants=1)) &
                    Q(status='open')  # 单人任务只能是开放状态
                )

                multi_person_condition = (
                    Q(max_participants__gt=1) &
                    Q(status__in=['open', 'taken', 'submitted']) &  # 多人任务允许这些状态
                    Q(current_participants__lt=F('max_participants'))  # 且未满员
                )

                # 组合所有条件
                queryset = queryset.filter(
                    time_condition & (single_person_condition | multi_person_condition)
                )
            else:
                queryset = queryset.filter(status=status)

        # 按用户筛选（我的任务）
        my_tasks = self.request.query_params.get('my_tasks')
        if my_tasks == 'true':
            queryset = queryset.filter(user=self.request.user)

        # 按接取者筛选（我接取的任务）
        my_taken = self.request.query_params.get('my_taken')
        if my_taken == 'true':
            # 支持单人任务和多人任务
            queryset = queryset.filter(
                Q(taker=self.request.user) |  # 单人任务：我是taker
                Q(participants__participant=self.request.user)  # 多人任务：我是参与者
            ).distinct()

        # 筛选可以加时的任务（绒布球筛选）
        can_overtime = self.request.query_params.get('can_overtime')
        if can_overtime == 'true':
            from django.utils import timezone
            from datetime import timedelta
            from .models import OvertimeAction

            # 基础条件：带锁任务、活跃状态、不是自己的任务
            queryset = queryset.filter(
                task_type='lock',
                status='active'
            ).exclude(user=self.request.user)

            # 排除两小时内已经对同一发布者加过时的任务
            two_hours_ago = timezone.now() - timedelta(hours=2)
            recent_overtime_publishers = OvertimeAction.objects.filter(
                user=self.request.user,
                created_at__gte=two_hours_ago
            ).values_list('task_publisher', flat=True).distinct()

            if recent_overtime_publishers:
                queryset = queryset.exclude(user__in=recent_overtime_publishers)

        # 处理排序参数
        sort_by = self.request.query_params.get('sort_by', 'user_activity')
        sort_order = self.request.query_params.get('sort_order', 'desc')

        # 定义排序字段映射
        sort_field_mapping = {
            'created_time': 'created_at',
            'end_time': 'end_time',
            'remaining_time': 'end_time',  # 剩余时间实际上是根据结束时间排序
            'difficulty': 'difficulty',
            'user_activity': 'user__last_active'  # 用户活跃度
        }

        # 获取实际的排序字段
        sort_field = sort_field_mapping.get(sort_by, 'created_at')

        # 处理排序方向
        if sort_order == 'desc':
            sort_field = f'-{sort_field}'

        # 对于剩余时间排序，需要特殊处理（只对活跃任务有意义）
        if sort_by == 'remaining_time':
            # 剩余时间排序：先按是否有结束时间排序，再按结束时间排序
            if sort_order == 'asc':
                # 升序：剩余时间少的在前（结束时间早的在前）
                queryset = queryset.order_by('end_time', 'created_at')
            else:
                # 降序：剩余时间多的在前（结束时间晚的在前）
                queryset = queryset.order_by('-end_time', '-created_at')
        else:
            # 其他排序方式
            queryset = queryset.order_by(sort_field, '-created_at')  # 添加创建时间作为次要排序

        return queryset

    def perform_create(self, serializer):
        from rest_framework.exceptions import ValidationError

        # 如果是带锁任务，需要先检查背包容量并生成钥匙道具
        if serializer.validated_data.get('task_type') == 'lock':
            user = self.request.user

            # 获取或创建用户背包
            inventory, _ = UserInventory.objects.get_or_create(user=user)

            # 检查背包是否有空间存放钥匙
            if not inventory.can_add_item():
                raise ValidationError({
                    'non_field_errors': [f'背包已满，无法生成钥匙道具。请先清理背包空间（当前 {inventory.used_slots}/{inventory.max_slots}）']
                })

            # 获取钥匙道具类型
            try:
                key_item_type = ItemType.objects.get(name='key')
            except ItemType.DoesNotExist:
                raise ValidationError({
                    'non_field_errors': ['系统错误：钥匙道具类型不存在']
                })

        # Debug: Log the validated data
        print(f"DEBUG: Serializer validated_data: {serializer.validated_data}")

        task = serializer.save()

        # Debug: Log the saved task
        print(f"DEBUG: Saved task - strict_mode: {task.strict_mode}, task_type: {task.task_type}")

        # 生成严格模式随机码
        if task.task_type == 'lock' and task.strict_mode:
            task.strict_code = self.generate_strict_code()
            task.save()
            print(f"DEBUG: Generated strict code: {task.strict_code}")
        else:
            print(f"DEBUG: No strict code generated - task_type: {task.task_type}, strict_mode: {task.strict_mode}")

        # 创建任务创建事件
        TaskTimelineEvent.objects.create(
            task=task,
            event_type='task_created',
            user=task.user,
            description=f'任务创建: {task.title}',
            metadata={
                'task_type': task.task_type,
                'difficulty': task.difficulty,
                'duration_value': task.duration_value
            }
        )

        # 如果是带锁任务，创建后直接开始并生成钥匙道具
        if task.task_type == 'lock':
            # 生成钥匙道具
            key_item = Item.objects.create(
                item_type=key_item_type,
                owner=task.user,
                original_owner=task.user,  # 设置原始拥有者为任务创建者
                inventory=inventory,
                properties={
                    'task_id': str(task.id),
                    'task_title': task.title,
                    'created_for_task': True,
                    'auto_destroy_on_completion': True
                }
            )

            task.status = 'active'
            task.start_time = timezone.now()

            # 计算结束时间
            if task.duration_type == 'fixed':
                end_time = task.start_time + timezone.timedelta(minutes=task.duration_value)
            elif task.duration_type == 'random':
                # 在范围内随机选择时间
                if task.duration_max and task.duration_max > task.duration_value:
                    random_minutes = random.randint(task.duration_value, task.duration_max)
                else:
                    # 如果没有设置最大时间或最大时间不合理，使用固定时间
                    random_minutes = task.duration_value
                end_time = task.start_time + timezone.timedelta(minutes=random_minutes)
            else:
                end_time = None

            task.end_time = end_time
            task.save()

            # 创建任务开始事件
            TaskTimelineEvent.objects.create(
                task=task,
                event_type='task_started',
                user=task.user,
                new_end_time=end_time,
                description=f'任务开始: 计划时长{task.duration_value}分钟，钥匙道具已生成',
                metadata={
                    'duration_type': task.duration_type,
                    'actual_duration_minutes': random_minutes if task.duration_type == 'random' else task.duration_value,
                    'key_item_id': str(key_item.id)
                }
            )

            # 如果是投票解锁类型，自动创建钥匙记录（兼容现有系统）
            if task.unlock_type == 'vote':
                TaskKey.objects.create(
                    task=task,
                    holder=task.user
                )
        elif task.task_type == 'board':
            # 任务板创建后设置为开放状态
            task.status = 'open'

            # 如果设置了奖励，需要从发布者的积分中扣除
            if task.reward and task.reward > 0:
                if task.user.coins < task.reward:
                    # 销毁任务相关的所有钥匙道具（如果有的话）
                    destroy_task_keys(task, reason="task_deleted", user=task.user, metadata={
                        'deletion_reason': 'insufficient_funds',
                        'required_coins': task.reward,
                        'available_coins': task.user.coins
                    })
                    # 删除刚创建的任务，因为积分不足
                    task.delete()
                    raise ValidationError({
                        'reward': [f'积分不足。您当前有{task.user.coins}积分，但设置的奖励需要{task.reward}积分']
                    })

                # 扣除发布者的积分
                task.user.coins -= task.reward
                task.user.save()

                # 创建积分扣除事件
                TaskTimelineEvent.objects.create(
                    task=task,
                    event_type='task_created',
                    user=task.user,
                    description=f'任务发布，扣除{task.reward}积分作为奖励',
                    metadata={
                        'task_type': task.task_type,
                        'reward_amount': task.reward,
                        'publisher_remaining_coins': task.user.coins
                    }
                )

            # 如果任务创建时就设置了deadline，立即调度自动结算
            if task.deadline:
                try:
                    from celery_app import app as celery_app
                    deadline_timestamp = task.deadline.timestamp()
                    celery_app.send_task(
                        'tasks.celery_tasks.schedule_board_task_auto_settlement',
                        args=[str(task.id), deadline_timestamp]
                    )
                    logger.info(f"Scheduled auto-settlement for board task {task.id} created with deadline at {task.deadline}")
                except Exception as e:
                    logger.error(f"Failed to schedule auto-settlement for newly created task {task.id}: {e}")

            task.save()

    def generate_strict_code(self):
        """Generate 4-character code like A1B2"""
        import random
        import string
        letters = random.choices(string.ascii_uppercase, k=2)
        digits = random.choices(string.digits, k=2)
        return f"{letters[0]}{digits[0]}{letters[1]}{digits[1]}"


class LockTaskDetailView(generics.RetrieveUpdateDestroyAPIView):
    """任务详情、更新和删除"""
    queryset = LockTask.objects.all()
    serializer_class = LockTaskSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def get_object(self):
        """获取任务对象前，先处理投票结果"""
        # 在获取任务详情时，自动处理过期的投票
        try:
            _process_voting_results_internal()
        except Exception as e:
            # 不让投票处理错误影响任务详情获取
            print(f"Warning: Failed to process voting results: {e}")

        return super().get_object()

    def get_permissions(self):
        """设置不同操作的权限"""
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            # 只有任务创建者或超级用户可以编辑和删除
            return [IsAuthenticated(), IsOwnerOrAdmin()]
        return [IsAuthenticated()]

    def perform_destroy(self, instance):
        """删除任务前销毁相关钥匙"""
        # 销毁任务相关的所有钥匙道具
        destroy_result = destroy_task_keys(instance, reason="task_deleted", user=self.request.user, metadata={
            'deletion_method': 'manual_delete',
            'deleted_by': self.request.user.username
        })

        # 执行实际删除
        super().perform_destroy(instance)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_task(request, pk):
    """开始任务"""
    task = get_object_or_404(LockTask, pk=pk)

    # 检查权限
    if task.user != request.user:
        return Response(
            {'error': '只有任务创建者可以开始任务'},
            status=status.HTTP_403_FORBIDDEN
        )

    # 检查任务状态
    if task.status != 'pending':
        return Response(
            {'error': '任务不是待开始状态'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 更新任务状态
    task.status = 'active'
    task.start_time = timezone.now()

    # 计算结束时间
    if task.duration_type == 'fixed':
        end_time = task.start_time + timezone.timedelta(minutes=task.duration_value)
    elif task.duration_type == 'random':
        # 在范围内随机选择时间
        if task.duration_max and task.duration_max > task.duration_value:
            random_minutes = random.randint(task.duration_value, task.duration_max)
        else:
            # 如果没有设置最大时间或最大时间不合理，使用固定时间
            random_minutes = task.duration_value
        end_time = task.start_time + timezone.timedelta(minutes=random_minutes)
    else:
        end_time = None

    task.end_time = end_time
    task.save()

    serializer = LockTaskSerializer(task)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_task(request, pk):
    """完成任务"""
    task = get_object_or_404(LockTask, pk=pk)

    # 检查任务状态
    if task.status not in ['active', 'voting']:
        return Response(
            {'error': '任务不在可完成状态'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 如果任务处于投票期，需要先检查投票期是否结束
    if task.status == 'voting':
        if task.voting_end_time and timezone.now() < task.voting_end_time:
            return Response(
                {'error': '投票期未结束，无法完成任务'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 投票期结束，先处理投票结果
        process_voting_results(request)
        # 重新获取任务状态
        task.refresh_from_db()

        # 如果处理后任务不是active状态，说明投票失败了
        if task.status != 'active':
            return Response(
                {'error': '投票未通过，任务已加时，请等待新的倒计时结束'},
                status=status.HTTP_400_BAD_REQUEST
            )

    # 检查是否是带锁任务，如果是，需要满足所有完成条件
    if task.task_type == 'lock':
        # 条件0: 冻结状态的任务不能完成
        if task.is_frozen:
            return Response(
                {'error': '冻结状态的任务无法完成，请先解冻'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 条件1: 倒计时必须结束
        if task.end_time and timezone.now() < task.end_time:
            return Response(
                {'error': '带锁任务必须等待倒计时结束后才能完成'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 条件2: 投票解锁类型的任务需要检查投票是否通过
        if task.unlock_type == 'vote':
            # 检查是否有投票记录且投票通过
            if not task.voting_end_time:
                return Response(
                    {'error': '投票解锁任务必须先发起投票'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 检查投票是否通过
            total_votes = task.votes.count()
            agree_votes = task.votes.filter(agree=True).count()

            # 检查投票数量是否达到门槛
            required_votes = task.vote_threshold or 1  # 如果没有设置门槛，默认需要1票
            if total_votes < required_votes:
                return Response(
                    {'error': f'投票数量不足，需要至少 {required_votes} 票，当前 {total_votes} 票'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 检查同意比例是否达到要求
            agreement_ratio = agree_votes / total_votes if total_votes > 0 else 0
            required_ratio = task.vote_agreement_ratio or 0.5

            if agreement_ratio < required_ratio:
                return Response(
                    {'error': f'投票同意率不足，需要 {required_ratio*100:.0f}%，当前 {agreement_ratio*100:.1f}%'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 投票通过，可以继续完成任务

        # 条件3: 检查用户是否持有对应的钥匙道具
        # 只有钥匙的当前持有者（无论是原始创建者还是其他人）可以完成任务
        task_key_item = Item.objects.filter(
            item_type__name='key',
            owner=request.user,
            status='available',
            properties__task_id=str(task.id)
        ).first()

        if not task_key_item:
            # 检查任务的原始创建者，提供更详细的错误信息
            original_key = Item.objects.filter(
                item_type__name='key',
                status='available',
                properties__task_id=str(task.id)
            ).first()

            if original_key and original_key.original_owner:
                if original_key.original_owner == request.user:
                    error_msg = '您已将此任务的钥匙转让给他人，无法完成任务。只有钥匙的当前持有者可以完成任务。'
                else:
                    error_msg = f'只有钥匙的当前持有者（{original_key.owner.username}）可以完成此任务。'
            else:
                error_msg = '您没有持有该任务的钥匙道具，无法完成任务'

            return Response(
                {'error': error_msg},
                status=status.HTTP_403_FORBIDDEN
            )

        # 使用通用钥匙销毁函数销毁所有任务相关钥匙
        destroy_result = destroy_task_keys(task, reason="task_completed", user=request.user, metadata={
            'completion_method': 'manual',
            'key_holder': request.user.username
        })

    # 更新任务状态
    task.status = 'completed'
    task.completed_at = timezone.now()

    # 任务完成时的奖励处理
    completion_rewards = 0
    if task.task_type == 'lock':
        # 1. 首先处理所有未发放的小时奖励
        hourly_rewards_processed = _process_task_hourly_rewards(task)

        # 2. 计算并发放完成奖励（基于难度的一次性奖励）
        completion_bonus = _calculate_completion_bonus(task)
        if completion_bonus > 0:
            task.user.coins += completion_bonus
            task.user.save()
            completion_rewards = completion_bonus

            # 创建完成奖励通知
            Notification.create_notification(
                recipient=task.user,
                notification_type='coins_earned_task_completion',
                actor=None,
                related_object_type='task',
                related_object_id=task.id,
                extra_data={
                    'task_title': task.title,
                    'completion_bonus': completion_bonus,
                    'difficulty': task.difficulty,
                    'hourly_rewards_processed': hourly_rewards_processed
                },
                priority='normal'
            )

    task.save()

    # 创建任务完成事件
    completion_metadata = {
        'completed_by': 'manual',
        'completion_time': task.completed_at.isoformat(),
        'key_destroyed': task.task_type == 'lock'
    }

    # 如果有钥匙被销毁，在元数据中记录详细信息
    if task.task_type == 'lock' and 'destroy_result' in locals() and destroy_result['success']:
        completion_metadata.update({
            'keys_destroyed': destroy_result['keys_destroyed'],
            'destroyed_key_details': destroy_result['destroyed_keys']
        })

    # 元数据中包含奖励信息
    if task.task_type == 'lock':
        completion_metadata.update({
            'reward_system': 'hourly_plus_completion_bonus',
            'completion_bonus': completion_rewards,
            'hourly_rewards_processed': hourly_rewards_processed if 'hourly_rewards_processed' in locals() else 0
        })

    if task.task_type == 'lock':
        # 记录完成时的所有条件状态
        completion_metadata.update({
            'time_expired': task.end_time and timezone.now() >= task.end_time,
            'vote_required': task.unlock_type == 'vote',
            'key_holder_completed': True,
            'was_frozen_at_completion': task.is_frozen,
            'total_frozen_duration': task.total_frozen_duration.total_seconds() if task.total_frozen_duration else 0
        })

        if task.unlock_type == 'vote':
            total_votes = task.votes.count()
            agree_votes = task.votes.filter(agree=True).count()
            completion_metadata.update({
                'total_votes': total_votes,
                'agree_votes': agree_votes,
                'agreement_ratio': agree_votes / total_votes if total_votes > 0 else 0,
                'required_ratio': task.vote_agreement_ratio or 0.5,
                'vote_agreement_ratio': task.vote_agreement_ratio
            })

    # 构建完成描述
    completion_description = '任务手动完成 - 满足所有完成条件'
    if task.task_type == 'lock':
        if 'destroy_result' in locals() and destroy_result['success'] and destroy_result['keys_destroyed'] > 0:
            completion_description += f'，已销毁 {destroy_result["keys_destroyed"]} 个相关钥匙'
        else:
            completion_description += '，钥匙道具已销毁'

    TaskTimelineEvent.objects.create(
        task=task,
        event_type='task_completed',
        user=request.user,
        description=completion_description,
        metadata=completion_metadata
    )

    serializer = LockTaskSerializer(task)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def stop_task(request, pk):
    """停止任务（标记为失败）"""
    task = get_object_or_404(LockTask, pk=pk)

    # 检查权限
    if task.user != request.user:
        return Response(
            {'error': '只有任务创建者可以停止任务'},
            status=status.HTTP_403_FORBIDDEN
        )

    # 检查任务状态
    if task.status not in ['active', 'voting']:
        return Response(
            {'error': '任务不在可停止状态'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 更新任务状态
    task.status = 'failed'
    task.end_time = timezone.now()
    task.save()

    # 销毁任务相关的所有钥匙道具
    destroy_result = destroy_task_keys(task, reason="task_stopped", user=request.user, metadata={
        'stopped_by': 'manual',
        'stop_time': task.end_time.isoformat()
    })

    # 创建任务停止事件
    stop_metadata = {
        'stopped_by': 'manual',
        'stop_time': task.end_time.isoformat()
    }

    # 如果有钥匙被销毁，在元数据中记录
    if destroy_result['success'] and destroy_result['keys_destroyed'] > 0:
        stop_metadata.update({
            'keys_destroyed': destroy_result['keys_destroyed'],
            'destroyed_key_details': destroy_result['destroyed_keys']
        })

    TaskTimelineEvent.objects.create(
        task=task,
        event_type='task_stopped',
        user=request.user,
        description=f'任务手动停止{"，已销毁 " + str(destroy_result["keys_destroyed"]) + " 个相关钥匙" if destroy_result["success"] and destroy_result["keys_destroyed"] > 0 else ""}',
        metadata=stop_metadata
    )

    serializer = LockTaskSerializer(task)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def take_board_task(request, pk):
    """接取任务板任务 - 支持单人和多人任务"""
    task = get_object_or_404(LockTask, pk=pk)

    # 检查是否是任务板
    if task.task_type != 'board':
        return Response(
            {'error': '只能接取任务板任务'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 检查是否是自己发布的任务
    if task.user == request.user:
        return Response(
            {'error': '不能接取自己发布的任务'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 检查是否已经参与过
    if TaskParticipant.objects.filter(task=task, participant=request.user).exists():
        return Response(
            {'error': '您已经参与了这个任务'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 判断是单人还是多人任务
    is_multi_person = task.max_participants and task.max_participants > 1

    if is_multi_person:
        # 多人任务逻辑
        # 检查任务状态：可以是'open'、'taken'或'submitted'（已有人提交但未满员）
        if task.status not in ['open', 'taken', 'submitted']:
            return Response(
                {'error': '任务不可接取'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 检查是否已满员
        current_participants = TaskParticipant.objects.filter(task=task).count()
        if current_participants >= task.max_participants:
            return Response(
                {'error': '任务已满员'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 创建参与记录
        participant = TaskParticipant.objects.create(
            task=task,
            participant=request.user
        )

        # 如果是第一个参与者，更新任务状态为taken
        if current_participants == 0 and task.status == 'open':
            task.status = 'taken'
            task.taker = request.user  # 保留第一个接取者信息
            task.taken_at = timezone.now()

            # 设置任务截止时间
            if task.max_duration:
                task.deadline = task.taken_at + timezone.timedelta(hours=task.max_duration)

                # 调度自动结算任务（使用Celery延时执行）
                try:
                    from celery_app import app as celery_app
                    deadline_timestamp = task.deadline.timestamp()
                    celery_app.send_task(
                        'tasks.celery_tasks.schedule_board_task_auto_settlement',
                        args=[str(task.id), deadline_timestamp]
                    )
                    logger.info(f"Scheduled auto-settlement for multi-person task {task.id} at {task.deadline}")
                except Exception as e:
                    logger.error(f"Failed to schedule auto-settlement for multi-person task {task.id}: {e}")

            task.save()

        notification_type = 'task_board_taken'
        extra_data = {
            'task_title': task.title,
            'participant': request.user.username,
            'current_participants': current_participants + 1,
            'max_participants': task.max_participants
        }

    else:
        # 单人任务逻辑（保持原有逻辑）
        if task.status != 'open':
            return Response(
                {'error': '任务不是开放状态'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 更新任务状态
        task.status = 'taken'
        task.taker = request.user
        task.taken_at = timezone.now()

        # 设置任务截止时间
        if task.max_duration:
            task.deadline = task.taken_at + timezone.timedelta(hours=task.max_duration)

            # 调度自动结算任务（使用Celery延时执行）
            try:
                from celery_app import app as celery_app
                deadline_timestamp = task.deadline.timestamp()
                celery_app.send_task(
                    'tasks.celery_tasks.schedule_board_task_auto_settlement',
                    args=[str(task.id), deadline_timestamp]
                )
                logger.info(f"Scheduled auto-settlement for task {task.id} at {task.deadline}")
            except Exception as e:
                logger.error(f"Failed to schedule auto-settlement for task {task.id}: {e}")

        task.save()

        # 为单人任务也创建参与记录（统一管理）
        TaskParticipant.objects.create(
            task=task,
            participant=request.user
        )

        notification_type = 'task_board_taken'
        extra_data = {
            'task_title': task.title,
            'taker': request.user.username,
            'deadline': task.deadline.isoformat() if task.deadline else None
        }

    # 创建任务接取通知
    Notification.create_notification(
        recipient=task.user,
        notification_type=notification_type,
        actor=request.user,
        related_object_type='task',
        related_object_id=task.id,
        extra_data=extra_data
    )

    serializer = LockTaskSerializer(task)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_board_task(request, pk):
    """提交任务板任务完成证明 - 支持单人和多人任务"""
    from .models import TaskSubmissionFile

    task = get_object_or_404(LockTask, pk=pk)

    # 检查是否是参与者
    try:
        participant = TaskParticipant.objects.get(task=task, participant=request.user)
    except TaskParticipant.DoesNotExist:
        return Response(
            {'error': '您不是此任务的参与者'},
            status=status.HTTP_403_FORBIDDEN
        )

    # 检查是否已经提交过
    if participant.status == 'submitted':
        return Response(
            {'error': '您已经提交过了'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 检查任务状态
    if task.status not in ['taken', 'submitted']:
        return Response(
            {'error': '任务状态不允许提交'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 获取完成证明
    completion_proof = request.data.get('completion_proof', '')
    if not completion_proof:
        return Response(
            {'error': '请提供完成证明'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 更新参与者状态
    participant.status = 'submitted'
    participant.submission_text = completion_proof
    participant.submitted_at = timezone.now()
    participant.save()

    # 判断是单人还是多人任务
    is_multi_person = task.max_participants and task.max_participants > 1

    if not is_multi_person:
        # 单人任务：直接更新任务状态
        task.status = 'submitted'
        task.completion_proof = completion_proof
        task.save()
    else:
        # 多人任务：更智能的状态转换逻辑
        if task.status == 'open':
            # 如果还是开放状态，第一个人提交时改为taken（表示有人开始工作）
            task.status = 'taken'
            task.save()
        elif task.status == 'taken':
            # 如果已经有人接取，第一个人提交时改为submitted
            task.status = 'submitted'
            task.save()
        # 如果已经是submitted状态，保持不变，允许其他人继续参与和提交

    # 处理上传的文件
    uploaded_files = request.FILES.getlist('files')
    if uploaded_files:
        for i, uploaded_file in enumerate(uploaded_files):
            # 创建文件记录
            submission_file = TaskSubmissionFile(
                task=task,
                uploader=request.user,
                participant=participant,  # 关联到参与者
                file=uploaded_file,
                file_name=uploaded_file.name,
                file_size=uploaded_file.size,
                description=request.data.get(f'file_descriptions[{i}]', ''),
                is_primary=(i == 0)  # 第一个文件设为主要文件
            )

            # 根据文件扩展名自动设置文件类型
            submission_file.file_type = submission_file.get_file_type_from_extension(uploaded_file.name)
            submission_file.save()

            logger.info(f"Uploaded file {uploaded_file.name} for task {task.id} by user {request.user.username}")

    # 创建任务提交通知
    if is_multi_person:
        # 多人任务：显示参与者信息
        submitted_count = TaskParticipant.objects.filter(task=task, status='submitted').count()
        extra_data = {
            'task_title': task.title,
            'submitter': request.user.username,
            'completion_proof_preview': completion_proof[:100] + '...' if len(completion_proof) > 100 else completion_proof,
            'file_count': len(uploaded_files) if uploaded_files else 0,
            'submitted_count': submitted_count,
            'max_participants': task.max_participants
        }
    else:
        # 单人任务：保持原有格式
        extra_data = {
            'task_title': task.title,
            'submitter': request.user.username,
            'completion_proof_preview': completion_proof[:100] + '...' if len(completion_proof) > 100 else completion_proof,
            'file_count': len(uploaded_files) if uploaded_files else 0
        }

    Notification.create_notification(
        recipient=task.user,
        notification_type='task_board_submitted',
        actor=request.user,
        related_object_type='task',
        related_object_id=task.id,
        extra_data=extra_data
    )

    serializer = LockTaskSerializer(task)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_voting(request, pk):
    """任务所属人发起投票"""
    task = get_object_or_404(LockTask, pk=pk)

    # 检查是否是投票解锁任务
    if task.unlock_type != 'vote':
        return Response(
            {'error': '该任务不是投票解锁类型'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 检查权限 - 只有任务所属人可以发起投票
    if task.user != request.user:
        return Response(
            {'error': '只有任务所属人可以发起投票'},
            status=status.HTTP_403_FORBIDDEN
        )

    # 检查任务状态 - 必须是活跃状态且倒计时已结束
    if task.status != 'active':
        return Response(
            {'error': '任务不在可发起投票状态'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 检查倒计时是否结束
    if task.end_time and timezone.now() < task.end_time:
        return Response(
            {'error': '请等待倒计时结束后再发起投票'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 检查是否已经在投票期
    if task.status == 'voting':
        return Response(
            {'error': '投票期已开始'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 清除之前的投票记录（如果有的话）
    task.votes.all().delete()

    # 开始投票期
    task.status = 'voting'
    task.voting_start_time = timezone.now()
    task.voting_end_time = task.voting_start_time + timezone.timedelta(minutes=task.voting_duration)
    task.save()

    # 创建进入投票期事件
    TaskTimelineEvent.objects.create(
        task=task,
        event_type='voting_started',
        user=request.user,
        description=f'任务所属人发起投票，进入{task.voting_duration}分钟投票期',
        metadata={
            'voting_duration_minutes': task.voting_duration,
            'voting_start_time': task.voting_start_time.isoformat(),
            'voting_end_time': task.voting_end_time.isoformat()
        }
    )

    return Response(LockTaskSerializer(task).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def vote_task(request, pk):
    """为任务投票"""
    task = get_object_or_404(LockTask, pk=pk)

    # 检查是否是投票解锁任务
    if task.unlock_type != 'vote':
        return Response(
            {'error': '该任务不是投票解锁类型'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 检查任务状态 - 只允许在投票期投票
    if task.status != 'voting':
        return Response(
            {'error': '任务不在投票期，请等待任务所属人发起投票'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 检查投票期是否已结束
    if task.voting_end_time and timezone.now() >= task.voting_end_time:
        return Response(
            {'error': '投票期已结束'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 检查是否已经投过票
    if TaskVote.objects.filter(task=task, voter=request.user).exists():
        return Response(
            {'error': '已经投过票了'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 创建投票
    serializer = TaskVoteCreateSerializer(
        data=request.data,
        context={'request': request, 'task': task}
    )

    if serializer.is_valid():
        vote = serializer.save()

        # 获取当前投票统计
        total_votes = task.votes.count()
        agree_votes = task.votes.filter(agree=True).count()

        # 创建投票事件记录
        TaskTimelineEvent.objects.create(
            task=task,
            event_type='task_voted',
            user=request.user,
            description=f'{request.user.username} 投票{"同意" if vote.agree else "反对"}（{agree_votes}/{total_votes}票同意）',
            metadata={
                'vote_agree': vote.agree,
                'total_votes': total_votes,
                'agree_votes': agree_votes,
                'agreement_ratio': agree_votes / total_votes if total_votes > 0 else 0,
                'required_ratio': task.vote_agreement_ratio or 0.5,
                'voting_period': True,
                'voting_end_time': task.voting_end_time.isoformat() if task.voting_end_time else None
            }
        )

        return Response(TaskVoteSerializer(vote).data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_board_task(request, pk):
    """发布者审核通过任务板任务 - 支持多人任务，不自动结算"""
    task = get_object_or_404(LockTask, pk=pk)

    # 检查权限 - 只有任务发布者可以审核
    if task.user != request.user:
        return Response(
            {'error': '只有任务发布者可以审核任务'},
            status=status.HTTP_403_FORBIDDEN
        )

    # 检查任务状态
    if task.status != 'submitted':
        return Response(
            {'error': '任务不是已提交状态'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 获取要审核的参与者ID（多人任务）或使用默认的taker（单人任务）
    participant_id = request.data.get('participant_id')

    # 判断是单人还是多人任务
    is_multi_person = task.max_participants and task.max_participants > 1

    if is_multi_person:
        # 多人任务：审核特定参与者
        if not participant_id:
            return Response(
                {'error': '多人任务需要指定参与者ID'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            participant = TaskParticipant.objects.get(id=participant_id, task=task)
        except TaskParticipant.DoesNotExist:
            return Response(
                {'error': '参与者不存在'},
                status=status.HTTP_404_NOT_FOUND
            )

        if participant.status != 'submitted':
            return Response(
                {'error': '该参与者未提交作品或已被审核'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 更新参与者状态
        participant.status = 'approved'
        participant.reviewed_at = timezone.now()
        participant.review_comment = request.data.get('review_comment', '')
        participant.save()

        # 创建审核事件
        TaskTimelineEvent.objects.create(
            task=task,
            event_type='participant_approved',
            user=request.user,
            description=f'参与者 {participant.participant.username} 的提交被审核通过',
            metadata={
                'approved_by': request.user.username,
                'participant_id': str(participant.id),
                'participant_username': participant.participant.username,
                'review_comment': participant.review_comment
            }
        )

        # 通知参与者
        Notification.create_notification(
            recipient=participant.participant,
            notification_type='task_board_approved',
            actor=request.user,
            related_object_type='task',
            related_object_id=task.id,
            extra_data={
                'task_title': task.title,
                'approver': request.user.username,
                'review_comment': participant.review_comment
            }
        )

        # 多人任务不自动结算，需要发布者手动结束任务

    else:
        # 单人任务：直接审核通过并完成任务
        try:
            participant = TaskParticipant.objects.get(task=task, participant=task.taker)
        except TaskParticipant.DoesNotExist:
            return Response(
                {'error': '找不到参与者记录'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 更新参与者状态
        participant.status = 'approved'
        participant.reviewed_at = timezone.now()
        participant.review_comment = request.data.get('review_comment', '')
        participant.save()

        # 单人任务立即完成
        task.status = 'completed'
        task.completed_at = timezone.now()

        # 处理奖励积分转移
        if task.reward and task.reward > 0:
            task.taker.coins += task.reward
            task.taker.save()

            # 创建奖励转移事件
            TaskTimelineEvent.objects.create(
                task=task,
                event_type='task_completed',
                user=request.user,
                description=f'任务审核通过，{task.taker.username}获得{task.reward}积分奖励',
                metadata={
                    'approved_by': request.user.username,
                    'reward_amount': task.reward,
                    'reward_recipient': task.taker.username,
                    'taker_total_coins': task.taker.coins
                }
            )

            # 创建任务奖励积分通知
            Notification.create_notification(
                recipient=task.taker,
                notification_type='coins_earned_task_reward',
                actor=request.user,
                related_object_type='task',
                related_object_id=task.id,
                extra_data={
                    'task_title': task.title,
                    'reward_amount': task.reward,
                    'approver': request.user.username
                }
            )

        # 创建任务审核通过通知
        Notification.create_notification(
            recipient=task.taker,
            notification_type='task_board_approved',
            actor=request.user,
            related_object_type='task',
            related_object_id=task.id,
            extra_data={
                'task_title': task.title,
                'approver': request.user.username,
                'reward_amount': task.reward if task.reward else 0
            }
        )

        task.save()

    serializer = LockTaskSerializer(task)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reject_board_task(request, pk):
    """发布者审核拒绝任务板任务 - 支持多人任务"""
    task = get_object_or_404(LockTask, pk=pk)

    # 检查权限 - 只有任务发布者可以审核
    if task.user != request.user:
        return Response(
            {'error': '只有任务发布者可以审核任务'},
            status=status.HTTP_403_FORBIDDEN
        )

    # 检查任务状态
    if task.status != 'submitted':
        return Response(
            {'error': '任务不是已提交状态'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 获取拒绝原因和参与者ID
    reject_reason = request.data.get('reject_reason', '')
    participant_id = request.data.get('participant_id')

    # 判断是单人还是多人任务
    is_multi_person = task.max_participants and task.max_participants > 1

    if is_multi_person:
        # 多人任务：拒绝特定参与者
        if not participant_id:
            return Response(
                {'error': '多人任务需要指定参与者ID'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            participant = TaskParticipant.objects.get(id=participant_id, task=task)
        except TaskParticipant.DoesNotExist:
            return Response(
                {'error': '参与者不存在'},
                status=status.HTTP_404_NOT_FOUND
            )

        if participant.status != 'submitted':
            return Response(
                {'error': '该参与者未提交作品或已被审核'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 更新参与者状态
        participant.status = 'rejected'
        participant.reviewed_at = timezone.now()
        participant.review_comment = reject_reason
        participant.save()

        # 创建拒绝事件
        TaskTimelineEvent.objects.create(
            task=task,
            event_type='participant_rejected',
            user=request.user,
            description=f'参与者 {participant.participant.username} 的提交被审核拒绝：{reject_reason}',
            metadata={
                'rejected_by': request.user.username,
                'participant_id': str(participant.id),
                'participant_username': participant.participant.username,
                'reject_reason': reject_reason
            }
        )

        # 通知参与者
        Notification.create_notification(
            recipient=participant.participant,
            notification_type='task_board_rejected',
            actor=request.user,
            related_object_type='task',
            related_object_id=task.id,
            extra_data={
                'task_title': task.title,
                'rejector': request.user.username,
                'reject_reason': reject_reason or '未提供原因'
            }
        )

    else:
        # 单人任务：直接拒绝并失败任务
        try:
            participant = TaskParticipant.objects.get(task=task, participant=task.taker)
        except TaskParticipant.DoesNotExist:
            return Response(
                {'error': '找不到参与者记录'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 更新参与者状态
        participant.status = 'rejected'
        participant.reviewed_at = timezone.now()
        participant.review_comment = reject_reason
        participant.save()

        # 审核拒绝，标记任务为失败
        task.status = 'failed'
        if reject_reason:
            task.completion_proof += f"\n\n审核拒绝原因: {reject_reason}"

        # 销毁任务相关的所有钥匙道具（对于带锁任务）
        destroy_task_keys(task, reason="task_rejected", user=request.user, metadata={
            'rejection_reason': reject_reason,
            'rejected_by': request.user.username
        })

        task.save()

        # 创建任务审核拒绝通知
        Notification.create_notification(
            recipient=task.taker,
            notification_type='task_board_rejected',
            actor=request.user,
            related_object_type='task',
            related_object_id=task.id,
            extra_data={
                'task_title': task.title,
                'rejector': request.user.username,
                'reject_reason': reject_reason or '未提供原因'
            }
        )

    serializer = LockTaskSerializer(task)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_overtime(request, pk):
    """为进行中的带锁任务随机加时"""
    from .utils import add_overtime_to_task

    task = get_object_or_404(LockTask, pk=pk)

    # 使用工具函数处理加时逻辑
    result = add_overtime_to_task(task, request.user)

    if result['success']:
        # 返回加时信息
        response_data = {
            'message': result['message'],
            'overtime_minutes': result['overtime_minutes'],
            'new_end_time': result['new_end_time'].isoformat() if result['new_end_time'] else None,
            'is_frozen': result['is_frozen'],
            'frozen_end_time': result['frozen_end_time'].isoformat() if result['frozen_end_time'] else None,
            'difficulty': result['task'].difficulty
        }
        return Response(response_data, status=status.HTTP_200_OK)
    else:
        return Response(
            {'error': result['message']},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_keys(request):
    """获取我持有的钥匙"""
    keys = TaskKey.objects.filter(holder=request.user, status='active')
    serializer = TaskKeySerializer(keys, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_voting_results(request):
    """处理投票期结束的任务"""
    return _process_voting_results_internal()


def _process_voting_results_internal():
    """内部函数：处理投票期结束的任务（可被定时任务调用）"""
    now = timezone.now()

    # 找到投票期已结束的任务
    voting_ended_tasks = LockTask.objects.filter(
        status='voting',
        voting_end_time__lte=now
    )

    processed_tasks = []

    for task in voting_ended_tasks:
        # 统计投票结果
        total_votes = task.votes.count()
        agree_votes = task.votes.filter(agree=True).count()

        # 统一的投票验证逻辑，与complete_task保持一致
        required_threshold = task.vote_threshold or 1  # 如果没有设置门槛，默认需要1票
        required_ratio = task.vote_agreement_ratio or 0.5

        # 计算同意比例
        if total_votes == 0:
            agreement_ratio = 0
        else:
            agreement_ratio = agree_votes / total_votes

        # 投票通过需要满足两个条件：
        # 1. 投票数量达到阈值
        # 2. 同意比例达到要求
        vote_passed = (total_votes >= required_threshold and
                      agreement_ratio >= required_ratio)

        if vote_passed:
            # 投票通过 - 回到活跃状态，等待实际时间结束后才能完成
            task.status = 'active'
            # 不设置 completed_at，因为任务还未完成
            # 不销毁钥匙道具，因为任务还未完成
            # 不发放完成奖励，因为任务还未完成

            task.save()

            # 创建投票通过事件（但任务未完成）
            TaskTimelineEvent.objects.create(
                task=task,
                event_type='vote_passed',
                user=None,  # 系统事件
                description=f'投票通过：{agree_votes}/{total_votes}票同意（{agreement_ratio*100:.1f}%），满足要求（需要≥{required_threshold}票且≥{required_ratio*100:.0f}%同意），任务回到活跃状态，等待实际时间结束后才能完成',
                metadata={
                    'total_votes': total_votes,
                    'agree_votes': agree_votes,
                    'agreement_ratio': agreement_ratio,
                    'required_ratio': required_ratio,
                    'required_threshold': required_threshold,
                    'vote_passed': True,
                    'auto_completed': False,
                    'completion_type': 'voting_passed_waiting_time',
                    'waiting_for_time_end': True
                }
            )

            # 发送投票通过通知给任务创建者
            Notification.create_notification(
                recipient=task.user,
                notification_type='task_vote_passed',
                title='投票通过 - 等待时间结束',
                message=f'您的任务《{task.title}》投票通过（{agree_votes}/{total_votes}票同意），现在需要等待实际时间结束后才能完成任务！',
                related_object_type='task',
                related_object_id=task.id,
                extra_data={
                    'task_title': task.title,
                    'agree_votes': agree_votes,
                    'total_votes': total_votes,
                    'agreement_ratio': agreement_ratio,
                    'auto_completed': False,
                    'waiting_for_time_end': True,
                    'end_time': task.end_time.isoformat() if task.end_time else None
                },
                priority='high'
            )

            processed_tasks.append({
                'id': str(task.id),
                'title': task.title,
                'result': 'passed',
                'votes': f'{agree_votes}/{total_votes}',
                'ratio': f'{agreement_ratio*100:.1f}%',
                'status': 'waiting_for_time_end',
                'end_time': task.end_time.isoformat() if task.end_time else None
            })
        else:
            # 投票失败 - 根据难度等级加时，回到active状态
            penalty_minutes = task.get_vote_penalty_minutes()

            # 计算新的结束时间
            if task.end_time:
                task.end_time = task.end_time + timezone.timedelta(minutes=penalty_minutes)
            else:
                task.end_time = now + timezone.timedelta(minutes=penalty_minutes)

            task.status = 'active'
            task.vote_failed_penalty_minutes = penalty_minutes
            task.save()

            # 创建投票失败事件
            TaskTimelineEvent.objects.create(
                task=task,
                event_type='vote_failed',
                user=None,  # 系统事件
                time_change_minutes=penalty_minutes,
                new_end_time=task.end_time,
                description=f'投票失败：{agree_votes}/{total_votes}票同意（{agreement_ratio*100:.1f}%），未满足要求（需要≥{required_threshold}票且≥{required_ratio*100:.0f}%同意），按{task.difficulty}难度加时{penalty_minutes}分钟',
                metadata={
                    'total_votes': total_votes,
                    'agree_votes': agree_votes,
                    'agreement_ratio': agreement_ratio,
                    'required_ratio': required_ratio,
                    'required_threshold': required_threshold,
                    'vote_passed': False,
                    'penalty_minutes': penalty_minutes,
                    'difficulty': task.difficulty
                }
            )

            # 发送投票失败通知给任务创建者
            Notification.create_notification(
                recipient=task.user,
                notification_type='task_vote_failed',
                title='投票未通过 - 任务已加时',
                message=f'您的任务《{task.title}》投票未通过（{agree_votes}/{total_votes}票同意），需要≥{required_threshold}票且≥{required_ratio*100:.0f}%同意，已按{task.difficulty}难度加时{penalty_minutes}分钟',
                related_object_type='task',
                related_object_id=task.id,
                extra_data={
                    'task_title': task.title,
                    'agree_votes': agree_votes,
                    'total_votes': total_votes,
                    'agreement_ratio': agreement_ratio,
                    'penalty_minutes': penalty_minutes,
                    'difficulty': task.difficulty,
                    'new_end_time': task.end_time.isoformat()
                },
                priority='high'
            )

            processed_tasks.append({
                'id': str(task.id),
                'title': task.title,
                'result': 'failed',
                'votes': f'{agree_votes}/{total_votes}',
                'ratio': f'{agreement_ratio*100:.1f}%',
                'penalty_minutes': penalty_minutes
            })

    return Response({
        'message': f'Processed {len(processed_tasks)} voting results',
        'processed_tasks': processed_tasks
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_and_complete_expired_tasks(request):
    """检查过期的带锁任务（但不自动完成，只是为了兼容性）"""
    # 注意：带锁任务不应该自动完成，需要手动完成并满足所有条件
    # 这个函数保留是为了兼容性，但不执行自动完成
    now = timezone.now()
    expired_tasks = LockTask.objects.filter(
        task_type='lock',
        status='active',
        end_time__lte=now
    )

    expired_task_info = []
    for task in expired_tasks:
        # 不自动完成，只记录过期信息
        expired_task_info.append({
            'id': str(task.id),
            'title': task.title,
            'expired_at': task.end_time.isoformat() if task.end_time else None,
            'can_complete': True,  # 时间已到，可以手动完成
            'note': '时间已到，等待手动完成并满足所有条件'
        })

    # 同时处理投票结果
    # 直接调用内部函数，不需要传递request参数
    _process_voting_results_internal()

    return Response({
        'message': f'Found {len(expired_task_info)} expired lock task(s) awaiting manual completion',
        'expired_tasks': expired_task_info,
        'note': 'Lock tasks require manual completion with proper conditions (time + vote + key holder)'
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_task_timeline(request, pk):
    """获取任务时间线事件"""
    task = get_object_or_404(LockTask, pk=pk)

    # 获取任务的所有时间线事件，按时间倒序
    timeline_events = TaskTimelineEvent.objects.filter(task=task).order_by('-created_at')

    serializer = TaskTimelineEventSerializer(timeline_events, many=True)
    return Response({
        'task_id': str(task.id),
        'task_title': task.title,
        'timeline_events': serializer.data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_hourly_rewards(request):
    """处理带锁任务的每小时积分奖励"""
    now = timezone.now()

    # 找到所有活跃状态的带锁任务（排除冻结状态的任务）
    active_lock_tasks = LockTask.objects.filter(
        task_type='lock',
        status__in=['active', 'voting'],  # 活跃状态和投票期都算活跃
        is_frozen=False  # 排除冻结状态的任务
    )

    processed_rewards = []

    for task in active_lock_tasks:
        if not task.start_time:
            continue

        # 计算任务已运行的总时间（小时），需要扣除冻结时间
        elapsed_time = now - task.start_time

        # 如果任务有冻结时长，需要扣除
        if task.total_frozen_duration:
            elapsed_time -= task.total_frozen_duration

        elapsed_hours = int(max(0, elapsed_time.total_seconds()) // 3600)

        if elapsed_hours < 1:
            # 任务运行不满一小时，跳过
            continue

        # 检查上次奖励时间
        if task.last_hourly_reward_at:
            # 如果已经有奖励记录，检查是否需要新的奖励
            time_since_last_reward = now - task.last_hourly_reward_at
            hours_since_last_reward = int(time_since_last_reward.total_seconds() // 3600)

            if hours_since_last_reward < 1:
                # 距离上次奖励不足一小时，跳过
                continue

            # 计算需要补发的奖励小时数
            next_reward_hour = task.total_hourly_rewards + 1
        else:
            # 第一次发放奖励，从第1小时开始
            next_reward_hour = 1

        # 发放所有应该获得但还没有获得的小时奖励
        rewards_to_give = elapsed_hours - task.total_hourly_rewards

        for hour_num in range(next_reward_hour, next_reward_hour + rewards_to_give):
            # 给用户增加1积分（coins）
            task.user.coins += 1
            task.user.save()

            # 创建奖励记录
            hourly_reward = HourlyReward.objects.create(
                task=task,
                user=task.user,
                reward_amount=1,
                hour_count=hour_num
            )

            # 记录到时间线
            TaskTimelineEvent.objects.create(
                task=task,
                event_type='hourly_reward',
                user=None,  # 系统事件
                description=f'第{hour_num}小时奖励：{task.user.username}获得1积分',
                metadata={
                    'reward_amount': 1,
                    'hour_count': hour_num,
                    'total_coins': task.user.coins
                }
            )

            # 减少通知频率：只在特定小时数时发送批量通知，减轻视觉负担
            should_notify = (
                hour_num == 1 or  # 第一小时
                hour_num % 3 == 0 or  # 每3小时
                hour_num == rewards_to_give  # 最后一个奖励
            )

            if should_notify:
                # 计算当前批次的奖励总数
                batch_start = max(1, hour_num - 2) if hour_num % 3 == 0 else hour_num
                batch_rewards = min(3, hour_num - batch_start + 1) if hour_num % 3 == 0 else 1

                Notification.create_notification(
                    recipient=task.user,
                    notification_type='coins_earned_hourly_batch',
                    actor=None,  # 系统通知
                    related_object_type='task',
                    related_object_id=task.id,
                    extra_data={
                        'task_title': task.title,
                        'current_hour': hour_num,
                        'batch_rewards': batch_rewards,
                        'total_hourly_rewards': task.total_hourly_rewards + 1,
                        'notification_type': 'batched'  # 标记为批量通知
                    },
                    priority='very_low'  # 更低优先级，减少视觉干扰
                )

            processed_rewards.append({
                'task_id': str(task.id),
                'task_title': task.title,
                'user': task.user.username,
                'hour_count': hour_num,
                'reward_amount': 1
            })

        # 更新任务的奖励记录
        if rewards_to_give > 0:
            task.total_hourly_rewards += rewards_to_give
            task.last_hourly_reward_at = now
            task.save()

    return Response({
        'message': f'Processed {len(processed_rewards)} hourly rewards',
        'rewards': processed_rewards
    })


def _process_task_hourly_rewards(task):
    """为单个任务处理所有未发放的小时奖励（任务完成时调用）"""
    if task.task_type != 'lock' or not task.start_time:
        return 0

    now = timezone.now()

    # 计算任务已运行的总时间（小时），需要扣除冻结时间
    elapsed_time = now - task.start_time

    # 如果任务有冻结时长，需要扣除
    if task.total_frozen_duration:
        elapsed_time -= task.total_frozen_duration

    # 如果当前是冻结状态，还需要扣除当前冻结期间的时间
    if task.is_frozen and task.frozen_at:
        current_frozen_duration = now - task.frozen_at
        elapsed_time -= current_frozen_duration

    elapsed_hours = int(max(0, elapsed_time.total_seconds()) // 3600)

    if elapsed_hours < 1:
        return 0

    # 计算需要发放的奖励数量
    rewards_to_give = elapsed_hours - task.total_hourly_rewards

    if rewards_to_give <= 0:
        return 0

    # 发放奖励
    next_reward_hour = task.total_hourly_rewards + 1

    for hour_num in range(next_reward_hour, next_reward_hour + rewards_to_give):
        # 给用户增加1积分
        task.user.coins += 1
        task.user.save()

        # 创建奖励记录
        HourlyReward.objects.create(
            task=task,
            user=task.user,
            reward_amount=1,
            hour_count=hour_num
        )

        # 记录到时间线
        TaskTimelineEvent.objects.create(
            task=task,
            event_type='hourly_reward',
            user=None,  # 系统事件
            description=f'任务完成时补发第{hour_num}小时奖励：{task.user.username}获得1积分',
            metadata={
                'reward_amount': 1,
                'hour_count': hour_num,
                'total_coins': task.user.coins,
                'completion_catchup': True
            }
        )

    # 更新任务的奖励记录
    task.total_hourly_rewards += rewards_to_give
    task.last_hourly_reward_at = now
    task.save()

    return rewards_to_give


def _calculate_completion_bonus(task):
    """计算任务完成奖励（基于难度的一次性奖励）"""
    if task.task_type != 'lock' or not task.start_time or not task.completed_at:
        return 0

    # 计算任务实际运行时间
    elapsed_time = task.completed_at - task.start_time
    elapsed_hours = elapsed_time.total_seconds() / 3600

    # 只有运行超过1小时的任务才给完成奖励
    if elapsed_hours < 1:
        return 0

    # 根据难度给予完成奖励
    difficulty_bonus = {
        'easy': 1,
        'normal': 2,
        'hard': 3,
        'hell': 4
    }

    return difficulty_bonus.get(task.difficulty, 0)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def manual_time_adjustment(request, pk):
    """手动调整任务时间（加时或减时）- 需要钥匙持有者权限"""
    task = get_object_or_404(LockTask, pk=pk)

    # 检查任务类型
    if task.task_type != 'lock':
        return Response(
            {'error': '只能调整带锁任务的时间'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 检查任务状态
    if task.status not in ['active', 'voting']:
        return Response(
            {'error': '任务不在可调整时间的状态'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 检查用户是否持有对应的钥匙道具
    task_key_item = Item.objects.filter(
        item_type__name='key',
        owner=request.user,
        status='available',
        properties__task_id=str(task.id)
    ).first()

    if not task_key_item:
        return Response(
            {'error': '只有钥匙持有者可以手动调整时间'},
            status=status.HTTP_403_FORBIDDEN
        )

    # 获取调整类型和参数
    adjustment_type = request.data.get('type')  # 'increase' 或 'decrease'

    if adjustment_type not in ['increase', 'decrease']:
        return Response(
            {'error': '调整类型必须是 increase 或 decrease'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 检查用户积分是否足够（每次操作消耗10积分）
    cost = 10
    if request.user.coins < cost:
        return Response(
            {'error': f'积分不足，需要{cost}积分，当前{request.user.coins}积分'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 固定时间调整（±20分钟）
    adjustment_minutes = 20

    # 记录原始结束时间
    original_end_time = task.end_time

    # 处理冻结状态的时间调整
    if task.is_frozen:
        # 如果任务已冻结，调整冻结时保存的结束时间
        if not task.frozen_end_time or not task.frozen_at:
            return Response(
                {'error': '冻结任务缺少必要的时间信息，无法调整'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 计算冻结时的剩余时间
        frozen_remaining_minutes = (task.frozen_end_time - task.frozen_at).total_seconds() / 60

        if adjustment_type == 'decrease':
            # 如果冻结时已经没有剩余时间，返回错误
            if frozen_remaining_minutes <= 0:
                return Response(
                    {'error': '任务在冻结时已无剩余时间，无法进行减时操作'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 如果剩余时间不足20分钟，减到冻结时刻
            if frozen_remaining_minutes < 20:
                adjustment_minutes = -int(frozen_remaining_minutes)
                task.frozen_end_time = task.frozen_at
            else:
                adjustment_minutes = -20
                task.frozen_end_time = task.frozen_end_time + timezone.timedelta(minutes=adjustment_minutes)
        else:  # increase
            adjustment_minutes = 20
            # 对于冻结的任务，直接在frozen_end_time基础上加时
            task.frozen_end_time = task.frozen_end_time + timezone.timedelta(minutes=adjustment_minutes)

        # 记录新的结束时间用于响应（实际上是frozen_end_time）
        new_end_time = task.frozen_end_time

    else:
        # 正常情况下的时间调整逻辑（任务未冻结）
        if task.end_time:
            now = timezone.now()
            time_remaining_minutes = (task.end_time - now).total_seconds() / 60

            if adjustment_type == 'decrease':
                # 如果倒计时已结束，返回错误
                if time_remaining_minutes <= 0:
                    return Response(
                        {'error': '倒计时已结束，无法进行减时操作'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # 如果剩余时间不足20分钟，直接减到倒计时结束
                if time_remaining_minutes < 20:
                    adjustment_minutes = -int(time_remaining_minutes)
                    new_end_time = now
                else:
                    adjustment_minutes = -20
                    new_end_time = task.end_time + timezone.timedelta(minutes=adjustment_minutes)
            else:  # increase
                adjustment_minutes = 20
                # 如果倒计时已经结束，从现在开始加时；否则从原结束时间加时
                if time_remaining_minutes <= 0:
                    # 倒计时已结束，从现在开始延长
                    new_end_time = now + timezone.timedelta(minutes=adjustment_minutes)
                else:
                    # 倒计时未结束，从原结束时间延长
                    new_end_time = task.end_time + timezone.timedelta(minutes=adjustment_minutes)

            task.end_time = new_end_time
        else:
            return Response(
                {'error': '任务没有设置结束时间，无法调整'},
                status=status.HTTP_400_BAD_REQUEST
            )

    task.save()

    # 扣除用户积分
    request.user.coins -= cost
    request.user.save()

    # 创建时间线事件
    event_type = 'time_wheel_increase' if adjustment_type == 'increase' else 'time_wheel_decrease'
    frozen_status = '（冻结状态）' if task.is_frozen else ''
    description = f'钥匙持有者手动{"加时" if adjustment_type == "increase" else "减时"}{abs(adjustment_minutes)}分钟{frozen_status}（消耗{cost}积分）'

    TaskTimelineEvent.objects.create(
        task=task,
        event_type=event_type,
        user=request.user,
        time_change_minutes=adjustment_minutes,
        previous_end_time=original_end_time,
        new_end_time=new_end_time,
        description=description,
        metadata={
            'adjustment_type': adjustment_type,
            'adjustment_minutes': abs(adjustment_minutes),
            'cost': cost,
            'user_remaining_coins': request.user.coins,
            'manual_adjustment': True,
            'key_holder_action': True,
            'is_frozen': task.is_frozen,
            'frozen_end_time': task.frozen_end_time.isoformat() if task.frozen_end_time else None
        }
    )

    return Response({
        'message': f'成功{"加时" if adjustment_type == "increase" else "减时"}{abs(adjustment_minutes)}分钟{frozen_status}',
        'adjustment_minutes': adjustment_minutes,
        'new_end_time': new_end_time.isoformat(),
        'is_frozen': task.is_frozen,
        'frozen_end_time': task.frozen_end_time.isoformat() if task.frozen_end_time else None,
        'cost': cost,
        'remaining_coins': request.user.coins
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_time_display(request, pk):
    """切换时间显示/隐藏状态 - 需要钥匙持有者权限"""
    task = get_object_or_404(LockTask, pk=pk)

    # 检查任务类型
    if task.task_type != 'lock':
        return Response(
            {'error': '只能切换带锁任务的时间显示'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 检查任务状态
    if task.status not in ['active', 'voting']:
        return Response(
            {'error': '任务不在可切换时间显示的状态'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 检查用户是否持有对应的钥匙道具
    task_key_item = Item.objects.filter(
        item_type__name='key',
        owner=request.user,
        status='available',
        properties__task_id=str(task.id)
    ).first()

    if not task_key_item:
        return Response(
            {'error': '只有钥匙持有者可以切换时间显示'},
            status=status.HTTP_403_FORBIDDEN
        )

    # 检查用户积分是否足够（每次操作消耗50积分）
    cost = 50
    if request.user.coins < cost:
        return Response(
            {'error': f'积分不足，需要{cost}积分，当前{request.user.coins}积分'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 切换时间显示状态
    task.time_display_hidden = not task.time_display_hidden
    task.save()

    # 扣除用户积分
    request.user.coins -= cost
    request.user.save()

    # 创建时间线事件
    action = '隐藏' if task.time_display_hidden else '显示'
    description = f'钥匙持有者切换时间显示为{action}（消耗{cost}积分）'

    TaskTimelineEvent.objects.create(
        task=task,
        event_type='manual_adjustment',
        user=request.user,
        description=description,
        metadata={
            'action': 'toggle_time_display',
            'time_display_hidden': task.time_display_hidden,
            'cost': cost,
            'user_remaining_coins': request.user.coins,
            'key_holder_action': True
        }
    )

    return Response({
        'message': f'成功{action}时间显示',
        'time_display_hidden': task.time_display_hidden,
        'cost': cost,
        'remaining_coins': request.user.coins
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def freeze_task(request, pk):
    """冻结任务倒计时 - 需要钥匙持有者权限"""
    task = get_object_or_404(LockTask, pk=pk)

    # 检查任务类型
    if task.task_type != 'lock':
        return Response(
            {'error': '只能冻结带锁任务'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 检查任务状态
    if task.status != 'active':
        return Response(
            {'error': '只能冻结进行中的任务'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 检查任务是否已经冻结
    if task.is_frozen:
        return Response(
            {'error': '任务已经处于冻结状态'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 检查用户是否持有对应的钥匙道具
    task_key_item = Item.objects.filter(
        item_type__name='key',
        owner=request.user,
        status='available',
        properties__task_id=str(task.id)
    ).first()

    if not task_key_item:
        return Response(
            {'error': '只有钥匙持有者可以冻结任务'},
            status=status.HTTP_403_FORBIDDEN
        )

    # 检查用户积分是否足够（每次操作消耗25积分）
    cost = 25
    if request.user.coins < cost:
        return Response(
            {'error': f'积分不足，需要{cost}积分，当前{request.user.coins}积分'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 冻结任务
    task.is_frozen = True
    task.frozen_at = timezone.now()
    task.frozen_end_time = task.end_time  # 保存当前的结束时间
    task.save()

    # 扣除用户积分
    request.user.coins -= cost
    request.user.save()

    # 创建时间线事件
    description = f'钥匙持有者冻结任务（消耗{cost}积分）'

    TaskTimelineEvent.objects.create(
        task=task,
        event_type='task_frozen',
        user=request.user,
        description=description,
        metadata={
            'action': 'freeze',
            'cost': cost,
            'user_remaining_coins': request.user.coins,
            'key_holder_action': True,
            'frozen_at': task.frozen_at.isoformat(),
            'frozen_end_time': task.frozen_end_time.isoformat() if task.frozen_end_time else None
        }
    )

    return Response({
        'message': '成功冻结任务',
        'is_frozen': task.is_frozen,
        'frozen_at': task.frozen_at,
        'cost': cost,
        'remaining_coins': request.user.coins
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def unfreeze_task(request, pk):
    """解冻任务倒计时 - 需要钥匙持有者权限"""
    task = get_object_or_404(LockTask, pk=pk)

    # 检查任务类型
    if task.task_type != 'lock':
        return Response(
            {'error': '只能解冻带锁任务'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 检查任务状态
    if task.status != 'active':
        return Response(
            {'error': '只能解冻进行中的任务'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 检查任务是否处于冻结状态
    if not task.is_frozen:
        return Response(
            {'error': '任务未处于冻结状态'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 检查用户是否持有对应的钥匙道具
    task_key_item = Item.objects.filter(
        item_type__name='key',
        owner=request.user,
        status='available',
        properties__task_id=str(task.id)
    ).first()

    if not task_key_item:
        return Response(
            {'error': '只有钥匙持有者可以解冻任务'},
            status=status.HTTP_403_FORBIDDEN
        )

    # 检查用户积分是否足够（每次操作消耗25积分）
    cost = 25
    if request.user.coins < cost:
        return Response(
            {'error': f'积分不足，需要{cost}积分，当前{request.user.coins}积分'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 计算剩余时间并解冻任务
    now = timezone.now()
    if task.frozen_end_time and task.frozen_at:
        # 计算冻结时剩余的时间
        remaining_time = task.frozen_end_time - task.frozen_at
        # 设置新的结束时间
        task.end_time = now + remaining_time

        # 更新总冻结时长
        frozen_duration = now - task.frozen_at
        task.total_frozen_duration += frozen_duration

    task.is_frozen = False
    task.frozen_at = None
    task.frozen_end_time = None
    task.save()

    # 扣除用户积分
    request.user.coins -= cost
    request.user.save()

    # 创建时间线事件
    description = f'钥匙持有者解冻任务（消耗{cost}积分）'

    TaskTimelineEvent.objects.create(
        task=task,
        event_type='task_unfrozen',
        user=request.user,
        description=description,
        metadata={
            'action': 'unfreeze',
            'cost': cost,
            'user_remaining_coins': request.user.coins,
            'key_holder_action': True,
            'new_end_time': task.end_time.isoformat() if task.end_time else None
        }
    )

    return Response({
        'message': '成功解冻任务',
        'is_frozen': task.is_frozen,
        'end_time': task.end_time,
        'cost': cost,
        'remaining_coins': request.user.coins
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_task_counts(request):
    """获取任务数量统计（用于筛选标签显示正确的数字）"""
    try:
        # 在获取统计时，自动处理过期的投票
        try:
            _process_voting_results_internal()
        except Exception as e:
            print(f"Warning: Failed to process voting results: {e}")

        # 基础查询集
        base_queryset = LockTask.objects.all()

        # 按任务类型分组统计
        lock_tasks = base_queryset.filter(task_type='lock')
        board_tasks = base_queryset.filter(task_type='board')

        # 计算可以加时的任务数量
        can_overtime_queryset = lock_tasks.filter(
            task_type='lock',
            status='active'
        ).exclude(user=request.user)

        # 排除两小时内已经对同一发布者加过时的任务
        from django.utils import timezone
        from datetime import timedelta
        two_hours_ago = timezone.now() - timedelta(hours=2)
        recent_overtime_publishers = OvertimeAction.objects.filter(
            user=request.user,
            created_at__gte=two_hours_ago
        ).values_list('task_publisher', flat=True).distinct()

        if recent_overtime_publishers:
            can_overtime_queryset = can_overtime_queryset.exclude(user__in=recent_overtime_publishers)

        # 带锁任务统计
        lock_counts = {
            'all': lock_tasks.count(),
            'active': lock_tasks.filter(status='active').count(),
            'voting': lock_tasks.filter(status='voting').count(),
            'completed': lock_tasks.filter(status='completed').count(),
            'my_tasks': lock_tasks.filter(user=request.user).count(),
            'can_overtime': can_overtime_queryset.count(),
        }

        # 任务板统计
        board_counts = {
            'all': board_tasks.count(),
            'open': board_tasks.filter(status='open').count(),
            'taken': board_tasks.filter(status='taken').count(),
            'submitted': board_tasks.filter(status='submitted').count(),
            'completed': board_tasks.filter(status='completed').count(),
            'my_published': board_tasks.filter(user=request.user).count(),
            'my_taken': board_tasks.filter(
                Q(taker=request.user) |  # 单人任务：我是taker
                Q(participants__participant=request.user)  # 多人任务：我是参与者
            ).distinct().count(),
        }

        return Response({
            'lock_tasks': lock_counts,
            'board_tasks': board_counts
        })

    except Exception as e:
        return Response(
            {'error': f'获取任务统计失败: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def end_board_task(request, pk):
    """结束任务板任务 - 支持单人和多人任务的不同结算逻辑"""
    task = get_object_or_404(LockTask, pk=pk)

    # 检查是否是任务板
    if task.task_type != 'board':
        return Response(
            {'error': '只能结束任务板任务'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 检查权限：只有发布者可以结束任务
    if task.user != request.user:
        return Response(
            {'error': '只有任务发布者可以结束任务'},
            status=status.HTTP_403_FORBIDDEN
        )

    # 获取结束原因
    end_reason = request.data.get('end_reason', '发布者手动结束任务')

    # 判断是单人还是多人任务
    is_multi_person = task.max_participants and task.max_participants > 1

    if not is_multi_person:
        # 单人任务结束逻辑
        return _end_single_person_task(task, end_reason, request.user)
    else:
        # 多人任务结束逻辑
        return _end_multi_person_task(task, end_reason, request.user)


def _end_single_person_task(task, end_reason, publisher):
    """结束单人任务"""
    # 单人任务只能在未提交状态结束，直接标记为失败
    if task.status not in ['open', 'taken']:
        return Response(
            {'error': '单人任务只能在开放或已接取状态下结束'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 标记为失败
    task.status = 'failed'
    task.completed_at = timezone.now()
    task.save()

    # 返还奖励给发布者
    if task.reward:
        _refund_task_reward(task, publisher, end_reason)

    # 创建时间线事件
    TaskTimelineEvent.objects.create(
        task=task,
        event_type='task_ended',
        user=publisher,
        description=f'任务被发布者结束：{end_reason}',
        metadata={'end_reason': end_reason, 'refunded_amount': task.reward or 0}
    )

    # 通知接取者（如果有）
    if task.taker:
        Notification.create_notification(
            recipient=task.taker,
            notification_type='task_board_ended',
            actor=publisher,
            related_object_type='task',
            related_object_id=task.id,
            extra_data={
                'task_title': task.title,
                'end_reason': end_reason,
                'task_status': 'failed'
            }
        )

    serializer = LockTaskSerializer(task)
    return Response(serializer.data)


def _end_multi_person_task(task, end_reason, publisher):
    """结束多人任务"""
    # 多人任务可以在任何状态下结束
    participants = TaskParticipant.objects.filter(task=task)
    submitted_participants = participants.filter(status='submitted')
    approved_participants = participants.filter(status='approved')

    if approved_participants.count() == 0:
        # 没有审核通过的参与者，标记为失败
        task.status = 'failed'
        task.completed_at = timezone.now()
        task.save()

        # 返还奖励给发布者
        if task.reward:
            if submitted_participants.count() == 0:
                _refund_task_reward(task, publisher, f'{end_reason}（无人提交）')
                result_message = '任务失败：无人提交'
            else:
                _refund_task_reward(task, publisher, f'{end_reason}（无人通过审核）')
                result_message = f'任务失败：有 {submitted_participants.count()} 人提交但无人通过审核'
        else:
            if submitted_participants.count() == 0:
                result_message = '任务失败：无人提交'
            else:
                result_message = f'任务失败：有 {submitted_participants.count()} 人提交但无人通过审核'
    else:
        # 有审核通过的参与者，根据审核情况结算
        total_participants = participants.count()

        # 标记任务为完成
        task.status = 'completed'
        task.completed_at = timezone.now()
        task.save()

        # 分发奖励给通过审核的参与者（向上取整）
        if task.reward and approved_participants.count() > 0:
            import math
            reward_per_person = math.ceil(task.reward / approved_participants.count())

            for participant in approved_participants:
                # 给参与者发放奖励
                from users.models import User
                participant.participant.coins += reward_per_person
                participant.participant.save()

                # 创建通知
                Notification.create_notification(
                    recipient=participant.participant,
                    notification_type='task_board_reward',
                    actor=publisher,
                    related_object_type='task',
                    related_object_id=task.id,
                    extra_data={
                        'task_title': task.title,
                        'reward_amount': reward_per_person
                    }
                )

        result_message = f'任务完成：{approved_participants.count()}/{total_participants} 人通过审核，积分已分配'

    # 创建时间线事件
    TaskTimelineEvent.objects.create(
        task=task,
        event_type='task_ended',
        user=publisher,
        description=f'任务被发布者结束：{end_reason}。{result_message}',
        metadata={
            'end_reason': end_reason,
            'total_participants': participants.count(),
            'submitted_participants': submitted_participants.count(),
            'approved_participants': participants.filter(status='approved').count(),
            'final_status': task.status
        }
    )

    # 通知所有参与者
    for participant in participants:
        Notification.create_notification(
            recipient=participant.participant,
            notification_type='task_board_ended',
            actor=publisher,
            related_object_type='task',
            related_object_id=task.id,
            extra_data={
                'task_title': task.title,
                'end_reason': end_reason,
                'task_status': task.status,
                'participant_status': participant.status
            }
        )

    serializer = LockTaskSerializer(task)
    return Response(serializer.data)


def _refund_task_reward(task, publisher, reason):
    """返还任务奖励给发布者"""
    if not task.reward:
        return

    # 返还coins给发布者
    publisher.coins += task.reward
    publisher.save()

    # 创建通知
    Notification.create_notification(
        recipient=publisher,
        notification_type='task_board_refund',
        related_object_type='task',
        related_object_id=task.id,
        extra_data={
            'task_title': task.title,
            'refund_amount': task.reward,
            'reason': reason
        }
    )

    logger.info(f"Refunded {task.reward} coins to {publisher.username} for task {task.id}: {reason}")


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def auto_settle_expired_board_tasks(request):
    """自动结算过期的任务板任务"""
    try:
        current_time = timezone.now()

        # 查找所有已过期但未结算的任务板任务
        expired_tasks = LockTask.objects.filter(
            task_type='board',
            deadline__isnull=False,
            deadline__lt=current_time,
            status__in=['taken', 'submitted']  # 只结算进行中或已提交的任务
        )

        results = []

        for task in expired_tasks:
            try:
                result = _auto_settle_expired_task(task)
                results.append(result)
                logger.info(f"Auto-settled expired task {task.id}: {result['action']}")
            except Exception as e:
                error_msg = f"Failed to auto-settle task {task.id}: {str(e)}"
                logger.error(error_msg)
                results.append({
                    'task_id': str(task.id),
                    'action': 'error',
                    'error': str(e)
                })

        return Response({
            'settled_count': len([r for r in results if r.get('action') != 'error']),
            'error_count': len([r for r in results if r.get('action') == 'error']),
            'results': results
        })

    except Exception as e:
        logger.error(f"Error in auto_settle_expired_board_tasks: {str(e)}")
        return Response(
            {'error': f'自动结算失败: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def _auto_settle_expired_task(task):
    """自动结算单个过期任务"""
    # 检查是否为多人任务
    is_multi_person = task.max_participants and task.max_participants > 1

    if is_multi_person:
        return _auto_settle_multi_person_expired_task(task)
    else:
        return _auto_settle_single_person_expired_task(task)


def _auto_settle_single_person_expired_task(task):
    """自动结算单人过期任务"""
    current_time = timezone.now()

    if task.status == 'submitted':
        # 已提交证明但未审核，自动通过
        task.status = 'completed'
        task.completed_at = current_time
        task.save()

        # 给接取者发放奖励
        if task.taker and task.reward:
            task.taker.coins += task.reward
            task.taker.save()

            # 通知接取者
            Notification.create_notification(
                recipient=task.taker,
                notification_type='task_board_approved',
                related_object_type='task',
                related_object_id=task.id,
                extra_data={
                    'task_title': task.title,
                    'reward_amount': task.reward,
                    'auto_approved': True,
                    'reason': 'deadline_expired'
                }
            )

        # 通知发布者
        Notification.create_notification(
            recipient=task.user,
            notification_type='task_board_ended',
            related_object_type='task',
            related_object_id=task.id,
            extra_data={
                'task_title': task.title,
                'auto_settled': True,
                'final_status': 'completed',
                'taker_username': task.taker.username if task.taker else None
            }
        )

        # 记录时间线事件
        TaskTimelineEvent.objects.create(
            task=task,
            event_type='task_completed',
            description=f'任务已到期，已提交证明自动审核通过',
            metadata={
                'auto_settled': True,
                'deadline_expired': True,
                'reward_amount': task.reward
            }
        )

        return {
            'task_id': str(task.id),
            'action': 'auto_approved',
            'reward_given': task.reward or 0,
            'recipient': task.taker.username if task.taker else None
        }

    elif task.status == 'taken':
        # 已接取但未提交证明，任务失败
        task.status = 'failed'
        task.completed_at = current_time
        task.save()

        # 退还奖励给发布者
        if task.reward:
            task.user.coins += task.reward
            task.user.save()

            # 通知发布者
            Notification.create_notification(
                recipient=task.user,
                notification_type='task_board_ended',
                related_object_type='task',
                related_object_id=task.id,
                extra_data={
                    'task_title': task.title,
                    'auto_settled': True,
                    'final_status': 'failed',
                    'refund_amount': task.reward,
                    'reason': '无人提交完成证明'
                }
            )

        # 通知接取者
        if task.taker:
            Notification.create_notification(
                recipient=task.taker,
                notification_type='task_board_ended',
                related_object_type='task',
                related_object_id=task.id,
                extra_data={
                    'task_title': task.title,
                    'auto_settled': True,
                    'final_status': 'failed',
                    'reason': '未在截止时间前提交完成证明'
                }
            )

        # 记录时间线事件
        TaskTimelineEvent.objects.create(
            task=task,
            event_type='task_failed',
            description=f'任务已到期，无人提交完成证明，自动标记为失败',
            metadata={
                'auto_settled': True,
                'deadline_expired': True,
                'refund_amount': task.reward
            }
        )

        return {
            'task_id': str(task.id),
            'action': 'failed_no_submission',
            'refund_amount': task.reward or 0
        }

    return {
        'task_id': str(task.id),
        'action': 'no_action_needed',
        'status': task.status
    }


def _auto_settle_multi_person_expired_task(task):
    """自动结算多人过期任务"""
    import math
    current_time = timezone.now()

    # 获取所有参与者
    participants = task.participants.all()
    approved_participants = participants.filter(status='approved')
    submitted_participants = participants.filter(status='submitted')

    # 自动审核通过所有已提交的参与者
    auto_approved_count = 0
    for participant in submitted_participants:
        participant.status = 'approved'
        participant.reviewed_at = current_time
        participant.review_comment = '任务到期自动审核通过'
        participant.save()
        auto_approved_count += 1

    # 重新获取已通过审核的参与者（包括新自动通过的）
    all_approved_participants = participants.filter(status='approved')

    if all_approved_participants.count() > 0:
        # 有通过审核的参与者，任务完成
        task.status = 'completed'
        task.completed_at = current_time

        # 分配奖励
        if task.reward:
            reward_per_person = math.ceil(task.reward / all_approved_participants.count())

            for participant in all_approved_participants:
                participant.reward_amount = reward_per_person
                participant.save()

                # 给参与者分配积分
                participant.participant.coins += reward_per_person
                participant.participant.save()

                # 通知参与者
                Notification.create_notification(
                    recipient=participant.participant,
                    notification_type='task_board_approved',
                    related_object_type='task',
                    related_object_id=task.id,
                    extra_data={
                        'task_title': task.title,
                        'reward_amount': reward_per_person,
                        'auto_approved': participant.status == 'approved' and participant.review_comment == '任务到期自动审核通过'
                    }
                )

        action_msg = f'completed_with_{all_approved_participants.count()}_participants'

        # 记录时间线事件
        TaskTimelineEvent.objects.create(
            task=task,
            event_type='task_completed',
            description=f'任务已到期，{auto_approved_count}位参与者自动审核通过，任务完成',
            metadata={
                'auto_settled': True,
                'deadline_expired': True,
                'auto_approved_count': auto_approved_count,
                'total_approved': all_approved_participants.count(),
                'reward_distributed': task.reward or 0
            }
        )

    else:
        # 无人通过审核，任务失败
        task.status = 'failed'
        task.completed_at = current_time

        # 退还奖励给发布者
        if task.reward:
            task.user.coins += task.reward
            task.user.save()

        action_msg = 'failed_no_approved_participants'

        # 记录时间线事件
        TaskTimelineEvent.objects.create(
            task=task,
            event_type='task_failed',
            description=f'任务已到期，无人通过审核，自动标记为失败',
            metadata={
                'auto_settled': True,
                'deadline_expired': True,
                'refund_amount': task.reward
            }
        )

    task.save()

    # 通知发布者
    Notification.create_notification(
        recipient=task.user,
        notification_type='task_board_ended',
        related_object_type='task',
        related_object_id=task.id,
        extra_data={
            'task_title': task.title,
            'auto_settled': True,
            'final_status': task.status,
            'approved_count': all_approved_participants.count(),
            'total_participants': participants.count()
        }
    )

    # 通知所有未通过审核的参与者
    for participant in participants.exclude(status='approved'):
        Notification.create_notification(
            recipient=participant.participant,
            notification_type='task_board_ended',
            related_object_type='task',
            related_object_id=task.id,
            extra_data={
                'task_title': task.title,
                'auto_settled': True,
                'final_status': task.status,
                'participant_status': participant.status
            }
        )

    return {
        'task_id': str(task.id),
        'action': action_msg,
        'auto_approved_count': auto_approved_count,
        'total_approved': all_approved_participants.count(),
        'reward_distributed': task.reward if task.status == 'completed' else 0,
        'refund_amount': task.reward if task.status == 'failed' else 0
    }


# ============================================================================
# 置顶惩罚系统 API - Pinning Penalty System
# ============================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def pin_task_owner(request, pk):
    """钥匙持有者置顶任务创建者"""
    task = get_object_or_404(LockTask, pk=pk)

    # 检查任务类型
    if task.task_type != 'lock':
        return Response(
            {'error': '只能置顶带锁任务的创建者'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 检查任务状态
    if task.status not in ['active', 'voting']:
        return Response(
            {'error': '任务不在可置顶状态'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 获取置顶参数
    coins_spent = request.data.get('coins_spent', 60)
    duration_minutes = request.data.get('duration_minutes', 30)

    # 使用队列管理器处理置顶逻辑
    result = PinningQueueManager.add_to_queue(
        task=task,
        key_holder=request.user,
        coins_spent=coins_spent,
        duration_minutes=duration_minutes
    )

    if result['success']:
        # 发送通知给被置顶的用户
        Notification.create_notification(
            recipient=task.user,
            notification_type='user_pinned',
            actor=request.user,
            related_object_type='task',
            related_object_id=task.id,
            extra_data={
                'task_title': task.title,
                'key_holder': request.user.username,
                'coins_spent': coins_spent,
                'duration_minutes': duration_minutes,
                'position': result.get('position')
            },
            priority='high'
        )

        return Response({
            'message': result['message'],
            'position': result.get('position'),
            'queue_status': result.get('queue_status'),
            'coins_remaining': request.user.coins
        }, status=status.HTTP_200_OK)
    else:
        return Response(
            {'error': result['message']},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_pinning_status(request):
    """获取当前置顶状态和队列信息"""
    try:
        # 先更新队列状态
        PinningQueueManager.update_queue()

        # 获取队列状态
        queue_status = PinningQueueManager.get_queue_status()

        return Response(queue_status, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Failed to get pinning status: {e}")
        return Response(
            {'error': '获取置顶状态失败'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def unpin_task_owner(request, pk):
    """取消置顶任务创建者（仅管理员或自动过期）"""
    task = get_object_or_404(LockTask, pk=pk)

    # 检查权限：只有管理员可以手动取消置顶
    if not (request.user.is_staff or request.user.is_superuser):
        return Response(
            {'error': '只有管理员可以手动取消置顶'},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        # 查找活跃的置顶记录
        pinned_record = PinnedUser.objects.filter(
            task=task,
            pinned_user=task.user,
            is_active=True
        ).first()

        if not pinned_record:
            return Response(
                {'error': '该用户当前未被置顶'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 取消置顶
        pinned_record.is_active = False
        pinned_record.position = None
        pinned_record.save()

        # 更新队列状态
        queue_result = PinningQueueManager.update_queue()

        # 创建时间线事件
        TaskTimelineEvent.objects.create(
            task=task,
            event_type='user_unpinned',
            user=request.user,
            description=f'{request.user.username} 手动取消了 {task.user.username} 的置顶',
            metadata={
                'manual_unpin': True,
                'admin_action': True,
                'pinned_user_id': str(task.user.id),
                'admin_id': str(request.user.id)
            }
        )

        # 发送通知
        Notification.create_notification(
            recipient=task.user,
            notification_type='user_unpinned',
            actor=request.user,
            related_object_type='task',
            related_object_id=task.id,
            extra_data={
                'task_title': task.title,
                'admin': request.user.username,
                'manual_unpin': True
            }
        )

        return Response({
            'message': f'已取消 {task.user.username} 的置顶',
            'queue_status': queue_result
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Failed to unpin user: {e}")
        return Response(
            {'error': '取消置顶失败'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_pinned_tasks_for_carousel(request):
    """获取置顶任务信息用于社区轮播组件"""
    try:
        # 获取活跃的置顶用户
        active_pins = PinningQueueManager.get_active_pinned_users()

        carousel_data = []
        for pin in active_pins:
            task = pin.task
            pinned_user = pin.pinned_user

            # 计算剩余时间
            now = timezone.now()
            time_remaining = max(0, (pin.expires_at - now).total_seconds())

            carousel_data.append({
                'id': str(pin.id),
                'position': pin.position,
                'task': {
                    'id': str(task.id),
                    'title': task.title,
                    'status': task.status,
                    'difficulty': task.difficulty,
                    'task_type': task.task_type
                },
                'pinned_user': {
                    'id': str(pinned_user.id),
                    'username': pinned_user.username
                },
                'key_holder': {
                    'id': str(pin.key_holder.id),
                    'username': pin.key_holder.username
                },
                'time_remaining': time_remaining,
                'expires_at': pin.expires_at.isoformat(),
                'created_at': pin.created_at.isoformat()
            })

        return Response({
            'pinned_tasks': carousel_data,
            'count': len(carousel_data)
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Failed to get pinned tasks for carousel: {e}")
        return Response(
            {'error': '获取置顶任务失败'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )