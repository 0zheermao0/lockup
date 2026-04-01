"""
男娘幻城 — URL 路由配置
所有端点均通过 /api/game/ 前缀访问
"""
from django.urls import path
from . import views

urlpatterns = [
    # 档案与初始化
    path('profile/', views.game_profile, name='game-profile'),
    path('profile/faction/', views.choose_faction, name='game-choose-faction'),
    path('profile/rest/', views.salon_rest, name='game-salon-rest'),

    # 区域
    path('zones/', views.zone_list, name='game-zone-list'),
    path('zones/travel/', views.travel_to_zone, name='game-zone-travel'),
    path('zones/<str:zone_name>/players/', views.zone_players, name='game-zone-players'),
    path('zones/<str:zone_name>/chat/', views.zone_chat, name='game-zone-chat'),
    path('zones/<str:zone_name>/speak/', views.zone_speak, name='game-zone-speak'),

    # 安检口
    path('checkpoint/session/', views.checkpoint_session_view, name='game-checkpoint-session'),
    path('checkpoint/inspect/', views.checkpoint_inspect, name='game-checkpoint-inspect'),
    path('checkpoint/interrogate/', views.checkpoint_interrogate, name='game-checkpoint-interrogate'),
    path('checkpoint/interrogate/<uuid:interrogation_id>/respond/', views.checkpoint_interrogate_respond, name='game-checkpoint-respond'),
    path('checkpoint/pat_down/', views.checkpoint_pat_down, name='game-checkpoint-pat-down'),
    path('checkpoint/suspicion/', views.checkpoint_suspicion, name='game-checkpoint-suspicion'),
    path('checkpoint/flee/', views.checkpoint_flee, name='game-checkpoint-flee'),

    # 打点
    path('bribe/propose/', views.bribe_propose, name='game-bribe-propose'),
    path('bribe/<uuid:transaction_id>/counter/', views.bribe_counter, name='game-bribe-counter'),
    path('bribe/<uuid:transaction_id>/accept/', views.bribe_accept, name='game-bribe-accept'),

    # 威胁
    path('extort/demand/', views.extort_demand, name='game-extort-demand'),
    path('extort/<uuid:transaction_id>/pay/', views.extort_pay, name='game-extort-pay'),
    path('extort/<uuid:transaction_id>/refuse/', views.extort_refuse, name='game-extort-refuse'),

    # 双边交易
    path('trade/propose/', views.trade_propose, name='game-trade-propose'),
    path('trade/<uuid:transaction_id>/accept/', views.trade_accept, name='game-trade-accept'),

    # 加密频道
    path('channel/<uuid:channel_id>/messages/', views.channel_messages, name='game-channel-messages'),
    path('channel/<uuid:channel_id>/send/', views.channel_send, name='game-channel-send'),

    # 拘禁
    path('detention/my/', views.detention_my, name='game-detention-my'),
    path('detention/<uuid:detention_id>/charm_warden/', views.detention_charm_warden, name='game-detention-charm'),

    # 锁控制权
    path('control-transfers/', views.control_transfers_list, name='game-control-transfers'),
    path('control-transfers/<uuid:transfer_id>/add_time/', views.control_transfer_add_time, name='game-control-add-time'),
    path('control-transfers/<uuid:transfer_id>/freeze/', views.control_transfer_freeze, name='game-control-freeze'),

    # 市场与采集
    path('market/rates/', views.market_rates, name='game-market-rates'),
    path('market/buy/', views.market_buy, name='game-market-buy'),
    path('ruins/deposits/', views.ruins_deposits, name='game-ruins-deposits'),
    path('ruins/harvest/', views.ruins_harvest, name='game-ruins-harvest'),
    path('ruins-deep/deposits/', views.ruins_deep_deposits, name='game-ruins-deep-deposits'),
    path('ruins-outer/deposits/', views.ruins_outer_deposits, name='game-ruins-outer-deposits'),

    # 背包与伪装
    path('inventory/', views.inventory_list, name='game-inventory'),
    path('inventory/equip/', views.equip_item, name='game-equip'),
    path('inventory/unequip/', views.unequip_item, name='game-unequip'),

    # 储物柜遭遇战
    path('armory/encounter/check/', views.armory_encounter_check, name='game-armory-encounter-check'),
    path('armory/toll/demand/', views.armory_toll_demand, name='game-armory-toll-demand'),
    path('armory/toll/<uuid:transaction_id>/pay/', views.armory_toll_pay, name='game-armory-toll-pay'),
    path('armory/toll/<uuid:transaction_id>/resist/', views.armory_toll_resist, name='game-armory-toll-resist'),
    path('armory/flee/', views.armory_flee, name='game-armory-flee'),

    # 下水道遭遇
    path('sewer/encounter/check/', views.sewer_encounter_check, name='game-sewer-encounter-check'),
    path('sewer/encounter/demand/', views.sewer_encounter_demand, name='game-sewer-encounter-demand'),

    # 黑市洗白
    path('black-market/launder/', views.bm_launder, name='game-bm-launder'),

    # 更衣室互助
    path('camp/share-food/', views.camp_share_food, name='game-camp-share-food'),
    path('camp/watch/start/', views.camp_watch_start, name='game-camp-watch-start'),
    path('camp/watch/active/', views.camp_watch_active, name='game-camp-watch-active'),
]
