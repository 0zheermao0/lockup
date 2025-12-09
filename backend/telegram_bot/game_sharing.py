"""
Telegram Bot游戏分享功能
正确实现：应用内发起游戏 -> 分享到Telegram -> Telegram中响应
"""

import json
import logging
from typing import Dict, Any, Optional
from django.contrib.auth import get_user_model
from django.utils import timezone
from store.models import Game, GameParticipant
from tasks.models import LockTask
from .services import telegram_service

User = get_user_model()
logger = logging.getLogger(__name__)


class TelegramGameSharing:
    """Telegram游戏分享管理器"""

    @staticmethod
    def generate_game_share_message(game: Game) -> tuple[str, dict]:
        """生成游戏分享消息和按钮"""

        # 游戏类型映射
        game_type_map = {
            'rock_paper_scissors': {
                'emoji': '✂️',
                'name': '石头剪刀布',
                'buttons': [
                    {'text': '✊ 石头', 'callback_data': f'game_{game.id}_rock'},
                    {'text': '✋ 布', 'callback_data': f'game_{game.id}_paper'},
                    {'text': '✌️ 剪刀', 'callback_data': f'game_{game.id}_scissors'}
                ]
            },
            'time_wheel': {
                'emoji': '🎯',
                'name': '时间转盘',
                'buttons': [
                    {'text': '🎯 参与挑战', 'callback_data': f'game_{game.id}_join'}
                ]
            }
        }

        game_info = game_type_map.get(game.game_type, {
            'emoji': '🎮',
            'name': game.get_game_type_display(),
            'buttons': [{'text': '🎮 参与游戏', 'callback_data': f'game_{game.id}_join'}]
        })

        # 计算剩余时间
        if game.expires_at:
            remaining = game.expires_at - timezone.now()
            if remaining.total_seconds() > 0:
                hours = int(remaining.total_seconds() // 3600)
                minutes = int((remaining.total_seconds() % 3600) // 60)
                time_left = f"{hours}小时{minutes}分钟" if hours > 0 else f"{minutes}分钟"
            else:
                time_left = "已过期"
        else:
            time_left = "无限制"

        # 生成分享消息
        message_text = f"""
{game_info['emoji']} **游戏挑战**

🎮 **游戏类型**: {game_info['name']}
👤 **发起者**: {game.creator.username}
💰 **赌注**: {game.bet_amount} 积分
⏰ **有效期**: {time_left}
👥 **参与人数**: {game.participants.count()}/{game.max_players}

💪 来接受挑战吧！
        """.strip()

        # 创建按钮键盘
        keyboard = {
            'inline_keyboard': [
                [{'text': btn['text'], 'callback_data': btn['callback_data']}
                 for btn in game_info['buttons']]
            ]
        }

        return message_text, keyboard

    @staticmethod
    def can_user_participate(user: User, game: Game) -> tuple[bool, str]:
        """检查用户是否可以参与游戏"""

        # 检查用户是否已绑定Telegram
        if not user.is_telegram_bound():
            return False, "用户未绑定Telegram"

        # 检查游戏状态
        if game.status != 'waiting':
            return False, "游戏已开始或已结束"

        # 检查是否已经参与
        if GameParticipant.objects.filter(game=game, user=user).exists():
            return False, "已经参与了这个游戏"

        # 检查是否是创建者
        if game.creator == user:
            return False, "不能参与自己创建的游戏"

        # 检查游戏是否已满
        if game.participants.count() >= game.max_players:
            return False, "游戏人数已满"

        # 检查游戏是否过期
        if game.expires_at and game.expires_at < timezone.now():
            return False, "游戏挑战已过期"

        # 检查用户是否处于带锁状态（关键校验）
        active_lock_task = LockTask.objects.filter(
            user=user,
            task_type='lock',
            status='active'
        ).first()

        if active_lock_task:
            return False, f"用户正在执行带锁任务《{active_lock_task.title}》，无法参与游戏"

        # 检查积分是否足够
        if user.coins < game.bet_amount:
            return False, f"积分不足，需要{game.bet_amount}积分"

        return True, "可以参与"

    @staticmethod
    async def handle_game_participation(user: User, game_id: str, choice: str = None) -> Dict[str, Any]:
        """处理Telegram中的游戏参与"""

        try:
            game = Game.objects.get(id=game_id)
        except Game.DoesNotExist:
            return {
                'success': False,
                'message': "游戏不存在",
                'should_edit_message': False
            }

        # 检查用户是否可以参与
        can_participate, reason = TelegramGameSharing.can_user_participate(user, game)
        if not can_participate:
            return {
                'success': False,
                'message': f"❌ 无法参与游戏：{reason}",
                'should_edit_message': False
            }

        try:
            # 创建游戏参与记录
            participant = GameParticipant.objects.create(
                game=game,
                user=user,
                choice=choice  # 对于石头剪刀布，记录选择
            )

            # 扣除积分
            user.coins -= game.bet_amount
            user.save()

            # 检查是否达到最大人数，如果是则开始游戏
            participant_count = game.participants.count()

            if participant_count >= game.max_players:
                # 游戏开始逻辑（调用现有的游戏处理逻辑）
                game_result = TelegramGameSharing._start_game(game)

                return {
                    'success': True,
                    'message': f"✅ 成功参与游戏！\n\n{game_result}",
                    'should_edit_message': True,
                    'new_message': f"🎮 游戏已开始！\n\n{game_result}"
                }
            else:
                return {
                    'success': True,
                    'message': f"✅ 成功参与游戏！等待其他玩家加入...\n当前人数：{participant_count}/{game.max_players}",
                    'should_edit_message': True,
                    'new_message': f"🎮 等待更多玩家...\n当前人数：{participant_count}/{game.max_players}"
                }

        except Exception as e:
            logger.error(f"处理游戏参与时出错: {e}")
            return {
                'success': False,
                'message': "参与游戏时出现错误，请稍后重试",
                'should_edit_message': False
            }

    @staticmethod
    def _start_game(game: Game) -> str:
        """开始游戏并返回结果"""

        if game.game_type == 'rock_paper_scissors':
            return TelegramGameSharing._handle_rock_paper_scissors(game)
        elif game.game_type == 'time_wheel':
            return TelegramGameSharing._handle_time_wheel(game)
        else:
            return "游戏类型不支持"

    @staticmethod
    def _handle_rock_paper_scissors(game: Game) -> str:
        """处理石头剪刀布游戏"""
        participants = list(GameParticipant.objects.filter(game=game))

        if len(participants) < 2:
            return "参与人数不足"

        # 游戏逻辑（复用现有逻辑）
        choices_map = {'rock': '✊ 石头', 'paper': '✋ 布', 'scissors': '✌️ 剪刀'}

        results = []
        for participant in participants:
            choice_display = choices_map.get(participant.choice, participant.choice)
            results.append(f"{participant.user.username}: {choice_display}")

        # 简单的胜负判断逻辑
        if len(participants) == 2:
            p1, p2 = participants[0], participants[1]
            winner = TelegramGameSharing._determine_rps_winner(p1.choice, p2.choice)

            if winner == 'tie':
                result_text = "🤝 平局！积分退还"
                # 退还积分
                for participant in participants:
                    participant.user.coins += game.bet_amount
                    participant.user.save()
            else:
                winner_participant = p1 if winner == 'p1' else p2
                loser_participant = p2 if winner == 'p1' else p1

                # 分配奖励
                total_reward = game.bet_amount * 2
                winner_participant.user.coins += total_reward
                winner_participant.user.save()

                result_text = f"🎉 {winner_participant.user.username} 获胜！\n获得 {total_reward} 积分"

        else:
            result_text = "多人游戏结果计算中..."

        # 更新游戏状态
        game.status = 'completed'
        game.completed_at = timezone.now()
        game.save()

        return f"🎮 游戏结果：\n\n" + "\n".join(results) + f"\n\n{result_text}"

    @staticmethod
    def _determine_rps_winner(choice1: str, choice2: str) -> str:
        """判断石头剪刀布胜负"""
        if choice1 == choice2:
            return 'tie'

        winning_combinations = {
            ('rock', 'scissors'): 'p1',
            ('scissors', 'paper'): 'p1',
            ('paper', 'rock'): 'p1',
            ('scissors', 'rock'): 'p2',
            ('paper', 'scissors'): 'p2',
            ('rock', 'paper'): 'p2',
        }

        return winning_combinations.get((choice1, choice2), 'tie')

    @staticmethod
    def _handle_time_wheel(game: Game) -> str:
        """处理时间转盘游戏"""
        import random

        participants = list(GameParticipant.objects.filter(game=game))
        time_options = [15, 30, 45, 60, 90, 120, 180, 240]

        results = []
        for participant in participants:
            selected_time = random.choice(time_options)
            results.append(f"{participant.user.username}: {selected_time}分钟")

            # 简单奖励逻辑
            reward = game.bet_amount + (selected_time // 30)  # 时间越长奖励越多
            participant.user.coins += reward
            participant.user.save()

        game.status = 'completed'
        game.completed_at = timezone.now()
        game.save()

        return f"🎯 时间转盘结果：\n\n" + "\n".join(results)


# 全局实例
telegram_game_sharing = TelegramGameSharing()