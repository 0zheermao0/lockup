from django.urls import path
from . import views

urlpatterns = [
    # 任务列表和创建
    path('', views.LockTaskListCreateView.as_view(), name='task-list-create'),

    # 任务详情、更新和删除
    path('<uuid:pk>/', views.LockTaskDetailView.as_view(), name='task-detail'),

    # 任务操作
    path('<uuid:pk>/start/', views.start_task, name='task-start'),
    path('<uuid:pk>/complete/', views.complete_task, name='task-complete'),
    path('<uuid:pk>/stop/', views.stop_task, name='task-stop'),
    path('<uuid:pk>/overtime/', views.add_overtime, name='task-overtime'),

    # 任务板操作
    path('<uuid:pk>/take/', views.take_board_task, name='board-task-take'),
    path('<uuid:pk>/submit/', views.submit_board_task, name='board-task-submit'),
    path('<uuid:pk>/approve/', views.approve_board_task, name='board-task-approve'),
    path('<uuid:pk>/reject/', views.reject_board_task, name='board-task-reject'),
    path('<uuid:pk>/end/', views.end_board_task, name='board-task-end'),

    # 投票
    path('<uuid:pk>/start-voting/', views.start_voting, name='task-start-voting'),
    path('<uuid:pk>/vote/', views.vote_task, name='task-vote'),

    # 钥匙玩法 - 手动时间调整和时间显示切换
    path('<uuid:pk>/manual-time-adjustment/', views.manual_time_adjustment, name='task-manual-time-adjustment'),
    path('<uuid:pk>/toggle-time-display/', views.toggle_time_display, name='task-toggle-time-display'),
    path('<uuid:pk>/use-detection-radar/', views.use_detection_radar, name='use-detection-radar'),
    path('<uuid:pk>/use-time-hourglass/', views.use_time_hourglass, name='use-time-hourglass'),
    path('use-blizzard-bottle/', views.use_blizzard_bottle, name='use-blizzard-bottle'),
    path('use-sun-bottle/', views.use_sun_bottle, name='use-sun-bottle'),

    # 冻结/解冻功能
    path('<uuid:pk>/freeze/', views.freeze_task, name='task-freeze'),
    path('<uuid:pk>/unfreeze/', views.unfreeze_task, name='task-unfreeze'),

    # 钥匙管理
    path('keys/my/', views.my_keys, name='my-keys'),

    # 自动完成过期任务和处理投票结果
    path('check-expired/', views.check_and_complete_expired_tasks, name='check-expired-tasks'),
    path('process-voting/', views.process_voting_results, name='process-voting-results'),

    # 任务时间线
    path('<uuid:pk>/timeline/', views.get_task_timeline, name='task-timeline'),

    # 小时奖励
    path('process-hourly-rewards/', views.process_hourly_rewards, name='process-hourly-rewards'),

    # 任务统计
    path('counts/', views.get_task_counts, name='task-counts'),

    # 任务板自动结算
    path('auto-settle-expired/', views.auto_settle_expired_board_tasks, name='auto-settle-expired-board-tasks'),

    # 置顶惩罚系统 - Pinning Penalty System
    path('<uuid:pk>/pin/', views.pin_task_owner, name='pin-task-owner'),
    path('<uuid:pk>/unpin/', views.unpin_task_owner, name='unpin-task-owner'),
    path('pinning-status/', views.get_pinning_status, name='get-pinning-status'),
    path('pinned-carousel/', views.get_pinned_tasks_for_carousel, name='get-pinned-tasks-carousel'),
]