"""
任务验证工具模块
Task validation utilities
"""
from typing import Tuple, Optional
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from .models import LockTask
from store.models import Item


def validate_task_completion_conditions(
    task: LockTask,
    user,
    require_has_key: bool = True
) -> Tuple[bool, Optional[Response]]:
    """
    验证任务是否满足完成条件

    Args:
        task: 要验证的带锁任务
        user: 执行操作的用户
        require_has_key: 是否需要验证用户持有钥匙（万能钥匙场景设为False）

    Returns:
        Tuple[bool, Optional[Response]]: (是否可以完成, 错误响应对象)
        - 如果可以完成：返回 (True, None)
        - 如果不能完成：返回 (False, Response对象)

    验证条件包括：
    1. 任务不能处于冻结状态
    2. 倒计时必须结束（如果有）
    3. 投票解锁任务需要投票通过
    4. 用户必须持有对应钥匙（可选）
    """
    # 条件1: 冻结状态的任务不能完成
    if task.is_frozen:
        return False, Response(
            {'error': '冻结状态的任务无法完成，请先解冻'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 条件2: 倒计时必须结束
    if task.end_time and timezone.now() < task.end_time:
        return False, Response(
            {'error': '带锁任务必须等待倒计时结束后才能完成'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 条件3: 投票解锁类型的任务需要检查投票是否通过
    if task.unlock_type == 'vote':
        # 检查是否处于投票已通过状态或有投票记录
        if task.status == 'voting_passed' or task.voting_end_time:
            # 投票已通过，可以完成
            pass
        else:
            return False, Response(
                {'error': '投票解锁任务必须先发起投票'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 检查投票是否通过（应用影响力皇冠效果）
        from .views import calculate_weighted_vote_counts  # 避免循环导入
        vote_counts = calculate_weighted_vote_counts(task)
        total_votes = vote_counts['total_votes']
        agree_votes = vote_counts['agree_votes']

        # 检查投票数量是否达到门槛
        required_votes = task.vote_threshold or 1  # 如果没有设置门槛，默认需要1票
        if total_votes < required_votes:
            return False, Response(
                {'error': f'投票数量不足，需要至少 {required_votes} 票，当前 {total_votes} 票'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 检查同意比例是否达到要求
        agreement_ratio = agree_votes / total_votes if total_votes > 0 else 0
        required_ratio = task.vote_agreement_ratio or 0.5
        if agreement_ratio < required_ratio:
            return False, Response(
                {'error': f'投票同意率不足，需要 {required_ratio*100:.0f}%，当前 {agreement_ratio*100:.1f}%'},
                status=status.HTTP_400_BAD_REQUEST
            )
        # 投票通过，可以继续完成任务

    # 条件4: 检查用户是否持有对应的钥匙道具
    # 只有钥匙的当前持有者（无论是原始创建者还是其他人）可以完成任务
    if not require_has_key:
        return True, None

    task_key_item = Item.objects.filter(
        item_type__name='key',
        owner=user,
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
            if original_key.original_owner == user:
                error_msg = '您已将此任务的钥匙转让给他人，无法完成任务。只有钥匙的当前持有者可以完成任务。'
            else:
                error_msg = f'只有钥匙的当前持有者（{original_key.owner.username}）可以完成此任务。'
        else:
            error_msg = '您没有持有该任务的钥匙道具，无法完成任务'

        return False, Response(
            {'error': error_msg},
            status=status.HTTP_403_FORBIDDEN
        )

    return True, None


# 保持向后兼容性的别名
_can_complete_lock_task = validate_task_completion_conditions