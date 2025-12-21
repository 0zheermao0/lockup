from django.urls import path
from . import views

app_name = 'posts'

urlpatterns = [
    # 动态相关
    path('', views.PostListCreateView.as_view(), name='post-list-create'),
    path('<str:post_id>/', views.get_post_detail, name='post-detail'),
    path('<str:post_id>/delete/', views.delete_post, name='delete-post'),
    path('stats/', views.post_stats, name='post-stats'),

    # 点赞相关
    path('<str:post_id>/like/', views.toggle_post_like, name='toggle-post-like'),

    # 评论相关
    path('<str:post_id>/comments/', views.create_comment, name='create-comment'),
    path('<str:post_id>/comments/list/', views.get_post_comments, name='get-post-comments'),
    path('comments/<str:comment_id>/replies/', views.get_comment_replies, name='get-comment-replies'),
    path('comments/<str:comment_id>/like/', views.toggle_comment_like, name='toggle-comment-like'),

    # 打卡投票相关
    path('<str:pk>/vote/', views.vote_checkin_post, name='vote-checkin-post'),
]