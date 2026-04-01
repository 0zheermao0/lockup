import json
from datetime import timedelta
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from tests.phantom_city.base import PhantomCityAPITestCase
from phantom_city.models import (
    GameZone, PlayerZonePresence, MimicProfile, PatrolProfile,
    CheckpointSession, CheckpointParticipant, InterrogationRequest,
    GrayMarketTransaction, DetentionRecord, GameControlTransfer,
    EncryptedChannel, PlayerCrystals, CrystalDeposit, GameItem,
    PlayerGameInventory, ActiveDisguise, SmuggleRun,
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


def make_presence(user, zone, exited_at=None):
    return PlayerZonePresence.objects.create(
        user=user,
        zone=zone,
        entered_at=timezone.now(),
        exited_at=exited_at,
    )


# ===========================================================================
# Base mixin for DRF token auth
# ===========================================================================

class APIAuthMixin:
    def setUp(self):
        super().setUp()
        self.api_client = APIClient()

    def authenticate_api(self, user):
        token, _ = Token.objects.get_or_create(user=user)
        self.api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def clear_auth(self):
        self.api_client.credentials()


# ===========================================================================
# Game Profile
# ===========================================================================

class GameProfileViewTest(PhantomCityAPITestCase):
    def test_profile_unauthenticated_returns_401(self):
        response = self.api_client.get('/api/game/profile/')
        self.assertIn(response.status_code, [401, 403])

    def test_profile_authenticated_returns_200(self):
        self.authenticate(self.user1)
        response = self.api_client.get('/api/game/profile/')
        self.assertEqual(response.status_code, 200)

    def test_profile_includes_user_data(self):
        self.authenticate(self.user1)
        response = self.api_client.get('/api/game/profile/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('mimic_profile', data)


# ===========================================================================
# Faction Choice
# ===========================================================================

class FactionChooseViewTest(PhantomCityAPITestCase):
    def test_choose_faction_unauthenticated_returns_401(self):
        response = self.api_client.post(
            '/api/game/profile/faction/',
            {'faction': 'mimic'},
            format='json'
        )
        self.assertIn(response.status_code, [401, 403])

    def test_choose_mimic_faction_creates_profile(self):
        self.authenticate(self.user1)
        response = self.api_client.post(
            '/api/game/profile/faction/',
            {'faction': 'mimic'},
            format='json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(MimicProfile.objects.filter(user=self.user1).exists())

    def test_choose_patrol_faction_creates_profile(self):
        self.authenticate(self.user2)
        response = self.api_client.post(
            '/api/game/profile/faction/',
            {'faction': 'patrol'},
            format='json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(PatrolProfile.objects.filter(user=self.user2).exists())

    def test_choose_invalid_faction_returns_400(self):
        self.authenticate(self.user1)
        response = self.api_client.post(
            '/api/game/profile/faction/',
            {'faction': 'invalid_faction'},
            format='json'
        )
        self.assertEqual(response.status_code, 400)

    def test_choose_faction_missing_body_returns_400(self):
        self.authenticate(self.user1)
        response = self.api_client.post(
            '/api/game/profile/faction/',
            {},
            format='json'
        )
        self.assertEqual(response.status_code, 400)


# ===========================================================================
# Zone Travel
# ===========================================================================

class ZoneTravelViewTest(PhantomCityAPITestCase):
    def setUp(self):
        super().setUp()
        make_zone('salon')
        make_zone('ruins')
        make_zone('checkpoint')
        make_zone('control_room')

    def test_zone_travel_unauthenticated_returns_401(self):
        response = self.api_client.post(
            '/api/game/zones/travel/',
            {'zone': 'salon'},
            format='json'
        )
        self.assertIn(response.status_code, [401, 403])

    def test_zone_travel_to_salon_succeeds(self):
        self.authenticate(self.user1)
        response = self.api_client.post(
            '/api/game/zones/travel/',
            {'zone': 'salon'},
            format='json'
        )
        self.assertEqual(response.status_code, 200)

    def test_zone_travel_to_invalid_zone_returns_400(self):
        self.authenticate(self.user1)
        response = self.api_client.post(
            '/api/game/zones/travel/',
            {'zone': 'the_void'},
            format='json'
        )
        self.assertEqual(response.status_code, 400)

    def test_zone_travel_creates_presence_record(self):
        self.authenticate(self.user1)
        self.api_client.post('/api/game/zones/travel/', {'zone': 'checkpoint'}, format='json')
        self.api_client.post('/api/game/zones/travel/', {'zone': 'ruins'}, format='json')
        zone = GameZone.objects.get(name='ruins')
        self.assertTrue(
            PlayerZonePresence.objects.filter(
                user=self.user1, zone=zone, exited_at=None
            ).exists()
        )

    def test_zone_travel_to_same_zone_returns_400(self):
        self.authenticate(self.user1)
        self.api_client.post('/api/game/zones/travel/', {'zone': 'salon'}, format='json')
        response = self.api_client.post(
            '/api/game/zones/travel/', {'zone': 'salon'}, format='json'
        )
        self.assertEqual(response.status_code, 400)


# ===========================================================================
# Zone Speak
# ===========================================================================

class ZoneSpeakViewTest(PhantomCityAPITestCase):
    def setUp(self):
        super().setUp()
        self.zone = make_zone('salon')

    def test_zone_speak_unauthenticated_returns_401(self):
        response = self.api_client.post(
            '/api/game/zones/salon/speak/',
            {'content': 'hello'},
            format='json'
        )
        self.assertIn(response.status_code, [401, 403])

    def test_zone_speak_succeeds_when_in_zone(self):
        make_presence(self.user1, self.zone)
        self.authenticate(self.user1)
        response = self.api_client.post(
            '/api/game/zones/salon/speak/',
            {'content': 'hello'},
            format='json'
        )
        self.assertEqual(response.status_code, 200)

    def test_zone_speak_fails_when_not_in_zone(self):
        self.authenticate(self.user1)
        response = self.api_client.post(
            '/api/game/zones/salon/speak/',
            {'content': 'hello'},
            format='json'
        )
        self.assertEqual(response.status_code, 400)

    def test_zone_speak_missing_content_returns_400(self):
        make_presence(self.user1, self.zone)
        self.authenticate(self.user1)
        response = self.api_client.post(
            '/api/game/zones/salon/speak/',
            {},
            format='json'
        )
        self.assertEqual(response.status_code, 400)


# ===========================================================================
# Checkpoint Session
# ===========================================================================

class CheckpointSessionViewTest(PhantomCityAPITestCase):
    def setUp(self):
        super().setUp()
        self.zone = make_zone('checkpoint')

    def test_checkpoint_session_unauthenticated_returns_401(self):
        response = self.api_client.get('/api/game/checkpoint/session/')
        self.assertIn(response.status_code, [401, 403])

    def test_checkpoint_session_returns_active_session(self):
        session = CheckpointSession.objects.create(zone=self.zone, status='active')
        self.authenticate(self.user1)
        response = self.api_client.get('/api/game/checkpoint/session/')
        self.assertEqual(response.status_code, 200)


# ===========================================================================
# Checkpoint Inspect
# ===========================================================================

class CheckpointInspectViewTest(PhantomCityAPITestCase):
    def setUp(self):
        super().setUp()
        self.zone = make_zone('checkpoint')
        self.session = CheckpointSession.objects.create(zone=self.zone, status='active')
        CheckpointParticipant.objects.create(
            user=self.user2, session=self.session, role='patrol'
        )
        CheckpointParticipant.objects.create(
            user=self.user1, session=self.session, role='smuggler'
        )
        make_mimic(self.user1)

    def test_checkpoint_inspect_unauthenticated_returns_401(self):
        response = self.api_client.post(
            '/api/game/checkpoint/inspect/',
            {'target_id': self.user1.pk},
            format='json'
        )
        self.assertIn(response.status_code, [401, 403])

    def test_checkpoint_inspect_succeeds(self):
        self.authenticate(self.user2)
        response = self.api_client.post(
            '/api/game/checkpoint/inspect/',
            {'target_id': self.user1.pk, 'session_id': str(self.session.pk)},
            format='json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('suspicion_score', data)

    def test_checkpoint_inspect_missing_target_returns_400(self):
        self.authenticate(self.user2)
        response = self.api_client.post(
            '/api/game/checkpoint/inspect/',
            {},
            format='json'
        )
        self.assertEqual(response.status_code, 400)


# ===========================================================================
# Checkpoint Interrogate
# ===========================================================================

class CheckpointInterrogateViewTest(PhantomCityAPITestCase):
    def setUp(self):
        super().setUp()
        self.zone = make_zone('checkpoint')
        self.session = CheckpointSession.objects.create(zone=self.zone, status='active')
        CheckpointParticipant.objects.create(
            user=self.user2, session=self.session, role='patrol'
        )
        CheckpointParticipant.objects.create(
            user=self.user1, session=self.session, role='smuggler'
        )
        make_mimic(self.user1)

    def test_interrogate_unauthenticated_returns_401(self):
        response = self.api_client.post(
            '/api/game/checkpoint/interrogate/',
            {'target_id': self.user1.pk, 'question': 'Where are you going?'},
            format='json'
        )
        self.assertIn(response.status_code, [401, 403])

    def test_interrogate_creates_request(self):
        self.authenticate(self.user2)
        response = self.api_client.post(
            '/api/game/checkpoint/interrogate/',
            {'target_id': self.user1.pk, 'question': 'Where are you going?',
             'session_id': str(self.session.pk)},
            format='json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            InterrogationRequest.objects.filter(
                target=self.user1, status='pending'
            ).exists()
        )

    def test_interrogate_missing_target_returns_400(self):
        self.authenticate(self.user2)
        response = self.api_client.post(
            '/api/game/checkpoint/interrogate/',
            {'session_id': str(self.session.pk)},
            format='json'
        )
        self.assertEqual(response.status_code, 400)


# ===========================================================================
# Bribe Flow
# ===========================================================================

class BribeViewTest(PhantomCityAPITestCase):
    def setUp(self):
        super().setUp()
        self.zone = make_zone('checkpoint')
        self.session = CheckpointSession.objects.create(zone=self.zone, status='active')
        make_mimic(self.user1)
        make_patrol(self.user2)
        make_crystals(self.user1, raw=10)
        make_crystals(self.user2)

    def test_bribe_propose_unauthenticated_returns_401(self):
        response = self.api_client.post(
            '/api/game/bribe/propose/',
            {'recipient_id': self.user2.pk, 'offer': {'crystals': 5}},
            format='json'
        )
        self.assertIn(response.status_code, [401, 403])

    def test_bribe_propose_succeeds(self):
        self.authenticate(self.user1)
        response = self.api_client.post(
            '/api/game/bribe/propose/',
            {'recipient_id': self.user2.pk, 'offer': {'crystals': 5}},
            format='json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success'))

    def test_bribe_propose_fails_insufficient_crystals(self):
        self.authenticate(self.user1)
        response = self.api_client.post(
            '/api/game/bribe/propose/',
            {'recipient_id': self.user2.pk, 'offer': {'crystals': 50}},
            format='json'
        )
        self.assertEqual(response.status_code, 400)

    def test_bribe_accept_succeeds(self):
        self.authenticate(self.user1)
        propose_response = self.api_client.post(
            '/api/game/bribe/propose/',
            {'recipient_id': self.user2.pk, 'offer': {'crystals': 5}},
            format='json'
        )
        tx_id = propose_response.json()['transaction']['id']

        self.authenticate(self.user2)
        response = self.api_client.post(
            f'/api/game/bribe/{tx_id}/accept/',
            format='json'
        )
        self.assertEqual(response.status_code, 200)

    def test_bribe_counter_offer_succeeds(self):
        self.authenticate(self.user1)
        propose_response = self.api_client.post(
            '/api/game/bribe/propose/',
            {'recipient_id': self.user2.pk, 'offer': {'crystals': 5}},
            format='json'
        )
        self.assertEqual(propose_response.status_code, 200)
        tx_id = propose_response.json()['transaction']['id']

        self.authenticate(self.user2)
        response = self.api_client.post(
            f'/api/game/bribe/{tx_id}/counter/',
            {'offer': {'crystals': 3}},
            format='json'
        )
        self.assertEqual(response.status_code, 200)


# ===========================================================================
# Extortion Flow
# ===========================================================================

class ExtortionViewTest(PhantomCityAPITestCase):
    def setUp(self):
        super().setUp()
        self.zone = make_zone('checkpoint')
        self.session = CheckpointSession.objects.create(zone=self.zone, status='active')
        self.patrol = make_patrol(self.user2)
        make_mimic(self.user1)
        make_crystals(self.user1, raw=10)
        make_crystals(self.user2)
        CheckpointParticipant.objects.create(
            user=self.user2, session=self.session, role='patrol'
        )
        CheckpointParticipant.objects.create(
            user=self.user1, session=self.session, role='smuggler'
        )

    def test_extort_demand_unauthenticated_returns_401(self):
        response = self.api_client.post(
            '/api/game/extort/demand/',
            {'target_id': self.user1.pk, 'demand': {'crystals': 3}},
            format='json'
        )
        self.assertIn(response.status_code, [401, 403])

    def test_extort_demand_fails_when_low_suspicion(self):
        self.authenticate(self.user2)
        response = self.api_client.post(
            '/api/game/extort/demand/',
            {'target_id': self.user1.pk, 'demand': {'crystals': 3}},
            format='json'
        )
        self.assertEqual(response.status_code, 400)

    def test_extort_pay_unauthenticated_returns_401(self):
        from phantom_city.services import TellService, TransactionService
        TellService.add_suspicion(self.patrol, self.user1, 25)
        result = TransactionService.propose_extortion(
            self.user2, self.user1, {'crystals': 3}, self.session
        )
        tx = result['transaction']
        response = self.api_client.post(f'/api/game/extort/{tx.pk}/pay/', format='json')
        self.assertIn(response.status_code, [401, 403])


# ===========================================================================
# Detention Charm Warden
# ===========================================================================

class DetentionCharmViewTest(PhantomCityAPITestCase):
    def setUp(self):
        super().setUp()
        make_zone('control_room')
        make_zone('salon')
        self.captor = self.user3
        self.prisoner = self.user1
        make_patrol(self.captor, authority_value=20)
        make_mimic(self.prisoner, purity_score=80)
        make_crystals(self.prisoner)
        from phantom_city.services import DetentionService
        self.detention = DetentionService.arrest(self.captor, self.prisoner)

    def test_charm_warden_unauthenticated_returns_401(self):
        response = self.api_client.post(
            f'/api/game/detention/{self.detention.pk}/charm_warden/',
            format='json'
        )
        self.assertIn(response.status_code, [401, 403])

    def test_charm_warden_succeeds_with_valid_prisoner(self):
        self.authenticate(self.prisoner)
        response = self.api_client.post(
            f'/api/game/detention/{self.detention.pk}/charm_warden/',
            format='json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success'))

    def test_charm_warden_fails_when_purity_low(self):
        self.prisoner.mimic_profile.purity_score = 50
        self.prisoner.mimic_profile.save()
        self.authenticate(self.prisoner)
        response = self.api_client.post(
            f'/api/game/detention/{self.detention.pk}/charm_warden/',
            format='json'
        )
        self.assertEqual(response.status_code, 400)


# ===========================================================================
# Detention Release (admin only)
# ===========================================================================

class DetentionMyViewTest(PhantomCityAPITestCase):
    """detention/my/ endpoint — returns current user's active detention."""

    def setUp(self):
        super().setUp()
        make_zone('control_room')
        make_zone('salon')
        self.captor = self.user3
        self.prisoner = self.user1
        make_patrol(self.captor)
        make_mimic(self.prisoner)
        make_crystals(self.prisoner)
        from phantom_city.services import DetentionService
        self.detention = DetentionService.arrest(self.captor, self.prisoner)

    def test_detention_my_unauthenticated_returns_401(self):
        response = self.api_client.get('/api/game/detention/my/', format='json')
        self.assertIn(response.status_code, [401, 403])

    def test_detention_my_returns_active_detention(self):
        self.authenticate(self.prisoner)
        response = self.api_client.get('/api/game/detention/my/', format='json')
        self.assertEqual(response.status_code, 200)

    def test_detention_my_returns_empty_when_not_detained(self):
        self.authenticate(self.user2)
        response = self.api_client.get('/api/game/detention/my/', format='json')
        self.assertEqual(response.status_code, 200)


# ===========================================================================
# Control Transfer
# ===========================================================================

class ControlTransferViewTest(PhantomCityAPITestCase):
    def setUp(self):
        super().setUp()
        make_zone('control_room')
        make_zone('salon')
        self.captor = self.user3
        self.prisoner = self.user1
        make_patrol(self.captor)
        mimic = make_mimic(self.prisoner)
        make_crystals(self.prisoner)
        task = self.create_test_lock_task(self.prisoner)
        mimic.active_run_lock_task = task
        mimic.save()
        from phantom_city.services import DetentionService
        self.detention = DetentionService.arrest(self.captor, self.prisoner)
        self.transfer = GameControlTransfer.objects.get(
            grantor=self.prisoner
        )

    def test_add_time_unauthenticated_returns_401(self):
        response = self.api_client.post(
            f'/api/game/control-transfers/{self.transfer.pk}/add_time/',
            {'minutes': 30},
            format='json'
        )
        self.assertIn(response.status_code, [401, 403])

    def test_add_time_by_grantee_succeeds(self):
        self.authenticate(self.captor)
        response = self.api_client.post(
            f'/api/game/control-transfers/{self.transfer.pk}/add_time/',
            {'minutes': 30},
            format='json'
        )
        self.assertEqual(response.status_code, 200)

    def test_add_time_by_non_grantee_returns_404(self):
        self.authenticate(self.user2)
        response = self.api_client.post(
            f'/api/game/control-transfers/{self.transfer.pk}/add_time/',
            {'minutes': 30},
            format='json'
        )
        self.assertEqual(response.status_code, 404)

    def test_freeze_unauthenticated_returns_401(self):
        response = self.api_client.post(
            f'/api/game/control-transfers/{self.transfer.pk}/freeze/',
            format='json'
        )
        self.assertIn(response.status_code, [401, 403])

    def test_freeze_by_grantee_succeeds(self):
        self.authenticate(self.captor)
        response = self.api_client.post(
            f'/api/game/control-transfers/{self.transfer.pk}/freeze/',
            format='json'
        )
        self.assertEqual(response.status_code, 200)

    def test_freeze_by_non_grantee_returns_404(self):
        self.authenticate(self.user2)
        response = self.api_client.post(
            f'/api/game/control-transfers/{self.transfer.pk}/freeze/',
            format='json'
        )
        self.assertEqual(response.status_code, 404)


# ===========================================================================
# Market
# ===========================================================================

class MarketViewTest(PhantomCityAPITestCase):
    def test_market_list_unauthenticated_returns_401(self):
        response = self.api_client.get('/api/game/market/rates/')
        self.assertIn(response.status_code, [401, 403])

    def test_market_list_returns_200(self):
        self.authenticate(self.user1)
        response = self.api_client.get('/api/game/market/rates/')
        self.assertEqual(response.status_code, 200)

    def test_market_buy_unauthenticated_returns_401(self):
        response = self.api_client.post(
            '/api/game/market/buy/',
            {'item_slug': 'test_item', 'quantity': 1},
            format='json'
        )
        self.assertIn(response.status_code, [401, 403])


# ===========================================================================
# Ruins Deposits and Harvest
# ===========================================================================

class RuinsViewTest(PhantomCityAPITestCase):
    def setUp(self):
        super().setUp()
        self.ruins_zone = make_zone('ruins')
        make_mimic(self.user1)
        make_crystals(self.user1)
        make_presence(self.user1, self.ruins_zone)
        self.deposit = CrystalDeposit.objects.create(
            zone=self.ruins_zone, quantity=10
        )
        self.lock_task = self.create_test_lock_task(self.user1)

    def test_ruins_deposits_unauthenticated_returns_401(self):
        response = self.api_client.get('/api/game/ruins/deposits/')
        self.assertIn(response.status_code, [401, 403])

    def test_ruins_deposits_returns_200(self):
        self.authenticate(self.user1)
        response = self.api_client.get('/api/game/ruins/deposits/')
        self.assertEqual(response.status_code, 200)

    def test_ruins_harvest_unauthenticated_returns_401(self):
        response = self.api_client.post(
            '/api/game/ruins/harvest/',
            {'deposit_id': str(self.deposit.pk)},
            format='json'
        )
        self.assertIn(response.status_code, [401, 403])

    def test_ruins_harvest_succeeds_when_in_ruins(self):
        from unittest.mock import patch
        self.authenticate(self.user1)
        with patch('random.randint', return_value=2):
            response = self.api_client.post(
                '/api/game/ruins/harvest/',
                {'deposit_id': str(self.deposit.pk)},
                format='json'
            )
        self.assertEqual(response.status_code, 200)

    def test_ruins_harvest_fails_when_not_in_ruins(self):
        salon = make_zone('salon')
        PlayerZonePresence.objects.filter(user=self.user1).update(
            exited_at=timezone.now()
        )
        make_presence(self.user1, salon)
        self.authenticate(self.user1)
        response = self.api_client.post(
            '/api/game/ruins/harvest/',
            {'deposit_id': str(self.deposit.pk)},
            format='json'
        )
        self.assertEqual(response.status_code, 400)

    def test_ruins_harvest_missing_deposit_id_returns_400(self):
        self.authenticate(self.user1)
        response = self.api_client.post(
            '/api/game/ruins/harvest/',
            {},
            format='json'
        )
        self.assertEqual(response.status_code, 400)


# ===========================================================================
# Inventory
# ===========================================================================

class InventoryViewTest(PhantomCityAPITestCase):
    def test_inventory_unauthenticated_returns_401(self):
        response = self.api_client.get('/api/game/inventory/')
        self.assertIn(response.status_code, [401, 403])

    def test_inventory_returns_200(self):
        self.authenticate(self.user1)
        response = self.api_client.get('/api/game/inventory/')
        self.assertEqual(response.status_code, 200)


# ===========================================================================
# Disguise Equip
# ===========================================================================

class DisguiseEquipViewTest(PhantomCityAPITestCase):
    def setUp(self):
        super().setUp()
        make_mimic(self.user1)

    def test_disguise_equip_unauthenticated_returns_401(self):
        response = self.api_client.post(
            '/api/game/inventory/equip/',
            {'outer_item_slug': 'coat', 'inner_item_slugs': []},
            format='json'
        )
        self.assertIn(response.status_code, [401, 403])

    def test_disguise_equip_missing_item_returns_404(self):
        self.authenticate(self.user1)
        response = self.api_client.post(
            '/api/game/inventory/equip/',
            {'item_id': 999999, 'slot': 'outer'},
            format='json'
        )
        self.assertEqual(response.status_code, 404)
