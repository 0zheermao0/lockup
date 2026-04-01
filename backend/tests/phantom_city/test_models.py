"""
幻城：禁断走私 — 模型单元测试
覆盖所有模型的创建、约束、默认值和关系
"""
import uuid
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from django.db import IntegrityError

from tests.phantom_city.base import PhantomCityTestCase
from phantom_city.models import (
    GameZone, PlayerZonePresence, MimicProfile, PatrolProfile,
    TellEvent, CheckpointSession, CheckpointParticipant, InterrogationRequest,
    GrayMarketTransaction, GameControlTransfer, DetentionRecord,
    FactionConversionEvent, EncryptedChannel, EncryptedMessage,
    ZoneChatMessage, CrystalDeposit, PlayerCrystals, GameMarketRate,
    GameItem, PlayerGameInventory, ActiveDisguise, SmuggleRun,
)


class GameZoneModelTest(PhantomCityTestCase):
    """GameZone 模型测试"""

    def setUp(self):
        super().setUp()
        self.zone = GameZone.objects.create(
            name='ruins',
            display_name='污染废墟',
            description='废墟测试区域',
        )

    def test_create_zone(self):
        self.assertEqual(self.zone.name, 'ruins')
        self.assertEqual(self.zone.display_name, '污染废墟')
        self.assertEqual(self.zone.crystal_respawn_rate, 5)
        self.assertEqual(self.zone.max_players, 50)
        self.assertEqual(self.zone.config, {})

    def test_zone_name_unique(self):
        with self.assertRaises(IntegrityError):
            GameZone.objects.create(
                name='ruins',
                display_name='另一个废墟',
                description='重复',
            )

    def test_zone_str(self):
        self.assertEqual(str(self.zone), '污染废墟')

    def test_all_zone_types(self):
        GameZone.objects.create(name='salon', display_name='纯净沙龙', description='沙龙')
        GameZone.objects.create(name='checkpoint', display_name='铁血防线', description='检查站')
        GameZone.objects.create(name='control_room', display_name='控制室', description='控制室')
        self.assertEqual(GameZone.objects.count(), 4)


class PlayerZonePresenceModelTest(PhantomCityTestCase):
    """PlayerZonePresence 模型测试"""

    def setUp(self):
        super().setUp()
        self.zone = GameZone.objects.create(
            name='salon', display_name='纯净沙龙', description='沙龙'
        )

    def test_create_presence(self):
        presence = PlayerZonePresence.objects.create(
            user=self.user1,
            zone=self.zone,
        )
        self.assertIsNotNone(presence.entered_at)
        self.assertIsNone(presence.exited_at)
        self.assertEqual(presence.entry_stats, {})

    def test_presence_str(self):
        presence = PlayerZonePresence.objects.create(
            user=self.user1,
            zone=self.zone,
        )
        self.assertIn(self.user1.username, str(presence))

    def test_multiple_presences_allowed(self):
        """同一用户可以有多条记录（历史）"""
        PlayerZonePresence.objects.create(user=self.user1, zone=self.zone)
        PlayerZonePresence.objects.create(user=self.user1, zone=self.zone)
        self.assertEqual(
            PlayerZonePresence.objects.filter(user=self.user1).count(), 2
        )

    def test_exit_presence(self):
        presence = PlayerZonePresence.objects.create(
            user=self.user1, zone=self.zone
        )
        presence.exited_at = timezone.now()
        presence.save()
        presence.refresh_from_db()
        self.assertIsNotNone(presence.exited_at)


class MimicProfileModelTest(PhantomCityTestCase):
    """MimicProfile 模型测试"""

    def test_create_mimic_profile_defaults(self):
        profile = MimicProfile.objects.create(user=self.user1)
        self.assertEqual(profile.depilation_charge, 100)
        self.assertEqual(profile.suppression_value, 0)
        self.assertEqual(profile.purity_score, 50)
        self.assertEqual(profile.femboy_score, 0)
        self.assertEqual(profile.smoothness_score, 0)
        self.assertEqual(profile.control_resistance, 0)
        self.assertEqual(profile.permanent_tells, [])
        self.assertEqual(profile.base_detectability, 0)
        self.assertEqual(profile.current_faction, 'mimic')
        self.assertFalse(profile.is_disguised)
        self.assertEqual(profile.total_successful_runs, 0)
        self.assertEqual(profile.total_failed_runs, 0)
        self.assertEqual(profile.total_crystals_collected, 0)

    def test_mimic_profile_one_to_one(self):
        MimicProfile.objects.create(user=self.user1)
        with self.assertRaises(IntegrityError):
            MimicProfile.objects.create(user=self.user1)

    def test_mimic_profile_str(self):
        profile = MimicProfile.objects.create(user=self.user1)
        self.assertIn('拟态者', str(profile))
        self.assertIn(self.user1.username, str(profile))

    def test_related_name(self):
        profile = MimicProfile.objects.create(user=self.user1)
        self.assertEqual(self.user1.mimic_profile, profile)


class PatrolProfileModelTest(PhantomCityTestCase):
    """PatrolProfile 模型测试"""

    def test_create_patrol_profile_defaults(self):
        profile = PatrolProfile.objects.create(user=self.user1)
        self.assertEqual(profile.authority_value, 80)
        self.assertEqual(profile.reputation_score, 60)
        self.assertEqual(profile.inspection_tokens, 10)
        self.assertEqual(profile.suspicion_evidence, {})
        self.assertEqual(profile.detection_tools, {})
        self.assertEqual(profile.current_faction, 'patrol')
        self.assertEqual(profile.total_arrests, 0)
        self.assertEqual(profile.false_accusations, 0)
        self.assertEqual(profile.total_correct_identifications, 0)

    def test_patrol_profile_one_to_one(self):
        PatrolProfile.objects.create(user=self.user1)
        with self.assertRaises(IntegrityError):
            PatrolProfile.objects.create(user=self.user1)

    def test_patrol_profile_str(self):
        profile = PatrolProfile.objects.create(user=self.user1)
        self.assertIn('巡逻队', str(profile))


class TellEventModelTest(PhantomCityTestCase):
    """TellEvent 模型测试"""

    def setUp(self):
        super().setUp()
        self.zone = GameZone.objects.create(
            name='checkpoint', display_name='铁血防线', description='检查站'
        )

    def test_create_tell_event(self):
        event = TellEvent.objects.create(
            player=self.user1,
            tell_type='body_hair',
            tell_text='*[袖口滑落，露出一截细毛]*',
            zone=self.zone,
            action_type='presence',
        )
        self.assertIsInstance(event.id, uuid.UUID)
        self.assertEqual(event.tell_type, 'body_hair')
        self.assertIsNone(event.checkpoint_session)
        self.assertEqual(event.stats_snapshot, {})

    def test_tell_event_str(self):
        event = TellEvent.objects.create(
            player=self.user1,
            tell_type='body_hair',
            tell_text='*test*',
            zone=self.zone,
        )
        self.assertIn(self.user1.username, str(event))

    def test_tell_event_uuid_pk(self):
        event = TellEvent.objects.create(
            player=self.user1,
            tell_type='suppression_tremor',
            tell_text='*test*',
            zone=self.zone,
        )
        self.assertIsInstance(event.pk, uuid.UUID)

    def test_discovered_by_m2m(self):
        event = TellEvent.objects.create(
            player=self.user1,
            tell_type='weight_anomaly',
            tell_text='*test*',
            zone=self.zone,
        )
        event.discovered_by.add(self.user2)
        self.assertIn(self.user2, event.discovered_by.all())


class CheckpointSessionModelTest(PhantomCityTestCase):
    """CheckpointSession 模型测试"""

    def setUp(self):
        super().setUp()
        self.zone = GameZone.objects.create(
            name='checkpoint', display_name='铁血防线', description='检查站'
        )

    def test_create_session(self):
        session = CheckpointSession.objects.create(zone=self.zone)
        self.assertIsInstance(session.id, uuid.UUID)
        self.assertEqual(session.status, 'active')
        self.assertEqual(session.npc_count, 0)
        self.assertEqual(session.npc_data, [])
        self.assertIsNotNone(session.opened_at)
        self.assertIsNone(session.closed_at)

    def test_session_str(self):
        session = CheckpointSession.objects.create(zone=self.zone)
        self.assertIn('active', str(session))


class CheckpointParticipantModelTest(PhantomCityTestCase):
    """CheckpointParticipant 模型测试"""

    def setUp(self):
        super().setUp()
        self.zone = GameZone.objects.create(
            name='checkpoint', display_name='铁血防线', description='检查站'
        )
        self.session = CheckpointSession.objects.create(zone=self.zone)

    def test_create_participant(self):
        participant = CheckpointParticipant.objects.create(
            session=self.session,
            user=self.user1,
            role='smuggler',
        )
        self.assertEqual(participant.outcome, 'pending')
        self.assertIsNone(participant.queue_position)
        self.assertEqual(participant.contraband_snapshot, [])

    def test_unique_together_session_user(self):
        CheckpointParticipant.objects.create(
            session=self.session, user=self.user1, role='smuggler'
        )
        with self.assertRaises(IntegrityError):
            CheckpointParticipant.objects.create(
                session=self.session, user=self.user1, role='patrol'
            )

    def test_different_users_same_session(self):
        CheckpointParticipant.objects.create(
            session=self.session, user=self.user1, role='smuggler'
        )
        CheckpointParticipant.objects.create(
            session=self.session, user=self.user2, role='patrol'
        )
        self.assertEqual(
            CheckpointParticipant.objects.filter(session=self.session).count(), 2
        )


class GrayMarketTransactionModelTest(PhantomCityTestCase):
    """GrayMarketTransaction 模型测试"""

    def test_create_transaction(self):
        tx = GrayMarketTransaction.objects.create(
            transaction_type='bribe',
            initiator=self.user1,
            recipient=self.user2,
            status='proposed',
            expires_at=timezone.now() + timedelta(minutes=30),
        )
        self.assertIsInstance(tx.id, uuid.UUID)
        self.assertEqual(tx.escrowed_crystals, 0)
        self.assertEqual(tx.offer_from_initiator, {})
        self.assertEqual(tx.offer_from_recipient, {})
        self.assertEqual(tx.negotiation_log, [])
        self.assertIsNone(tx.encrypted_channel_id)

    def test_transaction_str(self):
        tx = GrayMarketTransaction.objects.create(
            transaction_type='bribe',
            initiator=self.user1,
            recipient=self.user2,
            expires_at=timezone.now() + timedelta(minutes=30),
        )
        self.assertIn(self.user1.username, str(tx))


class GameControlTransferModelTest(PhantomCityTestCase):
    """GameControlTransfer 模型测试"""

    def setUp(self):
        super().setUp()
        self.lock_task = self.create_test_lock_task(self.user1, status='active')

    def test_create_control_transfer(self):
        transfer = GameControlTransfer.objects.create(
            lock_task=self.lock_task,
            grantor=self.user1,
            grantee=self.user2,
            source='arrest',
            duration_hours=12,
            expires_at=timezone.now() + timedelta(hours=12),
        )
        self.assertIsInstance(transfer.id, uuid.UUID)
        self.assertTrue(transfer.can_add_time)
        self.assertTrue(transfer.can_freeze)
        self.assertFalse(transfer.can_assign_tasks)
        self.assertTrue(transfer.is_active)
        self.assertIsNone(transfer.revoked_at)

    def test_transfer_str(self):
        transfer = GameControlTransfer.objects.create(
            lock_task=self.lock_task,
            grantor=self.user1,
            grantee=self.user2,
            source='arrest',
            duration_hours=12,
            expires_at=timezone.now() + timedelta(hours=12),
        )
        self.assertIn(self.user2.username, str(transfer))


class DetentionRecordModelTest(PhantomCityTestCase):
    """DetentionRecord 模型测试"""

    def test_create_detention(self):
        detention = DetentionRecord.objects.create(
            prisoner=self.user1,
            captor=self.user2,
            status='active',
            release_at=timezone.now() + timedelta(hours=12),
        )
        self.assertIsInstance(detention.id, uuid.UUID)
        self.assertEqual(detention.seized_crystals, 0)
        self.assertEqual(detention.duration_hours, 12)
        self.assertEqual(detention.charm_attempts_used, 0)
        self.assertIsNone(detention.last_charm_at)
        self.assertIsNone(detention.control_transfer)

    def test_detention_str(self):
        detention = DetentionRecord.objects.create(
            prisoner=self.user1,
            captor=self.user2,
            status='active',
            release_at=timezone.now() + timedelta(hours=12),
        )
        self.assertIn(self.user1.username, str(detention))


class EncryptedChannelModelTest(PhantomCityTestCase):
    """EncryptedChannel 模型测试"""

    def test_create_channel(self):
        channel = EncryptedChannel.objects.create(
            participant_a=self.user1,
            participant_b=self.user2,
        )
        self.assertIsInstance(channel.id, uuid.UUID)
        self.assertTrue(channel.is_active)
        self.assertIsNone(channel.closed_at)
        self.assertIsNone(channel.linked_transaction)

    def test_channel_str(self):
        channel = EncryptedChannel.objects.create(
            participant_a=self.user1,
            participant_b=self.user2,
        )
        self.assertIn(self.user1.username, str(channel))

    def test_encrypted_message(self):
        channel = EncryptedChannel.objects.create(
            participant_a=self.user1,
            participant_b=self.user2,
        )
        msg = EncryptedMessage.objects.create(
            channel=channel,
            sender=self.user1,
            content='测试消息',
        )
        self.assertFalse(msg.is_system)
        self.assertIn('测试消息', str(msg))

    def test_system_message(self):
        channel = EncryptedChannel.objects.create(
            participant_a=self.user1,
            participant_b=self.user2,
        )
        msg = EncryptedMessage.objects.create(
            channel=channel,
            sender=None,
            content='[系统消息]',
            is_system=True,
        )
        self.assertTrue(msg.is_system)
        self.assertIsNone(msg.sender)


class PlayerCrystalsModelTest(PhantomCityTestCase):
    """PlayerCrystals 模型测试"""

    def test_create_crystals(self):
        crystals = PlayerCrystals.objects.create(user=self.user1)
        self.assertEqual(crystals.raw_crystals, 0)
        self.assertEqual(crystals.purified_crystals, 0)

    def test_crystals_one_to_one(self):
        PlayerCrystals.objects.create(user=self.user1)
        with self.assertRaises(IntegrityError):
            PlayerCrystals.objects.create(user=self.user1)

    def test_crystals_str(self):
        crystals = PlayerCrystals.objects.create(
            user=self.user1, raw_crystals=10, purified_crystals=5
        )
        self.assertIn(self.user1.username, str(crystals))
        self.assertIn('10', str(crystals))


class GameItemModelTest(PhantomCityTestCase):
    """GameItem 模型测试"""

    def test_create_game_item(self):
        item = GameItem.objects.create(
            slug='test_item',
            name='测试道具',
            tier=1,
            slot='consumable',
            description='测试描述',
            price_crystals=10,
        )
        self.assertEqual(item.tier, 1)
        self.assertFalse(item.is_lock_device)
        self.assertFalse(item.is_removal_device)
        self.assertFalse(item.is_disguise_item)
        self.assertEqual(item.stat_modifiers, {})
        self.assertTrue(item.is_active)

    def test_item_slug_unique(self):
        GameItem.objects.create(
            slug='unique_item', name='A', tier=1, slot='consumable', description='A'
        )
        with self.assertRaises(IntegrityError):
            GameItem.objects.create(
                slug='unique_item', name='B', tier=1, slot='consumable', description='B'
            )

    def test_item_str(self):
        item = GameItem.objects.create(
            slug='str_test', name='名字测试', tier=2, slot='outer', description='d'
        )
        self.assertIn('名字测试', str(item))
        self.assertIn('2', str(item))


class PlayerGameInventoryModelTest(PhantomCityTestCase):
    """PlayerGameInventory 模型测试"""

    def setUp(self):
        super().setUp()
        self.item = GameItem.objects.create(
            slug='inv_item', name='背包道具', tier=1, slot='consumable', description='d'
        )

    def test_create_inventory(self):
        inv = PlayerGameInventory.objects.create(
            user=self.user1,
            item=self.item,
            quantity=3,
        )
        self.assertEqual(inv.quantity, 3)
        self.assertIsNotNone(inv.obtained_at)

    def test_unique_together_user_item(self):
        PlayerGameInventory.objects.create(
            user=self.user1, item=self.item, quantity=1
        )
        with self.assertRaises(IntegrityError):
            PlayerGameInventory.objects.create(
                user=self.user1, item=self.item, quantity=2
            )


class ActiveDisguiseModelTest(PhantomCityTestCase):
    """ActiveDisguise 模型测试"""

    def test_create_disguise(self):
        disguise = ActiveDisguise.objects.create(user=self.user1)
        self.assertIsNone(disguise.outer_layer_item)
        self.assertEqual(disguise.behavioral_mode, 'passive')
        self.assertEqual(disguise.computed_detectability, 0)
        self.assertEqual(disguise.computed_disguise_quality, 0)
        self.assertEqual(disguise.computed_active_tells, [])

    def test_disguise_one_to_one(self):
        ActiveDisguise.objects.create(user=self.user1)
        with self.assertRaises(IntegrityError):
            ActiveDisguise.objects.create(user=self.user1)

    def test_add_inner_items(self):
        disguise = ActiveDisguise.objects.create(user=self.user1)
        item = GameItem.objects.create(
            slug='inner_item', name='内层道具', tier=1, slot='inner', description='d'
        )
        disguise.inner_items.add(item)
        self.assertIn(item, disguise.inner_items.all())


class SmuggleRunModelTest(PhantomCityTestCase):
    """SmuggleRun 模型测试"""

    def test_create_smuggle_run(self):
        run = SmuggleRun.objects.create(player=self.user1)
        self.assertIsInstance(run.id, uuid.UUID)
        self.assertEqual(run.status, 'in_progress')
        self.assertEqual(run.crystals_collected, 0)
        self.assertEqual(run.crystals_delivered, 0)
        self.assertEqual(run.crystals_seized, 0)

    def test_smuggle_run_str(self):
        run = SmuggleRun.objects.create(player=self.user1)
        self.assertIsNotNone(str(run))


class CrystalDepositModelTest(PhantomCityTestCase):
    """CrystalDeposit 模型测试"""

    def setUp(self):
        super().setUp()
        self.zone = GameZone.objects.create(
            name='ruins', display_name='污染废墟', description='废墟'
        )

    def test_create_deposit(self):
        deposit = CrystalDeposit.objects.create(
            zone=self.zone,
            quantity=15,
            max_quantity=20,
        )
        self.assertIsInstance(deposit.id, uuid.UUID)
        self.assertEqual(deposit.respawn_rate_per_hour, 3)
        self.assertIsNone(deposit.last_harvested_at)
        self.assertIsNone(deposit.last_harvested_by)

    def test_deposit_str(self):
        deposit = CrystalDeposit.objects.create(
            zone=self.zone, quantity=5, max_quantity=20
        )
        self.assertIn('5', str(deposit))
        self.assertIn('20', str(deposit))


class GameMarketRateModelTest(PhantomCityTestCase):
    """GameMarketRate 模型测试"""

    def test_create_market_rate(self):
        rate = GameMarketRate.objects.create(
            item_slug='test_item',
            item_display_name='测试道具',
            current_price_crystals=50,
            base_price_crystals=50,
        )
        self.assertEqual(rate.demand_pressure, 1.0)
        self.assertEqual(rate.units_traded_last_period, 0)

    def test_item_slug_unique(self):
        GameMarketRate.objects.create(
            item_slug='unique_rate', item_display_name='A',
            current_price_crystals=10, base_price_crystals=10
        )
        with self.assertRaises(IntegrityError):
            GameMarketRate.objects.create(
                item_slug='unique_rate', item_display_name='B',
                current_price_crystals=20, base_price_crystals=20
            )
