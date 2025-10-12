from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # 认证相关
    path('register/', views.UserRegistrationView.as_view(), name='register'),
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('logout/', views.UserLogoutView.as_view(), name='logout'),
    path('password/change/', views.PasswordChangeView.as_view(), name='password-change'),

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
]