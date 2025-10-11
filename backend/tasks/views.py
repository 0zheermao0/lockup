from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q
import random

from .models import LockTask, TaskKey, TaskVote
from .serializers import (
    LockTaskSerializer, LockTaskCreateSerializer,
    TaskKeySerializer, TaskVoteSerializer, TaskVoteCreateSerializer
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
        task = serializer.save()

        # 如果是带锁任务，创建后直接开始
        if task.task_type == 'lock':
            task.status = 'active'
            task.start_time = timezone.now()

            # 计算结束时间
            if task.duration_type == 'fixed':
                end_time = task.start_time + timezone.timedelta(minutes=task.duration_value)
            elif task.duration_type == 'random':
                # 在范围内随机选择时间
                random_minutes = random.randint(task.duration_value, task.duration_max or task.duration_value)
                end_time = task.start_time + timezone.timedelta(minutes=random_minutes)
            else:
                end_time = None

            task.end_time = end_time
            task.save()

            # 如果是投票解锁类型，自动创建钥匙
            if task.unlock_type == 'vote':
                TaskKey.objects.create(
                    task=task,
                    holder=task.user  # 可以改为随机选择用户的逻辑
                )
        elif task.task_type == 'board':
            # 任务板创建后设置为开放状态
            task.status = 'open'
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
        random_minutes = random.randint(task.duration_value, task.duration_max or task.duration_value)
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

    # 检查权限
    if task.user != request.user:
        return Response(
            {'error': '只有任务创建者可以完成任务'},
            status=status.HTTP_403_FORBIDDEN
        )

    # 检查任务状态
    if task.status != 'active':
        return Response(
            {'error': '任务不是进行中状态'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 检查是否是带锁任务，如果是，需要倒计时结束后才能完成
    if task.task_type == 'lock' and task.end_time:
        if timezone.now() < task.end_time:
            return Response(
                {'error': '带锁任务必须等待倒计时结束后才能完成'},
                status=status.HTTP_400_BAD_REQUEST
            )

    # 更新任务状态
    task.status = 'completed'
    task.completed_at = timezone.now()
    task.save()

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
    if task.status != 'active':
        return Response(
            {'error': '任务不是进行中状态'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 更新任务状态
    task.status = 'failed'
    task.end_time = timezone.now()
    task.save()

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

    serializer = LockTaskSerializer(task)
    return Response(serializer.data)


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

    # 检查是否是自己的任务
    if task.user == request.user:
        return Response(
            {'error': '不能为自己的任务投票'},
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

        # 检查是否达到解锁条件
        total_votes = task.votes.count()
        agree_votes = task.votes.filter(agree=True).count()

        if (total_votes >= task.vote_threshold and
            agree_votes / total_votes >= task.vote_agreement_ratio):
            # 达到解锁条件，可以允许用户解锁任务
            pass  # 这里可以添加自动解锁逻辑

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

    # 更新任务结束时间
    if task.end_time:
        task.end_time = task.end_time + timezone.timedelta(minutes=overtime_minutes)
    else:
        # 如果没有结束时间，从现在开始加时
        task.end_time = timezone.now() + timezone.timedelta(minutes=overtime_minutes)

    task.save()

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