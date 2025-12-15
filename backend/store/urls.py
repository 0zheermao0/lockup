from django.urls import path
from . import views

urlpatterns = [
    # 商店相关
    path('items/', views.StoreItemListView.as_view(), name='store-items'),
    path('inventory/', views.UserInventoryView.as_view(), name='user-inventory'),

    # 购买相关
    path('purchase/', views.purchase_item, name='purchase-item'),
    path('upload-photo/', views.upload_photo_to_paper, name='upload-photo'),
    path('photo/<uuid:photo_id>/', views.view_photo, name='view-photo'),

    # 游戏相关
    path('time-wheel/', views.play_time_wheel, name='time-wheel'),
    path('games/', views.GameListCreateView.as_view(), name='games'),
    path('games/<uuid:game_id>/join/', views.join_game, name='join-game'),
    path('games/<uuid:game_id>/cancel/', views.cancel_game, name='cancel-game'),

    # 漂流瓶相关
    path('drift-bottles/', views.create_drift_bottle, name='create-drift-bottle'),

    # 探索相关
    path('bury-item/', views.bury_item, name='bury-item'),
    path('explore-zone/', views.explore_zone, name='explore-zone'),
    path('find-treasure/', views.find_treasure, name='find-treasure'),
    path('treasures/', views.BuriedTreasureListView.as_view(), name='buried-treasures'),
    path('zones/', views.get_available_zones, name='available-zones'),

    # 物品管理相关
    path('discard-item/', views.discard_item, name='discard-item'),
    path('return-item/', views.return_item_to_original_owner, name='return-item'),

    # 分享相关
    path('share-item/', views.create_share_link, name='create-share-link'),
    path('claim/<str:share_token>/', views.claim_shared_item, name='claim-shared-item'),

    # 万能钥匙相关
    path('use-universal-key/', views.use_universal_key, name='use-universal-key'),
    path('check-task-key-ownership/', views.check_task_key_ownership, name='check-task-key-ownership'),
    path('task-key-holder/<uuid:task_id>/', views.get_task_key_holder, name='get-task-key-holder'),
]