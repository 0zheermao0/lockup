"""
男娘幻城 — API 视图
所有"指令"均通过UI按钮触发对应API端点
"""
import logging
import math
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    GameZone, PlayerZonePresence, MimicProfile, PatrolProfile,
    TellEvent, CheckpointSession, CheckpointParticipant, InterrogationRequest,
    GrayMarketTransaction, GameControlTransfer, DetentionRecord,
    EncryptedChannel, EncryptedMessage, ZoneChatMessage,
    CrystalDeposit, PlayerCrystals, GameMarketRate,
    GameItem, PlayerGameInventory, ActiveDisguise, SmuggleRun,
)
from .serializers import (
    GameZoneSerializer, PlayerZonePresenceSerializer,
    MimicProfileSerializer, PatrolProfileSerializer, MimicProfilePublicSerializer,
    TellEventSerializer, CheckpointSessionSerializer, InterrogationRequestSerializer,
    GrayMarketTransactionSerializer, GameControlTransferSerializer,
    DetentionRecordSerializer, EncryptedChannelSerializer, EncryptedMessageSerializer,
    ZoneChatMessageSerializer, CrystalDepositSerializer, PlayerCrystalsSerializer,
    GameMarketRateSerializer, GameItemSerializer, PlayerGameInventorySerializer,
    ActiveDisguiseSerializer, SmuggleRunSerializer, GameProfileSerializer,
)
from .services import (
    TellService, CheckpointService, DetentionService, TransactionService,
    DisguiseService, CrystalService, ControlTransferService, ZoneService,
    ArmoryEncounterService, SewerEncounterService, CampAidService,
    _get_or_create_mimic_profile, _get_or_create_patrol_profile,
)

logger = logging.getLogger(__name__)


def _apply_deposit_respawn(deposits):
    """Apply time-based replenishment to deposits before returning them."""
    now = timezone.now()
    for deposit in deposits:
        if deposit.quantity < deposit.max_quantity and deposit.last_respawn_at:
            hours_elapsed = (now - deposit.last_respawn_at).total_seconds() / 3600
            gained = math.floor(hours_elapsed * deposit.respawn_rate_per_hour)
            if gained > 0:
                deposit.quantity = min(deposit.max_quantity, deposit.quantity + gained)
                deposit.last_respawn_at = now
                deposit.save(update_fields=['quantity', 'last_respawn_at'])


# ─────────────────────────────────────────────
# 档案与初始化
# ─────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def game_profile(request):
    """获取我的游戏档案（聚合视图）"""
    user = request.user
    _get_or_create_mimic_profile(user)

    serializer = GameProfileSerializer(user)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def choose_faction(request):
    """选择阵营（新玩家初始化）"""
    faction = request.data.get('faction')
    if faction not in ('mimic', 'patrol'):
        return Response({'error': '无效阵营'}, status=status.HTTP_400_BAD_REQUEST)

    user = request.user
    if faction == 'mimic':
        profile = _get_or_create_mimic_profile(user)
        profile.current_faction = 'mimic'
        profile.save(update_fields=['current_faction'])
    else:
        profile = _get_or_create_patrol_profile(user)
        profile.current_faction = 'patrol'
        profile.save(update_fields=['current_faction'])

    starting_zone = 'salon' if faction == 'mimic' else 'checkpoint'
    ZoneService.travel_to(user, starting_zone)

    return Response({'success': True, 'faction': faction})


# ─────────────────────────────────────────────
# 区域
# ─────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def zone_list(request):
    """区域列表（含在场玩家数）"""
    zones = GameZone.objects.all()
    serializer = GameZoneSerializer(zones, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def travel_to_zone(request):
    """移动到区域"""
    zone_name = request.data.get('zone')
    if not zone_name:
        return Response({'error': '请指定目标区域'}, status=status.HTTP_400_BAD_REQUEST)

    result = ZoneService.travel_to(request.user, zone_name)
    if not result['success']:
        return Response({'error': result['error']}, status=status.HTTP_400_BAD_REQUEST)

    return Response({'success': True, 'zone': GameZoneSerializer(result['zone']).data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def zone_players(request, zone_name):
    """区域内玩家列表"""
    try:
        zone = GameZone.objects.get(name=zone_name)
    except GameZone.DoesNotExist:
        return Response({'error': '区域不存在'}, status=status.HTTP_404_NOT_FOUND)

    presences = PlayerZonePresence.objects.filter(
        zone=zone, exited_at__isnull=True
    ).select_related('user')
    serializer = PlayerZonePresenceSerializer(presences, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def zone_chat(request, zone_name):
    """区域聊天记录（含破绽事件）"""
    try:
        zone = GameZone.objects.get(name=zone_name)
    except GameZone.DoesNotExist:
        return Response({'error': '区域不存在'}, status=status.HTTP_404_NOT_FOUND)

    messages = ZoneChatMessage.objects.filter(zone=zone).order_by('-created_at')[:50]
    serializer = ZoneChatMessageSerializer(reversed(list(messages)), many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def zone_speak(request, zone_name):
    """在区域发言（触发破绽评估）"""
    try:
        zone = GameZone.objects.get(name=zone_name)
    except GameZone.DoesNotExist:
        return Response({'error': '区域不存在'}, status=status.HTTP_404_NOT_FOUND)

    content = request.data.get('content', '').strip()
    if not content:
        return Response({'error': '发言内容不能为空'}, status=status.HTTP_400_BAD_REQUEST)

    result = ZoneService.speak(request.user, zone, content)
    if not result['success']:
        return Response({'error': result['error']}, status=status.HTTP_400_BAD_REQUEST)

    return Response({
        'success': True,
        'message': ZoneChatMessageSerializer(result['message']).data,
        'tells': TellEventSerializer(result['tells'], many=True).data,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def salon_rest(request):
    """安全区补觉（降低发毛值）"""
    user = request.user
    presence = PlayerZonePresence.objects.filter(
        user=user, exited_at__isnull=True
    ).select_related('zone').first()

    if not presence or presence.zone.name != 'salon':
        return Response({'error': '只能在闺房补觉'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        mimic = user.mimic_profile
        old_suppression = mimic.suppression_value
        mimic.suppression_value = max(0, mimic.suppression_value - 15)
        mimic.save(update_fields=['suppression_value'])
        return Response({
            'success': True,
            'suppression_before': old_suppression,
            'suppression_after': mimic.suppression_value,
        })
    except MimicProfile.DoesNotExist:
        return Response({'error': '档案不存在'}, status=status.HTTP_404_NOT_FOUND)


# ─────────────────────────────────────────────
# 安检口
# ─────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def checkpoint_session_view(request):
    """获取当前安检口会话"""
    try:
        zone = GameZone.objects.get(name='checkpoint')
    except GameZone.DoesNotExist:
        return Response({'error': '安检口区域未初始化'}, status=status.HTTP_404_NOT_FOUND)

    session = CheckpointService.get_or_create_active_session(zone)
    serializer = CheckpointSessionSerializer(session)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def checkpoint_inspect(request):
    """[UI按钮: 检查] 外观检查目标玩家"""
    target_id = request.data.get('target_id')
    session_id = request.data.get('session_id')

    if not target_id:
        return Response({'error': '请指定目标玩家'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        target = User.objects.get(id=target_id)
        session = CheckpointSession.objects.get(id=session_id)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)

    result = CheckpointService.inspect_player(request.user, target, session)
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def checkpoint_interrogate(request):
    """[UI按钮: 盘问] 向目标发起盘问请求"""
    target_id = request.data.get('target_id')
    session_id = request.data.get('session_id')
    question = request.data.get('question', '请说明你的来意。')

    if not target_id:
        return Response({'error': '请指定目标玩家'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        target = User.objects.get(id=target_id)
        session = CheckpointSession.objects.get(id=session_id)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)

    interrogation = CheckpointService.interrogate_player(
        request.user, target, session, question
    )
    return Response(InterrogationRequestSerializer(interrogation).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def checkpoint_interrogate_respond(request, interrogation_id):
    """被盘问者作答"""
    response_text = request.data.get('response', '').strip()
    if not response_text:
        return Response({'error': '回答不能为空'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        interrogation = InterrogationRequest.objects.get(
            id=interrogation_id, target=request.user
        )
    except InterrogationRequest.DoesNotExist:
        return Response({'error': '盘问请求不存在'}, status=status.HTTP_404_NOT_FOUND)

    if timezone.now() > interrogation.deadline:
        CheckpointService.expire_interrogation(interrogation)
        return Response({'error': '已超时，破绽已记录'}, status=status.HTTP_400_BAD_REQUEST)

    result = CheckpointService.respond_to_interrogation(interrogation, request.user, response_text)
    return Response({
        'success': True,
        'response_time': result['response_time'],
        'tells': TellEventSerializer(result['tells'], many=True).data,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def checkpoint_pat_down(request):
    """[UI按钮: 体检] 对目标进行体检（需嫌疑积分≥30）"""
    target_id = request.data.get('target_id')
    session_id = request.data.get('session_id')

    if not target_id:
        return Response({'error': '请指定目标玩家'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        target = User.objects.get(id=target_id)
        session = CheckpointSession.objects.get(id=session_id)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)

    result = CheckpointService.pat_down(request.user, target, session)

    if not result['success']:
        return Response({'error': result['error']}, status=status.HTTP_400_BAD_REQUEST)

    patrol_profile = _get_or_create_patrol_profile(request.user)
    response_data = {
        'success': True,
        'arrested': result.get('arrested', False),
        'false_accusation': result.get('false_accusation', False),
        'inspection_tokens_remaining': patrol_profile.inspection_tokens,
    }
    if result.get('arrested') and result.get('detention'):
        response_data['detention'] = DetentionRecordSerializer(result['detention']).data
        response_data['authority_gained'] = 10
        response_data['reputation_gained'] = 10
    elif result.get('false_accusation'):
        response_data['reputation_lost'] = 5

    return Response(response_data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def checkpoint_suspicion(request):
    """查看我的嫌疑积分图（小s专用）"""
    try:
        patrol_profile = request.user.patrol_profile
    except PatrolProfile.DoesNotExist:
        return Response({'error': '仅小s可查看'}, status=status.HTTP_403_FORBIDDEN)

    return Response({
        'suspicion_evidence': patrol_profile.suspicion_evidence,
        'inspection_tokens': patrol_profile.inspection_tokens,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def checkpoint_flee(request):
    """[UI按钮: 溜走] 小男娘溜走安检口队列"""
    session_id = request.data.get('session_id')
    if not session_id:
        return Response({'error': '请指定安检口会话'}, status=status.HTTP_400_BAD_REQUEST)
    result = CheckpointService.flee_checkpoint(request.user, session_id)
    if not result['success']:
        return Response({'error': result['error']}, status=status.HTTP_400_BAD_REQUEST)
    return Response(result)


# ─────────────────────────────────────────────
# 打点
# ─────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bribe_propose(request):
    """[UI按钮: 行贿] 向小s发起打点"""
    recipient_id = request.data.get('recipient_id')
    offer = request.data.get('offer', {})
    session_id = request.data.get('session_id')

    if not recipient_id:
        return Response({'error': '请指定目标'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        recipient = User.objects.get(id=recipient_id)
        session = CheckpointSession.objects.get(id=session_id) if session_id else None
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)

    result = TransactionService.propose_bribe(request.user, recipient, offer, session)
    if not result['success']:
        return Response({'error': result['error']}, status=status.HTTP_400_BAD_REQUEST)

    return Response({
        'success': True,
        'transaction': GrayMarketTransactionSerializer(result['transaction']).data,
        'channel': EncryptedChannelSerializer(result['channel']).data,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bribe_counter(request, transaction_id):
    """[UI按钮: 还价] 反提议"""
    new_offer = request.data.get('offer', {})

    try:
        tx = GrayMarketTransaction.objects.get(id=transaction_id)
    except GrayMarketTransaction.DoesNotExist:
        return Response({'error': '交易不存在'}, status=status.HTTP_404_NOT_FOUND)

    if request.user not in (tx.initiator, tx.recipient):
        return Response({'error': '无权操作'}, status=status.HTTP_403_FORBIDDEN)

    result = TransactionService.counter_offer(tx, request.user, new_offer)
    if not result['success']:
        return Response({'error': result['error']}, status=status.HTTP_400_BAD_REQUEST)

    return Response({'success': True, 'transaction': GrayMarketTransactionSerializer(tx).data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bribe_accept(request, transaction_id):
    """[UI按钮: 接受打点] 小s接受打点"""
    try:
        tx = GrayMarketTransaction.objects.get(
            id=transaction_id, recipient=request.user, transaction_type='bribe'
        )
    except GrayMarketTransaction.DoesNotExist:
        return Response({'error': '交易不存在'}, status=status.HTTP_404_NOT_FOUND)

    result = TransactionService.accept_bribe(tx, request.user)
    if not result['success']:
        return Response({'error': result['error']}, status=status.HTTP_400_BAD_REQUEST)

    return Response({'success': True})


# ─────────────────────────────────────────────
# 威胁
# ─────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def extort_demand(request):
    """[UI按钮: 威胁] 向嫌疑目标发出暗示"""
    target_id = request.data.get('target_id')
    demand = request.data.get('demand', {})
    session_id = request.data.get('session_id')

    if not target_id:
        return Response({'error': '请指定目标'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        target = User.objects.get(id=target_id)
        session = CheckpointSession.objects.get(id=session_id) if session_id else None
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)

    result = TransactionService.propose_extortion(request.user, target, demand, session)
    if not result['success']:
        return Response({'error': result['error']}, status=status.HTTP_400_BAD_REQUEST)

    return Response({
        'success': True,
        'transaction': GrayMarketTransactionSerializer(result['transaction']).data,
        'channel': EncryptedChannelSerializer(result['channel']).data,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def extort_pay(request, transaction_id):
    """[UI按钮: 支付威胁] 支付威胁要求"""
    try:
        tx = GrayMarketTransaction.objects.get(
            id=transaction_id, recipient=request.user, transaction_type='extortion'
        )
    except GrayMarketTransaction.DoesNotExist:
        return Response({'error': '威胁请求不存在'}, status=status.HTTP_404_NOT_FOUND)

    result = TransactionService.pay_extortion(tx, request.user)
    if not result['success']:
        return Response({'error': result['error']}, status=status.HTTP_400_BAD_REQUEST)

    return Response({'success': True})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def extort_refuse(request, transaction_id):
    """[UI按钮: 拒绝威胁] 拒绝威胁"""
    try:
        tx = GrayMarketTransaction.objects.get(
            id=transaction_id, recipient=request.user, transaction_type='extortion'
        )
    except GrayMarketTransaction.DoesNotExist:
        return Response({'error': '威胁请求不存在'}, status=status.HTTP_404_NOT_FOUND)

    tx.status = 'rejected'
    tx.save(update_fields=['status'])
    return Response({'success': True})


# ─────────────────────────────────────────────
# 双边交易
# ─────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trade_propose(request):
    """[UI按钮: 发起交易] 双边交易提议"""
    recipient_id = request.data.get('recipient_id')
    offer_a = request.data.get('offer_a', {})

    if not recipient_id:
        return Response({'error': '请指定交易对象'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        recipient = User.objects.get(id=recipient_id)
    except Exception:
        return Response({'error': '玩家不存在'}, status=status.HTTP_404_NOT_FOUND)

    result = TransactionService.propose_trade(request.user, recipient, offer_a)
    return Response({
        'success': True,
        'transaction': GrayMarketTransactionSerializer(result['transaction']).data,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trade_accept(request, transaction_id):
    """[UI按钮: 确认交易] 接受双边交易"""
    try:
        tx = GrayMarketTransaction.objects.get(
            id=transaction_id, recipient=request.user, transaction_type='trade'
        )
    except GrayMarketTransaction.DoesNotExist:
        return Response({'error': '交易不存在'}, status=status.HTTP_404_NOT_FOUND)

    offer_b = request.data.get('offer_b', {})
    tx.offer_from_recipient = offer_b
    tx.status = 'accepted'
    tx.save(update_fields=['offer_from_recipient', 'status'])

    result = TransactionService.complete_trade(tx)
    if not result['success']:
        return Response({'error': result.get('error', '交易失败')}, status=status.HTTP_400_BAD_REQUEST)

    return Response({'success': True})


# ─────────────────────────────────────────────
# 加密频道
# ─────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def channel_messages(request, channel_id):
    """获取加密频道消息（长轮询友好）"""
    try:
        channel = EncryptedChannel.objects.get(id=channel_id)
    except EncryptedChannel.DoesNotExist:
        return Response({'error': '频道不存在'}, status=status.HTTP_404_NOT_FOUND)

    if request.user not in (channel.participant_a, channel.participant_b):
        return Response({'error': '无权访问'}, status=status.HTTP_403_FORBIDDEN)

    since = request.query_params.get('since')
    messages = channel.messages.all()
    if since:
        messages = messages.filter(created_at__gt=since)

    serializer = EncryptedMessageSerializer(messages, many=True)
    return Response({
        'channel_id': str(channel.id),
        'is_active': channel.is_active,
        'messages': serializer.data,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def channel_send(request, channel_id):
    """发送加密频道消息"""
    try:
        channel = EncryptedChannel.objects.get(id=channel_id, is_active=True)
    except EncryptedChannel.DoesNotExist:
        return Response({'error': '频道不存在或已关闭'}, status=status.HTTP_404_NOT_FOUND)

    if request.user not in (channel.participant_a, channel.participant_b):
        return Response({'error': '无权访问'}, status=status.HTTP_403_FORBIDDEN)

    content = request.data.get('content', '').strip()
    if not content:
        return Response({'error': '消息不能为空'}, status=status.HTTP_400_BAD_REQUEST)

    msg = EncryptedMessage.objects.create(
        channel=channel,
        sender=request.user,
        content=content,
    )
    return Response(EncryptedMessageSerializer(msg).data)


# ─────────────────────────────────────────────
# 收押
# ─────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def detention_my(request):
    """获取我的收押状态"""
    detention = DetentionRecord.objects.filter(
        prisoner=request.user, status='active'
    ).select_related('captor', 'control_transfer').first()

    if not detention:
        return Response({'detained': False})

    return Response({
        'detained': True,
        'detention': DetentionRecordSerializer(detention).data,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def detention_charm_warden(request, detention_id):
    """[UI按钮: 哄骗看守] 尝试哄骗看守"""
    try:
        detention = DetentionRecord.objects.get(
            id=detention_id, prisoner=request.user, status='active'
        )
    except DetentionRecord.DoesNotExist:
        return Response({'error': '收押记录不存在'}, status=status.HTTP_404_NOT_FOUND)

    result = DetentionService.charm_warden(request.user, detention)
    if not result['success']:
        return Response({'error': result['error']}, status=status.HTTP_400_BAD_REQUEST)

    return Response(result)


# ─────────────────────────────────────────────
# 锁控制权
# ─────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def control_transfers_list(request):
    """我持有的锁控制权列表"""
    transfers = GameControlTransfer.objects.filter(
        grantee=request.user, is_active=True
    ).select_related('lock_task', 'grantor')
    serializer = GameControlTransferSerializer(transfers, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def control_transfer_add_time(request, transfer_id):
    """[UI按钮: 加时] 对囚犯LockTask加时"""
    try:
        transfer = GameControlTransfer.objects.get(
            id=transfer_id, grantee=request.user, is_active=True
        )
    except GameControlTransfer.DoesNotExist:
        return Response({'error': '控制权不存在'}, status=status.HTTP_404_NOT_FOUND)

    minutes = request.data.get('minutes', 60)
    result = ControlTransferService.add_time(transfer, request.user, int(minutes))
    if not result['success']:
        return Response({'error': result['error']}, status=status.HTTP_400_BAD_REQUEST)

    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def control_transfer_freeze(request, transfer_id):
    """[UI按钮: 冻结] 冻结囚犯LockTask"""
    try:
        transfer = GameControlTransfer.objects.get(
            id=transfer_id, grantee=request.user, is_active=True
        )
    except GameControlTransfer.DoesNotExist:
        return Response({'error': '控制权不存在'}, status=status.HTTP_404_NOT_FOUND)

    result = ControlTransferService.freeze(transfer, request.user)
    if not result['success']:
        return Response({'error': result['error']}, status=status.HTTP_400_BAD_REQUEST)

    return Response(result)


# ─────────────────────────────────────────────
# 市场与收集
# ─────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def market_rates(request):
    """当前市场价格"""
    rates = GameMarketRate.objects.all()
    serializer = GameMarketRateSerializer(rates, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def market_buy(request):
    """[UI按钮: 购买] 购买游戏道具"""
    item_slug = request.data.get('item_slug')
    quantity = int(request.data.get('quantity', 1))

    if not item_slug:
        return Response({'error': '请指定道具'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        item = GameItem.objects.get(slug=item_slug, is_active=True)
        rate = GameMarketRate.objects.get(item_slug=item_slug)
    except (GameItem.DoesNotExist, GameMarketRate.DoesNotExist):
        return Response({'error': '道具不存在或未上架'}, status=status.HTTP_404_NOT_FOUND)

    total_cost = rate.current_price_crystals * quantity

    try:
        player_crystals = request.user.crystals
        if player_crystals.purified_crystals < total_cost:
            return Response(
                {'error': f'提纯刀具不足（需要{total_cost}，当前{player_crystals.purified_crystals}）'},
                status=status.HTTP_400_BAD_REQUEST
            )
        player_crystals.purified_crystals -= total_cost
        player_crystals.save(update_fields=['purified_crystals'])
    except PlayerCrystals.DoesNotExist:
        return Response({'error': '刀具余额不足'}, status=status.HTTP_400_BAD_REQUEST)

    inv, _ = PlayerGameInventory.objects.get_or_create(
        user=request.user, item=item,
        defaults={'quantity': 0}
    )
    inv.quantity += quantity
    inv.save(update_fields=['quantity'])

    rate.units_traded_last_period += quantity
    rate.demand_pressure = min(3.0, rate.demand_pressure + 0.05 * quantity)
    rate.save(update_fields=['units_traded_last_period', 'demand_pressure'])

    return Response({
        'success': True,
        'item': GameItemSerializer(item).data,
        'quantity': quantity,
        'cost': total_cost,
        'crystals_remaining': player_crystals.purified_crystals,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ruins_deposits(request):
    """备皮间刀具矿点列表"""
    try:
        ruins = GameZone.objects.get(name='ruins')
    except GameZone.DoesNotExist:
        return Response({'error': '备皮间区域未初始化'}, status=status.HTTP_404_NOT_FOUND)

    deposits = list(CrystalDeposit.objects.filter(zone=ruins))
    _apply_deposit_respawn(deposits)
    serializer = CrystalDepositSerializer(deposits, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ruins_deep_deposits(request):
    """深处备皮间刀具矿点列表"""
    try:
        ruins_deep = GameZone.objects.get(name='ruins_deep')
    except GameZone.DoesNotExist:
        return Response({'error': '深处备皮间区域未初始化'}, status=status.HTTP_404_NOT_FOUND)

    deposits = list(CrystalDeposit.objects.filter(zone=ruins_deep))
    _apply_deposit_respawn(deposits)
    serializer = CrystalDepositSerializer(deposits, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ruins_outer_deposits(request):
    """外围备皮间刀具矿点列表"""
    try:
        ruins_outer = GameZone.objects.get(name='ruins_outer')
    except GameZone.DoesNotExist:
        return Response({'error': '外围备皮间区域未初始化'}, status=status.HTTP_404_NOT_FOUND)

    deposits = list(CrystalDeposit.objects.filter(zone=ruins_outer))
    _apply_deposit_respawn(deposits)
    serializer = CrystalDepositSerializer(deposits, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ruins_harvest(request):
    """[UI按钮: 收集] 收集刀具"""
    deposit_id = request.data.get('deposit_id')
    if not deposit_id:
        return Response({'error': '请指定矿点'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        deposit = CrystalDeposit.objects.get(id=deposit_id)
    except CrystalDeposit.DoesNotExist:
        return Response({'error': '矿点不存在'}, status=status.HTTP_404_NOT_FOUND)

    result = CrystalService.harvest(request.user, deposit)
    if not result['success']:
        return Response({'error': result['error']}, status=status.HTTP_400_BAD_REQUEST)

    return Response(result)


# ─────────────────────────────────────────────
# 背包与伪装
# ─────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def inventory_list(request):
    """我的游戏背包"""
    inventory = PlayerGameInventory.objects.filter(
        user=request.user
    ).select_related('item')
    serializer = PlayerGameInventorySerializer(inventory, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def equip_item(request):
    """[UI按钮: 装备] 装备伪装道具"""
    item_id = request.data.get('item_id')
    slot = request.data.get('slot', 'inner')

    try:
        inv = PlayerGameInventory.objects.get(user=request.user, item_id=item_id)
        item = inv.item
    except PlayerGameInventory.DoesNotExist:
        return Response({'error': '道具不在背包中'}, status=status.HTTP_404_NOT_FOUND)

    disguise, _ = ActiveDisguise.objects.get_or_create(user=request.user)

    if slot == 'outer':
        disguise.outer_layer_item = item
        disguise.save(update_fields=['outer_layer_item'])
    else:
        disguise.inner_items.add(item)

    DisguiseService.update_disguise_stats(request.user)
    return Response({
        'success': True,
        'disguise': ActiveDisguiseSerializer(disguise).data,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def unequip_item(request):
    """[UI按钮: 卸下] 卸下伪装道具"""
    item_id = request.data.get('item_id')
    slot = request.data.get('slot', 'inner')

    try:
        item = GameItem.objects.get(id=item_id)
        disguise = request.user.active_disguise
    except (GameItem.DoesNotExist, ActiveDisguise.DoesNotExist):
        return Response({'error': '道具或伪装不存在'}, status=status.HTTP_404_NOT_FOUND)

    if slot == 'outer':
        disguise.outer_layer_item = None
        disguise.save(update_fields=['outer_layer_item'])
    else:
        disguise.inner_items.remove(item)

    DisguiseService.update_disguise_stats(request.user)
    return Response({'success': True})


# ─────────────────────────────────────────────
# 储物柜遭遇战
# ─────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def armory_encounter_check(request):
    """进入储物柜后检查是否触发遭遇"""
    result = ArmoryEncounterService.check_for_encounter(request.user)
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def armory_toll_demand(request):
    """[小s] 向储物柜中的小男娘索取通行费"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    target_id = request.data.get('target_id')
    crystals = request.data.get('crystals', 30)
    if not target_id:
        return Response({'error': '请指定目标玩家'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        target = User.objects.get(id=target_id)
    except User.DoesNotExist:
        return Response({'error': '目标玩家不存在'}, status=status.HTTP_404_NOT_FOUND)
    result = ArmoryEncounterService.initiate_toll_demand(request.user, target, crystals)
    if not result['success']:
        return Response({'error': result['error']}, status=status.HTTP_400_BAD_REQUEST)
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def armory_toll_pay(request, transaction_id):
    """[小男娘] 支付储物柜通行费"""
    try:
        tx = GrayMarketTransaction.objects.get(id=transaction_id, transaction_type='armory_toll')
    except GrayMarketTransaction.DoesNotExist:
        return Response({'error': '交易不存在'}, status=status.HTTP_404_NOT_FOUND)
    result = ArmoryEncounterService.pay_toll(tx, request.user)
    if not result['success']:
        return Response({'error': result['error']}, status=status.HTTP_400_BAD_REQUEST)
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def armory_toll_resist(request, transaction_id):
    """[小男娘] 抵抗储物柜通行费索取"""
    try:
        tx = GrayMarketTransaction.objects.get(id=transaction_id, transaction_type='armory_toll')
    except GrayMarketTransaction.DoesNotExist:
        return Response({'error': '交易不存在'}, status=status.HTTP_404_NOT_FOUND)
    result = ArmoryEncounterService.resist_toll(tx, request.user)
    if not result['success']:
        return Response({'error': result['error']}, status=status.HTTP_400_BAD_REQUEST)
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def armory_flee(request):
    """[小男娘] 溜走储物柜（+15压制，-3纯净，移至闺房）"""
    result = ArmoryEncounterService.flee_armory(request.user)
    return Response(result)


# ─────────────────────────────────────────────
# 下水道遭遇
# ─────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sewer_encounter_check(request):
    """进入管道后检查是否触发遭遇"""
    result = SewerEncounterService.check_for_encounter(request.user)
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sewer_encounter_demand(request):
    """[小s] 在管道中强制收缴小男娘备皮刀"""
    target_id = request.data.get('target_id')
    amount = request.data.get('amount', 20)
    if not target_id:
        return Response({'error': '请指定目标玩家'}, status=status.HTTP_400_BAD_REQUEST)
    result = SewerEncounterService.sewer_demand(request.user, target_id, amount)
    if not result['success']:
        return Response({'error': result['error']}, status=status.HTTP_400_BAD_REQUEST)
    return Response(result)


# ─────────────────────────────────────────────
# 黑市洗白
# ─────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bm_launder(request):
    """[黑市] 将备皮刀以70%转换率洗白为脱毛仪"""
    amount = request.data.get('amount')
    if not amount:
        return Response({'error': '请指定洗白数量'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        amount = int(amount)
    except (ValueError, TypeError):
        return Response({'error': '数量格式错误'}, status=status.HTTP_400_BAD_REQUEST)
    result = CrystalService.launder_crystals(request.user, amount)
    if not result['success']:
        return Response({'error': result['error']}, status=status.HTTP_400_BAD_REQUEST)
    return Response(result)


# ─────────────────────────────────────────────
# 更衣室互助
# ─────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def camp_share_food(request):
    """[营地] 分享食物给目标玩家"""
    recipient_id = request.data.get('recipient_id')
    if not recipient_id:
        return Response({'error': '请指定目标玩家'}, status=status.HTTP_400_BAD_REQUEST)
    result = CampAidService.share_food(request.user, recipient_id)
    if not result['success']:
        return Response({'error': result['error']}, status=status.HTTP_400_BAD_REQUEST)
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def camp_watch_start(request):
    """[营地] 开始站岗警戒（10分钟）"""
    result = CampAidService.start_watch(request.user)
    if not result['success']:
        return Response({'error': result['error']}, status=status.HTTP_400_BAD_REQUEST)
    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def camp_watch_active(request):
    """[营地] 查看当前值班哨兵列表"""
    from .models import GameZone
    try:
        camp_zone = GameZone.objects.get(name='abandoned_camp')
    except GameZone.DoesNotExist:
        return Response([])
    watchers = CampAidService.get_active_watches(camp_zone)
    return Response(watchers)
