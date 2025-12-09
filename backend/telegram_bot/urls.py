from django.urls import path
from . import views

urlpatterns = [
    # Webhook
    path('webhook/', views.telegram_webhook, name='telegram_webhook'),

    # 绑定管理
    path('bind/', views.bind_telegram, name='bind_telegram'),
    path('unbind/', views.unbind_telegram, name='unbind_telegram'),
    path('status/', views.telegram_status, name='telegram_status'),
    path('toggle-notifications/', views.toggle_telegram_notifications, name='toggle_telegram_notifications'),

    # 功能 API
    path('add-overtime/', views.telegram_add_overtime, name='telegram_add_overtime'),
    path('search-users/', views.search_users_for_overtime, name='search_users_for_overtime'),
    path('share-task/', views.share_task_to_telegram, name='share_task_to_telegram'),

    # 游戏分享 API
    path('share-game/', views.share_game_to_telegram, name='share_game_to_telegram'),
    path('share-game-direct/', views.share_game_directly, name='share_game_directly'),

    # 测试 API
    path('test-notification/', views.test_telegram_notification, name='test_telegram_notification'),
]