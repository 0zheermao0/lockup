from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import login, logout
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta
from .models import User, Friendship, UserLevelUpgrade
from .serializers import (
    UserSerializer, UserPublicSerializer, UserRegistrationSerializer,
    UserLoginSerializer, UserProfileUpdateSerializer, FriendshipSerializer,
    FriendRequestSerializer, UserLevelUpgradeSerializer, UserStatsSerializer,
    PasswordChangeSerializer
)


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

        return Response({
            'user': UserSerializer(user).data,
            'token': token.key,
            'message': '登录成功'
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
