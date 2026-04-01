"""
男娘幻城 — 业务逻辑服务层
"""
import random
import logging
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from django.conf import settings

from .models import (
    GameZone, PlayerZonePresence, MimicProfile, PatrolProfile,
    TellEvent, CheckpointSession, CheckpointParticipant, InterrogationRequest,
    GrayMarketTransaction, GameControlTransfer, DetentionRecord,
    FactionConversionEvent, EncryptedChannel, EncryptedMessage,
    ZoneChatMessage, CrystalDeposit, PlayerCrystals, GameMarketRate,
    GameItem, PlayerGameInventory, ActiveDisguise, SmuggleRun,
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 破绽文本库
# ─────────────────────────────────────────────

TELL_TEXTS = {
    'body_hair': [
        '*[袖口滑落，露出一截细毛]*',
        '*[领口处有几根若隐若现的绒毛]*',
        '*[手背上的细毛在光线下清晰可见]*',
    ],
    'suppression_tremor': [
        '*[呼吸比正常人略深，每次吐气都带着极轻的颤音]*',
        '*[手指有轻微的颤抖，像是强行压制着某种情绪]*',
        '*[说话时嗓音有一丝不稳定的波动]*',
    ],
    'abnormal_pause': [
        '*[回答前有明显的——停顿]*',
        '*[沉默了几秒，才缓缓开口]*',
        '*[思考时间明显长于正常人]*',
    ],
    'weight_anomaly': [
        '*[步伐比空手时略重，靴底踏地声更实]*',
        '*[行李的重量让肩膀微微下沉]*',
        '*[每一步都带着一种刻意控制的稳重]*',
    ],
    'scent_residue': [
        '*[淡淡的备皮间气息，像是金属与湿土混合的味道]*',
        '*[衣物上残留着一股难以掩盖的尘埃气息]*',
        '*[空气中有一丝异常的化学气味]*',
    ],
    'disguise_fatigue': [
        '*[动作里有一种奇怪的机械感，像是在执行程序]*',
        '*[表情维持得太久，出现了细微的僵硬]*',
        '*[每个动作都略显刻意，缺乏自然的随意性]*',
    ],
    'lock_resonance': [
        '*[每隔一段时间会下意识地看向手腕]*',
        '*[偶尔会做出一个被什么东西牵制的微小动作]*',
        '*[无意识地触碰了一下腰间某个位置]*',
    ],
    'pitch_slippage': [
        '*[声音在某个字上轻微上扬，随后被刻意压平]*',
        '*[音调在句尾有一个几乎察觉不到的滑落]*',
        '*[发音时有一丝与外表不符的细腻感]*',
    ],
}


# ─────────────────────────────────────────────
# TellService — 破绽评估引擎
# ─────────────────────────────────────────────

class TellService:
    """评估玩家当前状态，生成破绽事件"""

    # 每种破绽的基础触发概率（满足条件时）
    BASE_PROBABILITIES = {
        'body_hair': 0.80,
        'suppression_tremor': 0.75,
        'abnormal_pause': 1.00,  # 超时必定触发
        'weight_anomaly': 0.60,
        'scent_residue': 0.70,
        'disguise_fatigue': 0.65,
        'lock_resonance': 0.55,
        'pitch_slippage': 0.50,
    }

    @classmethod
    def evaluate_tells(cls, player, zone, action_type='presence', session=None,
                       response_time_seconds=None):
        """
        评估玩家当前状态，生成适用的破绽事件。
        返回新创建的 TellEvent 列表。
        """
        try:
            mimic_profile = player.mimic_profile
        except MimicProfile.DoesNotExist:
            return []

        tells_generated = []
        stats_snapshot = {
            'depilation_charge': mimic_profile.depilation_charge,
            'suppression_value': mimic_profile.suppression_value,
            'purity_score': mimic_profile.purity_score,
            'femboy_score': mimic_profile.femboy_score,
        }

        # 1. 体毛破绽
        if mimic_profile.depilation_charge < 30:
            if random.random() < cls.BASE_PROBABILITIES['body_hair']:
                tells_generated.append(cls._create_tell(
                    player, 'body_hair', zone, session, action_type, stats_snapshot
                ))

        # 2. 压抑震颤
        if mimic_profile.suppression_value > 70:
            if random.random() < cls.BASE_PROBABILITIES['suppression_tremor']:
                tells_generated.append(cls._create_tell(
                    player, 'suppression_tremor', zone, session, action_type, stats_snapshot
                ))

        # 3. 异常停顿（由盘问超时触发，传入 response_time_seconds）
        if response_time_seconds is not None and response_time_seconds > 20:
            tells_generated.append(cls._create_tell(
                player, 'abnormal_pause', zone, session, action_type, stats_snapshot
            ))

        # 4. 重量异常（携带刀具）
        crystals = getattr(player, 'crystals', None)
        if crystals and crystals.raw_crystals > 0:
            if random.random() < cls.BASE_PROBABILITIES['weight_anomaly']:
                tells_generated.append(cls._create_tell(
                    player, 'weight_anomaly', zone, session, action_type, stats_snapshot
                ))

        # 5. 气味残留（在备皮间停留>2小时）
        ruins_zone = GameZone.objects.filter(name='ruins').first()
        if ruins_zone:
            recent_ruins = PlayerZonePresence.objects.filter(
                user=player,
                zone=ruins_zone,
                exited_at__isnull=True,
            ).first()
            if not recent_ruins:
                # 也检查最近2小时内离开备皮间的记录
                two_hours_ago = timezone.now() - timedelta(hours=2)
                recent_ruins = PlayerZonePresence.objects.filter(
                    user=player,
                    zone=ruins_zone,
                    exited_at__gte=two_hours_ago,
                ).first()
            if recent_ruins:
                time_in_ruins = timezone.now() - recent_ruins.entered_at
                if time_in_ruins.total_seconds() > 7200:  # 2小时
                    if random.random() < cls.BASE_PROBABILITIES['scent_residue']:
                        tells_generated.append(cls._create_tell(
                            player, 'scent_residue', zone, session, action_type, stats_snapshot
                        ))

        # 6. 伪装疲态（伪装时间>4小时）
        if mimic_profile.is_disguised and mimic_profile.disguise_start_time:
            disguise_duration = timezone.now() - mimic_profile.disguise_start_time
            if disguise_duration.total_seconds() > 14400:  # 4小时
                if random.random() < cls.BASE_PROBABILITIES['disguise_fatigue']:
                    tells_generated.append(cls._create_tell(
                        player, 'disguise_fatigue', zone, session, action_type, stats_snapshot
                    ))

        # 7. 锁链暗示（活跃LockTask剩余<20%）
        if mimic_profile.active_run_lock_task:
            lock_task = mimic_profile.active_run_lock_task
            if lock_task.start_time and lock_task.end_time:
                total_duration = (lock_task.end_time - lock_task.start_time).total_seconds()
                remaining = (lock_task.end_time - timezone.now()).total_seconds()
                if total_duration > 0 and (remaining / total_duration) < 0.20:
                    if random.random() < cls.BASE_PROBABILITIES['lock_resonance']:
                        tells_generated.append(cls._create_tell(
                            player, 'lock_resonance', zone, session, action_type, stats_snapshot
                        ))

        # 8. 声调滑落（盘问时发毛值>80）
        if action_type == 'interrogation_response' and mimic_profile.suppression_value > 80:
            if random.random() < cls.BASE_PROBABILITIES['pitch_slippage']:
                tells_generated.append(cls._create_tell(
                    player, 'pitch_slippage', zone, session, action_type, stats_snapshot
                ))

        return tells_generated

    @classmethod
    def _create_tell(cls, player, tell_type, zone, session, action_type, stats_snapshot):
        texts = TELL_TEXTS.get(tell_type, ['*[某种异常]*'])
        tell_text = random.choice(texts)
        return TellEvent.objects.create(
            player=player,
            tell_type=tell_type,
            tell_text=tell_text,
            zone=zone,
            checkpoint_session=session,
            action_type=action_type,
            stats_snapshot=stats_snapshot,
        )

    @classmethod
    def get_suspicion_score(cls, patrol_profile, target_player, session):
        """计算小s对目标玩家的嫌疑积分"""
        evidence = patrol_profile.suspicion_evidence
        player_id = str(target_player.id)
        return evidence.get(player_id, 0)

    @classmethod
    def add_suspicion(cls, patrol_profile, target_player, points, reason=''):
        """增加嫌疑积分"""
        evidence = patrol_profile.suspicion_evidence
        player_id = str(target_player.id)
        current = evidence.get(player_id, 0)
        evidence[player_id] = current + points
        patrol_profile.suspicion_evidence = evidence
        patrol_profile.save(update_fields=['suspicion_evidence'])

        # 嫌疑积分≥80时发出系统警告
        if evidence[player_id] >= 80:
            _send_zone_system_message(
                patrol_profile.user,
                f'[系统]: 警告 — {target_player.username} 的异常指数已超阈值',
            )
        return evidence[player_id]


# ─────────────────────────────────────────────
# CheckpointService — 安检口管理
# ─────────────────────────────────────────────

NPC_NAMES = [
    '旅行者甲', '旅行者乙', '商人丙', '过客丁', '行人戊',
    '访客己', '路人庚', '游客辛', '信使壬', '探险者癸',
    '普通市民', '货运员', '快递员', '记者', '医疗人员',
]

NPC_DESCRIPTIONS = [
    '一名穿着普通的旅行者，手持通行证，神情平静。',
    '一名背着大包的商人，看起来疲惫但从容。',
    '一名穿着制服的工作人员，步伐稳健。',
    '一名老年人，缓慢地向前移动，偶尔咳嗽。',
    '一名年轻人，戴着耳机，似乎在听音乐。',
]

# 红鲱鱼NPC（外表可疑但实为普通人）
RED_HERRING_TELLS = [
    '*[步伐有些急促，像是赶时间]*',
    '*[不断查看手表，显得焦虑]*',
    '*[衣物有些凌乱，像是刚赶路]*',
    '*[偶尔回头张望]*',
]


class CheckpointService:
    """安检口会话管理"""

    @classmethod
    def get_or_create_active_session(cls, zone):
        """获取或创建当前活跃的安检口会话"""
        session = CheckpointSession.objects.filter(
            zone=zone, status='active'
        ).first()
        if not session:
            session = cls.create_session(zone)
        return session

    @classmethod
    def create_session(cls, zone):
        """创建新安检口会话，生成NPC队列"""
        session = CheckpointSession.objects.create(zone=zone, status='active')
        cls._generate_npc_queue(session)
        return session

    @classmethod
    def _generate_npc_queue(cls, session):
        """生成10人NPC队列（含红鲱鱼）"""
        npc_count = 10
        npcs = []
        for i in range(npc_count):
            is_red_herring = random.random() < 0.20  # 20%红鲱鱼
            has_no_tells = random.random() < 0.20    # 20%完全无破绽

            npc = {
                'id': f'npc_{i}',
                'name': random.choice(NPC_NAMES),
                'description': random.choice(NPC_DESCRIPTIONS),
                'is_red_herring': is_red_herring,
                'tells': [],
                'auto_pass_at': (
                    timezone.now() + timedelta(minutes=random.randint(10, 30))
                ).isoformat(),
            }

            if is_red_herring:
                npc['tells'] = [random.choice(RED_HERRING_TELLS)]
            elif not has_no_tells:
                # 普通NPC偶尔有轻微破绽（不触发收押）
                pass

            npcs.append(npc)

        session.npc_data = npcs
        session.npc_count = npc_count
        session.save(update_fields=['npc_data', 'npc_count'])

    @classmethod
    def join_as_smuggler(cls, player, session):
        """小男娘加入安检口队列"""
        participant, created = CheckpointParticipant.objects.get_or_create(
            session=session,
            user=player,
            defaults={
                'role': 'smuggler',
                'outcome': 'pending',
            }
        )
        if created:
            # 快照当前携带的刀具
            crystals = getattr(player, 'crystals', None)
            participant.contraband_snapshot = {
                'raw_crystals': crystals.raw_crystals if crystals else 0,
            }
            participant.save(update_fields=['contraband_snapshot'])
        return participant

    @classmethod
    def join_as_patrol(cls, player, session):
        """小s加入安检口"""
        participant, _ = CheckpointParticipant.objects.get_or_create(
            session=session,
            user=player,
            defaults={'role': 'patrol', 'outcome': 'pending'}
        )
        return participant

    @classmethod
    def inspect_player(cls, patrol, target, session):
        """
        /inspect: 外观检查，返回目标描述+当前破绽文本。
        不消耗令牌，每次inspect后更新嫌疑积分。
        """
        patrol_profile = _get_or_create_patrol_profile(patrol)
        zone = session.zone

        # 生成当前破绽
        tells = TellService.evaluate_tells(target, zone, action_type='inspect', session=session)

        # 计算嫌疑增量
        suspicion_added = len(tells) * 5
        if suspicion_added > 0:
            total = TellService.add_suspicion(patrol_profile, target, suspicion_added, 'inspect')
        else:
            total = TellService.get_suspicion_score(patrol_profile, target, session)

        # 检查suppression>80加成
        try:
            mimic = target.mimic_profile
            if mimic.suppression_value > 80:
                total = TellService.add_suspicion(patrol_profile, target, 20, 'high_suppression')
        except MimicProfile.DoesNotExist:
            pass

        return {
            'tells': [{'type': t.tell_type, 'text': t.tell_text} for t in tells],
            'suspicion_score': total,
            'can_pat_down': total >= 30,
        }

    @classmethod
    def interrogate_player(cls, patrol, target, session, question):
        """
        /interrogate: 发起盘问请求（异步，30秒截止）。
        每批次最多2次盘问。
        """
        # 创建盘问请求
        deadline = timezone.now() + timedelta(seconds=30)
        interrogation = InterrogationRequest.objects.create(
            session=session,
            interrogator=patrol,
            target=target,
            question=question,
            deadline=deadline,
        )

        # 通知目标
        _notify_game(
            target,
            'game_interrogated',
            '你被盘问了',
            f'{patrol.username} 要求你回答: {question}',
            actor=patrol,
        )

        return interrogation

    @classmethod
    def respond_to_interrogation(cls, interrogation, player, response_text):
        """被盘问者作答"""
        if interrogation.status != 'pending':
            return None

        now = timezone.now()
        response_time = (now - interrogation.created_at).total_seconds()

        interrogation.response_text = response_text
        interrogation.response_time_seconds = int(response_time)
        interrogation.status = 'answered'
        interrogation.answered_at = now
        interrogation.save()

        # 评估破绽（超时+声调）
        tells = TellService.evaluate_tells(
            player,
            interrogation.session.zone,
            action_type='interrogation_response',
            session=interrogation.session,
            response_time_seconds=int(response_time),
        )

        # 更新嫌疑积分
        patrol_profile = _get_or_create_patrol_profile(interrogation.interrogator)
        if response_time > 20:
            TellService.add_suspicion(patrol_profile, player, 15, 'slow_response')
            interrogation.triggered_pause_tell = True
            interrogation.save(update_fields=['triggered_pause_tell'])

        return {'tells': tells, 'response_time': response_time}

    @classmethod
    def expire_interrogation(cls, interrogation):
        """盘问超时处理"""
        if interrogation.status != 'pending':
            return
        interrogation.status = 'expired'
        interrogation.save(update_fields=['status'])

        # 触发异常停顿破绽
        tells = TellService.evaluate_tells(
            interrogation.target,
            interrogation.session.zone,
            action_type='interrogation_timeout',
            session=interrogation.session,
            response_time_seconds=999,
        )

        patrol_profile = _get_or_create_patrol_profile(interrogation.interrogator)
        TellService.add_suspicion(patrol_profile, interrogation.target, 15, 'timeout')

    @classmethod
    @transaction.atomic
    def pat_down(cls, patrol, target, session):
        """
        /pat_down: 体检。需嫌疑积分≥30，消耗2令牌。
        找到违禁品→收押；未找到→声誉-5。
        """
        patrol_profile = _get_or_create_patrol_profile(patrol)
        suspicion = TellService.get_suspicion_score(patrol_profile, target, session)

        if suspicion < 30:
            return {'success': False, 'error': '嫌疑积分不足30，无法体检'}

        if patrol_profile.inspection_tokens < 2:
            return {'success': False, 'error': '配额不足'}

        patrol_profile.inspection_tokens -= 2
        patrol_profile.save(update_fields=['inspection_tokens'])

        # 检查是否携带违禁品
        crystals = getattr(target, 'crystals', None)
        has_contraband = crystals and crystals.raw_crystals > 0

        if has_contraband:
            # 收押
            detention = DetentionService.arrest(patrol, target, session)
            patrol_profile.total_arrests += 1
            patrol_profile.total_correct_identifications += 1
            patrol_profile.authority_value = min(100, patrol_profile.authority_value + 10)
            patrol_profile.reputation_score = min(100, patrol_profile.reputation_score + 10)
            patrol_profile.save(update_fields=['total_arrests', 'total_correct_identifications',
                                               'authority_value', 'reputation_score'])

            # 更新安检口参与状态
            CheckpointParticipant.objects.filter(
                session=session, user=target
            ).update(outcome='arrested', resolved_at=timezone.now())

            return {'success': True, 'arrested': True, 'detention': detention}
        else:
            # 误搜惩罚
            patrol_profile.reputation_score = max(0, patrol_profile.reputation_score - 5)
            patrol_profile.false_accusations += 1
            patrol_profile.save(update_fields=['reputation_score', 'false_accusations'])

            # 目标光滑度+10（被误搜奖励）
            try:
                mimic = target.mimic_profile
                mimic.purity_score = min(100, mimic.purity_score + 10)
                mimic.save(update_fields=['purity_score'])
            except MimicProfile.DoesNotExist:
                pass

            _notify_game(
                target, 'game_pat_down', '你被体检了',
                f'{patrol.username} 对你进行了体检，但没有发现任何问题。你的光滑度+10。',
                actor=patrol,
            )

            return {'success': True, 'arrested': False, 'false_accusation': True}

    @classmethod
    @transaction.atomic
    def flee_checkpoint(cls, player, session_id):
        """小男娘溜走安检口队列，代价：发毛值+20，光滑度-5"""
        try:
            session = CheckpointSession.objects.get(id=session_id, status='active')
        except CheckpointSession.DoesNotExist:
            return {'success': False, 'error': '安检口会话不存在或已关闭'}

        participant = CheckpointParticipant.objects.filter(
            session=session, user=player, outcome='pending', role='smuggler'
        ).first()
        if not participant:
            return {'success': False, 'error': '你没有待处理的安检口队列记录'}

        # 应用溜走惩罚
        try:
            mimic = player.mimic_profile
            mimic.suppression_value = min(100, mimic.suppression_value + 20)
            mimic.purity_score = max(0, mimic.purity_score - 5)
            mimic.save(update_fields=['suppression_value', 'purity_score'])
        except MimicProfile.DoesNotExist:
            pass

        # 标记参与者结果为溜走
        participant.outcome = 'fled'
        participant.resolved_at = timezone.now()
        participant.save(update_fields=['outcome', 'resolved_at'])

        # 移动玩家到闺房
        salon = GameZone.objects.filter(name='salon').first()
        if salon:
            PlayerZonePresence.objects.filter(
                user=player, exited_at__isnull=True
            ).update(exited_at=timezone.now())
            PlayerZonePresence.objects.create(user=player, zone=salon)

        # 区域广播
        checkpoint_zone = session.zone
        ZoneChatMessage.objects.create(
            zone=checkpoint_zone,
            sender=None,
            content=f'[系统]: {player.username} 慌乱地溜走了队列。',
            is_system=True,
        )

        _notify_game(
            player, 'game_checkpoint', '已溜走安检口',
            '你溜走了安检口队列。发毛值+20，光滑度-5。',
        )

        return {'success': True, 'suppression_added': 20, 'purity_lost': 5}


# ─────────────────────────────────────────────
# DetentionService — 收押与转化
# ─────────────────────────────────────────────

class DetentionService:

    @classmethod
    @transaction.atomic
    def arrest(cls, captor, prisoner, session=None):
        """收押流程：没收刀具，创建收押记录，转移锁控制权"""
        # 没收刀具
        seized_crystals = 0
        try:
            crystals = prisoner.crystals
            seized_crystals = crystals.raw_crystals
            crystals.raw_crystals = 0
            crystals.save(update_fields=['raw_crystals'])
        except PlayerCrystals.DoesNotExist:
            pass

        # 将囚犯移入禁闭室
        control_room = GameZone.objects.filter(name='control_room').first()
        if control_room:
            PlayerZonePresence.objects.filter(
                user=prisoner, exited_at__isnull=True
            ).update(exited_at=timezone.now())
            PlayerZonePresence.objects.create(user=prisoner, zone=control_room)

        # 创建收押记录
        duration_hours = 12
        release_at = timezone.now() + timedelta(hours=duration_hours)
        detention = DetentionRecord.objects.create(
            prisoner=prisoner,
            captor=captor,
            status='active',
            seized_crystals=seized_crystals,
            duration_hours=duration_hours,
            release_at=release_at,
        )

        # 创建锁控制权转移（如果囚犯有活跃LockTask）
        try:
            mimic = prisoner.mimic_profile
            if mimic.active_run_lock_task:
                control_transfer = GameControlTransfer.objects.create(
                    lock_task=mimic.active_run_lock_task,
                    grantor=prisoner,
                    grantee=captor,
                    source='arrest',
                    can_add_time=True,
                    can_freeze=True,
                    can_assign_tasks=True,
                    duration_hours=duration_hours,
                    expires_at=release_at,
                )
                detention.control_transfer = control_transfer
                detention.save(update_fields=['control_transfer'])

            mimic.purity_score = max(0, mimic.purity_score - 10)
            mimic.save(update_fields=['purity_score'])
        except MimicProfile.DoesNotExist:
            pass

        # 更新跑商记录
        SmuggleRun.objects.filter(
            player=prisoner, status='in_progress'
        ).update(
            status='failed_arrested',
            crystals_seized=seized_crystals,
            completed_at=timezone.now(),
            detention_record=detention,
        )

        _notify_game(
            prisoner, 'game_arrested', '你已被收押',
            f'[男娘幻城] 你已被 {captor.username} 收押。'
            f'小s没收了你的 {seized_crystals} 枚刀具，'
            f'并取得了你锁的临时控制权。剩余时间: {duration_hours}小时',
            actor=captor,
            priority='urgent',
        )

        return detention

    @classmethod
    @transaction.atomic
    def charm_warden(cls, prisoner, detention):
        """
        /charm_warden: 哄骗看守。
        条件: purity_score≥70 AND captor.authority_value≤40
        冷却: 4小时
        """
        if detention.status != 'active':
            return {'success': False, 'error': '收押已结束'}

        try:
            mimic = prisoner.mimic_profile
        except MimicProfile.DoesNotExist:
            return {'success': False, 'error': '档案不存在'}

        if mimic.purity_score < 70:
            return {'success': False, 'error': f'光滑度不足（当前{mimic.purity_score}，需要70）'}

        # 检查冷却
        if detention.last_charm_at:
            cooldown_end = detention.last_charm_at + timedelta(hours=4)
            if timezone.now() < cooldown_end:
                remaining = (cooldown_end - timezone.now()).seconds // 60
                return {'success': False, 'error': f'哄骗冷却中，还需{remaining}分钟'}

        captor = detention.captor
        try:
            patrol_profile = captor.patrol_profile
        except PatrolProfile.DoesNotExist:
            return {'success': False, 'error': '看守档案不存在'}

        if patrol_profile.authority_value > 40:
            return {'success': False, 'error': f'看守管控力过高（当前{patrol_profile.authority_value}，需≤40）'}

        # 扣减属性
        authority_drain = random.randint(10, 20)
        patrol_profile.authority_value = max(0, patrol_profile.authority_value - authority_drain)
        patrol_profile.save(update_fields=['authority_value'])

        mimic.purity_score = max(0, mimic.purity_score - 10)
        mimic.save(update_fields=['purity_score'])

        detention.charm_attempts_used += 1
        detention.last_charm_at = timezone.now()
        detention.save(update_fields=['charm_attempts_used', 'last_charm_at'])

        # 发送加密频道感知消息
        _send_encrypted_system_message(
            prisoner, captor,
            f'[男娘幻城·系统感知]: 禁闭室的空气改变了。'
            f'你注意到——某些东西正在动摇你的判断。[管控力-{authority_drain}]'
        )

        _notify_game(
            captor, 'game_charm_attempt', '哄骗尝试',
            f'{prisoner.username} 对你发动了哄骗。你的管控力-{authority_drain}。',
            actor=prisoner,
        )

        # 检查是否触发阵营转化
        if patrol_profile.authority_value <= 0:
            conversion = cls._execute_faction_conversion(captor, patrol_profile, prisoner, detention)
            return {
                'success': True,
                'authority_drained': authority_drain,
                'conversion_triggered': True,
                'conversion': conversion,
            }

        return {
            'success': True,
            'authority_drained': authority_drain,
            'captor_authority_remaining': patrol_profile.authority_value,
            'conversion_triggered': False,
        }

    @classmethod
    @transaction.atomic
    def _execute_faction_conversion(cls, captor, patrol_profile, prisoner, detention):
        """执行阵营转化：小s→小男娘"""
        # 记录转化事件
        conversion = FactionConversionEvent.objects.create(
            converted_user=captor,
            from_faction='patrol',
            to_faction='mimic',
            detention_record=detention,
            charm_attempts_count=detention.charm_attempts_used,
            authority_at_conversion=patrol_profile.authority_value,
        )

        # 转化小s档案
        patrol_profile.current_faction = 'mimic'
        patrol_profile.save(update_fields=['current_faction'])

        # 创建或更新小男娘档案
        mimic_profile, _ = MimicProfile.objects.get_or_create(
            user=captor,
            defaults={'current_faction': 'mimic'}
        )
        mimic_profile.current_faction = 'mimic'
        mimic_profile.save(update_fields=['current_faction'])

        # 立即释放囚犯
        cls.release(detention, reason='released_conversion')

        # 系统广播
        checkpoint_zone = GameZone.objects.filter(name='checkpoint').first()
        if checkpoint_zone:
            ZoneChatMessage.objects.create(
                zone=checkpoint_zone,
                sender=None,
                content=f'[系统]: 防线出现了裂缝。一名小s员加入了另一侧。',
                is_system=True,
            )

        _notify_game(
            captor, 'game_faction_converted', '阵营转化',
            f'你已被 {prisoner.username} 的哄骗所动摇，转化为小男娘阵营。',
            actor=prisoner,
            priority='urgent',
        )

        return conversion

    @classmethod
    @transaction.atomic
    def release(cls, detention, reason='released_timeout'):
        """释放囚犯"""
        if detention.status != 'active':
            return

        detention.status = reason
        detention.released_at = timezone.now()
        detention.save(update_fields=['status', 'released_at'])

        # 撤销锁控制权
        if detention.control_transfer:
            detention.control_transfer.is_active = False
            detention.control_transfer.revoked_at = timezone.now()
            detention.control_transfer.revoked_reason = reason
            detention.control_transfer.save(update_fields=['is_active', 'revoked_at', 'revoked_reason'])

        # 将囚犯移回闺房
        salon_zone = GameZone.objects.filter(name='salon').first()
        if salon_zone:
            PlayerZonePresence.objects.filter(
                user=detention.prisoner, exited_at__isnull=True
            ).update(exited_at=timezone.now())
            PlayerZonePresence.objects.create(user=detention.prisoner, zone=salon_zone)

        _notify_game(
            detention.prisoner, 'game_detention_released', '收押解除',
            f'你已从禁闭室获释，回到了闺房。',
        )


# ─────────────────────────────────────────────
# TransactionService — 灰色市场交易
# ─────────────────────────────────────────────

class TransactionService:

    @classmethod
    @transaction.atomic
    def propose_bribe(cls, initiator, recipient, offer, session=None):
        """发起打点：创建交易记录+加密频道"""
        crystals_offered = offer.get('crystals', 0)

        # 验证刀具余额
        if crystals_offered > 0:
            try:
                initiator_crystals = initiator.crystals
                if initiator_crystals.raw_crystals < crystals_offered:
                    return {'success': False, 'error': '刀具不足'}
                # 托管刀具
                initiator_crystals.raw_crystals -= crystals_offered
                initiator_crystals.save(update_fields=['raw_crystals'])
            except PlayerCrystals.DoesNotExist:
                if crystals_offered > 0:
                    return {'success': False, 'error': '刀具不足'}

        expires_at = timezone.now() + timedelta(minutes=30)
        tx = GrayMarketTransaction.objects.create(
            transaction_type='bribe',
            initiator=initiator,
            recipient=recipient,
            status='proposed',
            offer_from_initiator=offer,
            escrowed_crystals=crystals_offered,
            checkpoint_session=session,
            expires_at=expires_at,
        )

        # 创建加密频道
        channel = EncryptedChannel.objects.create(
            participant_a=initiator,
            participant_b=recipient,
            linked_transaction=tx,
        )
        tx.encrypted_channel_id = channel.id
        tx.status = 'negotiating'
        tx.save(update_fields=['encrypted_channel_id', 'status'])

        # 发送开场系统消息
        EncryptedMessage.objects.create(
            channel=channel,
            sender=None,
            content=f'[加密频道已建立] {initiator.username} 向你发起了打点提议。',
            is_system=True,
        )

        _notify_game(
            recipient, 'game_bribe_received', '收到打点提议',
            f'{initiator.username} 向你发起了打点，提供 {crystals_offered} 刀具。',
            actor=initiator,
        )

        return {'success': True, 'transaction': tx, 'channel': channel}

    @classmethod
    @transaction.atomic
    def counter_offer(cls, tx, user, new_offer):
        """反提议"""
        if tx.status not in ('proposed', 'negotiating'):
            return {'success': False, 'error': '交易状态不允许反提议'}

        # 记录到谈判日志
        log_entry = {
            'user': user.username,
            'offer': new_offer,
            'timestamp': timezone.now().isoformat(),
        }
        tx.negotiation_log = tx.negotiation_log + [log_entry]

        if user == tx.initiator:
            tx.offer_from_initiator = new_offer
        else:
            tx.offer_from_recipient = new_offer

        tx.status = 'negotiating'
        tx.save()

        # 发送频道消息
        if tx.encrypted_channel_id:
            try:
                channel = EncryptedChannel.objects.get(id=tx.encrypted_channel_id)
                EncryptedMessage.objects.create(
                    channel=channel,
                    sender=None,
                    content=f'[系统]: {user.username} 提出了新的条件。',
                    is_system=True,
                )
            except EncryptedChannel.DoesNotExist:
                pass

        return {'success': True, 'transaction': tx}

    @classmethod
    @transaction.atomic
    def accept_bribe(cls, tx, patrol):
        """小s接受打点：释放托管物品，标记通过"""
        if tx.status != 'negotiating':
            return {'success': False, 'error': '交易状态不允许接受'}

        # 转移托管刀具给小s
        if tx.escrowed_crystals > 0:
            patrol_crystals, _ = PlayerCrystals.objects.get_or_create(user=patrol)
            patrol_crystals.purified_crystals += tx.escrowed_crystals
            patrol_crystals.save(update_fields=['purified_crystals'])

        tx.status = 'completed'
        tx.accepted_at = timezone.now()
        tx.save(update_fields=['status', 'accepted_at'])

        # 标记小男娘通过
        if tx.checkpoint_session:
            CheckpointParticipant.objects.filter(
                session=tx.checkpoint_session, user=tx.initiator
            ).update(outcome='bribed_through', resolved_at=timezone.now())

        # 关闭加密频道
        if tx.encrypted_channel_id:
            EncryptedChannel.objects.filter(id=tx.encrypted_channel_id).update(
                is_active=False, closed_at=timezone.now()
            )

        return {'success': True, 'transaction': tx}

    @classmethod
    @transaction.atomic
    def betray_after_bribe(cls, tx, patrol):
        """接受打点后仍收押（背叛）"""
        if tx.status != 'completed':
            return {'success': False, 'error': '交易未完成'}

        tx.status = 'betrayed'
        tx.save(update_fields=['status'])

        # 声誉惩罚（×0.4扣除）
        try:
            patrol_profile = patrol.patrol_profile
            penalty = int(patrol_profile.reputation_score * 0.4)
            patrol_profile.reputation_score = max(0, patrol_profile.reputation_score - penalty)
            patrol_profile.save(update_fields=['reputation_score'])
        except PatrolProfile.DoesNotExist:
            pass

        return {'success': True}

    @classmethod
    @transaction.atomic
    def propose_extortion(cls, patrol, target, demand, session=None):
        """发起威胁（需嫌疑积分≥20）"""
        patrol_profile = _get_or_create_patrol_profile(patrol)
        suspicion = TellService.get_suspicion_score(patrol_profile, target, session)

        if suspicion < 20:
            return {'success': False, 'error': '嫌疑积分不足20，无法威胁'}

        expires_at = timezone.now() + timedelta(minutes=15)
        tx = GrayMarketTransaction.objects.create(
            transaction_type='extortion',
            initiator=patrol,
            recipient=target,
            status='proposed',
            offer_from_initiator=demand,
            checkpoint_session=session,
            expires_at=expires_at,
        )

        # 创建加密频道，发送暗示性消息
        channel = EncryptedChannel.objects.create(
            participant_a=patrol,
            participant_b=target,
            linked_transaction=tx,
        )
        tx.encrypted_channel_id = channel.id
        tx.status = 'negotiating'
        tx.save(update_fields=['encrypted_channel_id', 'status'])

        EncryptedMessage.objects.create(
            channel=channel,
            sender=patrol,
            content=f'你的通行证...看起来没什么问题。不过，这个时候还是需要——额外的关照吧。',
            is_system=False,
        )

        _notify_game(
            target, 'game_extortion_received', '收到威胁',
            f'{patrol.username} 向你发出了暗示。',
            actor=patrol,
        )

        return {'success': True, 'transaction': tx, 'channel': channel}

    @classmethod
    @transaction.atomic
    def pay_extortion(cls, tx, target):
        """支付威胁"""
        demand = tx.offer_from_initiator
        crystals_demanded = demand.get('crystals', 0)

        if crystals_demanded > 0:
            try:
                target_crystals = target.crystals
                if target_crystals.raw_crystals < crystals_demanded:
                    return {'success': False, 'error': '刀具不足'}
                target_crystals.raw_crystals -= crystals_demanded
                target_crystals.save(update_fields=['raw_crystals'])

                patrol_crystals, _ = PlayerCrystals.objects.get_or_create(user=tx.initiator)
                patrol_crystals.purified_crystals += crystals_demanded
                patrol_crystals.save(update_fields=['purified_crystals'])
            except PlayerCrystals.DoesNotExist:
                return {'success': False, 'error': '刀具不足'}

        tx.status = 'completed'
        tx.accepted_at = timezone.now()
        tx.save(update_fields=['status', 'accepted_at'])

        return {'success': True}

    @classmethod
    @transaction.atomic
    def propose_trade(cls, initiator, recipient, offer_a, offer_b=None):
        """发起双边交易"""
        expires_at = timezone.now() + timedelta(minutes=60)
        tx = GrayMarketTransaction.objects.create(
            transaction_type='trade',
            initiator=initiator,
            recipient=recipient,
            status='proposed',
            offer_from_initiator=offer_a,
            offer_from_recipient=offer_b or {},
            expires_at=expires_at,
        )
        _notify_game(
            recipient, 'game_bribe_received', '收到交易邀请',
            f'{initiator.username} 向你发起了交易。',
            actor=initiator,
        )
        return {'success': True, 'transaction': tx}

    @classmethod
    @transaction.atomic
    def complete_trade(cls, tx):
        """完成双边交易，执行物品/刀具交换"""
        offer_a = tx.offer_from_initiator
        offer_b = tx.offer_from_recipient

        # 交换刀具
        crystals_a = offer_a.get('crystals', 0)
        crystals_b = offer_b.get('crystals', 0)

        if crystals_a > 0:
            a_crystals = PlayerCrystals.objects.get(user=tx.initiator)
            b_crystals, _ = PlayerCrystals.objects.get_or_create(user=tx.recipient)
            a_crystals.raw_crystals -= crystals_a
            b_crystals.raw_crystals += crystals_a
            a_crystals.save(update_fields=['raw_crystals'])
            b_crystals.save(update_fields=['raw_crystals'])

        if crystals_b > 0:
            b_crystals = PlayerCrystals.objects.get(user=tx.recipient)
            a_crystals, _ = PlayerCrystals.objects.get_or_create(user=tx.initiator)
            b_crystals.raw_crystals -= crystals_b
            a_crystals.raw_crystals += crystals_b
            b_crystals.save(update_fields=['raw_crystals'])
            a_crystals.save(update_fields=['raw_crystals'])

        tx.status = 'completed'
        tx.accepted_at = timezone.now()
        tx.save(update_fields=['status', 'accepted_at'])
        return {'success': True}


# ─────────────────────────────────────────────
# DisguiseService — 伪装计算
# ─────────────────────────────────────────────

# 完全变装套装道具（slug列表）
FULL_DISGUISE_SET = {
    'professional_makeup_kit',
    'thigh_high_socks',
    'silky_lingerie_set',
    'concealing_foundation',
}


class DisguiseService:

    @classmethod
    def compute_detectability(cls, mimic_profile, active_disguise=None):
        """计算当前被发现率（0-100）"""
        base = mimic_profile.base_detectability  # 永久基础（脱毛仪后+15）
        score = base

        # 无伪装时
        if not active_disguise:
            score += mimic_profile.femboy_score // 10
            return min(100, max(0, score))

        # 外层道具加成
        if active_disguise.outer_layer_item:
            modifiers = active_disguise.outer_layer_item.stat_modifiers
            score += modifiers.get('detectability', 0)

        # 内层道具加成
        inner_slugs = set()
        for item in active_disguise.inner_items.all():
            modifiers = item.stat_modifiers
            score += modifiers.get('detectability', 0)
            inner_slugs.add(item.slug)

        # 完全变装套装悖论：4件套-8 detectability
        if FULL_DISGUISE_SET.issubset(inner_slugs):
            score -= 8

        # 发毛值影响
        if mimic_profile.suppression_value > 70:
            score += 10

        return min(100, max(0, score))

    @classmethod
    def compute_disguise_quality(cls, active_disguise=None):
        """计算伪装质量（0-100）"""
        if not active_disguise:
            return 0

        quality = 0
        if active_disguise.outer_layer_item:
            modifiers = active_disguise.outer_layer_item.stat_modifiers
            quality += modifiers.get('disguise_quality', 0)

        for item in active_disguise.inner_items.all():
            modifiers = item.stat_modifiers
            quality += modifiers.get('disguise_quality', 0)

        return min(100, quality)

    @classmethod
    def update_disguise_stats(cls, user):
        """重新计算并保存伪装统计，同时将道具的 femboy_score/smoothness_score 应用到 MimicProfile"""
        try:
            mimic = user.mimic_profile
            disguise = user.active_disguise
        except (MimicProfile.DoesNotExist, ActiveDisguise.DoesNotExist):
            return

        detectability = cls.compute_detectability(mimic, disguise)
        quality = cls.compute_disguise_quality(disguise)
        disguise.computed_detectability = detectability
        disguise.computed_disguise_quality = quality
        disguise.save(update_fields=['computed_detectability', 'computed_disguise_quality'])

        # 汇总所有已装备道具的 femboy_score / smoothness_score 加成，写入 MimicProfile
        total_femboy = 0
        total_smoothness = 0
        all_items = list(disguise.inner_items.all())
        if disguise.outer_layer_item:
            all_items.append(disguise.outer_layer_item)
        for item in all_items:
            mods = item.stat_modifiers
            total_femboy += mods.get('femboy_score', 0)
            total_smoothness += mods.get('smoothness_score', 0)

        # 保留自然增长（备皮间收集），加上道具加成，上限100
        # 用 base_femboy = max(0, 现有值 - 上次装备加成) 不好追踪，
        # 简化：将道具加成直接叠加，但不超过上限
        new_femboy = min(100, mimic.femboy_score + total_femboy)
        new_smoothness = min(100, mimic.smoothness_score + total_smoothness)
        if new_femboy != mimic.femboy_score or new_smoothness != mimic.smoothness_score:
            mimic.femboy_score = new_femboy
            mimic.smoothness_score = new_smoothness
            mimic.save(update_fields=['femboy_score', 'smoothness_score'])


# ─────────────────────────────────────────────
# CrystalService — 刀具收集与市场
# ─────────────────────────────────────────────

class CrystalService:

    @classmethod
    @transaction.atomic
    def harvest(cls, player, deposit):
        """收集刀具（仅限备皮间区域的小男娘，需要活跃锁任务）"""
        try:
            mimic = player.mimic_profile
        except MimicProfile.DoesNotExist:
            return {'success': False, 'error': '只有小男娘可以收集刀具'}

        # 检查是否在备皮间
        current_zone = PlayerZonePresence.objects.filter(
            user=player, exited_at__isnull=True
        ).select_related('zone').first()

        if not current_zone or current_zone.zone.name not in ('ruins', 'ruins_deep', 'ruins_outer'):
            return {'success': False, 'error': '只能在备皮间区域收集刀具'}

        if deposit.quantity <= 0:
            return {'success': False, 'error': '此矿点已耗尽'}

        # 需要活跃锁任务才能收集
        from tasks.models import LockTask
        active_lock = LockTask.objects.filter(
            user=player, status='active'
        ).first()
        if not active_lock:
            return {'success': False, 'error': '需要处于活跃锁任务中才能收集刀具'}

        # 收集量：1-3（受femboy_score加成）
        base_harvest = random.randint(1, 3)
        bonus = mimic.femboy_score // 50  # 每50点+1
        harvest_amount = min(deposit.quantity, base_harvest + bonus)

        deposit.quantity -= harvest_amount
        deposit.last_harvested_at = timezone.now()
        deposit.last_harvested_by = player
        deposit.save(update_fields=['quantity', 'last_harvested_at', 'last_harvested_by'])

        # 增加玩家刀具
        player_crystals, _ = PlayerCrystals.objects.get_or_create(user=player)
        player_crystals.raw_crystals += harvest_amount
        player_crystals.save(update_fields=['raw_crystals'])

        # 收集副作用：发毛值+5，femboy_score微增（备皮间环境影响）
        fields_to_save = ['total_crystals_collected', 'suppression_value', 'femboy_score']
        mimic.total_crystals_collected += harvest_amount
        mimic.suppression_value = min(100, mimic.suppression_value + 5)
        # femboy_score 每次收集+1，上限100（长期在备皮间中会改变气质）
        mimic.femboy_score = min(100, mimic.femboy_score + 1)
        mimic.save(update_fields=fields_to_save)

        return {
            'success': True,
            'harvested': harvest_amount,
            'remaining': deposit.quantity,
            'suppression_value': mimic.suppression_value,
            'femboy_score': mimic.femboy_score,
        }

    @classmethod
    @transaction.atomic
    def launder_crystals(cls, player, raw_amount):
        """黑市洗白备皮刀：70%转换率，需在 black_market 区域"""
        current_zone = PlayerZonePresence.objects.filter(
            user=player, exited_at__isnull=True
        ).select_related('zone').first()
        if not current_zone or current_zone.zone.name != 'black_market':
            return {'success': False, 'error': '只能在黑市进行洗白'}

        try:
            crystals = player.crystals
        except PlayerCrystals.DoesNotExist:
            return {'success': False, 'error': '未找到刀具账户'}

        if raw_amount <= 0:
            return {'success': False, 'error': '数量必须大于0'}
        if crystals.raw_crystals < raw_amount:
            return {'success': False, 'error': f'备皮刀不足，当前仅有 {crystals.raw_crystals}'}

        purified_gained = int(raw_amount * 0.70)
        crystals.raw_crystals -= raw_amount
        crystals.purified_crystals += purified_gained
        crystals.save(update_fields=['raw_crystals', 'purified_crystals'])

        ZoneChatMessage.objects.create(
            zone=current_zone.zone,
            sender=None,
            content='[系统]: 一笔交易悄然完成。',
            is_system=True,
        )

        return {
            'success': True,
            'raw_consumed': raw_amount,
            'purified_gained': purified_gained,
        }

    @classmethod
    def recalculate_market_rates(cls):
        """根据供需重算市场价格（Celery任务调用）"""
        rates = GameMarketRate.objects.all()
        for rate in rates:
            # 供需压力影响价格
            demand = rate.demand_pressure
            new_price = int(rate.base_price_crystals * demand)
            new_price = max(1, new_price)  # 最低1刀具

            rate.current_price_crystals = new_price
            # 重置交易量
            rate.units_traded_last_period = 0
            rate.save(update_fields=['current_price_crystals', 'units_traded_last_period'])

        logger.info(f'市场价格已重算，共更新 {rates.count()} 条记录')


# ─────────────────────────────────────────────
# ControlTransferService — 锁控制权代理
# ─────────────────────────────────────────────

class ControlTransferService:

    @classmethod
    def add_time(cls, transfer, grantee, minutes):
        """代理执行：对囚犯LockTask加时"""
        if not transfer.is_active:
            return {'success': False, 'error': '控制权已失效'}
        if transfer.grantee != grantee:
            return {'success': False, 'error': '无权操作'}
        if not transfer.can_add_time:
            return {'success': False, 'error': '此控制权不包含加时权限'}

        lock_task = transfer.lock_task
        if lock_task.end_time:
            lock_task.end_time += timedelta(minutes=minutes)
            lock_task.save(update_fields=['end_time'])

        # 在LockTask时间线留下记录（如果有TaskTimelineEvent模型）
        _record_control_action(lock_task, grantee, 'add_time', {'minutes': minutes})

        _notify_game(
            transfer.grantor, 'task_overtime_added', '锁被加时',
            f'[男娘幻城] {grantee.username} 对你的锁加时了 {minutes} 分钟。',
            actor=grantee,
        )

        return {'success': True, 'new_end_time': lock_task.end_time}

    @classmethod
    def freeze(cls, transfer, grantee):
        """代理执行：冻结囚犯LockTask"""
        if not transfer.is_active:
            return {'success': False, 'error': '控制权已失效'}
        if transfer.grantee != grantee:
            return {'success': False, 'error': '无权操作'}
        if not transfer.can_freeze:
            return {'success': False, 'error': '此控制权不包含冻结权限'}

        lock_task = transfer.lock_task
        if not lock_task.is_frozen:
            lock_task.is_frozen = True
            lock_task.frozen_at = timezone.now()
            lock_task.frozen_end_time = lock_task.end_time
            lock_task.save(update_fields=['is_frozen', 'frozen_at', 'frozen_end_time'])

        _record_control_action(lock_task, grantee, 'freeze', {})

        _notify_game(
            transfer.grantor, 'task_frozen_by_vote', '锁被冻结',
            f'[男娘幻城] {grantee.username} 冻结了你的锁。',
            actor=grantee,
        )

        return {'success': True}


# ─────────────────────────────────────────────
# ArmoryEncounterService — 储物柜暗道遭遇战
# ─────────────────────────────────────────────

class ArmoryEncounterService:

    TOLL_EXPIRE_MINUTES = 10

    @classmethod
    def check_for_encounter(cls, player):
        """进入储物柜时检查遭遇。50%概率触发（若有不同派系玩家在场）"""
        armory_zone = GameZone.objects.filter(name='armory').first()
        if not armory_zone:
            return {'triggered': False}

        others = PlayerZonePresence.objects.filter(
            zone=armory_zone, exited_at__isnull=True
        ).exclude(user=player).select_related('user')

        if not others.exists():
            return {'triggered': False}

        if random.random() > 0.5:
            return {'triggered': False}

        # 选择第一个其他玩家
        other_presence = others.first()
        other = other_presence.user

        # 确定角色
        try:
            player.mimic_profile
            player_role = 'target'
        except MimicProfile.DoesNotExist:
            player_role = 'demand'

        try:
            other.patrol_profile
            other_role = 'demand'
        except PatrolProfile.DoesNotExist:
            other_role = 'target'

        # 若双方同阵营，不触发
        if player_role == other_role:
            return {'triggered': False}

        return {
            'triggered': True,
            'other_player': {'id': other.id, 'username': other.username},
            'role': player_role,
        }

    @classmethod
    @transaction.atomic
    def initiate_toll_demand(cls, patrol, target_mimic, demanded_crystals):
        """小s在储物柜索取通行费"""
        try:
            patrol.patrol_profile
        except PatrolProfile.DoesNotExist:
            return {'success': False, 'error': '只有小s可以索取通行费'}

        # 确认双方都在储物柜
        armory_zone = GameZone.objects.filter(name='armory').first()
        patrol_presence = PlayerZonePresence.objects.filter(
            user=patrol, zone=armory_zone, exited_at__isnull=True
        ).first()
        mimic_presence = PlayerZonePresence.objects.filter(
            user=target_mimic, zone=armory_zone, exited_at__isnull=True
        ).first()
        if not patrol_presence or not mimic_presence:
            return {'success': False, 'error': '双方必须都在储物柜'}

        # 创建加密频道
        channel = EncryptedChannel.objects.create(
            initiator=patrol,
            recipient=target_mimic,
            status='active',
        )
        EncryptedMessage.objects.create(
            channel=channel,
            sender=None,
            content=f'[系统]: {patrol.username} 拦住了去路，索取通行费。',
            is_system=True,
        )

        tx = GrayMarketTransaction.objects.create(
            transaction_type='armory_toll',
            initiator=patrol,
            recipient=target_mimic,
            status='proposed',
            offer_from_initiator={'crystals': demanded_crystals},
            encrypted_channel_id=channel.id,
            zone_name='armory',
            expires_at=timezone.now() + timedelta(minutes=cls.TOLL_EXPIRE_MINUTES),
        )

        return {'success': True, 'transaction_id': str(tx.id), 'channel_id': str(channel.id)}

    @classmethod
    @transaction.atomic
    def pay_toll(cls, tx, mimic):
        """小男娘支付通行费"""
        if tx.status != 'proposed':
            return {'success': False, 'error': '交易已结束'}
        if tx.recipient != mimic:
            return {'success': False, 'error': '无权操作'}

        amount = tx.offer_from_initiator.get('crystals', 0)
        try:
            crystals = mimic.crystals
        except PlayerCrystals.DoesNotExist:
            return {'success': False, 'error': '刀具账户不存在'}

        if crystals.raw_crystals < amount:
            return {'success': False, 'error': f'备皮刀不足，需要 {amount}'}

        # 转移备皮刀
        crystals.raw_crystals -= amount
        crystals.save(update_fields=['raw_crystals'])

        try:
            patrol_crystals = tx.initiator.crystals
            patrol_crystals.raw_crystals += amount
            patrol_crystals.save(update_fields=['raw_crystals'])
        except PlayerCrystals.DoesNotExist:
            pass

        # 属性变化
        try:
            mimic_profile = mimic.mimic_profile
            mimic_profile.purity_score = min(100, mimic_profile.purity_score + 3)
            mimic_profile.suppression_value = max(0, mimic_profile.suppression_value - 5)
            mimic_profile.save(update_fields=['purity_score', 'suppression_value'])
        except MimicProfile.DoesNotExist:
            pass

        try:
            patrol_profile = tx.initiator.patrol_profile
            patrol_profile.authority_value = max(0, patrol_profile.authority_value - 5)
            patrol_profile.save(update_fields=['authority_value'])
        except PatrolProfile.DoesNotExist:
            pass

        tx.initiator.add_coins(3, 'event_reward', '储物柜通行费')

        tx.status = 'completed'
        tx.accepted_at = timezone.now()
        tx.save(update_fields=['status', 'accepted_at'])

        _notify_game(tx.initiator, 'game_armory', '通行费已收取', f'{mimic.username} 支付了 {amount} 备皮刀。')

        return {'success': True, 'crystals_paid': amount}

    @classmethod
    @transaction.atomic
    def resist_toll(cls, tx, mimic):
        """小男娘抵抗通行费索取（control_resistance检定）"""
        if tx.status != 'proposed':
            return {'success': False, 'error': '交易已结束'}
        if tx.recipient != mimic:
            return {'success': False, 'error': '无权操作'}

        try:
            mimic_profile = mimic.mimic_profile
        except MimicProfile.DoesNotExist:
            return {'success': False, 'error': '档案不存在'}

        resistance = getattr(mimic_profile, 'control_resistance', 0)
        roll = random.randint(0, max(1, resistance) + 20)

        if roll > 30:
            # 成功抵抗
            mimic_profile.suppression_value = min(100, mimic_profile.suppression_value + 5)
            mimic_profile.purity_score = min(100, mimic_profile.purity_score + 5)
            mimic_profile.save(update_fields=['suppression_value', 'purity_score'])

            try:
                patrol_profile = tx.initiator.patrol_profile
                patrol_profile.authority_value = max(0, patrol_profile.authority_value - 10)
                patrol_profile.save(update_fields=['authority_value'])
            except PatrolProfile.DoesNotExist:
                pass

            mimic.add_coins(2, 'event_reward', '成功抵抗储物柜威胁')
            tx.status = 'rejected'
            tx.save(update_fields=['status'])

            _notify_game(tx.initiator, 'game_armory', '抵抗成功', f'{mimic.username} 成功抵抗了索取。')

            return {'success': True, 'escaped': True, 'suppression_change': 5}
        else:
            # 抵抗失败，强制收缴
            amount = tx.offer_from_initiator.get('crystals', 0)
            try:
                crystals = mimic.crystals
                seized = min(crystals.raw_crystals, amount)
                crystals.raw_crystals -= seized
                crystals.save(update_fields=['raw_crystals'])
            except PlayerCrystals.DoesNotExist:
                seized = 0

            try:
                patrol_crystals = tx.initiator.crystals
                patrol_crystals.raw_crystals += seized
                patrol_crystals.save(update_fields=['raw_crystals'])
            except PlayerCrystals.DoesNotExist:
                pass

            mimic_profile.suppression_value = min(100, mimic_profile.suppression_value + 15)
            mimic_profile.purity_score = max(0, mimic_profile.purity_score - 3)
            mimic_profile.save(update_fields=['suppression_value', 'purity_score'])

            tx.initiator.add_coins(3, 'event_reward', '储物柜强制收缴')
            tx.status = 'completed'
            tx.accepted_at = timezone.now()
            tx.save(update_fields=['status', 'accepted_at'])

            _notify_game(tx.initiator, 'game_armory', '强制收缴成功', f'已强制收缴 {mimic.username} 的 {seized} 备皮刀。')

            return {'success': True, 'escaped': False, 'crystals_seized': seized}

    @classmethod
    @transaction.atomic
    def flee_armory(cls, mimic):
        """小男娘溜走储物柜（+15压制，-3纯净，移至闺房）"""
        # 取消进行中的toll交易
        GrayMarketTransaction.objects.filter(
            recipient=mimic,
            transaction_type='armory_toll',
            status='proposed',
        ).update(status='rejected')

        try:
            mimic_profile = mimic.mimic_profile
            mimic_profile.suppression_value = min(100, mimic_profile.suppression_value + 15)
            mimic_profile.purity_score = max(0, mimic_profile.purity_score - 3)
            mimic_profile.save(update_fields=['suppression_value', 'purity_score'])
        except MimicProfile.DoesNotExist:
            pass

        salon = GameZone.objects.filter(name='salon').first()
        if salon:
            PlayerZonePresence.objects.filter(user=mimic, exited_at__isnull=True).update(exited_at=timezone.now())
            PlayerZonePresence.objects.create(user=mimic, zone=salon)
            ZoneChatMessage.objects.create(
                zone=salon,
                sender=None,
                content=f'[系统]: {mimic.username} 慌乱地跑进了闺房。',
                is_system=True,
            )

        return {'success': True, 'suppression_added': 15}


# ─────────────────────────────────────────────
# SewerEncounterService — 下水道遭遇
# ─────────────────────────────────────────────

class SewerEncounterService:

    @classmethod
    @transaction.atomic
    def check_for_encounter(cls, player):
        """进入管道时检查遭遇（30%概率）"""
        sewer_zone = GameZone.objects.filter(name='sewer').first()
        if not sewer_zone:
            return {'triggered': False}

        others = PlayerZonePresence.objects.filter(
            zone=sewer_zone, exited_at__isnull=True
        ).exclude(user=player).select_related('user')

        if not others.exists():
            return {'triggered': False}

        if random.random() > 0.30:
            return {'triggered': False}

        other = others.first().user

        # 确定双方角色
        try:
            player.mimic_profile
            player_is_mimic = True
        except MimicProfile.DoesNotExist:
            player_is_mimic = False

        try:
            other.mimic_profile
            other_is_mimic = True
        except MimicProfile.DoesNotExist:
            other_is_mimic = False

        # 小男娘互认：立即结算
        if player_is_mimic and other_is_mimic:
            for u in (player, other):
                try:
                    mp = u.mimic_profile
                    mp.suppression_value = max(0, mp.suppression_value - 5)
                    mp.purity_score = min(100, mp.purity_score + 2)
                    mp.save(update_fields=['suppression_value', 'purity_score'])
                except MimicProfile.DoesNotExist:
                    pass
                u.add_coins(1, 'event_reward', '管道小男娘互认')

            return {
                'triggered': True,
                'type': 'mimic_mimic',
                'resolved': True,
                'other_player': {'id': other.id, 'username': other.username},
            }

        # 小s vs 小男娘
        if player_is_mimic and not other_is_mimic:
            role = 'target'
        elif not player_is_mimic and other_is_mimic:
            role = 'demand'
        else:
            return {'triggered': False}

        # 小s视角：评估破绽（最多2条）
        tells_data = []
        if role == 'demand':
            tells_data = TellService.evaluate_tells(player, sewer_zone, action_type='zone_entry')
            tells_data = tells_data[:2]

        return {
            'triggered': True,
            'type': 'patrol_mimic',
            'resolved': False,
            'role': role,
            'other_player': {'id': other.id, 'username': other.username},
            'tells': [t.tell_text for t in tells_data] if tells_data else [],
        }

    @classmethod
    @transaction.atomic
    def sewer_demand(cls, patrol, mimic_id, amount):
        """小s在管道中强制收缴备皮刀"""
        try:
            patrol.patrol_profile
        except PatrolProfile.DoesNotExist:
            return {'success': False, 'error': '只有小s可以执行此操作'}

        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            mimic = User.objects.get(id=mimic_id)
        except User.DoesNotExist:
            return {'success': False, 'error': '目标玩家不存在'}

        sewer_zone = GameZone.objects.filter(name='sewer').first()
        mimic_presence = PlayerZonePresence.objects.filter(
            user=mimic, zone=sewer_zone, exited_at__isnull=True
        ).first()
        if not mimic_presence:
            return {'success': False, 'error': '目标玩家不在管道中'}

        try:
            crystals = mimic.crystals
            seized = min(crystals.raw_crystals, amount)
            crystals.raw_crystals -= seized
            crystals.save(update_fields=['raw_crystals'])
        except PlayerCrystals.DoesNotExist:
            seized = 0

        try:
            patrol_crystals = patrol.crystals
            patrol_crystals.raw_crystals += seized
            patrol_crystals.save(update_fields=['raw_crystals'])
        except PlayerCrystals.DoesNotExist:
            pass

        try:
            mimic_profile = mimic.mimic_profile
            mimic_profile.suppression_value = min(100, mimic_profile.suppression_value + 5)
            mimic_profile.save(update_fields=['suppression_value'])
        except MimicProfile.DoesNotExist:
            pass

        patrol.add_coins(2, 'event_reward', '管道检查收缴')

        # 评估破绽（最多2条，用于小s记录）
        tells_data = TellService.evaluate_tells(mimic, sewer_zone, action_type='zone_entry')
        tells_data = tells_data[:2]

        _notify_game(mimic, 'game_sewer', '管道检查', f'{patrol.username} 在管道中收缴了你 {seized} 备皮刀。')

        return {
            'success': True,
            'crystals_seized': seized,
            'tells': [t.tell_text for t in tells_data],
        }


# ─────────────────────────────────────────────
# CampAidService — 更衣室互助
# ─────────────────────────────────────────────

class CampAidService:
    WATCH_DURATION_MINUTES = 10

    @classmethod
    @transaction.atomic
    def share_food(cls, giver, recipient_id):
        """分享食物：消耗一个消耗品，接受者发毛值-10，给予者光滑度+2，+1 coin"""
        camp_zone = GameZone.objects.filter(name='abandoned_camp').first()
        if not camp_zone:
            return {'success': False, 'error': '区域不存在'}

        giver_presence = PlayerZonePresence.objects.filter(
            user=giver, zone=camp_zone, exited_at__isnull=True
        ).first()
        if not giver_presence:
            return {'success': False, 'error': '你不在更衣室'}

        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            recipient = User.objects.get(id=recipient_id)
        except User.DoesNotExist:
            return {'success': False, 'error': '目标玩家不存在'}

        recipient_presence = PlayerZonePresence.objects.filter(
            user=recipient, zone=camp_zone, exited_at__isnull=True
        ).first()
        if not recipient_presence:
            return {'success': False, 'error': '目标玩家不在更衣室'}

        # 消耗一个消耗品
        consumable = PlayerGameInventory.objects.filter(
            user=giver, item__slot='consumable', quantity__gt=0
        ).select_related('item').first()
        if not consumable:
            return {'success': False, 'error': '背包中没有消耗品'}

        item_name = consumable.item.name
        consumable.quantity -= 1
        if consumable.quantity == 0:
            consumable.delete()
        else:
            consumable.save(update_fields=['quantity'])

        # 接受者发毛值-10
        try:
            recipient_profile = recipient.mimic_profile
            recipient_profile.suppression_value = max(0, recipient_profile.suppression_value - 10)
            recipient_profile.save(update_fields=['suppression_value'])
            new_suppression = recipient_profile.suppression_value
        except MimicProfile.DoesNotExist:
            new_suppression = 0

        # 给予者光滑度+2，+1 coin
        try:
            giver_profile = giver.mimic_profile
            giver_profile.purity_score = min(100, giver_profile.purity_score + 2)
            giver_profile.save(update_fields=['purity_score'])
        except MimicProfile.DoesNotExist:
            pass

        giver.add_coins(1, 'event_reward', '营地互助分享食物')

        ZoneChatMessage.objects.create(
            zone=camp_zone,
            sender=None,
            content=f'[系统]: {giver.username} 向 {recipient.username} 分享了食物。',
            is_system=True,
        )

        _notify_game(recipient, 'game_camp', '收到食物', f'{giver.username} 向你分享了食物，发毛值-10。')

        return {
            'success': True,
            'item_used': item_name,
            'recipient_suppression': new_suppression,
        }

    @classmethod
    @transaction.atomic
    def start_watch(cls, watcher):
        """开始站岗警戒（10分钟）"""
        camp_zone = GameZone.objects.filter(name='abandoned_camp').first()
        if not camp_zone:
            return {'success': False, 'error': '区域不存在'}

        presence = PlayerZonePresence.objects.filter(
            user=watcher, zone=camp_zone, exited_at__isnull=True
        ).first()
        if not presence:
            return {'success': False, 'error': '你不在更衣室'}

        watch_until = timezone.now() + timedelta(minutes=cls.WATCH_DURATION_MINUTES)
        stats = presence.entry_stats or {}
        stats['on_watch'] = True
        stats['watch_until'] = watch_until.isoformat()
        presence.entry_stats = stats
        presence.save(update_fields=['entry_stats'])

        ZoneChatMessage.objects.create(
            zone=camp_zone,
            sender=None,
            content=f'[系统]: {watcher.username} 开始站岗警戒。',
            is_system=True,
        )

        return {'success': True, 'watch_until': watch_until.isoformat()}

    @classmethod
    def get_active_watches(cls, zone):
        """返回当前在岗的玩家列表"""
        now = timezone.now()
        presences = PlayerZonePresence.objects.filter(
            zone=zone, exited_at__isnull=True
        ).select_related('user')

        watchers = []
        for p in presences:
            stats = p.entry_stats or {}
            if stats.get('on_watch') and stats.get('watch_until'):
                try:
                    from django.utils.dateparse import parse_datetime
                    until = parse_datetime(stats['watch_until'])
                    if until and until > now:
                        watchers.append({'id': p.user.id, 'username': p.user.username})
                except Exception:
                    pass
        return watchers

    @classmethod
    def patrol_alert(cls, patrol_player, zone):
        """小s进入营地时，通知值班哨兵"""
        watchers = cls.get_active_watches(zone)
        if watchers:
            ZoneChatMessage.objects.create(
                zone=zone,
                sender=None,
                content=f'[系统警报]: 营地哨兵发现小s员 {patrol_player.username} 接近！',
                is_system=True,
            )


# ─────────────────────────────────────────────
# ZoneService — 区域移动
# ─────────────────────────────────────────────

class ZoneService:

    # 区域邻接图：只能移动到相邻区域
    ZONE_ADJACENCY = {
        'black_market':       ['salon'],
        'salon':              ['black_market', 'checkpoint', 'armory', 'sewer'],
        'armory':             ['salon', 'abandoned_camp'],
        'checkpoint':         ['salon', 'abandoned_camp'],
        'sewer':              ['salon', 'ruins_outer'],
        'abandoned_camp':     ['armory', 'checkpoint', 'ruins', 'ruins_outer'],
        'ruins_outer':        ['sewer', 'abandoned_camp', 'ruins'],
        'ruins':              ['abandoned_camp', 'ruins_outer', 'ruins_deep'],
        'ruins_deep':         ['ruins'],
        'interrogation_room': [],  # 仅系统（被盘问）可移入
        'control_room':       [],  # 仅系统（被捕）可移入
    }
    # 首次进入游戏（无当前位置）允许选择的起始区域
    ENTRY_ZONES = ['salon', 'checkpoint']
    # 仅系统可移入的区域，玩家不能主动进入
    SYSTEM_ONLY_ZONES = ['control_room', 'interrogation_room']

    @classmethod
    @transaction.atomic
    def travel_to(cls, player, zone_name):
        """移动到指定区域"""
        try:
            zone = GameZone.objects.get(name=zone_name)
        except GameZone.DoesNotExist:
            return {'success': False, 'error': '区域不存在'}

        # 检查是否在收押中
        active_detention = DetentionRecord.objects.filter(
            prisoner=player, status='active'
        ).first()
        if active_detention and zone_name != 'control_room':
            return {'success': False, 'error': '你正处于收押状态，无法移动'}

        # 系统专用区域：玩家不能主动进入
        if zone_name in cls.SYSTEM_ONLY_ZONES:
            if zone_name == 'control_room' and not active_detention:
                return {'success': False, 'error': '禁闭室仅在被捕时可进入'}
            elif zone_name == 'interrogation_room':
                return {'success': False, 'error': '审问室仅在被盘问时可进入'}

        # 离开当前区域
        old_presence = PlayerZonePresence.objects.filter(
            user=player, exited_at__isnull=True
        ).first()

        if old_presence:
            if old_presence.zone == zone:
                return {'success': False, 'error': '你已在此区域'}

            # 邻接限制：只能移动到相邻区域
            current_zone_name = old_presence.zone.name
            allowed = cls.ZONE_ADJACENCY.get(current_zone_name, [])
            if zone_name not in allowed:
                return {'success': False, 'error': f'无法直接前往{zone.display_name}，需经过中间地点'}

            # 安检口队列锁：小男娘在pending状态时无法直接离开（只能溜走或通过）
            if current_zone_name == 'checkpoint' and zone_name not in ('abandoned_camp',):
                pending = CheckpointParticipant.objects.filter(
                    session__status='active', user=player,
                    outcome='pending', role='smuggler'
                ).first()
                if pending:
                    return {'success': False, 'error': '你正在安检口队列中，请使用溜走选项离开'}

            old_presence.exited_at = timezone.now()
            old_presence.save(update_fields=['exited_at'])
        else:
            # 首次进入游戏：只能进入起始区域（被捕时可直接进入禁闭室）
            if zone_name not in cls.ENTRY_ZONES and not (active_detention and zone_name == 'control_room'):
                return {'success': False, 'error': f'初次进入游戏只能前往闺房或安检口'}

        # 进入新区域
        try:
            mimic = player.mimic_profile
            stats_snapshot = {
                'depilation_charge': mimic.depilation_charge,
                'suppression_value': mimic.suppression_value,
                'purity_score': mimic.purity_score,
            }
        except MimicProfile.DoesNotExist:
            stats_snapshot = {}

        new_presence = PlayerZonePresence.objects.create(
            user=player,
            zone=zone,
            entry_stats=stats_snapshot,
        )

        # 区域聊天系统消息
        ZoneChatMessage.objects.create(
            zone=zone,
            sender=None,
            content=f'[系统]: {player.username} 进入了{zone.display_name}。',
            is_system=True,
        )

        # 进入安检口时自动加入队列
        if zone_name == 'checkpoint':
            session = CheckpointService.get_or_create_active_session(zone)
            CheckpointService.join_as_smuggler(player, session)

        # 安全区补觉：降低发毛值
        if zone_name == 'salon':
            cls._apply_salon_rest(player)

        # 更衣室轻度补觉：降低发毛值；小s进入触发哨兵警报
        if zone_name == 'abandoned_camp':
            cls._apply_camp_rest(player)
            try:
                player.patrol_profile
                CampAidService.patrol_alert(player, zone)
            except PatrolProfile.DoesNotExist:
                pass

        # 下水道环境惩罚：发毛值+10
        if zone_name == 'sewer':
            cls._enter_sewer(player)

        # 进入备皮间/深处备皮间/外围备皮间：开始伪装计时（发毛值积累）
        if zone_name in ('ruins', 'ruins_deep', 'ruins_outer'):
            cls._enter_ruins(player)

        # 离开备皮间/深处备皮间/外围备皮间：停止伪装计时
        if old_presence and old_presence.zone.name in ('ruins', 'ruins_deep', 'ruins_outer'):
            cls._exit_ruins(player)

        # 从安检口离开（小男娘方向）：记录通关成功
        if old_presence and old_presence.zone.name == 'checkpoint' and zone_name == 'abandoned_camp':
            cls._record_checkpoint_pass(player)

        return {'success': True, 'zone': zone, 'presence': new_presence}

    @classmethod
    def _apply_salon_rest(cls, player):
        """在闺房自动降低发毛值"""
        try:
            mimic = player.mimic_profile
            if mimic.suppression_value > 0:
                mimic.suppression_value = max(0, mimic.suppression_value - 15)
                mimic.save(update_fields=['suppression_value'])
        except MimicProfile.DoesNotExist:
            pass

    @classmethod
    def _enter_ruins(cls, player):
        """进入备皮间：开启伪装状态（发毛值开始累积）"""
        try:
            mimic = player.mimic_profile
            if not mimic.is_disguised:
                mimic.is_disguised = True
                mimic.disguise_start_time = timezone.now()
                mimic.save(update_fields=['is_disguised', 'disguise_start_time'])
        except MimicProfile.DoesNotExist:
            pass

    @classmethod
    def _exit_ruins(cls, player):
        """离开备皮间/深处备皮间：关闭伪装状态"""
        try:
            mimic = player.mimic_profile
            if mimic.is_disguised:
                mimic.is_disguised = False
                mimic.save(update_fields=['is_disguised'])
        except MimicProfile.DoesNotExist:
            pass

    @classmethod
    def _enter_sewer(cls, player):
        """下水道环境惩罚：发毛值+10"""
        try:
            mimic = player.mimic_profile
            mimic.suppression_value = min(100, mimic.suppression_value + 10)
            mimic.save(update_fields=['suppression_value'])
        except MimicProfile.DoesNotExist:
            pass

    @classmethod
    def _apply_camp_rest(cls, player):
        """更衣室轻度补觉：降低发毛值5"""
        try:
            mimic = player.mimic_profile
            if mimic.suppression_value > 0:
                mimic.suppression_value = max(0, mimic.suppression_value - 5)
                mimic.save(update_fields=['suppression_value'])
        except MimicProfile.DoesNotExist:
            pass

    @classmethod
    def _record_checkpoint_pass(cls, player):
        """从安检口成功穿越到备皮间：记录统计，奖励光滑度"""
        try:
            mimic = player.mimic_profile
            mimic.total_successful_runs += 1
            mimic.purity_score = min(100, mimic.purity_score + 5)
            mimic.save(update_fields=['total_successful_runs', 'purity_score'])
        except MimicProfile.DoesNotExist:
            pass
        from .models import CheckpointParticipant
        CheckpointParticipant.objects.filter(
            user=player, role='smuggler', outcome='pending'
        ).update(outcome='passed')

    @classmethod
    def speak(cls, player, zone, content):
        """在区域发言，触发破绽评估"""
        # 检查是否在该区域
        presence = PlayerZonePresence.objects.filter(
            user=player, zone=zone, exited_at__isnull=True
        ).first()
        if not presence:
            return {'success': False, 'error': '你不在此区域'}

        # 创建聊天消息
        msg = ZoneChatMessage.objects.create(
            zone=zone,
            sender=player,
            content=content,
        )

        # 如果在安检口，评估破绽
        tells = []
        if zone.name == 'checkpoint':
            session = CheckpointSession.objects.filter(
                zone=zone, status='active'
            ).first()
            tells = TellService.evaluate_tells(
                player, zone, action_type='speak', session=session
            )

        return {'success': True, 'message': msg, 'tells': tells}


# ─────────────────────────────────────────────
# 辅助函数
# ─────────────────────────────────────────────

def _get_or_create_patrol_profile(user):
    profile, _ = PatrolProfile.objects.get_or_create(user=user)
    return profile


def _get_or_create_mimic_profile(user):
    profile, _ = MimicProfile.objects.get_or_create(user=user)
    return profile


def _notify_game(recipient, notification_type, title, message, actor=None, priority='normal'):
    """发送游戏通知（复用 users.Notification）"""
    try:
        from users.models import Notification
        Notification.create_notification(
            recipient=recipient,
            notification_type=notification_type,
            title=title,
            message=message,
            actor=actor,
            priority=priority,
        )
    except Exception as e:
        logger.warning(f'发送通知失败: {e}')


def _send_zone_system_message(user, content):
    """向用户当前区域发送系统消息"""
    presence = PlayerZonePresence.objects.filter(
        user=user, exited_at__isnull=True
    ).select_related('zone').first()
    if presence:
        ZoneChatMessage.objects.create(
            zone=presence.zone,
            sender=None,
            content=content,
            is_system=True,
        )


def _send_encrypted_system_message(user_a, user_b, content):
    """创建或复用加密频道，发送系统消息"""
    channel = EncryptedChannel.objects.filter(
        participant_a=user_a,
        participant_b=user_b,
        is_active=True,
    ).first() or EncryptedChannel.objects.filter(
        participant_a=user_b,
        participant_b=user_a,
        is_active=True,
    ).first()

    if not channel:
        channel = EncryptedChannel.objects.create(
            participant_a=user_a,
            participant_b=user_b,
        )

    EncryptedMessage.objects.create(
        channel=channel,
        sender=None,
        content=content,
        is_system=True,
    )


def _record_control_action(lock_task, actor, action_type, metadata):
    """在LockTask时间线记录游戏控制操作"""
    try:
        from tasks.models import TaskTimelineEvent
        TaskTimelineEvent.objects.create(
            task=lock_task,
            actor=actor,
            event_type='item_effect_applied',
            metadata={
                'game': 'phantom_city',
                'type': action_type,
                **metadata,
            }
        )
    except Exception:
        pass  # TaskTimelineEvent可能不存在，静默忽略
