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
    async def generate_game_share_message(game: Game) -> tuple[str, dict]:
        """生成游戏分享消息和按钮"""
        from asgiref.sync import sync_to_async

        # 游戏类型映射
        game_type_map = {
            'rock_paper_scissors': {
                'emoji': '✂️',
                'name': '石头剪刀布',
                'buttons': [
                    {'text': '✊ 石头', 'callback_data': f'sharegame_join_{game.id}_rock'},
                    {'text': '✋ 布', 'callback_data': f'sharegame_join_{game.id}_paper'},
                    {'text': '✌️ 剪刀', 'callback_data': f'sharegame_join_{game.id}_scissors'}
                ]
            },
            'time_wheel': {
                'emoji': '🎯',
                'name': '时间转盘',
                'buttons': [
                    {'text': '🎯 参与挑战', 'callback_data': f'sharegame_join_{game.id}_join'}
                ]
            },
            'dice': {
                'emoji': '🎲',
                'name': '掷骰子',
                'buttons': [
                    {'text': '📈 大 (4-6)', 'callback_data': f'sharegame_join_{game.id}_big'},
                    {'text': '📉 小 (1-3)', 'callback_data': f'sharegame_join_{game.id}_small'}
                ]
            }
        }

        game_info = game_type_map.get(game.game_type, {
            'emoji': '🎮',
            'name': game.get_game_type_display(),
            'buttons': [{'text': '🎮 参与游戏', 'callback_data': f'game_{game.id}_join'}]
        })

        # 使用 sync_to_async 获取创建者信息和参与者数量
        creator = await sync_to_async(lambda: game.creator)()
        participant_count = await sync_to_async(game.participants.count)()
        # 使用 Telegram 用户名（如果可用），否则使用应用用户名
        creator_display_name = creator.telegram_username or creator.username

        # 生成分享消息
        message_text = f"""
{game_info['emoji']} **游戏挑战**

🎮 **游戏类型**: {game_info['name']}
👤 **发起者**: {creator_display_name}
💰 **赌注**: {game.bet_amount} 积分
👥 **参与人数**: {participant_count}/{game.max_players}

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
    async def can_user_participate(user: User, game: Game) -> tuple[bool, str]:
        """检查用户是否可以参与游戏"""
        from asgiref.sync import sync_to_async

        # 检查用户是否已绑定Telegram
        if not user.is_telegram_bound():
            return False, "用户未绑定Telegram"

        # 检查游戏状态
        if game.status != 'waiting':
            return False, "游戏已开始或已结束"

        # 检查是否已经参与
        already_participating = await sync_to_async(
            GameParticipant.objects.filter(game=game, user=user).exists
        )()
        if already_participating:
            return False, "已经参与了这个游戏"

        # 检查是否是创建者
        creator = await sync_to_async(lambda: game.creator)()
        if creator == user:
            return False, "不能参与自己创建的游戏"

        # 检查游戏是否已满
        participant_count = await sync_to_async(game.participants.count)()
        if participant_count >= game.max_players:
            return False, "游戏人数已满"

        # 检查用户是否处于带锁状态（关键校验）
        active_lock_task = await sync_to_async(
            LockTask.objects.filter(
                user=user,
                task_type='lock',
                status='active'
            ).first
        )()

        if active_lock_task:
            return False, f"用户正在执行带锁任务《{active_lock_task.title}》，无法参与游戏"

        # 检查积分是否足够
        if user.coins < game.bet_amount:
            return False, f"积分不足，需要{game.bet_amount}积分"

        return True, "可以参与"

    @staticmethod
    async def handle_game_participation(user: User, game_id: str, choice: str = None) -> Dict[str, Any]:
        """处理Telegram中的游戏参与"""
        from asgiref.sync import sync_to_async

        try:
            game = await sync_to_async(Game.objects.get)(id=game_id)
        except Game.DoesNotExist:
            return {
                'success': False,
                'message': "游戏不存在",
                'should_edit_message': False
            }

        # 检查用户是否可以参与
        can_participate, reason = await TelegramGameSharing.can_user_participate(user, game)
        if not can_participate:
            return {
                'success': False,
                'message': f"❌ 无法参与游戏：{reason}",
                'should_edit_message': False
            }

        try:
            # 创建游戏参与记录
            # 对于骰子游戏，存储用户的猜测
            if game.game_type == 'dice':
                action = {'guess': choice}  # choice is 'big' or 'small'
                participant = await sync_to_async(GameParticipant.objects.create)(
                    game=game,
                    user=user,
                    action=action
                )
            else:
                participant = await sync_to_async(GameParticipant.objects.create)(
                    game=game,
                    user=user,
                    choice=choice  # 对于石头剪刀布，记录选择
                )

            # 扣除积分
            user.coins -= game.bet_amount
            await sync_to_async(user.save)()

            # 检查是否达到最大人数，如果是则开始游戏
            participant_count = await sync_to_async(game.participants.count)()

            if participant_count >= game.max_players:
                # 游戏开始逻辑（调用现有的游戏处理逻辑）
                game_result = await sync_to_async(TelegramGameSharing._start_game)(game)

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
        elif game.game_type == 'dice':
            return TelegramGameSharing._handle_dice_game(game)
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
            # 使用 Telegram 用户名（如果可用）
            display_name = participant.user.telegram_username or participant.user.username
            results.append(f"{display_name}: {choice_display}")

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

                # 使用 Telegram 用户名（如果可用）
                winner_display_name = winner_participant.user.telegram_username or winner_participant.user.username
                result_text = f"🎉 {winner_display_name} 获胜！\n获得 {total_reward} 积分"

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
            # 使用 Telegram 用户名（如果可用）
            display_name = participant.user.telegram_username or participant.user.username
            results.append(f"{display_name}: {selected_time}分钟")

            # 简单奖励逻辑
            reward = game.bet_amount + (selected_time // 30)  # 时间越长奖励越多
            participant.user.coins += reward
            participant.user.save()

        game.status = 'completed'
        game.completed_at = timezone.now()
        game.save()

        return f"🎯 时间转盘结果：\n\n" + "\n".join(results)

    @staticmethod
    def _handle_dice_game(game: Game) -> str:
        """处理掷骰子游戏"""
        import random

        participants = list(GameParticipant.objects.filter(game=game))

        if len(participants) < 2:
            return "参与人数不足"

        # 掷骰子 (1-6)
        dice_result = random.randint(1, 6)
        is_big = dice_result >= 4  # 4, 5, 6 为大

        # 结果映射
        result_map = {
            1: '⚀ 一点',
            2: '⚁ 二点',
            3: '⚂ 三点',
            4: '⚃ 四点',
            5: '⚄ 五点',
            6: '⚅ 六点'
        }

        # 判断胜负
        big_winners = []
        small_winners = []

        for participant in participants:
            guess = participant.action.get('guess') if participant.action else None
            if guess == 'big':
                big_winners.append(participant)
            elif guess == 'small':
                small_winners.append(participant)

        # 确定获胜方
        if is_big:
            winners = big_winners
            winning_choice = '大 (4-6)'
            losing_choice = '小 (1-3)'
        else:
            winners = small_winners
            winning_choice = '小 (1-3)'
            losing_choice = '大 (4-6)'

        # 计算奖池
        total_pot = game.bet_amount * len(participants)

        # 构建结果文本
        result_text = f"""🎲 **掷骰子游戏结果**

🎲 骰子点数：**{result_map[dice_result]}** ({'大' if is_big else 'small'})

👥 **玩家选择：**"""

        for participant in participants:
            guess = participant.action.get('guess') if participant.action else None
            guess_display = '📈 大' if guess == 'big' else '📉 小'
            # 使用 Telegram 用户名（如果可用）
            display_name = participant.user.telegram_username or participant.user.username
            result_text += f"\n• {display_name}: {guess_display}"

        result_text += f"\n\n🏆 **获胜方：**{winning_choice}\n"

        # 分配奖励
        if winners:
            reward_per_winner = total_pot // len(winners)
            for winner in winners:
                winner.user.coins += reward_per_winner
                winner.user.save()

            # 使用 Telegram 用户名（如果可用）
            winner_names = [w.user.telegram_username or w.user.username for w in winners]
            result_text += f"\n🎉 **获胜者：**{', '.join(winner_names)}\n"
            result_text += f"💰 每人获得 **{reward_per_winner}** 积分"
        else:
            # 无人获胜，退还积分
            for participant in participants:
                participant.user.coins += game.bet_amount
                participant.user.save()
            result_text += "\n🤝 无人猜中，积分已退还"

        # 更新游戏状态
        game.status = 'completed'
        game.completed_at = timezone.now()
        # 使用 Telegram 用户名（如果可用）
        winner_names_data = [w.user.telegram_username or w.user.username for w in winners] if winners else []
        game.result = {
            'dice_result': dice_result,
            'is_big': is_big,
            'winners': winner_names_data
        }
        game.save()

        return result_text


# 全局实例
telegram_game_sharing = TelegramGameSharing()