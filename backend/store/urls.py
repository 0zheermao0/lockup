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
    path('note/<uuid:note_id>/view/', views.view_note, name='view-note'),
    path('note/<uuid:note_id>/edit/', views.edit_note, name='edit-note'),

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

    # 小金库相关
    path('treasury/<uuid:item_id>/deposit/', views.deposit_treasury_coins, name='deposit-treasury-coins'),
    path('treasury/<uuid:item_id>/withdraw/', views.withdraw_treasury_coins, name='withdraw-treasury-coins'),

    # 新增道具使用相关
    path('use-lucky-charm/', views.use_lucky_charm, name='use-lucky-charm'),
    path('use-energy-potion/', views.use_energy_potion, name='use-energy-potion'),
    path('use-time-anchor/', views.use_time_anchor, name='use-time-anchor'),
    path('use-exploration-compass/', views.use_exploration_compass, name='use-exploration-compass'),
    path('use-influence-crown/', views.use_influence_crown, name='use-influence-crown'),
    path('use-small-campfire/', views.use_small_campfire, name='use-small-campfire'),
    path('use-small-campfire-on-task/', views.use_small_campfire_on_task, name='use-small-campfire-on-task'),
    path('frozen-tasks/', views.get_frozen_tasks, name='get-frozen-tasks'),

    # 分享功能相关
    path('shared-tasks/', views.get_shared_tasks, name='get-shared-tasks'),

    # 撤销奖品预留
    path('items/<uuid:item_id>/revoke-prize/', views.revoke_item_prize, name='revoke-item-prize'),

    # 角斗场游戏
    path('arena-games/', views.create_arena_game, name='create-arena-game'),
    path('arena-games/list/', views.list_arena_games, name='list-arena-games'),
    path('arena-games/<uuid:game_id>/join/', views.join_arena_game, name='join-arena-game'),
    path('arena-games/<uuid:game_id>/enter/', views.enter_arena_audience, name='enter-arena-audience'),
    path('arena-games/<uuid:game_id>/vote/', views.vote_arena_game, name='vote-arena-game'),
    path('arena-games/<uuid:game_id>/settle/', views.settle_arena_game, name='settle-arena-game'),
    path('arena-games/<uuid:game_id>/status/', views.get_arena_game_status, name='arena-game-status'),
]