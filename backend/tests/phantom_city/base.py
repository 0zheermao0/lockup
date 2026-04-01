"""
幻城测试基类 — 不依赖 BaseBusinessLogicTestCase.setUpTestData（该方法引用了
store.ItemType 上不存在的字段 price/max_quantity，导致测试数据库初始化失败）。
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

from phantom_city.models import (
    GameZone, PlayerZonePresence, MimicProfile, PatrolProfile,
    PlayerCrystals,
)

User = get_user_model()

_zone_display = {
    'ruins': '污染废墟',
    'salon': '纯净沙龙',
    'checkpoint': '铁血防线',
    'control_room': '控制室',
}


class PhantomCityTestCase(TestCase):
    """轻量级幻城测试基类，自行创建用户，不依赖损坏的 setUpTestData。"""

    def setUp(self):
        self.user1 = User.objects.create_user(
            username='pc_user1', email='pc1@test.com', password='pass',
            level=2, coins=500,
        )
        self.user2 = User.objects.create_user(
            username='pc_user2', email='pc2@test.com', password='pass',
            level=2, coins=500,
        )
        self.user3 = User.objects.create_user(
            username='pc_user3', email='pc3@test.com', password='pass',
            level=3, coins=500,
        )
        self.admin = User.objects.create_user(
            username='pc_admin', email='pcadmin@test.com', password='pass',
            level=5, is_superuser=True, is_staff=True,
        )

    # ── zone helpers ──────────────────────────────────────────────────────────

    def make_zone(self, name):
        display = _zone_display.get(name, name)
        zone, _ = GameZone.objects.get_or_create(
            name=name,
            defaults={'display_name': display, 'description': name},
        )
        return zone

    def make_all_zones(self):
        return {n: self.make_zone(n) for n in _zone_display}

    # ── profile helpers ───────────────────────────────────────────────────────

    def make_mimic(self, user, **kwargs):
        return MimicProfile.objects.create(user=user, **kwargs)

    def make_patrol(self, user, **kwargs):
        return PatrolProfile.objects.create(user=user, **kwargs)

    def make_crystals(self, user, raw=0, purified=0):
        pc, _ = PlayerCrystals.objects.get_or_create(user=user)
        pc.raw_crystals = raw
        pc.purified_crystals = purified
        pc.save()
        return pc

    def make_presence(self, user, zone, exited_at=None, entered_at=None):
        presence = PlayerZonePresence.objects.create(
            user=user,
            zone=zone,
            exited_at=exited_at,
        )
        if entered_at is not None:
            PlayerZonePresence.objects.filter(pk=presence.pk).update(entered_at=entered_at)
            presence.refresh_from_db()
        return presence

    # ── lock task helper ──────────────────────────────────────────────────────

    def create_test_lock_task(self, user, **kwargs):
        from tasks.models import LockTask
        defaults = {
            'user': user,
            'task_type': 'lock',
            'status': 'active',
            'difficulty': 'medium',
            'start_time': timezone.now(),
            'end_time': timezone.now() + __import__('datetime').timedelta(hours=2),
            'is_frozen': False,
            'unlock_type': 'time',
            'vote_threshold': 1,
            'vote_agreement_ratio': 0.5,
        }
        defaults.update(kwargs)
        return LockTask.objects.create(**defaults)


class PhantomCityAPITestCase(PhantomCityTestCase):
    """带 DRF APIClient 的幻城视图测试基类。"""

    def setUp(self):
        super().setUp()
        self.api_client = APIClient()

    def authenticate(self, user):
        token, _ = Token.objects.get_or_create(user=user)
        self.api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def clear_auth(self):
        self.api_client.credentials()
