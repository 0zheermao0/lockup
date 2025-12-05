from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
import random

from .models import LockTask, TaskKey, TaskVote, OvertimeAction, TaskTimelineEvent, HourlyReward
from store.models import ItemType, UserInventory, Item
from users.models import Notification
from .serializers import (
    LockTaskSerializer, LockTaskCreateSerializer,
    TaskKeySerializer, TaskVoteSerializer, TaskVoteCreateSerializer,
    TaskTimelineEventSerializer
)


class LockTaskListCreateView(generics.ListCreateAPIView):
    """任务列表和创建"""
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return LockTaskCreateSerializer
        return LockTaskSerializer

    def get_queryset(self):
        queryset = LockTask.objects.all()

        # 按任务类型筛选
        task_type = self.request.query_params.get('task_type')
        if task_type:
            queryset = queryset.filter(task_type=task_type)

        # 按状态筛选
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)

        # 按用户筛选（我的任务）
        my_tasks = self.request.query_params.get('my_tasks')
        if my_tasks == 'true':
            queryset = queryset.filter(user=self.request.user)

        # 按接取者筛选（我接取的任务）
        my_taken = self.request.query_params.get('my_taken')
        if my_taken == 'true':
            queryset = queryset.filter(taker=self.request.user)

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

        task = serializer.save()

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

            task.save()


class LockTaskDetailView(generics.RetrieveUpdateDestroyAPIView):
    """任务详情、更新和删除"""
    queryset = LockTask.objects.all()
    serializer_class = LockTaskSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """设置不同操作的权限"""
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            # 只有任务创建者或超级用户可以编辑和删除
            return [IsAuthenticated(), IsOwnerOrAdmin()]
        return [IsAuthenticated()]


class IsOwnerOrAdmin(permissions.BasePermission):
    """只有拥有者或管理员可以操作"""

    def has_object_permission(self, request, view, obj):
        return obj.user == request.user or request.user.is_superuser


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
        # 条件1: 倒计时必须结束
        if task.end_time and timezone.now() < task.end_time:
            return Response(
                {'error': '带锁任务必须等待倒计时结束后才能完成'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 条件2: 投票解锁类型的任务现在会自动完成，不允许手动完成
        if task.unlock_type == 'vote':
            return Response(
                {'error': '投票解锁任务会在投票通过后自动完成，无需手动操作'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 条件3: 必须是任务创建者（钥匙持有者）
        if task.user != request.user:
            return Response(
                {'error': '只有任务创建者（钥匙持有者）可以完成带锁任务'},
                status=status.HTTP_403_FORBIDDEN
            )

        # 条件4: 检查用户是否持有对应的钥匙道具
        task_key_item = Item.objects.filter(
            item_type__name='key',
            owner=request.user,
            status='available',
            properties__task_id=str(task.id)
        ).first()

        if not task_key_item:
            return Response(
                {'error': '您没有持有该任务的钥匙道具，无法完成任务'},
                status=status.HTTP_403_FORBIDDEN
            )

        # 销毁钥匙道具
        task_key_item.status = 'used'
        task_key_item.used_at = timezone.now()
        task_key_item.inventory = None  # 从背包中移除
        task_key_item.save()

    # 更新任务状态
    task.status = 'completed'
    task.completed_at = timezone.now()
    task.save()

    # 创建任务完成事件
    completion_metadata = {
        'completed_by': 'manual',
        'completion_time': task.completed_at.isoformat(),
        'key_destroyed': task.task_type == 'lock'
    }

    if task.task_type == 'lock':
        # 记录完成时的所有条件状态
        completion_metadata.update({
            'time_expired': task.end_time and timezone.now() >= task.end_time,
            'vote_required': task.unlock_type == 'vote',
            'key_holder_completed': True
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

    TaskTimelineEvent.objects.create(
        task=task,
        event_type='task_completed',
        user=request.user,
        description=f'任务手动完成 - 满足所有完成条件{"，钥匙道具已销毁" if task.task_type == "lock" else ""}',
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

    # 创建任务停止事件
    TaskTimelineEvent.objects.create(
        task=task,
        event_type='task_stopped',
        user=request.user,
        description=f'任务手动停止',
        metadata={
            'stopped_by': 'manual',
            'stop_time': task.end_time.isoformat()
        }
    )

    serializer = LockTaskSerializer(task)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def take_board_task(request, pk):
    """接取任务板任务"""
    task = get_object_or_404(LockTask, pk=pk)

    # 检查是否是任务板
    if task.task_type != 'board':
        return Response(
            {'error': '只能接取任务板任务'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 检查任务状态
    if task.status != 'open':
        return Response(
            {'error': '任务不是开放状态'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 检查是否是自己发布的任务
    if task.user == request.user:
        return Response(
            {'error': '不能接取自己发布的任务'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 更新任务状态
    task.status = 'taken'
    task.taker = request.user
    task.taken_at = timezone.now()

    # 设置任务截止时间（基于max_duration）
    if task.max_duration:
        task.deadline = task.taken_at + timezone.timedelta(hours=task.max_duration)

    task.save()

    # 创建任务接取通知
    Notification.create_notification(
        recipient=task.user,
        notification_type='task_board_taken',
        actor=request.user,
        related_object_type='task',
        related_object_id=task.id,
        extra_data={
            'task_title': task.title,
            'taker': request.user.username,
            'deadline': task.deadline.isoformat() if task.deadline else None
        }
    )

    serializer = LockTaskSerializer(task)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_board_task(request, pk):
    """提交任务板任务完成证明"""
    task = get_object_or_404(LockTask, pk=pk)

    # 检查权限
    if task.taker != request.user:
        return Response(
            {'error': '只有接取者可以提交任务'},
            status=status.HTTP_403_FORBIDDEN
        )

    # 检查任务状态
    if task.status != 'taken':
        return Response(
            {'error': '任务不是已接取状态'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 获取完成证明
    completion_proof = request.data.get('completion_proof', '')
    if not completion_proof:
        return Response(
            {'error': '请提供完成证明'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 更新任务状态为已提交，等待发布者审核
    task.status = 'submitted'
    task.completion_proof = completion_proof
    # 注意：不设置completed_at，因为任务还未正式完成
    task.save()

    # 创建任务提交通知
    Notification.create_notification(
        recipient=task.user,
        notification_type='task_board_submitted',
        actor=request.user,
        related_object_type='task',
        related_object_id=task.id,
        extra_data={
            'task_title': task.title,
            'submitter': request.user.username,
            'completion_proof_preview': completion_proof[:100] + '...' if len(completion_proof) > 100 else completion_proof
        }
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
    """发布者审核通过任务板任务"""
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

    # 审核通过，标记任务为已完成
    task.status = 'completed'
    task.completed_at = timezone.now()

    # 处理奖励积分转移
    if task.reward and task.reward > 0 and task.taker:
        # 给接取者奖励积分
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
    """发布者审核拒绝任务板任务"""
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

    # 获取拒绝原因
    reject_reason = request.data.get('reject_reason', '')

    # 审核拒绝，标记任务为失败
    task.status = 'failed'
    # 可以在completion_proof中添加拒绝原因
    if reject_reason:
        task.completion_proof += f"\n\n审核拒绝原因: {reject_reason}"
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
    task = get_object_or_404(LockTask, pk=pk)

    # 检查是否是带锁任务
    if task.task_type != 'lock':
        return Response(
            {'error': '只能为带锁任务加时'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 检查任务状态
    if task.status != 'active':
        return Response(
            {'error': '只能为进行中的任务加时'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 检查是否是自己的任务（不能为自己的任务加时）
    if task.user == request.user:
        return Response(
            {'error': '不能为自己的任务加时'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 检查一小时内是否已经为同一个发布者的任务加过时
    one_hour_ago = timezone.now() - timedelta(hours=1)
    recent_overtime = OvertimeAction.objects.filter(
        user=request.user,
        task_publisher=task.user,
        created_at__gte=one_hour_ago
    ).exists()

    if recent_overtime:
        return Response(
            {'error': '一小时内只能对同一个发布者的带锁任务随机加时一次'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 检查任务是否已经结束
    if task.end_time and timezone.now() >= task.end_time:
        return Response(
            {'error': '任务已经结束，无法加时'},
            status=status.HTTP_400_BAD_REQUEST
        )

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
    overtime_minutes = random.randint(min_overtime, max_overtime)

    # 记录时间变化前的状态
    previous_end_time = task.end_time

    # 更新任务结束时间
    if task.end_time:
        task.end_time = task.end_time + timezone.timedelta(minutes=overtime_minutes)
    else:
        # 如果没有结束时间，从现在开始加时
        task.end_time = timezone.now() + timezone.timedelta(minutes=overtime_minutes)

    task.save()

    # 记录加时操作
    OvertimeAction.objects.create(
        task=task,
        user=request.user,
        task_publisher=task.user,
        overtime_minutes=overtime_minutes
    )

    # 创建时间线事件
    TaskTimelineEvent.objects.create(
        task=task,
        event_type='overtime_added',
        user=request.user,
        time_change_minutes=overtime_minutes,
        previous_end_time=previous_end_time,
        new_end_time=task.end_time,
        description=f'{request.user.username} 为任务随机加时 {overtime_minutes} 分钟',
        metadata={
            'difficulty': task.difficulty,
            'overtime_range': f'{min_overtime}-{max_overtime} 分钟',
            'base_overtime': base_overtime
        }
    )

    # 创建加时通知
    Notification.create_notification(
        recipient=task.user,
        notification_type='task_overtime_added',
        actor=request.user,
        related_object_type='task',
        related_object_id=task.id,
        extra_data={
            'overtime_minutes': overtime_minutes,
            'difficulty': task.difficulty,
            'new_end_time': task.end_time.isoformat() if task.end_time else None
        }
    )

    # 返回加时信息
    response_data = {
        'message': f'成功为任务加时 {overtime_minutes} 分钟',
        'overtime_minutes': overtime_minutes,
        'new_end_time': task.end_time.isoformat() if task.end_time else None,
        'difficulty': task.difficulty
    }

    return Response(response_data, status=status.HTTP_200_OK)


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
        required_threshold = task.vote_threshold or 0
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
            # 投票通过 - 自动完成任务
            task.status = 'completed'
            task.completed_at = timezone.now()

            # 检查并销毁钥匙道具（如果存在）
            from store.models import Item
            task_key_item = Item.objects.filter(
                item_type__name='key',
                owner=task.user,
                status='available',
                properties__task_id=str(task.id)
            ).first()

            if task_key_item:
                # 销毁钥匙道具
                task_key_item.status = 'used'
                task_key_item.used_at = timezone.now()
                task_key_item.inventory = None  # 从背包中移除
                task_key_item.save()

            task.save()

            # 创建投票通过并自动完成事件
            TaskTimelineEvent.objects.create(
                task=task,
                event_type='task_completed',
                user=None,  # 系统事件
                description=f'投票通过并自动完成：{agree_votes}/{total_votes}票同意（{agreement_ratio*100:.1f}%），满足要求（需要≥{required_threshold}票且≥{required_ratio*100:.0f}%同意），任务已自动完成',
                metadata={
                    'total_votes': total_votes,
                    'agree_votes': agree_votes,
                    'agreement_ratio': agreement_ratio,
                    'required_ratio': required_ratio,
                    'required_threshold': required_threshold,
                    'vote_passed': True,
                    'auto_completed': True,
                    'completion_type': 'voting_auto',
                    'key_destroyed': task_key_item is not None
                }
            )

            # 发送任务自动完成通知给任务创建者
            Notification.create_notification(
                recipient=task.user,
                notification_type='task_vote_passed',
                title='投票通过 - 任务已自动完成',
                message=f'您的任务《{task.title}》投票通过（{agree_votes}/{total_votes}票同意），任务已自动完成！',
                related_object_type='task',
                related_object_id=task.id,
                extra_data={
                    'task_title': task.title,
                    'agree_votes': agree_votes,
                    'total_votes': total_votes,
                    'agreement_ratio': agreement_ratio,
                    'auto_completed': True
                },
                priority='high'
            )

            processed_tasks.append({
                'id': str(task.id),
                'title': task.title,
                'result': 'passed',
                'votes': f'{agree_votes}/{total_votes}',
                'ratio': f'{agreement_ratio*100:.1f}%'
            })
        else:
            # 投票失败 - 固定加时15分钟，回到active状态
            penalty_minutes = 15

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
    process_voting_results(request)

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

    # 找到所有活跃状态的带锁任务
    active_lock_tasks = LockTask.objects.filter(
        task_type='lock',
        status__in=['active', 'voting']  # 活跃状态和投票期都算活跃
    )

    processed_rewards = []

    for task in active_lock_tasks:
        if not task.start_time:
            continue

        # 计算任务已运行的总时间（小时）
        elapsed_time = now - task.start_time
        elapsed_hours = int(elapsed_time.total_seconds() // 3600)

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

            # 创建小时奖励积分通知
            Notification.create_notification(
                recipient=task.user,
                notification_type='coins_earned_hourly',
                actor=None,  # 系统通知
                related_object_type='task',
                related_object_id=task.id,
                extra_data={
                    'task_title': task.title,
                    'hour_count': hour_num,
                    'reward_amount': 1,
                    'total_hourly_rewards': task.total_hourly_rewards + 1
                },
                priority='low'  # 小时奖励是低优先级通知
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