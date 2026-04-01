"""
男娘幻城 — Celery 后台任务
"""
import logging
import random
from datetime import timedelta
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name='phantom_city.generate_tell_events')
def generate_tell_events():
    """每15分钟：为安检口内玩家评估并生成破绽事件"""
    from .models import GameZone, PlayerZonePresence, CheckpointSession
    from .services import TellService

    try:
        checkpoint_zone = GameZone.objects.get(name='checkpoint')
    except GameZone.DoesNotExist:
        return

    active_session = CheckpointSession.objects.filter(
        zone=checkpoint_zone, status='active'
    ).first()

    if not active_session:
        return

    # 获取安检口内的小男娘
    presences = PlayerZonePresence.objects.filter(
        zone=checkpoint_zone, exited_at__isnull=True
    ).select_related('user')

    count = 0
    for presence in presences:
        tells = TellService.evaluate_tells(
            presence.user,
            checkpoint_zone,
            action_type='presence',
            session=active_session,
        )
        count += len(tells)

    logger.info(f'破绽评估完成，共生成 {count} 条破绽事件')
    return count


@shared_task(name='phantom_city.accumulate_suppression')
def accumulate_suppression():
    """每30分钟：伪装中玩家发毛值+3"""
    from .models import MimicProfile
    from users.models import Notification

    profiles = MimicProfile.objects.filter(is_disguised=True)
    updated = 0

    for profile in profiles:
        old_value = profile.suppression_value
        profile.suppression_value = min(100, profile.suppression_value + 3)
        profile.save(update_fields=['suppression_value'])
        updated += 1

        # 发毛值临界警告（>85）
        if old_value <= 85 and profile.suppression_value > 85:
            try:
                Notification.create_notification(
                    recipient=profile.user,
                    notification_type='game_suppression_critical',
                    title='发毛值临界',
                    message=f'你的发毛值已达到 {profile.suppression_value}，即将触发文字故障！请尽快前往闺房补觉。',
                    priority='urgent',
                )
            except Exception as e:
                logger.warning(f'发送压抑警告通知失败: {e}')

    logger.info(f'发毛值累积完成，共更新 {updated} 个档案')
    return updated


@shared_task(name='phantom_city.decay_depilation_charge')
def decay_depilation_charge():
    """每60分钟：脱毛仪电量衰减（备皮间-5，其他-2）"""
    from .models import MimicProfile, PlayerZonePresence, GameZone
    from users.models import Notification

    try:
        ruins_zone = GameZone.objects.get(name='ruins')
    except GameZone.DoesNotExist:
        ruins_zone = None

    profiles = MimicProfile.objects.filter(depilation_charge__gt=0)
    updated = 0

    for profile in profiles:
        # 检查是否在备皮间
        in_ruins = ruins_zone and PlayerZonePresence.objects.filter(
            user=profile.user,
            zone=ruins_zone,
            exited_at__isnull=True,
        ).exists()

        decay = 5 if in_ruins else 2
        old_charge = profile.depilation_charge
        profile.depilation_charge = max(0, profile.depilation_charge - decay)
        profile.save(update_fields=['depilation_charge'])
        updated += 1

        # 电量不足警告（首次降至30以下）
        if old_charge >= 30 and profile.depilation_charge < 30:
            try:
                Notification.create_notification(
                    recipient=profile.user,
                    notification_type='game_depilation_low',
                    title='脱毛仪电量不足',
                    message=f'脱毛仪电量已降至 {profile.depilation_charge}，体毛破绽将被激活！',
                    priority='high',
                )
            except Exception as e:
                logger.warning(f'发送电量警告通知失败: {e}')

    logger.info(f'脱毛仪电量衰减完成，共更新 {updated} 个档案')
    return updated


@shared_task(name='phantom_city.expire_control_transfers')
def expire_control_transfers():
    """每10分钟：到期控制权撤销"""
    from .models import GameControlTransfer
    from users.models import Notification

    now = timezone.now()
    expired = GameControlTransfer.objects.filter(
        is_active=True,
        expires_at__lte=now,
    )

    count = 0
    for transfer in expired:
        transfer.is_active = False
        transfer.revoked_at = now
        transfer.revoked_reason = 'expired'
        transfer.save(update_fields=['is_active', 'revoked_at', 'revoked_reason'])
        count += 1

        # 通知受让方
        try:
            Notification.create_notification(
                recipient=transfer.grantee,
                notification_type='game_control_transfer_expired',
                title='锁控制权到期',
                message=f'你对 {transfer.grantor.username} 锁的控制权已到期。',
            )
        except Exception as e:
            logger.warning(f'发送控制权到期通知失败: {e}')

    logger.info(f'控制权到期处理完成，共撤销 {count} 条记录')
    return count


@shared_task(name='phantom_city.process_detention_releases')
def process_detention_releases():
    """每5分钟：到期收押自动释放"""
    from .models import DetentionRecord
    from .services import DetentionService

    now = timezone.now()
    expired_detentions = DetentionRecord.objects.filter(
        status='active',
        release_at__lte=now,
    )

    count = 0
    for detention in expired_detentions:
        try:
            DetentionService.release(detention, reason='released_timeout')
            count += 1
        except Exception as e:
            logger.error(f'释放收押 {detention.id} 失败: {e}')

    logger.info(f'收押到期释放完成，共释放 {count} 名囚犯')
    return count


@shared_task(name='phantom_city.regen_authority_values')
def regen_authority_values():
    """每60分钟：小s管控力自然回复+2"""
    from .models import PatrolProfile

    profiles = PatrolProfile.objects.filter(authority_value__lt=100)
    count = 0

    for profile in profiles:
        profile.authority_value = min(100, profile.authority_value + 2)
        profile.save(update_fields=['authority_value'])
        count += 1

    logger.info(f'管控力回复完成，共更新 {count} 个档案')
    return count


@shared_task(name='phantom_city.respawn_crystals')
def respawn_crystals():
    """每60分钟：刀具矿点补充"""
    from .models import CrystalDeposit

    deposits = CrystalDeposit.objects.all()
    count = 0

    for deposit in deposits:
        if deposit.quantity < deposit.max_quantity:
            deposit.quantity = min(
                deposit.max_quantity,
                deposit.quantity + deposit.respawn_rate_per_hour
            )
            deposit.last_respawn_at = timezone.now()
            deposit.save(update_fields=['quantity', 'last_respawn_at'])
            count += 1

    logger.info(f'刀具矿点补充完成，共更新 {count} 个矿点')
    return count



@shared_task(name='phantom_city.recalculate_market_rates')
def recalculate_market_rates():
    """每6小时：根据供需重算市场价格"""
    from .services import CrystalService
    CrystalService.recalculate_market_rates()
    logger.info('市场价格重算完成')


@shared_task(name='phantom_city.generate_checkpoint_npcs')
def generate_checkpoint_npcs():
    """每2小时：刷新安检口NPC队列"""
    from .models import GameZone, CheckpointSession
    from .services import CheckpointService

    try:
        checkpoint_zone = GameZone.objects.get(name='checkpoint')
    except GameZone.DoesNotExist:
        return

    active_session = CheckpointSession.objects.filter(
        zone=checkpoint_zone, status='active'
    ).first()

    if active_session:
        CheckpointService._generate_npc_queue(active_session)
        logger.info(f'安检口NPC队列已刷新，会话 {active_session.id}')


@shared_task(name='phantom_city.cleanup_expired_channels')
def cleanup_expired_channels():
    """每2小时：清理已结束的加密频道消息"""
    from .models import EncryptedChannel, EncryptedMessage

    cutoff = timezone.now() - timedelta(hours=24)
    closed_channels = EncryptedChannel.objects.filter(
        is_active=False,
        closed_at__lte=cutoff,
    )

    count = 0
    for channel in closed_channels:
        deleted, _ = EncryptedMessage.objects.filter(channel=channel).delete()
        count += deleted

    logger.info(f'加密频道清理完成，共删除 {count} 条消息')
    return count


@shared_task(name='phantom_city.reset_inspection_tokens')
def reset_inspection_tokens():
    """每天午夜：重置小s配额"""
    from .models import PatrolProfile
    from django.utils import timezone

    today = timezone.now().date()
    profiles = PatrolProfile.objects.exclude(inspection_tokens_last_reset=today)
    count = 0

    for profile in profiles:
        profile.inspection_tokens = 10
        profile.inspection_tokens_last_reset = today
        profile.save(update_fields=['inspection_tokens', 'inspection_tokens_last_reset'])
        count += 1

    logger.info(f'配额重置完成，共重置 {count} 个档案')
    return count
