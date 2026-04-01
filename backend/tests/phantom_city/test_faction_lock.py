"""
测试带锁状态与阵营切换联动：
- has_active_lock 字段正确反映带锁状态
- 开始带锁任务 → 阵营变为拟态者，传送至沙龙
- 完成带锁任务 → 阵营变为巡逻队，传送至检查站
- 停止带锁任务 → 阵营变为巡逻队，传送至检查站
"""
from datetime import timedelta
from django.utils import timezone
from phantom_city.models import GameZone, PlayerZonePresence, MimicProfile
from tasks.models import LockTask
from tests.phantom_city.base import PhantomCityAPITestCase


def _current_zone_name(user):
    presence = PlayerZonePresence.objects.filter(
        user=user, exited_at__isnull=True
    ).select_related('zone').first()
    return presence.zone.name if presence else None


class HasActiveLockFieldTest(PhantomCityAPITestCase):
    """GET /api/game/profile/ 的 has_active_lock 字段测试"""

    def setUp(self):
        super().setUp()
        self.make_zone('salon')
        self.make_zone('checkpoint')
        MimicProfile.objects.get_or_create(user=self.user1)

    def test_no_lock_task_returns_false(self):
        self.authenticate(self.user1)
        response = self.api_client.get('/api/game/profile/')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['has_active_lock'])

    def test_active_lock_task_returns_true(self):
        self.create_test_lock_task(self.user1, status='active')
        self.authenticate(self.user1)
        response = self.api_client.get('/api/game/profile/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['has_active_lock'])

    def test_voting_lock_task_returns_true(self):
        self.create_test_lock_task(self.user1, status='voting')
        self.authenticate(self.user1)
        response = self.api_client.get('/api/game/profile/')
        self.assertTrue(response.data['has_active_lock'])

    def test_voting_passed_lock_task_returns_true(self):
        self.create_test_lock_task(self.user1, status='voting_passed')
        self.authenticate(self.user1)
        response = self.api_client.get('/api/game/profile/')
        self.assertTrue(response.data['has_active_lock'])

    def test_completed_lock_task_returns_false(self):
        self.create_test_lock_task(self.user1, status='completed')
        self.authenticate(self.user1)
        response = self.api_client.get('/api/game/profile/')
        self.assertFalse(response.data['has_active_lock'])

    def test_failed_lock_task_returns_false(self):
        self.create_test_lock_task(self.user1, status='failed')
        self.authenticate(self.user1)
        response = self.api_client.get('/api/game/profile/')
        self.assertFalse(response.data['has_active_lock'])

    def test_board_task_does_not_count(self):
        self.create_test_lock_task(self.user1, task_type='board', status='active')
        self.authenticate(self.user1)
        response = self.api_client.get('/api/game/profile/')
        self.assertFalse(response.data['has_active_lock'])


class StartTaskFactionTest(PhantomCityAPITestCase):
    """开始带锁任务 → 阵营变为拟态者，传送至沙龙"""

    def setUp(self):
        super().setUp()
        self.salon = self.make_zone('salon')
        self.checkpoint = self.make_zone('checkpoint')
        MimicProfile.objects.get_or_create(user=self.user1)
        # 初始在检查站
        self.make_presence(self.user1, self.checkpoint)

    def test_start_lock_task_sets_has_active_lock(self):
        task = self.create_test_lock_task(self.user1, status='pending',
                                          start_time=None, end_time=None)
        self.authenticate(self.user1)
        response = self.api_client.post(f'/api/tasks/{task.id}/start/')
        self.assertEqual(response.status_code, 200)

        profile_resp = self.api_client.get('/api/game/profile/')
        self.assertTrue(profile_resp.data['has_active_lock'])

    def test_start_lock_task_teleports_to_salon(self):
        task = self.create_test_lock_task(self.user1, status='pending',
                                          start_time=None, end_time=None)
        self.authenticate(self.user1)
        self.api_client.post(f'/api/tasks/{task.id}/start/')
        self.assertEqual(_current_zone_name(self.user1), 'salon')

    def test_start_board_task_does_not_teleport(self):
        task = self.create_test_lock_task(self.user1, task_type='board',
                                          status='pending', start_time=None, end_time=None)
        self.authenticate(self.user1)
        self.api_client.post(f'/api/tasks/{task.id}/start/')
        # 仍在检查站，未传送
        self.assertEqual(_current_zone_name(self.user1), 'checkpoint')


class StopTaskFactionTest(PhantomCityAPITestCase):
    """停止带锁任务 → 阵营变为巡逻队，传送至检查站"""

    def setUp(self):
        super().setUp()
        self.salon = self.make_zone('salon')
        self.checkpoint = self.make_zone('checkpoint')
        MimicProfile.objects.get_or_create(user=self.user1)
        # 初始在沙龙（带锁中）
        self.make_presence(self.user1, self.salon)

    def test_stop_lock_task_clears_has_active_lock(self):
        task = self.create_test_lock_task(self.user1, status='active')
        self.authenticate(self.user1)
        response = self.api_client.post(f'/api/tasks/{task.id}/stop/')
        self.assertEqual(response.status_code, 200)

        profile_resp = self.api_client.get('/api/game/profile/')
        self.assertFalse(profile_resp.data['has_active_lock'])

    def test_stop_lock_task_teleports_to_checkpoint(self):
        task = self.create_test_lock_task(self.user1, status='active')
        self.authenticate(self.user1)
        self.api_client.post(f'/api/tasks/{task.id}/stop/')
        self.assertEqual(_current_zone_name(self.user1), 'checkpoint')

    def test_stop_requires_owner(self):
        task = self.create_test_lock_task(self.user1, status='active')
        self.authenticate(self.user2)
        response = self.api_client.post(f'/api/tasks/{task.id}/stop/')
        self.assertEqual(response.status_code, 403)
        # 任务状态未变
        task.refresh_from_db()
        self.assertEqual(task.status, 'active')
