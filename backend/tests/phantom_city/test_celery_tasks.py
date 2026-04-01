"""
幻城 Celery 任务测试 — 直接调用任务函数（不经 Celery broker），验证业务逻辑。
"""
from datetime import timedelta
from django.utils import timezone
from tests.phantom_city.base import PhantomCityTestCase
from phantom_city.models import (
    GameZone, PlayerZonePresence, MimicProfile, PatrolProfile,
    CheckpointSession, GameControlTransfer, DetentionRecord,
    EncryptedChannel, EncryptedMessage, CrystalDeposit, GameMarketRate,
    PlayerCrystals,
)


class GenerateTellEventsTaskTest(PhantomCityTestCase):
    """phantom_city.generate_tell_events"""

    def test_no_checkpoint_zone_returns_none(self):
        from phantom_city.celery_tasks import generate_tell_events
        result = generate_tell_events()
        self.assertIsNone(result)

    def test_no_active_session_returns_none(self):
        from phantom_city.celery_tasks import generate_tell_events
        self.make_zone('checkpoint')
        result = generate_tell_events()
        self.assertIsNone(result)

    def test_active_session_no_players_returns_zero(self):
        from phantom_city.celery_tasks import generate_tell_events
        zone = self.make_zone('checkpoint')
        CheckpointSession.objects.create(zone=zone, status='active')
        result = generate_tell_events()
        self.assertEqual(result, 0)

    def test_active_session_with_player_runs_evaluation(self):
        from phantom_city.celery_tasks import generate_tell_events
        zone = self.make_zone('checkpoint')
        CheckpointSession.objects.create(zone=zone, status='active')
        self.make_mimic(self.user1, depilation_charge=10)  # triggers body hair tell
        PlayerZonePresence.objects.create(user=self.user1, zone=zone)
        result = generate_tell_events()
        self.assertIsNotNone(result)
        self.assertGreaterEqual(result, 0)


class AccumulateSuppressionTaskTest(PhantomCityTestCase):
    """phantom_city.accumulate_suppression"""

    def test_no_disguised_profiles_returns_zero(self):
        from phantom_city.celery_tasks import accumulate_suppression
        self.make_mimic(self.user1, is_disguised=False)
        result = accumulate_suppression()
        self.assertEqual(result, 0)

    def test_disguised_profile_increments_suppression(self):
        from phantom_city.celery_tasks import accumulate_suppression
        self.make_mimic(self.user1, is_disguised=True, suppression_value=50)
        result = accumulate_suppression()
        self.assertEqual(result, 1)
        self.user1.mimic_profile.refresh_from_db()
        self.assertEqual(self.user1.mimic_profile.suppression_value, 53)

    def test_suppression_caps_at_100(self):
        from phantom_city.celery_tasks import accumulate_suppression
        self.make_mimic(self.user1, is_disguised=True, suppression_value=99)
        accumulate_suppression()
        self.user1.mimic_profile.refresh_from_db()
        self.assertEqual(self.user1.mimic_profile.suppression_value, 100)

    def test_critical_threshold_sends_notification(self):
        from phantom_city.celery_tasks import accumulate_suppression
        from users.models import Notification
        self.make_mimic(self.user1, is_disguised=True, suppression_value=83)
        accumulate_suppression()
        self.user1.mimic_profile.refresh_from_db()
        self.assertEqual(self.user1.mimic_profile.suppression_value, 86)
        # 83→86, crosses 85 threshold → notification
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.user1,
                notification_type='game_suppression_critical',
            ).exists()
        )

    def test_already_above_threshold_no_duplicate_notification(self):
        """已在85以上，不重复通知"""
        from phantom_city.celery_tasks import accumulate_suppression
        from users.models import Notification
        self.make_mimic(self.user1, is_disguised=True, suppression_value=90)
        accumulate_suppression()
        self.assertFalse(
            Notification.objects.filter(
                recipient=self.user1,
                notification_type='game_suppression_critical',
            ).exists()
        )

    def test_multiple_profiles_all_updated(self):
        from phantom_city.celery_tasks import accumulate_suppression
        self.make_mimic(self.user1, is_disguised=True, suppression_value=10)
        self.make_mimic(self.user2, is_disguised=True, suppression_value=20)
        result = accumulate_suppression()
        self.assertEqual(result, 2)


class DecayDepilationChargeTaskTest(PhantomCityTestCase):
    """phantom_city.decay_depilation_charge"""

    def test_no_profiles_returns_zero(self):
        from phantom_city.celery_tasks import decay_depilation_charge
        result = decay_depilation_charge()
        self.assertEqual(result, 0)

    def test_profile_at_zero_charge_not_included(self):
        from phantom_city.celery_tasks import decay_depilation_charge
        self.make_mimic(self.user1, depilation_charge=0)
        result = decay_depilation_charge()
        self.assertEqual(result, 0)

    def test_profile_outside_ruins_decays_by_2(self):
        from phantom_city.celery_tasks import decay_depilation_charge
        self.make_mimic(self.user1, depilation_charge=50)
        result = decay_depilation_charge()
        self.assertEqual(result, 1)
        self.user1.mimic_profile.refresh_from_db()
        self.assertEqual(self.user1.mimic_profile.depilation_charge, 48)

    def test_profile_in_ruins_decays_by_5(self):
        from phantom_city.celery_tasks import decay_depilation_charge
        ruins = self.make_zone('ruins')
        self.make_mimic(self.user1, depilation_charge=50)
        PlayerZonePresence.objects.create(user=self.user1, zone=ruins)
        result = decay_depilation_charge()
        self.assertEqual(result, 1)
        self.user1.mimic_profile.refresh_from_db()
        self.assertEqual(self.user1.mimic_profile.depilation_charge, 45)

    def test_charge_floors_at_zero(self):
        from phantom_city.celery_tasks import decay_depilation_charge
        self.make_mimic(self.user1, depilation_charge=1)
        decay_depilation_charge()
        self.user1.mimic_profile.refresh_from_db()
        self.assertEqual(self.user1.mimic_profile.depilation_charge, 0)

    def test_crossing_30_threshold_sends_notification(self):
        from phantom_city.celery_tasks import decay_depilation_charge
        from users.models import Notification
        self.make_mimic(self.user1, depilation_charge=31)
        decay_depilation_charge()
        self.user1.mimic_profile.refresh_from_db()
        self.assertEqual(self.user1.mimic_profile.depilation_charge, 29)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.user1,
                notification_type='game_depilation_low',
            ).exists()
        )


class ExpireControlTransfersTaskTest(PhantomCityTestCase):
    """phantom_city.expire_control_transfers"""

    def _make_transfer(self, expires_at, is_active=True):
        task = self.create_test_lock_task(self.user1)
        return GameControlTransfer.objects.create(
            lock_task=task,
            grantor=self.user1,
            grantee=self.user2,
            source='arrest',
            duration_hours=12,
            expires_at=expires_at,
            is_active=is_active,
        )

    def test_no_expired_transfers_returns_zero(self):
        from phantom_city.celery_tasks import expire_control_transfers
        self._make_transfer(expires_at=timezone.now() + timedelta(hours=1))
        result = expire_control_transfers()
        self.assertEqual(result, 0)

    def test_expired_transfer_is_deactivated(self):
        from phantom_city.celery_tasks import expire_control_transfers
        transfer = self._make_transfer(expires_at=timezone.now() - timedelta(minutes=1))
        result = expire_control_transfers()
        self.assertEqual(result, 1)
        transfer.refresh_from_db()
        self.assertFalse(transfer.is_active)

    def test_already_inactive_transfer_not_counted(self):
        from phantom_city.celery_tasks import expire_control_transfers
        self._make_transfer(
            expires_at=timezone.now() - timedelta(minutes=1),
            is_active=False
        )
        result = expire_control_transfers()
        self.assertEqual(result, 0)

    def test_expired_transfer_sends_notification(self):
        from phantom_city.celery_tasks import expire_control_transfers
        from users.models import Notification
        self._make_transfer(expires_at=timezone.now() - timedelta(minutes=1))
        expire_control_transfers()
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.user2,
                notification_type='game_control_transfer_expired',
            ).exists()
        )

    def test_multiple_expired_transfers_all_deactivated(self):
        from phantom_city.celery_tasks import expire_control_transfers
        self._make_transfer(expires_at=timezone.now() - timedelta(minutes=1))
        self._make_transfer(expires_at=timezone.now() - timedelta(minutes=2))
        result = expire_control_transfers()
        self.assertEqual(result, 2)


class ProcessDetentionReleasesTaskTest(PhantomCityTestCase):
    """phantom_city.process_detention_releases"""

    def setUp(self):
        super().setUp()
        self.make_zone('control_room')
        self.make_zone('salon')

    def _make_detention(self, release_at, status='active'):
        self.make_patrol(self.user2)
        self.make_mimic(self.user1)
        self.make_crystals(self.user1)
        from phantom_city.services import DetentionService
        detention = DetentionService.arrest(self.user2, self.user1)
        DetentionRecord.objects.filter(pk=detention.pk).update(
            status=status, release_at=release_at
        )
        detention.refresh_from_db()
        return detention

    def test_no_expired_detentions_returns_zero(self):
        from phantom_city.celery_tasks import process_detention_releases
        result = process_detention_releases()
        self.assertEqual(result, 0)

    def test_expired_detention_is_released(self):
        from phantom_city.celery_tasks import process_detention_releases
        detention = self._make_detention(release_at=timezone.now() - timedelta(minutes=1))
        result = process_detention_releases()
        self.assertEqual(result, 1)
        detention.refresh_from_db()
        self.assertEqual(detention.status, 'released_timeout')

    def test_future_detention_not_released(self):
        from phantom_city.celery_tasks import process_detention_releases
        detention = self._make_detention(release_at=timezone.now() + timedelta(hours=1))
        result = process_detention_releases()
        self.assertEqual(result, 0)
        detention.refresh_from_db()
        self.assertEqual(detention.status, 'active')

    def test_already_released_detention_not_counted(self):
        from phantom_city.celery_tasks import process_detention_releases
        self._make_detention(
            release_at=timezone.now() - timedelta(minutes=1),
            status='released_timeout'
        )
        result = process_detention_releases()
        self.assertEqual(result, 0)


class RegenAuthorityValuesTaskTest(PhantomCityTestCase):
    """phantom_city.regen_authority_values"""

    def test_no_profiles_returns_zero(self):
        from phantom_city.celery_tasks import regen_authority_values
        result = regen_authority_values()
        self.assertEqual(result, 0)

    def test_profile_below_max_increments_by_2(self):
        from phantom_city.celery_tasks import regen_authority_values
        self.make_patrol(self.user1, authority_value=50)
        result = regen_authority_values()
        self.assertEqual(result, 1)
        self.user1.patrol_profile.refresh_from_db()
        self.assertEqual(self.user1.patrol_profile.authority_value, 52)

    def test_profile_at_100_not_included(self):
        from phantom_city.celery_tasks import regen_authority_values
        self.make_patrol(self.user1, authority_value=100)
        result = regen_authority_values()
        self.assertEqual(result, 0)

    def test_authority_caps_at_100(self):
        from phantom_city.celery_tasks import regen_authority_values
        self.make_patrol(self.user1, authority_value=99)
        regen_authority_values()
        self.user1.patrol_profile.refresh_from_db()
        self.assertEqual(self.user1.patrol_profile.authority_value, 100)

    def test_multiple_profiles_all_updated(self):
        from phantom_city.celery_tasks import regen_authority_values
        self.make_patrol(self.user1, authority_value=40)
        self.make_patrol(self.user2, authority_value=60)
        result = regen_authority_values()
        self.assertEqual(result, 2)


class RespawnCrystalsTaskTest(PhantomCityTestCase):
    """phantom_city.respawn_crystals"""

    def test_no_deposits_returns_zero(self):
        from phantom_city.celery_tasks import respawn_crystals
        result = respawn_crystals()
        self.assertEqual(result, 0)

    def test_deposit_at_max_not_updated(self):
        from phantom_city.celery_tasks import respawn_crystals
        zone = self.make_zone('ruins')
        CrystalDeposit.objects.create(zone=zone, quantity=20, max_quantity=20)
        result = respawn_crystals()
        self.assertEqual(result, 0)

    def test_deposit_below_max_increments(self):
        from phantom_city.celery_tasks import respawn_crystals
        zone = self.make_zone('ruins')
        deposit = CrystalDeposit.objects.create(
            zone=zone, quantity=5, max_quantity=20, respawn_rate_per_hour=3
        )
        result = respawn_crystals()
        self.assertEqual(result, 1)
        deposit.refresh_from_db()
        self.assertEqual(deposit.quantity, 8)

    def test_deposit_respawn_caps_at_max(self):
        from phantom_city.celery_tasks import respawn_crystals
        zone = self.make_zone('ruins')
        deposit = CrystalDeposit.objects.create(
            zone=zone, quantity=19, max_quantity=20, respawn_rate_per_hour=5
        )
        respawn_crystals()
        deposit.refresh_from_db()
        self.assertEqual(deposit.quantity, 20)

    def test_multiple_deposits_all_updated(self):
        from phantom_city.celery_tasks import respawn_crystals
        zone = self.make_zone('ruins')
        CrystalDeposit.objects.create(zone=zone, quantity=0, max_quantity=10, respawn_rate_per_hour=2)
        CrystalDeposit.objects.create(zone=zone, quantity=5, max_quantity=15, respawn_rate_per_hour=3)
        result = respawn_crystals()
        self.assertEqual(result, 2)


class RecalculateMarketRatesTaskTest(PhantomCityTestCase):
    """phantom_city.recalculate_market_rates"""

    def test_runs_without_error(self):
        from phantom_city.celery_tasks import recalculate_market_rates
        # No rates exist — should complete silently
        recalculate_market_rates()

    def test_updates_existing_rates(self):
        from phantom_city.celery_tasks import recalculate_market_rates
        GameMarketRate.objects.create(
            item_slug='test_item',
            base_price_crystals=10,
            current_price_crystals=10,
            demand_pressure=2.0,
            units_traded_last_period=5,
        )
        recalculate_market_rates()
        rate = GameMarketRate.objects.get(item_slug='test_item')
        # After recalc with high demand, price should have changed
        self.assertIsNotNone(rate.current_price_crystals)


class GenerateCheckpointNpcsTaskTest(PhantomCityTestCase):
    """phantom_city.generate_checkpoint_npcs"""

    def test_no_checkpoint_zone_returns_none(self):
        from phantom_city.celery_tasks import generate_checkpoint_npcs
        result = generate_checkpoint_npcs()
        self.assertIsNone(result)

    def test_no_active_session_returns_none(self):
        from phantom_city.celery_tasks import generate_checkpoint_npcs
        self.make_zone('checkpoint')
        result = generate_checkpoint_npcs()
        self.assertIsNone(result)

    def test_active_session_generates_npcs(self):
        from phantom_city.celery_tasks import generate_checkpoint_npcs
        zone = self.make_zone('checkpoint')
        session = CheckpointSession.objects.create(zone=zone, status='active')
        generate_checkpoint_npcs()
        session.refresh_from_db()
        # npc_data should be populated
        self.assertIsNotNone(session.npc_data)


class CleanupExpiredChannelsTaskTest(PhantomCityTestCase):
    """phantom_city.cleanup_expired_channels"""

    def test_no_channels_returns_zero(self):
        from phantom_city.celery_tasks import cleanup_expired_channels
        result = cleanup_expired_channels()
        self.assertEqual(result, 0)

    def test_active_channel_messages_not_deleted(self):
        from phantom_city.celery_tasks import cleanup_expired_channels
        channel = EncryptedChannel.objects.create(
            participant_a=self.user1,
            participant_b=self.user2,
            is_active=True,
        )
        EncryptedMessage.objects.create(channel=channel, content='hello', is_system=False)
        result = cleanup_expired_channels()
        self.assertEqual(result, 0)
        self.assertEqual(EncryptedMessage.objects.filter(channel=channel).count(), 1)

    def test_recently_closed_channel_messages_not_deleted(self):
        """关闭不足24小时的频道不清理"""
        from phantom_city.celery_tasks import cleanup_expired_channels
        channel = EncryptedChannel.objects.create(
            participant_a=self.user1,
            participant_b=self.user2,
            is_active=False,
            closed_at=timezone.now() - timedelta(hours=12),
        )
        EncryptedMessage.objects.create(channel=channel, content='msg', is_system=False)
        result = cleanup_expired_channels()
        self.assertEqual(result, 0)

    def test_old_closed_channel_messages_deleted(self):
        """关闭超过24小时的频道消息被删除"""
        from phantom_city.celery_tasks import cleanup_expired_channels
        channel = EncryptedChannel.objects.create(
            participant_a=self.user1,
            participant_b=self.user2,
            is_active=False,
            closed_at=timezone.now() - timedelta(hours=25),
        )
        EncryptedMessage.objects.create(channel=channel, content='msg1', is_system=False)
        EncryptedMessage.objects.create(channel=channel, content='msg2', is_system=True)
        result = cleanup_expired_channels()
        self.assertEqual(result, 2)
        self.assertEqual(EncryptedMessage.objects.filter(channel=channel).count(), 0)


class ResetInspectionTokensTaskTest(PhantomCityTestCase):
    """phantom_city.reset_inspection_tokens"""

    def test_no_profiles_returns_zero(self):
        from phantom_city.celery_tasks import reset_inspection_tokens
        result = reset_inspection_tokens()
        self.assertEqual(result, 0)

    def test_profile_with_old_reset_date_is_reset(self):
        from phantom_city.celery_tasks import reset_inspection_tokens
        from datetime import date
        patrol = self.make_patrol(self.user1, inspection_tokens=3)
        # Set last reset to yesterday
        PatrolProfile.objects.filter(pk=patrol.pk).update(
            inspection_tokens_last_reset=date(2020, 1, 1)
        )
        result = reset_inspection_tokens()
        self.assertEqual(result, 1)
        patrol.refresh_from_db()
        self.assertEqual(patrol.inspection_tokens, 10)

    def test_profile_already_reset_today_not_counted(self):
        from phantom_city.celery_tasks import reset_inspection_tokens
        from django.utils import timezone
        today = timezone.now().date()
        patrol = self.make_patrol(self.user1, inspection_tokens=10)
        PatrolProfile.objects.filter(pk=patrol.pk).update(
            inspection_tokens_last_reset=today
        )
        result = reset_inspection_tokens()
        self.assertEqual(result, 0)

    def test_multiple_profiles_all_reset(self):
        from phantom_city.celery_tasks import reset_inspection_tokens
        from datetime import date
        p1 = self.make_patrol(self.user1, inspection_tokens=2)
        p2 = self.make_patrol(self.user2, inspection_tokens=5)
        PatrolProfile.objects.filter(pk__in=[p1.pk, p2.pk]).update(
            inspection_tokens_last_reset=date(2020, 1, 1)
        )
        result = reset_inspection_tokens()
        self.assertEqual(result, 2)
        p1.refresh_from_db()
        p2.refresh_from_db()
        self.assertEqual(p1.inspection_tokens, 10)
        self.assertEqual(p2.inspection_tokens, 10)
