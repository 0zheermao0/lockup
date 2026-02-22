from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import PermissionDenied
from django.contrib.auth import login, logout
from django.db.models import Q, Count
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.conf import settings
from datetime import timedelta
from tasks.pagination import DynamicPageNumberPagination
from .models import User, Friendship, UserLevelUpgrade, DailyLoginReward, UserCheckIn, Notification, EmailVerification, PasswordReset, ActivityLog, CoinsLog, Conversation, PrivateMessage
from datetime import date, timedelta
from .serializers import (
    UserSerializer, UserPublicSerializer, UserRegistrationSerializer,
    UserLoginSerializer, UserProfileUpdateSerializer, FriendshipSerializer,
    FriendRequestSerializer, UserLevelUpgradeSerializer, UserStatsSerializer,
    PasswordChangeSerializer, SimplePasswordChangeSerializer, NotificationSerializer, NotificationCreateSerializer,
    PasswordResetRequestSerializer, PasswordResetConfirmSerializer, ActivityLogSerializer, CoinsLogSerializer,
    TelegramLoginRequestSerializer, ConversationSerializer, PrivateMessageSerializer
)
from utils.email_verification import (
    create_and_send_verification, verify_email_code, is_email_domain_allowed
)
from utils.password_reset import (
    create_and_send_password_reset, reset_user_password
)


def get_client_ip(request):
    """获取客户端IP地址"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


class EmailVerificationSendView(APIView):
    """发送邮箱验证码"""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip().lower()

        if not email:
            return Response({
                'error': '邮箱地址不能为空'
            }, status=status.HTTP_400_BAD_REQUEST)

        # 检查邮箱格式
        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError

        try:
            validate_email(email)
        except ValidationError:
            return Response({
                'error': '邮箱格式不正确'
            }, status=status.HTTP_400_BAD_REQUEST)

        # 检查邮箱是否已被注册
        if User.objects.filter(email=email).exists():
            return Response({
                'error': '该邮箱已被注册'
            }, status=status.HTTP_400_BAD_REQUEST)

        # 获取客户端IP
        ip_address = get_client_ip(request)

        # 创建并发送验证码
        success, message, extra_info = create_and_send_verification(email, ip_address)

        if success:
            return Response({
                'message': message,
                'expires_in_minutes': extra_info.get('expires_in_minutes'),
                'remaining_attempts': extra_info.get('remaining_attempts')
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': message,
                'remaining_attempts': extra_info.get('remaining_attempts', 0)
            }, status=status.HTTP_400_BAD_REQUEST)


class EmailVerificationVerifyView(APIView):
    """验证邮箱验证码"""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        code = request.data.get('code', '').strip()

        if not email or not code:
            return Response({
                'error': '邮箱和验证码不能为空'
            }, status=status.HTTP_400_BAD_REQUEST)

        # 验证邮箱验证码
        success, message = verify_email_code(email, code)

        if success:
            return Response({
                'message': message,
                'verified': True
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': message,
                'verified': False
            }, status=status.HTTP_400_BAD_REQUEST)


class UserRegistrationView(generics.CreateAPIView):
    """用户注册视图"""

    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # 创建认证token
        token, created = Token.objects.get_or_create(user=user)

        return Response({
            'user': UserSerializer(user).data,
            'token': token.key,
            'message': '注册成功'
        }, status=status.HTTP_201_CREATED)


class UserLoginView(generics.GenericAPIView):
    """用户登录视图"""

    serializer_class = UserLoginSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']
        login(request, user)

        # 获取或创建token
        token, created = Token.objects.get_or_create(user=user)

        # 更新用户活跃度
        user.update_activity()

        # 处理每日登录奖励
        daily_reward, is_new, reward_message = DailyLoginReward.claim_daily_reward(user)
        daily_reward_message = f"，{reward_message}" if is_new else ""

        return Response({
            'user': UserSerializer(user).data,
            'token': token.key,
            'message': f'登录成功{daily_reward_message}'
        })


class UserLogoutView(generics.GenericAPIView):
    """用户登出视图"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # 删除token
        try:
            token = Token.objects.get(user=request.user)
            token.delete()
        except Token.DoesNotExist:
            pass

        logout(request)
        return Response({'message': '登出成功'})


class UserProfileView(generics.RetrieveUpdateAPIView):
    """用户资料视图"""

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return UserProfileUpdateSerializer
        return UserSerializer


class UserDetailView(generics.RetrieveAPIView):
    """其他用户详情视图"""

    queryset = User.objects.all()
    serializer_class = UserPublicSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request_user'] = self.request.user
        return context


class UserListView(generics.ListAPIView):
    """用户列表视图"""

    queryset = User.objects.all()
    serializer_class = UserPublicSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.query_params.get('search', None)
        level = self.request.query_params.get('level', None)

        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) | Q(bio__icontains=search)
            )

        if level:
            try:
                level_int = int(level)
                queryset = queryset.filter(level=level_int)
            except ValueError:
                pass

        return queryset.order_by('-activity_score', '-last_active')


class FriendListView(generics.ListAPIView):
    """好友列表视图"""

    serializer_class = FriendshipSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Friendship.objects.filter(
            Q(from_user=user) | Q(to_user=user),
            status='accepted'
        )


class FriendRequestView(generics.CreateAPIView):
    """发送好友请求视图"""

    serializer_class = FriendRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class FriendRequestListView(generics.ListAPIView):
    """好友请求列表视图"""

    serializer_class = FriendshipSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Friendship.objects.filter(
            to_user=user,
            status='pending'
        ).order_by('-created_at')


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def accept_friend_request(request, friendship_id):
    """接受好友请求"""
    try:
        friendship = Friendship.objects.get(
            id=friendship_id,
            to_user=request.user,
            status='pending'
        )
        friendship.status = 'accepted'
        friendship.save()

        # 创建反向好友关系
        Friendship.objects.get_or_create(
            from_user=friendship.to_user,
            to_user=friendship.from_user,
            defaults={'status': 'accepted'}
        )

        return Response({
            'message': '好友请求已接受',
            'friendship': FriendshipSerializer(friendship).data
        })
    except Friendship.DoesNotExist:
        return Response(
            {'error': '好友请求不存在'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def reject_friend_request(request, friendship_id):
    """拒绝好友请求"""
    try:
        friendship = Friendship.objects.get(
            id=friendship_id,
            to_user=request.user,
            status='pending'
        )
        friendship.delete()

        return Response({'message': '好友请求已拒绝'})
    except Friendship.DoesNotExist:
        return Response(
            {'error': '好友请求不存在'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def promote_user(request, user_id):
    """晋升用户等级（仅4级用户可操作）"""
    if request.user.level != 4:
        return Response(
            {'error': '只有4级用户可以晋升其他用户'},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        user = User.objects.get(id=user_id)
        if user.level >= 4:
            return Response(
                {'error': '用户已是最高等级'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 检查今日是否已经晋升过其他用户
        today = timezone.now().date()
        today_promotions = UserLevelUpgrade.objects.filter(
            promoted_by=request.user,
            created_at__date=today,
            reason='manual'
        ).count()

        if today_promotions >= 1:
            return Response(
                {'error': '每天只能晋升一个用户'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 执行晋升
        old_level = user.level
        user.level = min(4, user.level + 1)
        user.save()

        # 记录晋升日志
        UserLevelUpgrade.objects.create(
            user=user,
            promoted_by=request.user,
            from_level=old_level,
            to_level=user.level,
            reason='manual'
        )

        return Response({
            'message': f'用户已晋升至{user.level}级',
            'user': UserPublicSerializer(user).data
        })

    except User.DoesNotExist:
        return Response(
            {'error': '用户不存在'},
            status=status.HTTP_404_NOT_FOUND
        )


class PasswordChangeView(generics.GenericAPIView):
    """密码修改视图"""

    serializer_class = PasswordChangeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({'message': '密码修改成功'})


class SimplePasswordChangeView(APIView):
    """简化密码修改视图（无需原密码验证）"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """处理密码修改请求"""
        serializer = SimplePasswordChangeSerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': '密码修改成功'
            }, status=status.HTTP_200_OK)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class PasswordResetRequestView(APIView):
    """密码重置请求视图"""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """处理密码重置请求"""
        serializer = PasswordResetRequestSerializer(data=request.data)

        if serializer.is_valid():
            email = serializer.validated_data['email']
            ip_address = get_client_ip(request)

            # 创建并发送密码重置码
            success, message, extra_info = create_and_send_password_reset(email, ip_address)

            if success:
                return Response({
                    'message': message,
                    'expires_in_minutes': extra_info.get('expires_in_minutes', 15),
                    'remaining_attempts': extra_info.get('remaining_attempts', 0)
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': message,
                    'remaining_attempts': extra_info.get('remaining_attempts', 0)
                }, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class PasswordResetConfirmView(APIView):
    """密码重置确认视图"""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """处理密码重置确认"""
        serializer = PasswordResetConfirmSerializer(data=request.data)

        if serializer.is_valid():
            email = serializer.validated_data['email']
            reset_code = serializer.validated_data['reset_code']
            new_password = serializer.validated_data['new_password']

            # 重置密码
            success, message = reset_user_password(email, reset_code, new_password)

            if success:
                return Response({
                    'message': message
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': message
                }, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def upload_avatar(request):
    """上传用户头像"""
    if 'avatar' not in request.FILES:
        return Response(
            {'error': '请选择头像文件'},
            status=status.HTTP_400_BAD_REQUEST
        )

    avatar_file = request.FILES['avatar']

    # 验证文件类型
    if not avatar_file.content_type.startswith('image/'):
        return Response(
            {'error': '请上传图片文件'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 验证文件大小 (2.5MB)
    if avatar_file.size > int(2.5 * 1024 * 1024):
        return Response(
            {'error': '图片大小不能超过2.5MB'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 保存头像
    user = request.user
    user.avatar = avatar_file
    user.save()

    # 更新用户活跃度
    user.update_activity()

    return Response({
        'message': '头像上传成功',
        'avatar_url': user.avatar.url if user.avatar else None
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_stats(request):
    """用户统计信息"""
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)

    # 总用户数
    total_users = User.objects.count()

    # 等级分布
    level_distribution = {}
    for i in range(1, 5):
        level_distribution[f'level_{i}'] = User.objects.filter(level=i).count()

    # 今日活跃用户
    active_users_today = User.objects.filter(
        last_active__date=today
    ).count()

    # 本周新用户
    new_users_this_week = User.objects.filter(
        created_at__date__gte=week_ago
    ).count()

    # 最活跃用户（前10名）
    top_active_users = User.objects.order_by(
        '-activity_score'
    )[:10]

    stats_data = {
        'total_users': total_users,
        'level_distribution': level_distribution,
        'active_users_today': active_users_today,
        'new_users_this_week': new_users_this_week,
        'top_active_users': top_active_users
    }

    serializer = UserStatsSerializer(stats_data)
    return Response(serializer.data)


class NotificationListView(generics.ListAPIView):
    """通知列表视图"""
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = DynamicPageNumberPagination

    def get_queryset(self):
        user = self.request.user

        # 获取查询参数
        is_read = self.request.query_params.get('is_read', None)
        notification_type = self.request.query_params.get('type', None)

        queryset = Notification.objects.filter(recipient=user)

        # 按已读状态过滤
        if is_read is not None:
            queryset = queryset.filter(is_read=is_read.lower() == 'true')

        # 按通知类型过滤
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)

        # 排序（移除手动limit处理，让DRF pagination处理）
        return queryset.order_by('-created_at')


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_notification_read(request, notification_id):
    """标记通知为已读"""
    try:
        notification = Notification.objects.get(
            id=notification_id,
            recipient=request.user
        )
        notification.mark_as_read()

        return Response({
            'message': '通知已标记为已读',
            'notification': NotificationSerializer(notification).data
        })
    except Notification.DoesNotExist:
        return Response(
            {'error': '通知不存在'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_all_notifications_read(request):
    """标记所有通知为已读"""
    count = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).update(
        is_read=True,
        read_at=timezone.now()
    )

    return Response({
        'message': f'已标记{count}条通知为已读',
        'marked_count': count
    })


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_notification(request, notification_id):
    """删除通知"""
    try:
        notification = Notification.objects.get(
            id=notification_id,
            recipient=request.user
        )
        notification.delete()

        return Response({'message': '通知已删除'})
    except Notification.DoesNotExist:
        return Response(
            {'error': '通知不存在'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def clear_read_notifications(request):
    """清理所有已读通知"""
    count, _ = Notification.objects.filter(
        recipient=request.user,
        is_read=True
    ).delete()

    return Response({
        'message': f'已清理{count}条已读通知',
        'cleared_count': count
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def notification_stats(request):
    """获取通知统计信息"""
    user = request.user

    total_notifications = Notification.objects.filter(recipient=user).count()
    unread_notifications = Notification.objects.filter(
        recipient=user,
        is_read=False
    ).count()

    # 按类型统计未读通知
    unread_by_type = {}
    for type_choice in Notification.TYPE_CHOICES:
        type_name = type_choice[0]
        type_display = type_choice[1]

        count = Notification.objects.filter(
            recipient=user,
            notification_type=type_name,
            is_read=False
        ).count()

        if count > 0:
            unread_by_type[type_name] = {
                'display_name': type_display,
                'count': count
            }

    # 按优先级统计未读通知
    unread_by_priority = {}
    for priority_choice in Notification.PRIORITY_CHOICES:
        priority_name = priority_choice[0]
        priority_display = priority_choice[1]

        count = Notification.objects.filter(
            recipient=user,
            priority=priority_name,
            is_read=False
        ).count()

        if count > 0:
            unread_by_priority[priority_name] = {
                'display_name': priority_display,
                'count': count
            }

    return Response({
        'total_notifications': total_notifications,
        'unread_notifications': unread_notifications,
        'unread_by_type': unread_by_type,
        'unread_by_priority': unread_by_priority
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_notification(request):
    """创建通知（管理员功能）"""
    # 检查是否是管理员
    if not request.user.is_superuser:
        return Response(
            {'error': '没有权限'},
            status=status.HTTP_403_FORBIDDEN
        )

    serializer = NotificationCreateSerializer(data=request.data)
    if serializer.is_valid():
        try:
            recipient = User.objects.get(id=serializer.validated_data['recipient_id'])

            notification = Notification.create_notification(
                recipient=recipient,
                notification_type=serializer.validated_data['notification_type'],
                title=serializer.validated_data.get('title'),
                message=serializer.validated_data.get('message'),
                actor=None,  # 管理员创建，无特定actor
                related_object_type=serializer.validated_data.get('related_object_type'),
                related_object_id=serializer.validated_data.get('related_object_id'),
                extra_data=serializer.validated_data.get('extra_data', {}),
                priority=serializer.validated_data.get('priority', 'normal')
            )

            return Response({
                'message': '通知创建成功',
                'notification': NotificationSerializer(notification).data
            }, status=status.HTTP_201_CREATED)

        except User.DoesNotExist:
            return Response(
                {'error': '接收者不存在'},
                status=status.HTTP_404_NOT_FOUND
            )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def daily_login_reward(request):
    """
    每日登录奖励接口
    GET: 检查今日奖励状态
    POST: 领取今日奖励
    """
    user = request.user

    if request.method == 'GET':
        # 检查今日奖励状态
        reward_info = DailyLoginReward.get_today_reward_info(user)
        return Response({
            'has_claimed': reward_info['has_claimed'],
            'reward_amount': reward_info['reward_amount'],
            'date': reward_info['date'],
            'user_level': reward_info['user_level']
        })

    elif request.method == 'POST':
        # 领取今日奖励
        reward, is_new, message = DailyLoginReward.claim_daily_reward(user)

        return Response({
            'success': is_new,
            'message': message,
            'reward_amount': reward.reward_amount,
            'date': reward.date.isoformat(),
            'current_coins': user.coins
        })


class ActivityLogListView(generics.ListAPIView):
    """获取当前用户的活跃度变化日志"""
    serializer_class = ActivityLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = DynamicPageNumberPagination

    def get_queryset(self):
        return ActivityLog.objects.filter(
            user=self.request.user
        ).select_related('user')


class CoinsLogListView(generics.ListAPIView):
    """获取当前用户的积分变化日志"""
    serializer_class = CoinsLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = DynamicPageNumberPagination

    def get_queryset(self):
        queryset = CoinsLog.objects.filter(user=self.request.user)

        # 按类型过滤
        change_type = self.request.query_params.get('type', None)
        if change_type:
            if change_type == 'income':
                queryset = queryset.filter(amount__gt=0)
            elif change_type == 'expense':
                queryset = queryset.filter(amount__lt=0)
            else:
                queryset = queryset.filter(change_type=change_type)

        return queryset


class LevelProgressView(APIView):
    """获取当前用户的等级升级进度"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        current_level = user.level

        # 获取下一级要求
        requirements = self._get_level_requirements(user, current_level + 1)

        # 计算各维度进度
        progress = {
            'current_level': current_level,
            'target_level': current_level + 1 if current_level < 4 else None,
            'is_max_level': current_level >= 4,
            'dimensions': requirements,
            'overall_progress': self._calculate_overall_progress(requirements),
        }

        return Response(progress)

    def _get_level_requirements(self, user, target_level):
        """获取各维度升级要求"""
        if target_level > 4:
            return []

        # 等级要求定义
        level_requirements = {
            2: {
                'activity_score': {'required': 100, 'label': '活跃度', 'unit': ''},
                'total_posts': {'required': 5, 'label': '发布动态', 'unit': '条'},
                'total_likes_received': {'required': 10, 'label': '收到点赞', 'unit': '个'},
                'lock_duration_hours': {'required': 24, 'label': '带锁时长', 'unit': '小时'},
            },
            3: {
                'activity_score': {'required': 300, 'label': '活跃度', 'unit': ''},
                'total_posts': {'required': 20, 'label': '发布动态', 'unit': '条'},
                'total_likes_received': {'required': 50, 'label': '收到点赞', 'unit': '个'},
                'lock_duration_hours': {'required': 7 * 24, 'label': '带锁时长', 'unit': '小时'},
                'task_completion_rate': {'required': 80.0, 'label': '任务完成率', 'unit': '%'},
            },
            4: {
                'activity_score': {'required': 1000, 'label': '活跃度', 'unit': ''},
                'total_posts': {'required': 50, 'label': '发布动态', 'unit': '条'},
                'total_likes_received': {'required': 1000, 'label': '收到点赞', 'unit': '个'},
                'lock_duration_hours': {'required': 30 * 24, 'label': '带锁时长', 'unit': '小时'},
                'task_completion_rate': {'required': 90.0, 'label': '任务完成率', 'unit': '%'},
            }
        }

        requirements_def = level_requirements.get(target_level, {})
        dimensions = []

        # 获取用户当前值
        lock_duration_hours = user.get_total_lock_duration() / 60  # 分钟转小时
        task_completion_rate = user.get_task_completion_rate()

        current_values = {
            'activity_score': user.activity_score,
            'total_posts': user.total_posts,
            'total_likes_received': user.total_likes_received,
            'lock_duration_hours': lock_duration_hours,
            'task_completion_rate': task_completion_rate,
        }

        for key, config in requirements_def.items():
            current = current_values.get(key, 0)
            required = config['required']

            # 计算百分比（最高100%）
            if required > 0:
                percentage = min(100, round((current / required) * 100, 1))
            else:
                percentage = 100

            is_met = current >= required

            dimensions.append({
                'name': key,
                'label': config['label'],
                'current': current,
                'required': required,
                'unit': config['unit'],
                'percentage': percentage,
                'is_met': is_met
            })

        return dimensions

    def _calculate_overall_progress(self, dimensions):
        """计算总体进度"""
        if not dimensions:
            return 100

        total_percentage = sum(d['percentage'] for d in dimensions)
        return round(total_percentage / len(dimensions), 1)


class TelegramAuthLoginView(APIView):
    """Telegram授权登录视图"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """处理Telegram登录请求"""
        # 获取Telegram登录数据
        telegram_data = request.data

        # 验证必需字段
        required_fields = ['id', 'auth_date', 'hash']
        for field in required_fields:
            if field not in telegram_data:
                return Response(
                    {'error': f'缺少必需字段: {field}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # 验证Telegram数据签名
        if not self._verify_telegram_auth(telegram_data):
            return Response(
                {'error': 'Telegram登录验证失败，数据可能被篡改'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 检查auth_date是否过期（24小时内有效）
        import time
        from django.utils import timezone

        auth_date = telegram_data.get('auth_date', 0)
        current_time = int(time.time())
        if current_time - auth_date > 86400:  # 24小时 = 86400秒
            return Response(
                {'error': '登录链接已过期，请重新登录'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 获取Telegram用户ID
        telegram_user_id = str(telegram_data.get('id'))

        # 查找已绑定的用户
        try:
            user = User.objects.get(telegram_user_id=telegram_user_id)
        except User.DoesNotExist:
            # Generate registration token for new users
            import uuid
            from django.core.cache import cache

            reg_token = f"reg_{uuid.uuid4().hex[:32]}"
            # Store in cache with Telegram data, expire in 10 minutes
            cache.set(f"tg_reg:{reg_token}", {
                'telegram_user_id': telegram_user_id,
                'telegram_username': telegram_data.get('username', ''),
                'first_name': telegram_data.get('first_name', ''),
                'last_name': telegram_data.get('last_name', ''),
            }, timeout=600)

            bot_username = getattr(settings, 'TELEGRAM_BOT_USERNAME', 'lock_heart_bot')

            return Response(
                {
                    'error': '该Telegram账号未绑定任何用户',
                    'code': 'USER_NOT_FOUND',
                    'bot_url': f'https://t.me/{bot_username}?start={reg_token}'
                },
                status=status.HTTP_404_NOT_FOUND
            )

        # 更新用户的Telegram信息
        user.telegram_username = telegram_data.get('username', '')
        if telegram_data.get('first_name') or telegram_data.get('last_name'):
            full_name = ' '.join(filter(None, [
                telegram_data.get('first_name', ''),
                telegram_data.get('last_name', '')
            ]))
            # 如果用户没有设置bio，可以保存Telegram名称
            if not user.bio and full_name:
                pass  # 可选：保存到某个字段

        user.save()

        # 登录用户
        login(request, user)

        # 获取或创建token
        token, created = Token.objects.get_or_create(user=user)

        # 更新用户活跃度
        user.update_activity()

        # 处理每日登录奖励
        daily_reward, is_new, reward_message = DailyLoginReward.claim_daily_reward(user)
        daily_reward_message = f"，{reward_message}" if is_new else ""

        return Response({
            'user': UserSerializer(user).data,
            'token': token.key,
            'message': f'Telegram登录成功{daily_reward_message}'
        })

    def _verify_telegram_auth(self, data):
        """验证Telegram登录数据的签名"""
        from django.conf import settings
        import hashlib
        import hmac

        # 获取Bot Token
        bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
        if not bot_token:
            return False

        # 创建数据检查字符串（按字母顺序排列的字段）
        data_check_string = []

        # 按字母顺序排列所有字段（除了hash）
        for key in sorted(data.keys()):
            if key != 'hash' and data[key] is not None:
                data_check_string.append(f"{key}={data[key]}")

        data_check_string = '\n'.join(data_check_string)

        # 使用Bot Token的SHA256哈希作为密钥
        secret_key = hashlib.sha256(bot_token.encode()).digest()

        # 计算HMAC-SHA256
        computed_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        # 比较计算的hash与提供的hash
        return computed_hash == data.get('hash')


class CommunityLeaderboardView(APIView):
    """社区排行榜 - 滚动7天统计"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """获取社区排行榜数据（最近7天）"""
        from datetime import timedelta
        from django.db.models import Sum, Count
        from posts.models import Post, PostLike, Comment
        from tasks.models import LockTask
        from .models import ActivityLog, CoinsLog

        # 获取用户详细信息的辅助函数
        def get_user_info(user_id):
            if not user_id:
                return None
            try:
                user = User.objects.get(id=user_id)
                from utils.media import get_full_media_url
                return {
                    'id': user.id,
                    'username': user.username,
                    'level': user.level,
                    'avatar': get_full_media_url(user.avatar.url) if user.avatar else None
                }
            except User.DoesNotExist:
                return None

        # 格式化排行榜数据的辅助函数
        def format_leaderboard(queryset, value_key, user_key='user'):
            result = []
            rank = 1
            for item in queryset:
                user_id = item.get(user_key)
                user_info = get_user_info(user_id)
                if user_info:
                    result.append({
                        'rank': rank,
                        'user': user_info,
                        'value': item[value_key]
                    })
                    rank += 1
            return result

        try:
            # 计算7天前的时间点
            seven_days_ago = timezone.now() - timedelta(days=7)

            # 1. 获赞最多的用户（最近7天发布的动态获得的点赞）
            top_likes_received = PostLike.objects.filter(
                post__created_at__gte=seven_days_ago
            ).values('post__user').annotate(
                total_likes=Count('id')
            ).filter(
                total_likes__gt=0
            ).order_by('-total_likes')[:3]

            # 2. 获得评论最多的用户（最近7天发布的动态获得的评论）
            top_comments_received = Comment.objects.filter(
                post__created_at__gte=seven_days_ago
            ).values('post__user').annotate(
                total_comments=Count('id')
            ).filter(
                total_comments__gt=0
            ).order_by('-total_comments')[:3]

            # 3. 活跃度提升最多的用户（最近7天的activity_gain总和）
            top_activity_gained = ActivityLog.objects.filter(
                created_at__gte=seven_days_ago,
                action_type='activity_gain'
            ).values('user').annotate(
                total_gained=Sum('points_change')
            ).filter(
                total_gained__gt=0
            ).order_by('-total_gained')[:3]

            # 4. 获得积分最多的用户（最近7天的正积分总和）
            top_coins_earned = CoinsLog.objects.filter(
                created_at__gte=seven_days_ago,
                amount__gt=0
            ).values('user').annotate(
                total_earned=Sum('amount')
            ).filter(
                total_earned__gt=0
            ).order_by('-total_earned')[:3]

            # 5. 发布动态最多的用户（最近7天）
            top_posts_created = Post.objects.filter(
                created_at__gte=seven_days_ago
            ).values('user').annotate(
                post_count=Count('id')
            ).filter(
                post_count__gt=0
            ).order_by('-post_count')[:3]

            # 6. 发布任务最多的用户（最近7天创建的带锁任务）
            top_tasks_created = LockTask.objects.filter(
                created_at__gte=seven_days_ago,
                task_type='lock'
            ).values('user').annotate(
                task_count=Count('id')
            ).filter(
                task_count__gt=0
            ).order_by('-task_count')[:3]

            # 7. 完成任务最多的用户（最近7天完成的带锁任务）
            top_tasks_completed = LockTask.objects.filter(
                completed_at__gte=seven_days_ago,
                task_type='lock',
                status='completed'
            ).values('user').annotate(
                completed_count=Count('id')
            ).filter(
                completed_count__gt=0
            ).order_by('-completed_count')[:3]

            leaderboard_data = {
                'most_likes_received': {
                    'title': '获赞最多',
                    'icon': '👍',
                    'description': '最近7天发布的动态获得最多点赞',
                    'unit': '赞',
                    'data': format_leaderboard(top_likes_received, 'total_likes', 'post__user')
                },
                'most_comments_received': {
                    'title': '获评论最多',
                    'icon': '💬',
                    'description': '最近7天发布的动态获得最多评论',
                    'unit': '评论',
                    'data': format_leaderboard(top_comments_received, 'total_comments', 'post__user')
                },
                'most_activity_gained': {
                    'title': '活跃度提升最多',
                    'icon': '⚡',
                    'description': '最近7天活跃度提升最多',
                    'unit': '活跃度',
                    'data': format_leaderboard(top_activity_gained, 'total_gained')
                },
                'most_coins_earned': {
                    'title': '积分获取最多',
                    'icon': '🪙',
                    'description': '最近7天获得积分最多',
                    'unit': '积分',
                    'data': format_leaderboard(top_coins_earned, 'total_earned')
                },
                'most_posts_created': {
                    'title': '发布动态最多',
                    'icon': '📝',
                    'description': '最近7天发布动态最多',
                    'unit': '条动态',
                    'data': format_leaderboard(top_posts_created, 'post_count')
                },
                'most_tasks_created': {
                    'title': '发布任务最多',
                    'icon': '📋',
                    'description': '最近7天发布带锁任务最多',
                    'unit': '个任务',
                    'data': format_leaderboard(top_tasks_created, 'task_count')
                },
                'most_tasks_completed': {
                    'title': '完成任务最多',
                    'icon': '✅',
                    'description': '最近7天完成带锁任务最多',
                    'unit': '个任务',
                    'data': format_leaderboard(top_tasks_completed, 'completed_count')
                },
                'updated_at': timezone.now().isoformat()
            }

            return Response(leaderboard_data)

        except Exception as e:
            import traceback
            print(f"CommunityLeaderboardView error: {str(e)}")
            print(traceback.format_exc())
            return Response(
                {'error': f'获取排行榜数据失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TelegramLoginConfigView(APIView):
    """获取Telegram Login Widget配置"""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        """返回Telegram Login Widget所需的配置"""
        from django.conf import settings

        # 使用 TELEGRAM_BOT_USERNAME 作为 bot_name
        bot_name = getattr(settings, 'TELEGRAM_BOT_USERNAME', '')
        frontend_url = getattr(settings, 'FRONTEND_URL', '')

        if not bot_name:
            return Response(
                {'error': 'Telegram Bot未配置'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({
            'bot_name': bot_name,
            'auth_url': f"{frontend_url}/auth/telegram-callback"
        })


class NotificationSettingsView(APIView):
    """用户通知设置视图"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """获取用户通知设置"""
        user = request.user
        return Response({
            'task_deadline_reminder_minutes': user.task_deadline_reminder_minutes,
            'telegram_min_priority': user.telegram_min_priority,
            'telegram_min_priority_display': user.get_telegram_min_priority_display(),
        })

    def patch(self, request):
        """更新用户通知设置"""
        user = request.user
        data = request.data

        # 验证并更新任务截止提醒时间
        if 'task_deadline_reminder_minutes' in data:
            minutes = data['task_deadline_reminder_minutes']
            try:
                minutes = int(minutes)
                if not (5 <= minutes <= 120):
                    return Response(
                        {'error': '任务截止提醒时间必须在 5-120 分钟之间'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                user.task_deadline_reminder_minutes = minutes
            except (ValueError, TypeError):
                return Response(
                    {'error': '任务截止提醒时间必须是有效的整数'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # 验证并更新 Telegram 最低优先级
        if 'telegram_min_priority' in data:
            priority = data['telegram_min_priority']
            valid_priorities = ['low', 'normal', 'high', 'urgent']
            if priority not in valid_priorities:
                return Response(
                    {'error': f'Telegram 最低优先级必须是以下之一: {", ".join(valid_priorities)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            user.telegram_min_priority = priority

        user.save(update_fields=['task_deadline_reminder_minutes', 'telegram_min_priority'])

        return Response({
            'message': '通知设置已更新',
            'task_deadline_reminder_minutes': user.task_deadline_reminder_minutes,
            'telegram_min_priority': user.telegram_min_priority,
            'telegram_min_priority_display': user.get_telegram_min_priority_display(),
        })


class ConversationListView(generics.ListAPIView):
    """获取当前用户的所有会话"""
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = DynamicPageNumberPagination

    def get_queryset(self):
        return Conversation.objects.filter(
            participants=self.request.user
        ).prefetch_related('participants', 'messages__sender')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class MessageListView(generics.ListAPIView):
    """获取指定会话的消息列表"""
    serializer_class = PrivateMessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = DynamicPageNumberPagination

    def get_queryset(self):
        conversation_id = self.kwargs.get('conversation_id')
        conversation = get_object_or_404(Conversation, id=conversation_id)

        # 检查用户是否是参与者
        if not conversation.participants.filter(id=self.request.user.id).exists():
            raise PermissionDenied("您不是该会话的参与者")

        return PrivateMessage.objects.filter(
            conversation=conversation
        ).select_related('sender').order_by('-created_at')


class SendMessageView(APIView):
    """发送私聊消息"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        recipient_id = request.data.get('recipient_id')
        content = request.data.get('content', '').strip()
        message_type = request.data.get('message_type', 'text')
        file_duration = request.data.get('file_duration')

        if not recipient_id:
            return Response({'error': '请指定接收者'}, status=status.HTTP_400_BAD_REQUEST)

        # 验证消息类型
        if message_type not in ['text', 'image', 'voice']:
            return Response({'error': '无效的消息类型'}, status=status.HTTP_400_BAD_REQUEST)

        # 文本消息需要内容
        if message_type == 'text' and not content:
            return Response({'error': '消息内容不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        # 图片和语音消息需要文件
        file_url = None
        if message_type in ['image', 'voice']:
            uploaded_file = request.FILES.get('file')
            if uploaded_file:
                file_url = self._handle_file_upload(uploaded_file, message_type)
                if not file_url:
                    return Response({'error': '文件上传失败'}, status=status.HTTP_400_BAD_REQUEST)
            elif not content:  # 如果没有文件且没有内容，返回错误
                return Response({'error': '请上传文件'}, status=status.HTTP_400_BAD_REQUEST)

        if content and len(content) > 2000:
            return Response({'error': '消息内容不能超过2000字'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            recipient = User.objects.get(id=recipient_id)
        except User.DoesNotExist:
            return Response({'error': '接收者不存在'}, status=status.HTTP_404_NOT_FOUND)

        # 不能给自己发消息
        if recipient.id == request.user.id:
            return Response({'error': '不能给自己发送消息'}, status=status.HTTP_400_BAD_REQUEST)

        # 获取或创建会话
        conversation = self._get_or_create_conversation(request.user, recipient)

        # 创建消息
        message_data = {
            'conversation': conversation,
            'sender': request.user,
            'message_type': message_type,
            'content': content or '',
        }

        if file_url:
            message_data['file_url'] = file_url
        if file_duration and message_type == 'voice':
            try:
                message_data['file_duration'] = int(file_duration)
            except (ValueError, TypeError):
                pass

        message = PrivateMessage.objects.create(**message_data)

        # 更新会话更新时间
        conversation.save()  # triggers auto_now

        # 创建通知
        notification_message = content[:100] + ('...' if len(content) > 100 else '')
        if message_type == 'image':
            notification_message = '[图片]' + (' ' + notification_message if notification_message else '')
        elif message_type == 'voice':
            notification_message = '[语音]' + (' ' + notification_message if notification_message else '')

        Notification.create_notification(
            recipient=recipient,
            notification_type='private_message',
            title=f"{request.user.username} 发来一条私信",
            message=notification_message,
            actor=request.user,
            related_object_type='private_message',
            related_object_id=str(message.id),
            extra_data={
                'conversation_id': str(conversation.id),
                'sender_id': request.user.id,
                'sender_username': request.user.username,
                'message_preview': content[:50] if content else '[媒体消息]',
                'message_type': message_type
            },
            priority='normal'
        )

        serializer = PrivateMessageSerializer(message, context={'request': request})
        return Response({
            'message': '发送成功',
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)

    def _handle_file_upload(self, file, message_type):
        """处理文件上传，返回文件URL"""
        from django.conf import settings
        from django.core.files.storage import default_storage
        from django.core.files.base import ContentFile
        import os
        import uuid

        # 验证文件类型
        if message_type == 'image':
            allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            max_size = 5 * 1024 * 1024  # 5MB
        elif message_type == 'voice':
            allowed_types = ['audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/ogg', 'audio/webm']
            max_size = 10 * 1024 * 1024  # 10MB
        else:
            return None

        if file.content_type not in allowed_types:
            return None

        if file.size > max_size:
            return None

        # 生成唯一文件名
        ext = os.path.splitext(file.name)[1].lower()
        if not ext:
            if message_type == 'image':
                ext = '.jpg'
            else:
                ext = '.mp3'

        filename = f"{uuid.uuid4()}{ext}"
        upload_path = f"private_messages/{message_type}s/{filename}"

        # 保存文件
        try:
            path = default_storage.save(upload_path, ContentFile(file.read()))
            # 返回完整URL
            return f"{settings.MEDIA_URL}{path}"
        except Exception as e:
            print(f"File upload error: {e}")
            return None

    def _get_or_create_conversation(self, user1, user2):
        """获取或创建两个用户之间的会话"""
        conversation = Conversation.objects.filter(
            participants=user1
        ).filter(
            participants=user2
        ).first()

        if not conversation:
            conversation = Conversation.objects.create()
            conversation.participants.add(user1, user2)

        return conversation


class MarkMessageReadView(APIView):
    """标记会话消息为已读"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, conversation_id):
        conversation = get_object_or_404(Conversation, id=conversation_id)

        # 检查用户是否是参与者
        if not conversation.participants.filter(id=request.user.id).exists():
            raise PermissionDenied("您不是该会话的参与者")

        # 标记对方发送的消息为已读
        unread_messages = PrivateMessage.objects.filter(
            conversation=conversation,
            is_read=False
        ).exclude(sender=request.user)

        count = unread_messages.count()
        unread_messages.update(is_read=True, read_at=timezone.now())

        return Response({
            'message': f'已标记 {count} 条消息为已读',
            'marked_count': count
        })


class GetOrCreateConversationView(APIView):
    """获取或创建两个用户之间的会话"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user_id = request.data.get('user_id')

        if not user_id:
            return Response({'error': '请指定用户ID'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            other_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': '用户不存在'}, status=status.HTTP_404_NOT_FOUND)

        # 不能和自己创建会话
        if other_user.id == request.user.id:
            return Response({'error': '不能和自己创建会话'}, status=status.HTTP_400_BAD_REQUEST)

        # 查找现有会话
        conversation = Conversation.objects.filter(
            participants=request.user
        ).filter(
            participants=other_user
        ).first()

        created = False
        if not conversation:
            # 创建新会话
            conversation = Conversation.objects.create()
            conversation.participants.add(request.user, other_user)
            created = True

        # 序列化并返回
        serializer = ConversationSerializer(conversation, context={'request': request})
        return Response({
            'conversation': serializer.data,
            'created': created
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def check_in(request):
    """Handle daily check-in"""
    user = request.user
    today = date.today()

    # Check if already checked in today
    if UserCheckIn.objects.filter(user=user, check_in_date=today).exists():
        return Response({
            'success': False,
            'error': '今天已经签到过了'
        })

    # Calculate consecutive days
    yesterday = today - timedelta(days=1)
    yesterday_checkin = UserCheckIn.objects.filter(
        user=user,
        check_in_date=yesterday
    ).first()

    if yesterday_checkin:
        consecutive_days = yesterday_checkin.consecutive_days + 1
    else:
        consecutive_days = 1

    # Calculate reward (base 1 + Fibonacci bonus)
    base_reward = 1
    bonus = UserCheckIn.calculate_bonus(consecutive_days)
    total_reward = base_reward + bonus

    # Create check-in record
    checkin = UserCheckIn.objects.create(
        user=user,
        check_in_date=today,
        coins_earned=total_reward,
        consecutive_days=consecutive_days
    )

    # Add coins to user
    user.add_coins(
        amount=total_reward,
        change_type='daily_checkin',
        description=f'第{consecutive_days}天连续签到奖励',
        metadata={
            'consecutive_days': consecutive_days,
            'base_reward': base_reward,
            'bonus': bonus
        }
    )

    # Create notification
    Notification.create_notification(
        recipient=user,
        notification_type='coins_earned_daily_checkin',
        actor=None,
        extra_data={
            'consecutive_days': consecutive_days,
            'coins_earned': total_reward,
            'base_reward': base_reward,
            'bonus': bonus
        },
        priority='normal'
    )

    return Response({
        'success': True,
        'coins_earned': total_reward,
        'consecutive_days': consecutive_days,
        'base_reward': base_reward,
        'bonus': bonus,
        'message': f'签到成功！获得 {total_reward} 积分（连续{consecutive_days}天）'
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_checkin_calendar(request):
    """Get check-in calendar data for a month"""
    user = request.user
    year = int(request.query_params.get('year', date.today().year))
    month = int(request.query_params.get('month', date.today().month))

    checkins = UserCheckIn.get_month_checkins(user, year, month)
    checkin_dates = {c.check_in_date: c for c in checkins}

    # Get task completion data for each day (optional enhancement)
    # This would show if user completed tasks on specific days

    return Response({
        'year': year,
        'month': month,
        'checkins': [
            {
                'date': c.check_in_date.isoformat(),
                'coins_earned': c.coins_earned,
                'consecutive_days': c.consecutive_days
            }
            for c in checkins
        ],
        'today': date.today().isoformat(),
        'can_checkin': not UserCheckIn.objects.filter(
            user=user,
            check_in_date=date.today()
        ).exists(),
        'current_streak': UserCheckIn.get_consecutive_days(user)
    })
