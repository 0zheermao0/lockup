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

    # 投票
    path('<uuid:pk>/vote/', views.vote_task, name='task-vote'),

    # 钥匙管理
    path('keys/my/', views.my_keys, name='my-keys'),

    # 自动完成过期任务
    path('check-expired/', views.check_and_complete_expired_tasks, name='check-expired-tasks'),

    # 任务时间线
    path('<uuid:pk>/timeline/', views.get_task_timeline, name='task-timeline'),
]