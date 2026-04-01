from datetime import timedelta
from unittest.mock import patch
from django.utils import timezone
from tests.phantom_city.base import PhantomCityTestCase
from phantom_city.models import (
    GameZone, PlayerZonePresence, MimicProfile, PatrolProfile,
    TellEvent, CheckpointSession, CheckpointParticipant, InterrogationRequest,
    GrayMarketTransaction, GameControlTransfer, DetentionRecord,
    FactionConversionEvent, EncryptedChannel, EncryptedMessage,
    ZoneChatMessage, CrystalDeposit, PlayerCrystals, GameMarketRate,
    GameItem, PlayerGameInventory, ActiveDisguise, SmuggleRun,
)
from phantom_city.services import (
    TellService, CheckpointService, DetentionService, TransactionService,
    DisguiseService, CrystalService, ControlTransferService, ZoneService,
    FULL_DISGUISE_SET,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_zone(name):
    zone, _ = GameZone.objects.get_or_create(name=name)
    return zone


def make_mimic(user, **kwargs):
    return MimicProfile.objects.create(user=user, **kwargs)


def make_patrol(user, **kwargs):
    return PatrolProfile.objects.create(user=user, **kwargs)


def make_crystals(user, raw=0, purified=0):
    pc, _ = PlayerCrystals.objects.get_or_create(user=user)
    pc.raw_crystals = raw
    pc.purified_crystals = purified
    pc.save()
    return pc


def make_presence(user, zone, exited_at=None, entered_at=None):
    presence = PlayerZonePresence.objects.create(
        user=user,
        zone=zone,
        exited_at=exited_at,
    )
    if entered_at is not None:
        # auto_now_add ignores passed value; use update() to set historical time
        PlayerZonePresence.objects.filter(pk=presence.pk).update(entered_at=entered_at)
        presence.refresh_from_db()
    return presence


# ===========================================================================
# TellService tests
# ===========================================================================

class TellServiceNoProfileTest(PhantomCityTestCase):
    """evaluate_tells returns [] when player has no MimicProfile."""

    def setUp(self):
        super().setUp()
        self.zone = make_zone('checkpoint')

    def test_no_mimic_profile_returns_empty(self):
        result = TellService.evaluate_tells(self.user1, self.zone)
        self.assertEqual(result, [])


class TellServiceBodyHairTest(PhantomCityTestCase):
    def setUp(self):
        super().setUp()
        self.zone = make_zone('checkpoint')
        self.mimic = make_mimic(self.user1, depilation_charge=20)

    def test_body_hair_triggers_when_charge_low_and_random_passes(self):
        with patch('random.random', return_value=0.0):
            tells = TellService.evaluate_tells(self.user1, self.zone)
        tell_types = [t.tell_type for t in tells]
        self.assertIn('body_hair', tell_types)

    def test_body_hair_does_not_trigger_when_charge_high(self):
        self.mimic.depilation_charge = 50
        self.mimic.save()
        with patch('random.random', return_value=0.0):
            tells = TellService.evaluate_tells(self.user1, self.zone)
        tell_types = [t.tell_type for t in tells]
        self.assertNotIn('body_hair', tell_types)

    def test_body_hair_does_not_trigger_when_random_fails(self):
        with patch('random.random', return_value=1.0):
            tells = TellService.evaluate_tells(self.user1, self.zone)
        tell_types = [t.tell_type for t in tells]
        self.assertNotIn('body_hair', tell_types)


class TellServiceSuppressionTremorTest(PhantomCityTestCase):
    def setUp(self):
        super().setUp()
        self.zone = make_zone('checkpoint')
        self.mimic = make_mimic(self.user1, suppression_value=80)

    def test_suppression_tremor_triggers_when_value_high_and_random_passes(self):
        with patch('random.random', return_value=0.0):
            tells = TellService.evaluate_tells(self.user1, self.zone)
        tell_types = [t.tell_type for t in tells]
        self.assertIn('suppression_tremor', tell_types)

    def test_suppression_tremor_does_not_trigger_when_value_low(self):
        self.mimic.suppression_value = 50
        self.mimic.save()
        with patch('random.random', return_value=0.0):
            tells = TellService.evaluate_tells(self.user1, self.zone)
        tell_types = [t.tell_type for t in tells]
        self.assertNotIn('suppression_tremor', tell_types)

    def test_suppression_tremor_does_not_trigger_when_random_fails(self):
        with patch('random.random', return_value=1.0):
            tells = TellService.evaluate_tells(self.user1, self.zone)
        tell_types = [t.tell_type for t in tells]
        self.assertNotIn('suppression_tremor', tell_types)


class TellServiceAbnormalPauseTest(PhantomCityTestCase):
    def setUp(self):
        super().setUp()
        self.zone = make_zone('checkpoint')
        self.mimic = make_mimic(self.user1)

    def test_abnormal_pause_always_triggers_when_response_time_over_20(self):
        with patch('random.random', return_value=1.0):
            tells = TellService.evaluate_tells(
                self.user1, self.zone,
                action_type='interrogation_response',
                response_time_seconds=25
            )
        tell_types = [t.tell_type for t in tells]
        self.assertIn('abnormal_pause', tell_types)

    def test_abnormal_pause_does_not_trigger_when_response_time_under_20(self):
        with patch('random.random', return_value=0.0):
            tells = TellService.evaluate_tells(
                self.user1, self.zone,
                action_type='interrogation_response',
                response_time_seconds=10
            )
        tell_types = [t.tell_type for t in tells]
        self.assertNotIn('abnormal_pause', tell_types)

    def test_abnormal_pause_does_not_trigger_when_no_response_time(self):
        with patch('random.random', return_value=0.0):
            tells = TellService.evaluate_tells(self.user1, self.zone)
        tell_types = [t.tell_type for t in tells]
        self.assertNotIn('abnormal_pause', tell_types)


class TellServiceWeightAnomalyTest(PhantomCityTestCase):
    def setUp(self):
        super().setUp()
        self.zone = make_zone('checkpoint')
        self.mimic = make_mimic(self.user1)

    def test_weight_anomaly_triggers_when_has_crystals_and_random_passes(self):
        make_crystals(self.user1, raw=5)
        with patch('random.random', return_value=0.0):
            tells = TellService.evaluate_tells(self.user1, self.zone)
        tell_types = [t.tell_type for t in tells]
        self.assertIn('weight_anomaly', tell_types)

    def test_weight_anomaly_does_not_trigger_when_no_crystals(self):
        make_crystals(self.user1, raw=0)
        with patch('random.random', return_value=0.0):
            tells = TellService.evaluate_tells(self.user1, self.zone)
        tell_types = [t.tell_type for t in tells]
        self.assertNotIn('weight_anomaly', tell_types)

    def test_weight_anomaly_does_not_trigger_when_random_fails(self):
        make_crystals(self.user1, raw=5)
        with patch('random.random', return_value=1.0):
            tells = TellService.evaluate_tells(self.user1, self.zone)
        tell_types = [t.tell_type for t in tells]
        self.assertNotIn('weight_anomaly', tell_types)


class TellServiceScentResidueTest(PhantomCityTestCase):
    def setUp(self):
        super().setUp()
        self.zone = make_zone('checkpoint')
        self.ruins_zone = make_zone('ruins')
        self.mimic = make_mimic(self.user1)

    def test_scent_residue_triggers_when_was_in_ruins_recently(self):
        recent = timezone.now() - timedelta(hours=3)
        make_presence(self.user1, self.ruins_zone, entered_at=recent)
        with patch('random.random', return_value=0.0):
            tells = TellService.evaluate_tells(self.user1, self.zone)
        tell_types = [t.tell_type for t in tells]
        self.assertIn('scent_residue', tell_types)

    def test_scent_residue_does_not_trigger_when_not_in_ruins(self):
        salon = make_zone('salon')
        make_presence(self.user1, salon)
        with patch('random.random', return_value=0.0):
            tells = TellService.evaluate_tells(self.user1, self.zone)
        tell_types = [t.tell_type for t in tells]
        self.assertNotIn('scent_residue', tell_types)


class TellServiceDisguiseFatigueTest(PhantomCityTestCase):
    def setUp(self):
        super().setUp()
        self.zone = make_zone('checkpoint')
        old_time = timezone.now() - timedelta(hours=5)
        self.mimic = make_mimic(
            self.user1,
            is_disguised=True,
            disguise_start_time=old_time
        )

    def test_disguise_fatigue_triggers_when_disguised_over_4h_and_random_passes(self):
        with patch('random.random', return_value=0.0):
            tells = TellService.evaluate_tells(self.user1, self.zone)
        tell_types = [t.tell_type for t in tells]
        self.assertIn('disguise_fatigue', tell_types)

    def test_disguise_fatigue_does_not_trigger_when_not_disguised(self):
        self.mimic.is_disguised = False
        self.mimic.save()
        with patch('random.random', return_value=0.0):
            tells = TellService.evaluate_tells(self.user1, self.zone)
        tell_types = [t.tell_type for t in tells]
        self.assertNotIn('disguise_fatigue', tell_types)

    def test_disguise_fatigue_does_not_trigger_when_recently_disguised(self):
        self.mimic.disguise_start_time = timezone.now() - timedelta(hours=1)
        self.mimic.save()
        with patch('random.random', return_value=0.0):
            tells = TellService.evaluate_tells(self.user1, self.zone)
        tell_types = [t.tell_type for t in tells]
        self.assertNotIn('disguise_fatigue', tell_types)


class TellServicePitchSlippageTest(PhantomCityTestCase):
    def setUp(self):
        super().setUp()
        self.zone = make_zone('checkpoint')
        self.mimic = make_mimic(self.user1, suppression_value=85)

    def test_pitch_slippage_triggers_for_interrogation_high_suppression(self):
        with patch('random.random', return_value=0.0):
            tells = TellService.evaluate_tells(
                self.user1, self.zone,
                action_type='interrogation_response'
            )
        tell_types = [t.tell_type for t in tells]
        self.assertIn('pitch_slippage', tell_types)

    def test_pitch_slippage_does_not_trigger_for_non_interrogation(self):
        with patch('random.random', return_value=0.0):
            tells = TellService.evaluate_tells(
                self.user1, self.zone,
                action_type='presence'
            )
        tell_types = [t.tell_type for t in tells]
        self.assertNotIn('pitch_slippage', tell_types)

    def test_pitch_slippage_does_not_trigger_when_suppression_low(self):
        self.mimic.suppression_value = 50
        self.mimic.save()
        with patch('random.random', return_value=0.0):
            tells = TellService.evaluate_tells(
                self.user1, self.zone,
                action_type='interrogation_response'
            )
        tell_types = [t.tell_type for t in tells]
        self.assertNotIn('pitch_slippage', tell_types)


class TellServiceAddSuspicionTest(PhantomCityTestCase):
    def setUp(self):
        super().setUp()
        self.patrol = make_patrol(self.user2)

    def test_add_suspicion_returns_new_total(self):
        score = TellService.add_suspicion(self.patrol, self.user1, 25, reason='test')
        self.assertEqual(score, 25)

    def test_add_suspicion_accumulates(self):
        TellService.add_suspicion(self.patrol, self.user1, 10)
        score = TellService.add_suspicion(self.patrol, self.user1, 15)
        self.assertEqual(score, 25)

    def test_add_suspicion_updates_evidence_dict(self):
        TellService.add_suspicion(self.patrol, self.user1, 20, reason='body_hair')
        self.patrol.refresh_from_db()
        key = str(self.user1.pk)
        self.assertIn(key, self.patrol.suspicion_evidence)


class TellServiceGetSuspicionScoreTest(PhantomCityTestCase):
    def setUp(self):
        super().setUp()
        self.patrol = make_patrol(self.user2)
        self.zone = make_zone('checkpoint')
        self.session = CheckpointSession.objects.create(zone=self.zone, status='active')

    def test_get_suspicion_score_returns_zero_for_clean_target(self):
        score = TellService.get_suspicion_score(self.patrol, self.user1, self.session)
        self.assertEqual(score, 0)

    def test_get_suspicion_score_returns_accumulated_points(self):
        TellService.add_suspicion(self.patrol, self.user1, 40)
        score = TellService.get_suspicion_score(self.patrol, self.user1, self.session)
        self.assertEqual(score, 40)


# ===========================================================================
# CheckpointService tests
# ===========================================================================

class CheckpointServiceSessionTest(PhantomCityTestCase):
    def setUp(self):
        super().setUp()
        self.zone = make_zone('checkpoint')

    def test_create_session_returns_active_session(self):
        session = CheckpointService.create_session(self.zone)
        self.assertEqual(session.status, 'active')
        self.assertEqual(session.zone, self.zone)

    def test_create_session_generates_10_npcs(self):
        session = CheckpointService.create_session(self.zone)
        self.assertEqual(len(session.npc_data), 10)

    def test_get_or_create_active_session_creates_when_none(self):
        session = CheckpointService.get_or_create_active_session(self.zone)
        self.assertIsNotNone(session)
        self.assertEqual(session.status, 'active')

    def test_get_or_create_active_session_returns_existing(self):
        first = CheckpointService.get_or_create_active_session(self.zone)
        second = CheckpointService.get_or_create_active_session(self.zone)
        self.assertEqual(first.pk, second.pk)


class CheckpointServiceJoinTest(PhantomCityTestCase):
    def setUp(self):
        super().setUp()
        self.zone = make_zone('checkpoint')
        self.session = CheckpointService.create_session(self.zone)

    def test_join_as_smuggler(self):
        participant = CheckpointService.join_as_smuggler(self.user1, self.session)
        self.assertEqual(participant.role, 'smuggler')
        self.assertEqual(participant.user, self.user1)

    def test_join_as_patrol(self):
        participant = CheckpointService.join_as_patrol(self.user2, self.session)
        self.assertEqual(participant.role, 'patrol')
        self.assertEqual(participant.user, self.user2)

    def test_join_as_smuggler_idempotent(self):
        p1 = CheckpointService.join_as_smuggler(self.user1, self.session)
        p2 = CheckpointService.join_as_smuggler(self.user1, self.session)
        self.assertEqual(p1.pk, p2.pk)

    def test_join_as_patrol_idempotent(self):
        p1 = CheckpointService.join_as_patrol(self.user2, self.session)
        p2 = CheckpointService.join_as_patrol(self.user2, self.session)
        self.assertEqual(p1.pk, p2.pk)


class CheckpointServiceInspectTest(PhantomCityTestCase):
    def setUp(self):
        super().setUp()
        self.zone = make_zone('checkpoint')
        self.session = CheckpointService.create_session(self.zone)
        self.patrol_user = self.user2
        self.target_user = self.user1
        make_mimic(self.target_user)

    def test_inspect_player_returns_tells_and_suspicion(self):
        result = CheckpointService.inspect_player(
            self.patrol_user, self.target_user, self.session
        )
        self.assertIn('tells', result)
        self.assertIn('suspicion_score', result)
        self.assertIn('can_pat_down', result)

    def test_inspect_player_can_pat_down_false_below_threshold(self):
        result = CheckpointService.inspect_player(
            self.patrol_user, self.target_user, self.session
        )
        self.assertFalse(result['can_pat_down'])

    def test_inspect_player_can_pat_down_true_at_threshold(self):
        patrol = PatrolProfile.objects.filter(user=self.patrol_user).first()
        if not patrol:
            patrol = make_patrol(self.patrol_user)
        TellService.add_suspicion(patrol, self.target_user, 30)
        result = CheckpointService.inspect_player(
            self.patrol_user, self.target_user, self.session
        )
        self.assertTrue(result['can_pat_down'])

    def test_inspect_player_auto_creates_patrol_profile(self):
        PatrolProfile.objects.filter(user=self.patrol_user).delete()
        CheckpointService.inspect_player(self.patrol_user, self.target_user, self.session)
        self.assertTrue(PatrolProfile.objects.filter(user=self.patrol_user).exists())


class CheckpointServiceInterrogateTest(PhantomCityTestCase):
    def setUp(self):
        super().setUp()
        self.zone = make_zone('checkpoint')
        self.session = CheckpointService.create_session(self.zone)
        self.patrol_user = self.user2
        self.target_user = self.user1
        make_mimic(self.target_user)

    def test_interrogate_creates_request_with_deadline(self):
        req = CheckpointService.interrogate_player(
            self.patrol_user, self.target_user, self.session, 'What are you carrying?'
        )
        self.assertIsInstance(req, InterrogationRequest)
        self.assertEqual(req.status, 'pending')
        self.assertIsNotNone(req.deadline)
        delta = req.deadline - timezone.now()
        self.assertAlmostEqual(delta.total_seconds(), 30, delta=5)


class CheckpointServiceRespondTest(PhantomCityTestCase):
    def setUp(self):
        super().setUp()
        self.zone = make_zone('checkpoint')
        self.session = CheckpointService.create_session(self.zone)
        self.patrol_user = self.user2
        self.target_user = self.user1
        make_mimic(self.target_user)
        self.req = CheckpointService.interrogate_player(
            self.patrol_user, self.target_user, self.session, 'Where are you going?'
        )

    def test_respond_to_pending_interrogation_succeeds(self):
        result = CheckpointService.respond_to_interrogation(
            self.req, self.target_user, 'Just passing through'
        )
        self.assertIsNotNone(result)

    def test_respond_to_non_pending_returns_none(self):
        self.req.status = 'answered'
        self.req.save()
        result = CheckpointService.respond_to_interrogation(
            self.req, self.target_user, 'Too late'
        )
        self.assertIsNone(result)

    def test_slow_response_adds_suspicion_and_sets_pause_tell(self):
        patrol = PatrolProfile.objects.filter(user=self.patrol_user).first()
        if not patrol:
            patrol = make_patrol(self.patrol_user)

        initial_score = TellService.get_suspicion_score(patrol, self.target_user, self.session)

        # Simulate slow response by patching response_time measurement
        with patch.object(CheckpointService, 'respond_to_interrogation',
                          wraps=CheckpointService.respond_to_interrogation):
            # Manually set response time > 20 via patching time
            self.req.refresh_from_db()
            # Set created_at far in the past to simulate slow response
            self.req.created_at = timezone.now() - timedelta(seconds=25)
            self.req.save()
            CheckpointService.respond_to_interrogation(
                self.req, self.target_user, 'Slow answer'
            )

        self.req.refresh_from_db()
        self.assertTrue(self.req.triggered_pause_tell)


class CheckpointServicePatDownTest(PhantomCityTestCase):
    def setUp(self):
        super().setUp()
        self.zone = make_zone('checkpoint')
        self.session = CheckpointService.create_session(self.zone)
        self.patrol_user = self.user2
        self.target_user = self.user1
        make_mimic(self.target_user)
        self.patrol = make_patrol(self.patrol_user)

    def test_pat_down_fails_when_suspicion_below_30(self):
        result = CheckpointService.pat_down(self.patrol_user, self.target_user, self.session)
        self.assertFalse(result['success'])

    def test_pat_down_fails_when_insufficient_tokens(self):
        TellService.add_suspicion(self.patrol, self.target_user, 30)
        self.patrol.inspection_tokens = 1
        self.patrol.save()
        result = CheckpointService.pat_down(self.patrol_user, self.target_user, self.session)
        self.assertFalse(result['success'])

    def test_pat_down_arrests_when_crystals_found(self):
        TellService.add_suspicion(self.patrol, self.target_user, 30)
        self.patrol.inspection_tokens = 5
        self.patrol.save()
        make_crystals(self.target_user, raw=3)
        result = CheckpointService.pat_down(self.patrol_user, self.target_user, self.session)
        self.assertTrue(result['success'])
        self.assertTrue(result['arrested'])

    def test_pat_down_penalizes_patrol_when_no_contraband(self):
        TellService.add_suspicion(self.patrol, self.target_user, 30)
        self.patrol.inspection_tokens = 5
        self.patrol.reputation_score = 50
        self.patrol.save()
        make_crystals(self.target_user, raw=0)
        result = CheckpointService.pat_down(self.patrol_user, self.target_user, self.session)
        self.assertTrue(result['success'])
        self.assertFalse(result['arrested'])
        self.patrol.refresh_from_db()
        self.assertEqual(self.patrol.reputation_score, 45)

    def test_pat_down_consumes_2_tokens(self):
        TellService.add_suspicion(self.patrol, self.target_user, 30)
        self.patrol.inspection_tokens = 5
        self.patrol.save()
        make_crystals(self.target_user, raw=0)
        CheckpointService.pat_down(self.patrol_user, self.target_user, self.session)
        self.patrol.refresh_from_db()
        self.assertEqual(self.patrol.inspection_tokens, 3)


# ===========================================================================
# DetentionService tests
# ===========================================================================

class DetentionServiceArrestTest(PhantomCityTestCase):
    def setUp(self):
        super().setUp()
        self.control_zone = make_zone('control_room')
        self.captor = self.user3
        self.prisoner = self.user1
        make_patrol(self.captor)
        make_mimic(self.prisoner)
        make_crystals(self.prisoner, raw=5)

    def test_arrest_creates_detention_record(self):
        record = DetentionService.arrest(self.captor, self.prisoner)
        self.assertIsInstance(record, DetentionRecord)

    def test_arrest_seizes_crystals(self):
        DetentionService.arrest(self.captor, self.prisoner)
        crystals = PlayerCrystals.objects.get(user=self.prisoner)
        self.assertEqual(crystals.raw_crystals, 0)

    def test_arrest_creates_12h_detention(self):
        record = DetentionService.arrest(self.captor, self.prisoner)
        duration = record.release_at - record.arrested_at
        self.assertAlmostEqual(duration.total_seconds(), 43200, delta=10)

    def test_arrest_moves_prisoner_to_control_room(self):
        DetentionService.arrest(self.captor, self.prisoner)
        presence = PlayerZonePresence.objects.filter(
            user=self.prisoner, zone=self.control_zone, exited_at=None
        ).first()
        self.assertIsNotNone(presence)

    def test_arrest_decrements_purity(self):
        self.prisoner.mimic_profile.purity_score = 50
        self.prisoner.mimic_profile.save()
        DetentionService.arrest(self.captor, self.prisoner)
        self.prisoner.mimic_profile.refresh_from_db()
        self.assertEqual(self.prisoner.mimic_profile.purity_score, 40)

    def test_arrest_creates_control_transfer_when_active_lock_task(self):
        task = self.create_test_lock_task(self.prisoner)
        self.prisoner.mimic_profile.active_run_lock_task = task
        self.prisoner.mimic_profile.save()
        DetentionService.arrest(self.captor, self.prisoner)
        self.assertTrue(
            GameControlTransfer.objects.filter(grantor=self.prisoner).exists()
        )


class DetentionServiceCharmTest(PhantomCityTestCase):
    def setUp(self):
        super().setUp()
        self.control_zone = make_zone('control_room')
        self.captor = self.user3
        self.prisoner = self.user1
        self.patrol = make_patrol(self.captor, authority_value=20)
        mimic = make_mimic(self.prisoner, purity_score=80)
        make_crystals(self.prisoner)
        self.detention = DetentionService.arrest(self.captor, self.prisoner)

    def test_charm_succeeds_with_valid_conditions(self):
        result = DetentionService.charm_warden(self.prisoner, self.detention)
        self.assertTrue(result['success'])

    def test_charm_fails_when_detention_not_active(self):
        self.detention.status = 'released_timeout'
        self.detention.save()
        result = DetentionService.charm_warden(self.prisoner, self.detention)
        self.assertFalse(result['success'])

    def test_charm_fails_when_no_mimic_profile(self):
        MimicProfile.objects.filter(user=self.prisoner).delete()
        # Refresh prisoner to clear cached mimic_profile relation
        from django.contrib.auth import get_user_model
        User = get_user_model()
        fresh_prisoner = User.objects.get(pk=self.prisoner.pk)
        result = DetentionService.charm_warden(fresh_prisoner, self.detention)
        self.assertFalse(result['success'])

    def test_charm_fails_when_purity_below_70(self):
        self.prisoner.mimic_profile.purity_score = 60
        self.prisoner.mimic_profile.save()
        result = DetentionService.charm_warden(self.prisoner, self.detention)
        self.assertFalse(result['success'])

    def test_charm_fails_when_attempted_within_4h(self):
        DetentionService.charm_warden(self.prisoner, self.detention)
        # Restore purity for second attempt
        self.prisoner.mimic_profile.refresh_from_db()
        self.prisoner.mimic_profile.purity_score = 80
        self.prisoner.mimic_profile.save()
        result = DetentionService.charm_warden(self.prisoner, self.detention)
        self.assertFalse(result['success'])

    def test_charm_fails_when_patrol_authority_too_high(self):
        # setUp creates captor with authority=20; use a separate user/detention with authority=50
        from django.contrib.auth import get_user_model
        User = get_user_model()
        strong_captor = User.objects.create_user(
            username='strong_captor', email='sc@test.com', password='p'
        )
        make_patrol(strong_captor, authority_value=50)
        weak_prisoner = User.objects.create_user(
            username='weak_prisoner', email='wp@test.com', password='p'
        )
        make_mimic(weak_prisoner, purity_score=80)
        make_crystals(weak_prisoner)
        make_zone('control_room')
        detention2 = DetentionService.arrest(strong_captor, weak_prisoner)
        result = DetentionService.charm_warden(weak_prisoner, detention2)
        self.assertFalse(result["success"])
        self.assertIn('威权值过高', result.get('error', ''))

    def test_charm_reduces_captor_authority(self):
        initial_authority = self.patrol.authority_value
        result = DetentionService.charm_warden(self.prisoner, self.detention)
        self.assertTrue(result['success'])
        self.patrol.refresh_from_db()
        self.assertLess(self.patrol.authority_value, initial_authority)

    def test_charm_triggers_faction_conversion_when_authority_reaches_zero(self):
        # Create fresh captor with low authority to avoid cached PatrolProfile issue
        from django.contrib.auth import get_user_model
        User = get_user_model()
        weak_captor = User.objects.create_user(
            username='weak_captor', email='wc@test.com', password='p'
        )
        # authority=5 so drain of 10 reaches 0
        make_patrol(weak_captor, authority_value=5)
        prisoner2 = User.objects.create_user(
            username='prisoner2', email='p2@test.com', password='p'
        )
        make_mimic(prisoner2, purity_score=80)
        make_crystals(prisoner2)
        make_zone('control_room')
        make_zone('salon')
        detention2 = DetentionService.arrest(weak_captor, prisoner2)
        with patch('random.randint', return_value=10):
            result = DetentionService.charm_warden(prisoner2, detention2)
        self.assertTrue(result['success'])
        self.assertTrue(result.get('conversion_triggered', False))
        self.assertTrue(
            FactionConversionEvent.objects.filter(converted_user=weak_captor).exists()
        )
        self.assertTrue(MimicProfile.objects.filter(user=weak_captor).exists())


class DetentionServiceReleaseTest(PhantomCityTestCase):
    def setUp(self):
        super().setUp()
        self.control_zone = make_zone('control_room')
        self.salon_zone = make_zone('salon')
        self.captor = self.user3
        self.prisoner = self.user1
        make_patrol(self.captor)
        make_mimic(self.prisoner)
        make_crystals(self.prisoner)
        self.detention = DetentionService.arrest(self.captor, self.prisoner)

    def test_release_sets_status(self):
        DetentionService.release(self.detention)
        self.detention.refresh_from_db()
        self.assertEqual(self.detention.status, 'released_timeout')

    def test_release_sets_released_at(self):
        DetentionService.release(self.detention)
        self.detention.refresh_from_db()
        self.assertIsNotNone(self.detention.released_at)

    def test_release_moves_prisoner_to_salon(self):
        DetentionService.release(self.detention)
        presence = PlayerZonePresence.objects.filter(
            user=self.prisoner, zone=self.salon_zone, exited_at=None
        ).first()
        self.assertIsNotNone(presence)

    def test_release_revokes_control_transfer(self):
        task = self.create_test_lock_task(self.prisoner)
        self.prisoner.mimic_profile.active_run_lock_task = task
        self.prisoner.mimic_profile.save()
        detention = DetentionService.arrest(self.captor, self.prisoner)
        transfer = GameControlTransfer.objects.get(grantor=self.prisoner)
        DetentionService.release(detention)
        transfer.refresh_from_db()
        self.assertFalse(transfer.is_active)


# ===========================================================================
# TransactionService tests
# ===========================================================================

class TransactionServiceBribeTest(PhantomCityTestCase):
    def setUp(self):
        super().setUp()
        self.zone = make_zone('checkpoint')
        self.session = CheckpointService.create_session(self.zone)
        self.smuggler = self.user1
        self.patrol_user = self.user2
        make_mimic(self.smuggler)
        make_patrol(self.patrol_user)
        make_crystals(self.smuggler, raw=10)
        make_crystals(self.patrol_user)

    def test_propose_bribe_success(self):
        offer = {'crystals': 5}
        result = TransactionService.propose_bribe(
            self.smuggler, self.patrol_user, offer, self.session
        )
        self.assertTrue(result['success'])
        self.assertIn('transaction', result)
        self.assertIn('channel', result)

    def test_propose_bribe_fails_insufficient_crystals(self):
        offer = {'crystals': 20}
        result = TransactionService.propose_bribe(
            self.smuggler, self.patrol_user, offer, self.session
        )
        self.assertFalse(result['success'])

    def test_propose_bribe_escrows_crystals(self):
        offer = {'crystals': 5}
        TransactionService.propose_bribe(self.smuggler, self.patrol_user, offer, self.session)
        crystals = PlayerCrystals.objects.get(user=self.smuggler)
        self.assertEqual(crystals.raw_crystals, 5)

    def test_propose_bribe_creates_encrypted_channel(self):
        offer = {'crystals': 5}
        result = TransactionService.propose_bribe(
            self.smuggler, self.patrol_user, offer, self.session
        )
        self.assertIsInstance(result['channel'], EncryptedChannel)

    def test_accept_bribe_transfers_crystals_to_patrol(self):
        offer = {'crystals': 5}
        result = TransactionService.propose_bribe(
            self.smuggler, self.patrol_user, offer, self.session
        )
        tx = result['transaction']
        accept_result = TransactionService.accept_bribe(tx, self.patrol_user)
        self.assertTrue(accept_result['success'])
        patrol_crystals = PlayerCrystals.objects.get(user=self.patrol_user)
        self.assertEqual(patrol_crystals.purified_crystals, 5)

    def test_accept_bribe_sets_status_completed(self):
        offer = {'crystals': 5}
        result = TransactionService.propose_bribe(
            self.smuggler, self.patrol_user, offer, self.session
        )
        tx = result['transaction']
        TransactionService.accept_bribe(tx, self.patrol_user)
        tx.refresh_from_db()
        self.assertEqual(tx.status, 'completed')

    def test_accept_bribe_fails_when_not_negotiating(self):
        offer = {'crystals': 5}
        result = TransactionService.propose_bribe(
            self.smuggler, self.patrol_user, offer, self.session
        )
        tx = result['transaction']
        tx.status = 'completed'
        tx.save()
        accept_result = TransactionService.accept_bribe(tx, self.patrol_user)
        self.assertFalse(accept_result['success'])

    def test_betray_after_bribe_sets_betrayed_status(self):
        offer = {'crystals': 5}
        result = TransactionService.propose_bribe(
            self.smuggler, self.patrol_user, offer, self.session
        )
        tx = result['transaction']
        TransactionService.accept_bribe(tx, self.patrol_user)
        betray_result = TransactionService.betray_after_bribe(tx, self.patrol_user)
        self.assertFalse(betray_result['success'] is False)
        tx.refresh_from_db()
        self.assertEqual(tx.status, 'betrayed')

    def test_betray_deducts_patrol_reputation(self):
        # Default reputation is 60; after 40% deduction: 60 - 24 = 36
        offer = {'crystals': 5}
        result = TransactionService.propose_bribe(
            self.smuggler, self.patrol_user, offer, self.session
        )
        tx = result["transaction"]
        TransactionService.accept_bribe(tx, self.patrol_user)
        TransactionService.betray_after_bribe(tx, self.patrol_user)
        patrol = PatrolProfile.objects.get(user=self.patrol_user)
        # 60 - int(60 * 0.4) = 60 - 24 = 36
        self.assertEqual(patrol.reputation_score, 36)

    def test_betray_fails_when_not_completed(self):
        offer = {'crystals': 5}
        result = TransactionService.propose_bribe(
            self.smuggler, self.patrol_user, offer, self.session
        )
        tx = result['transaction']
        betray_result = TransactionService.betray_after_bribe(tx, self.patrol_user)
        self.assertFalse(betray_result['success'])


class TransactionServiceExtortionTest(PhantomCityTestCase):
    def setUp(self):
        super().setUp()
        self.zone = make_zone('checkpoint')
        self.session = CheckpointService.create_session(self.zone)
        self.patrol_user = self.user2
        self.target_user = self.user1
        self.patrol = make_patrol(self.patrol_user)
        make_mimic(self.target_user)
        make_crystals(self.target_user, raw=10)
        make_crystals(self.patrol_user)

    def test_propose_extortion_fails_when_suspicion_below_20(self):
        demand = {'crystals': 3}
        result = TransactionService.propose_extortion(
            self.patrol_user, self.target_user, demand, self.session
        )
        self.assertFalse(result['success'])

    def test_propose_extortion_succeeds_when_suspicion_high(self):
        TellService.add_suspicion(self.patrol, self.target_user, 25)
        demand = {'crystals': 3}
        result = TransactionService.propose_extortion(
            self.patrol_user, self.target_user, demand, self.session
        )
        self.assertTrue(result['success'])

    def test_pay_extortion_transfers_crystals(self):
        TellService.add_suspicion(self.patrol, self.target_user, 25)
        demand = {'crystals': 3}
        result = TransactionService.propose_extortion(
            self.patrol_user, self.target_user, demand, self.session
        )
        tx = result['transaction']
        pay_result = TransactionService.pay_extortion(tx, self.target_user)
        self.assertTrue(pay_result['success'])
        target_crystals = PlayerCrystals.objects.get(user=self.target_user)
        self.assertEqual(target_crystals.raw_crystals, 7)

    def test_pay_extortion_fails_insufficient_crystals(self):
        TellService.add_suspicion(self.patrol, self.target_user, 25)
        demand = {'crystals': 20}
        result = TransactionService.propose_extortion(
            self.patrol_user, self.target_user, demand, self.session
        )
        tx = result['transaction']
        pay_result = TransactionService.pay_extortion(tx, self.target_user)
        self.assertFalse(pay_result['success'])


# ===========================================================================
# DisguiseService tests
# ===========================================================================

class DisguiseServiceDetectabilityTest(PhantomCityTestCase):
    def setUp(self):
        super().setUp()
        self.mimic = make_mimic(self.user1, base_detectability=20, femboy_score=40)

    def test_compute_detectability_no_disguise(self):
        result = DisguiseService.compute_detectability(self.mimic)
        expected = 20 + 40 // 10
        self.assertEqual(result, expected)

    def test_compute_detectability_clamped_to_100(self):
        self.mimic.base_detectability = 95
        self.mimic.suppression_value = 80
        self.mimic.save()
        result = DisguiseService.compute_detectability(self.mimic)
        self.assertLessEqual(result, 100)

    def test_compute_detectability_clamped_to_0(self):
        self.mimic.base_detectability = 0
        self.mimic.femboy_score = 0
        self.mimic.save()
        result = DisguiseService.compute_detectability(self.mimic)
        self.assertGreaterEqual(result, 0)

    def test_compute_detectability_adds_suppression_penalty_when_high(self):
        from phantom_city.models import ActiveDisguise
        disguise = ActiveDisguise.objects.create(user=self.user1)
        self.mimic.suppression_value = 80
        self.mimic.save()
        result_high = DisguiseService.compute_detectability(self.mimic, disguise)
        self.mimic.suppression_value = 50
        self.mimic.save()
        result_low = DisguiseService.compute_detectability(self.mimic, disguise)
        self.assertEqual(result_high - result_low, 10)


class DisguiseServiceQualityTest(PhantomCityTestCase):
    def setUp(self):
        super().setUp()

    def test_compute_disguise_quality_no_disguise_returns_0(self):
        result = DisguiseService.compute_disguise_quality(None)
        self.assertEqual(result, 0)


# ===========================================================================
# CrystalService tests
# ===========================================================================

class CrystalServiceHarvestTest(PhantomCityTestCase):
    def setUp(self):
        super().setUp()
        self.ruins_zone = make_zone('ruins')
        self.mimic = make_mimic(
            self.user1,
            femboy_score=50,
            total_crystals_collected=0
        )
        make_crystals(self.user1, raw=0)
        make_presence(self.user1, self.ruins_zone)
        self.deposit = CrystalDeposit.objects.create(zone=self.ruins_zone, quantity=10)
        self.lock_task = self.create_test_lock_task(self.user1)

    def test_harvest_success(self):
        with patch('random.randint', return_value=2):
            result = CrystalService.harvest(self.user1, self.deposit)
        self.assertTrue(result['success'])

    def test_harvest_fails_when_no_mimic_profile(self):
        MimicProfile.objects.filter(user=self.user2).delete()
        result = CrystalService.harvest(self.user2, self.deposit)
        self.assertFalse(result['success'])

    def test_harvest_fails_when_not_in_ruins(self):
        salon = make_zone('salon')
        PlayerZonePresence.objects.filter(user=self.user1).update(
            exited_at=timezone.now()
        )
        make_presence(self.user1, salon)
        result = CrystalService.harvest(self.user1, self.deposit)
        self.assertFalse(result['success'])

    def test_harvest_fails_when_deposit_empty(self):
        self.deposit.quantity = 0
        self.deposit.save()
        result = CrystalService.harvest(self.user1, self.deposit)
        self.assertFalse(result['success'])

    def test_harvest_updates_player_crystals(self):
        with patch('random.randint', return_value=2):
            result = CrystalService.harvest(self.user1, self.deposit)
        crystals = PlayerCrystals.objects.get(user=self.user1)
        self.assertGreater(crystals.raw_crystals, 0)

    def test_harvest_updates_deposit_quantity(self):
        initial_qty = self.deposit.quantity
        with patch('random.randint', return_value=2):
            result = CrystalService.harvest(self.user1, self.deposit)
        self.deposit.refresh_from_db()
        self.assertLess(self.deposit.quantity, initial_qty)

    def test_harvest_updates_total_crystals_collected(self):
        with patch('random.randint', return_value=2):
            CrystalService.harvest(self.user1, self.deposit)
        self.mimic.refresh_from_db()
        self.assertGreater(self.mimic.total_crystals_collected, 0)

    def test_harvest_returns_harvested_and_remaining(self):
        with patch('random.randint', return_value=2):
            result = CrystalService.harvest(self.user1, self.deposit)
        self.assertIn('harvested', result)
        self.assertIn('remaining', result)


class CrystalServiceMarketRateTest(PhantomCityTestCase):
    def setUp(self):
        super().setUp()

    def test_recalculate_market_rates(self):
        rate = GameMarketRate.objects.create(
            base_price_crystals=10, item_slug="test_item_1", item_display_name="Test 1",
            current_price_crystals=10,
            demand_pressure=1.5,
            units_traded_last_period=100
        )
        CrystalService.recalculate_market_rates()
        rate.refresh_from_db()
        self.assertEqual(rate.current_price_crystals, 15)
        self.assertEqual(rate.units_traded_last_period, 0)

    def test_recalculate_market_rates_minimum_price_is_1(self):
        rate = GameMarketRate.objects.create(
            base_price_crystals=1, item_slug="test_item_2", item_display_name="Test 2",
            current_price_crystals=1,
            demand_pressure=0.0,
            units_traded_last_period=5
        )
        CrystalService.recalculate_market_rates()
        rate.refresh_from_db()
        self.assertEqual(rate.current_price_crystals, 1)


# ===========================================================================
# ControlTransferService tests
# ===========================================================================

class ControlTransferServiceTest(PhantomCityTestCase):
    def setUp(self):
        super().setUp()
        self.control_zone = make_zone('control_room')
        self.salon_zone = make_zone('salon')
        self.captor = self.user3
        self.prisoner = self.user1
        make_patrol(self.captor)
        mimic = make_mimic(self.prisoner)
        make_crystals(self.prisoner)
        task = self.create_test_lock_task(self.prisoner)
        mimic.active_run_lock_task = task
        mimic.save()
        self.task = task
        self.detention = DetentionService.arrest(self.captor, self.prisoner)
        self.transfer = GameControlTransfer.objects.get(
            grantor=self.prisoner
        )

    def test_add_time_success(self):
        original_end = self.task.end_time
        result = ControlTransferService.add_time(self.transfer, self.captor, 30)
        self.assertTrue(result['success'])
        self.task.refresh_from_db()
        expected = original_end + timedelta(minutes=30)
        self.assertAlmostEqual(
            self.task.end_time.timestamp(), expected.timestamp(), delta=1
        )

    def test_add_time_fails_when_transfer_inactive(self):
        self.transfer.is_active = False
        self.transfer.save()
        result = ControlTransferService.add_time(self.transfer, self.captor, 30)
        self.assertFalse(result['success'])

    def test_add_time_fails_when_wrong_grantee(self):
        result = ControlTransferService.add_time(self.transfer, self.user2, 30)
        self.assertFalse(result['success'])

    def test_add_time_fails_when_can_add_time_false(self):
        self.transfer.can_add_time = False
        self.transfer.save()
        result = ControlTransferService.add_time(self.transfer, self.captor, 30)
        self.assertFalse(result['success'])

    def test_freeze_success(self):
        result = ControlTransferService.freeze(self.transfer, self.captor)
        self.assertTrue(result['success'])
        self.task.refresh_from_db()
        self.assertTrue(self.task.is_frozen)
        self.assertIsNotNone(self.task.frozen_at)
        self.assertIsNotNone(self.task.frozen_end_time)

    def test_freeze_fails_when_transfer_inactive(self):
        self.transfer.is_active = False
        self.transfer.save()
        result = ControlTransferService.freeze(self.transfer, self.captor)
        self.assertFalse(result['success'])

    def test_freeze_fails_when_wrong_grantee(self):
        result = ControlTransferService.freeze(self.transfer, self.user2)
        self.assertFalse(result['success'])

    def test_freeze_fails_when_can_freeze_false(self):
        self.transfer.can_freeze = False
        self.transfer.save()
        result = ControlTransferService.freeze(self.transfer, self.captor)
        self.assertFalse(result['success'])


# ===========================================================================
# ZoneService tests
# ===========================================================================

class ZoneServiceTravelTest(PhantomCityTestCase):
    def setUp(self):
        super().setUp()
        self.salon = make_zone('salon')
        self.ruins = make_zone('ruins')
        self.checkpoint = make_zone('checkpoint')
        self.control_room = make_zone('control_room')

    def test_travel_to_valid_zone_succeeds(self):
        result = ZoneService.travel_to(self.user1, 'salon')
        self.assertTrue(result['success'])

    def test_travel_to_nonexistent_zone_fails(self):
        result = ZoneService.travel_to(self.user1, 'nonexistent_zone')
        self.assertFalse(result['success'])

    def test_travel_to_same_zone_fails(self):
        ZoneService.travel_to(self.user1, 'salon')
        result = ZoneService.travel_to(self.user1, 'salon')
        self.assertFalse(result['success'])

    def test_travel_exits_current_zone(self):
        ZoneService.travel_to(self.user1, 'salon')
        ZoneService.travel_to(self.user1, 'checkpoint')
        old = PlayerZonePresence.objects.filter(
            user=self.user1, zone=self.salon
        ).first()
        self.assertIsNotNone(old.exited_at)

    def test_travel_creates_zone_presence(self):
        ZoneService.travel_to(self.user1, 'salon')
        presence = PlayerZonePresence.objects.filter(
            user=self.user1, zone=self.salon, exited_at=None
        ).first()
        self.assertIsNotNone(presence)

    def test_travel_creates_system_chat_message(self):
        ZoneService.travel_to(self.user1, 'salon')
        msg = ZoneChatMessage.objects.filter(zone=self.salon).first()
        self.assertIsNotNone(msg)

    def test_travel_to_checkpoint_auto_joins_as_smuggler(self):
        session = CheckpointService.get_or_create_active_session(self.checkpoint)
        ZoneService.travel_to(self.user1, 'checkpoint')
        participant = CheckpointParticipant.objects.filter(
            user=self.user1, session=session, role='smuggler'
        ).first()
        self.assertIsNotNone(participant)

    def test_travel_to_salon_reduces_suppression(self):
        mimic = make_mimic(self.user1, suppression_value=30)
        ZoneService.travel_to(self.user1, 'salon')
        mimic.refresh_from_db()
        self.assertEqual(mimic.suppression_value, 15)

    def test_travel_to_salon_suppression_min_0(self):
        mimic = make_mimic(self.user1, suppression_value=5)
        ZoneService.travel_to(self.user1, 'salon')
        mimic.refresh_from_db()
        self.assertGreaterEqual(mimic.suppression_value, 0)

    def test_travel_blocked_when_detained_and_not_control_room(self):
        make_patrol(self.user3)
        make_mimic(self.user1)
        make_crystals(self.user1)
        DetentionService.arrest(self.user3, self.user1)
        result = ZoneService.travel_to(self.user1, 'salon')
        self.assertFalse(result['success'])

    def test_travel_allowed_to_control_room_when_detained(self):
        make_patrol(self.user3)
        make_mimic(self.user1)
        make_crystals(self.user1)
        # Arrest moves prisoner to control_room, so we need to test from there
        # First travel somewhere else so arrest can move them there
        # This tests that the detention check allows control_room destination
        detention = DetentionService.arrest(self.user3, self.user1)
        # Move out of control_room manually for the test
        PlayerZonePresence.objects.filter(
            user=self.user1, exited_at=None
        ).update(exited_at=timezone.now())
        result = ZoneService.travel_to(self.user1, 'control_room')
        self.assertTrue(result['success'])


class ZoneServiceSpeakTest(PhantomCityTestCase):
    def setUp(self):
        super().setUp()
        self.zone = make_zone('salon')
        ZoneService.travel_to(self.user1, 'salon')

    def test_speak_creates_chat_message(self):
        result = ZoneService.speak(self.user1, self.zone, 'Hello there')
        self.assertTrue(result['success'])
        self.assertIsInstance(result['message'], ZoneChatMessage)

    def test_speak_fails_when_player_not_in_zone(self):
        result = ZoneService.speak(self.user2, self.zone, 'Hello')
        self.assertFalse(result['success'])

    def test_speak_in_checkpoint_evaluates_tells(self):
        checkpoint_zone = make_zone('checkpoint')
        make_mimic(self.user1, depilation_charge=10)
        ZoneService.travel_to(self.user1, 'checkpoint')
        with patch('random.random', return_value=0.0):
            result = ZoneService.speak(self.user1, checkpoint_zone, 'Just passing')
        self.assertIn('tells', result)

    def test_speak_in_salon_returns_empty_tells(self):
        result = ZoneService.speak(self.user1, self.zone, 'Hello')
        self.assertTrue(result['success'])
        tells = result.get('tells', [])
        self.assertEqual(tells, [])
