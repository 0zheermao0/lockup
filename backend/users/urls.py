from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # 认证相关
    path('register/', views.UserRegistrationView.as_view(), name='register'),
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('logout/', views.UserLogoutView.as_view(), name='logout'),
    path('telegram-auth/', views.TelegramAuthLoginView.as_view(), name='telegram-auth'),
    path('telegram-config/', views.TelegramLoginConfigView.as_view(), name='telegram-config'),
    path('password/change/', views.PasswordChangeView.as_view(), name='password-change'),
    path('password/change-simple/', views.SimplePasswordChangeView.as_view(), name='simple-password-change'),
    path('password/reset-request/', views.PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password/reset-confirm/', views.PasswordResetConfirmView.as_view(), name='password-reset-confirm'),

    # 邮箱验证
    path('email/send-verification/', views.EmailVerificationSendView.as_view(), name='send-email-verification'),
    path('email/verify/', views.EmailVerificationVerifyView.as_view(), name='verify-email'),

    # 用户资料
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    path('profile/avatar/', views.upload_avatar, name='upload-avatar'),
    path('users/', views.UserListView.as_view(), name='user-list'),
    path('users/<int:pk>/', views.UserDetailView.as_view(), name='user-detail'),
    path('stats/', views.user_stats, name='user-stats'),

    # 好友功能
    path('friends/', views.FriendListView.as_view(), name='friend-list'),
    path('friend-requests/', views.FriendRequestListView.as_view(), name='friend-request-list'),
    path('friend-requests/send/', views.FriendRequestView.as_view(), name='send-friend-request'),
    path('friend-requests/<int:friendship_id>/accept/', views.accept_friend_request, name='accept-friend-request'),
    path('friend-requests/<int:friendship_id>/reject/', views.reject_friend_request, name='reject-friend-request'),

    # 等级管理
    path('users/<int:user_id>/promote/', views.promote_user, name='promote-user'),

    # 每日登录奖励
    path('daily-reward/', views.daily_login_reward, name='daily-login-reward'),

    # 通知系统
    path('notifications/', views.NotificationListView.as_view(), name='notification-list'),
    path('notifications/stats/', views.notification_stats, name='notification-stats'),
    path('notifications/create/', views.create_notification, name='create-notification'),
    path('notifications/<uuid:notification_id>/read/', views.mark_notification_read, name='mark-notification-read'),
    path('notifications/<uuid:notification_id>/delete/', views.delete_notification, name='delete-notification'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark-all-notifications-read'),
    path('notifications/clear-read/', views.clear_read_notifications, name='clear-read-notifications'),

    # 活跃度日志
    path('activity-logs/', views.ActivityLogListView.as_view(), name='activity-logs'),

    # 积分日志
    path('coins-logs/', views.CoinsLogListView.as_view(), name='coins-logs'),

    # 等级进度
    path('level-progress/', views.LevelProgressView.as_view(), name='level-progress'),

    # 社区排行榜
    path('community-leaderboard/', views.CommunityLeaderboardView.as_view(), name='community-leaderboard'),
]