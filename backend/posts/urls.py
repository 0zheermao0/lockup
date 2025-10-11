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
    path('comments/<str:comment_id>/like/', views.toggle_comment_like, name='toggle-comment-like'),
]