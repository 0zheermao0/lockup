"""
Telegram Bot游戏分享功能
复用原有游戏的结算和规则
"""

import json
import logging
import random
from typing import Dict, Any
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from asgiref.sync import sync_to_async

from store.models import Game, GameParticipant, Item, UserInventory, GameSession
from tasks.models import LockTask, TaskTimelineEvent
from users.models import Notification

User = get_user_model()
logger = logging.getLogger(__name__)


class TelegramGameSharing:
    """Telegram游戏分享管理器 - 复用原有游戏逻辑"""

    @staticmethod
    async def generate_game_share_message(game: Game) -> tuple[str, dict]:
        """生成游戏分享消息和按钮"""

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
        """检查用户是否可以参与游戏 - 复用原有逻辑"""

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

        # 检查用户是否处于带锁状态（只对非掷骰子游戏需要）
        # 掷骰子游戏不需要带锁任务，石头剪刀布和时间转盘需要
        if game.game_type != 'dice':
            active_lock_task = await sync_to_async(
                LockTask.objects.filter(
                    user=user,
                    task_type='lock',
                    status='active'
                ).first
            )()
            if not active_lock_task:
                return False, "只有处于带锁任务状态时才能参与此游戏"

        # 检查积分是否足够
        if user.coins < game.bet_amount:
            return False, f"积分不足，需要{game.bet_amount}积分"

        # 对于掷骰子游戏，如果有物品奖励，需要检查参与者背包空间
        if game.game_type == 'dice':
            game_data = await sync_to_async(lambda: game.game_data)()
            if game_data.get('item_reward_id'):
                inventory, _ = await sync_to_async(UserInventory.objects.get_or_create)(user=user)
                if inventory.available_slots < 1:
                    return False, f'背包空间不足，剩余{inventory.available_slots}格，无法参与有奖励物品的游戏'

        return True, "可以参与"

    @staticmethod
    async def handle_game_participation(user: User, game_id: str, choice: str = None) -> Dict[str, Any]:
        """处理Telegram中的游戏参与 - 完全复用原有逻辑"""

        try:
            game = await sync_to_async(Game.objects.get)(id=game_id, status='waiting')
        except Game.DoesNotExist:
            return {
                'success': False,
                'message': "游戏不存在或已开始",
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
            # 扣除积分 - 使用 deduct_coins
            await sync_to_async(user.deduct_coins)(
                amount=game.bet_amount,
                change_type='game_participation',
                description=f'参与{game.get_game_type_display()}游戏消耗',
                metadata={'game_id': str(game.id), 'game_type': game.game_type}
            )

            # 创建参与记录，存储玩家的选择
            if game.game_type == 'dice':
                action = {'guess': choice}
            else:
                action = {'choice': choice}

            participant_record = await sync_to_async(GameParticipant.objects.create)(
                game=game,
                user=user,
                action=action
            )

            # 小游戏活跃度奖励
            await sync_to_async(user.update_activity)(points=1)

            # 检查是否可以开始游戏
            participant_count = await sync_to_async(game.participants.count)()

            if participant_count >= game.max_players:
                # 游戏开始 - 使用try/except确保即使结算失败也不会影响参与
                try:
                    if game.game_type == 'rock_paper_scissors':
                        return await TelegramGameSharing._handle_rock_paper_scissors_game(game, user)
                    elif game.game_type == 'dice':
                        return await TelegramGameSharing._handle_dice_game(game, user)
                    else:
                        return {
                            'success': True,
                            'message': "✅ 成功参与游戏！游戏即将开始...",
                            'should_edit_message': True,
                            'new_message': "🎮 游戏已满员，即将开始！"
                        }
                except Exception as settlement_error:
                    # 结算失败，但用户已成功参与
                    logger.error(f"游戏结算时出错 (游戏ID: {game_id}): {settlement_error}", exc_info=True)
                    return {
                        'success': True,  # 参与成功
                        'message': "✅ 成功参与游戏！但结算时出现错误，请联系管理员",
                        'should_edit_message': True,
                        'new_message': f"🎮 游戏已满员！\n\n您已成功参与，但结算时出现技术问题。\n请联系管理员处理。"
                    }
            else:
                return {
                    'success': True,
                    'message': f"✅ 成功参与游戏！等待其他玩家加入...\n当前人数：{participant_count}/{game.max_players}",
                    'should_edit_message': True,
                    'new_message': f"🎮 等待更多玩家...\n当前人数：{participant_count}/{game.max_players}"
                }

        except Exception as e:
            logger.error(f"处理游戏参与时出错: {e}", exc_info=True)
            return {
                'success': False,
                'message': "参与游戏时出现错误，请稍后重试",
                'should_edit_message': False
            }

    @staticmethod
    async def _handle_rock_paper_scissors_game(game: Game, user: User) -> Dict[str, Any]:
        """处理石头剪刀布游戏 - 完全复用原有逻辑"""
        try:
            participants = await sync_to_async(list)(GameParticipant.objects.filter(game=game))
            valid_choices = ['rock', 'paper', 'scissors']

            # 收集玩家选择并验证
            results = []
            valid_participants = []

            for participant in participants:
                player_choice = participant.action.get('choice')

                # 如果玩家没有提供有效选择，随机分配一个
                if not player_choice or player_choice not in valid_choices:
                    player_choice = random.choice(valid_choices)
                    participant.action = {'choice': player_choice}
                    await sync_to_async(participant.save)()

                valid_participants.append(participant)
                display_name = participant.user.telegram_username or participant.user.username
                results.append({
                    'player': display_name,
                    'choice': player_choice
                })

            # 确定赢家
            if len(valid_participants) == 2:
                p1, p2 = valid_participants
                choice1 = p1.action['choice']
                choice2 = p2.action['choice']

                creator = await sync_to_async(lambda: game.creator)()

                if choice1 == choice2:
                    # 平局，重新开始
                    game.status = 'waiting'
                    await sync_to_async(game.save)()

                    # 平局时返还发起人（游戏创建者）的积分
                    await sync_to_async(creator.add_coins)(
                        amount=game.bet_amount,
                        change_type='game_refund',
                        description='石头剪刀布游戏平局返还',
                        metadata={'game_id': str(game.id), 'result': 'tie'}
                    )

                    # 给双方发送平局通知
                    for participant in valid_participants:
                        opponent = p2 if participant == p1 else p1
                        is_creator = participant.user == creator
                        display_opponent = opponent.user.telegram_username or opponent.user.username
                        message = f'与 {display_opponent} 的石头剪刀布游戏平局，游戏重新开始'
                        if is_creator:
                            message += f'，已返还 {game.bet_amount} 积分'

                        await sync_to_async(Notification.create_notification)(
                            recipient=participant.user,
                            notification_type='game_result',
                            actor=opponent.user,
                            title='石头剪刀布平局',
                            message=message,
                            related_object_type='game',
                            related_object_id=game.id,
                            extra_data={
                                'game_type': 'rock_paper_scissors',
                                'result': 'tie',
                                'your_choice': participant.action['choice'],
                                'opponent_choice': opponent.action['choice'],
                                'opponent_username': opponent.user.username,
                                'opponent_id': opponent.user.id,
                                'bet_amount': game.bet_amount,
                                'coins_refunded': game.bet_amount if is_creator else 0
                            },
                            priority='normal'
                        )

                    return {
                        'success': True,
                        'message': "🤝 平局！游戏重新开始，发起人积分已返还",
                        'should_edit_message': True,
                        'new_message': "🤝 平局！游戏将重新开始。"
                    }

                # 判断胜负
                elif (choice1 == 'rock' and choice2 == 'scissors') or \
                     (choice1 == 'paper' and choice2 == 'rock') or \
                     (choice1 == 'scissors' and choice2 == 'paper'):
                    winner = p1.user
                    loser = p2.user
                else:
                    winner = p2.user
                    loser = p1.user

                # 存储结果
                game.result = {
                    'winner': winner.username,
                    'loser': loser.username,
                    'winner_choice': choice1 if winner == p1.user else choice2,
                    'loser_choice': choice2 if winner == p1.user else choice1,
                    'game_results': results
                }
                game.status = 'completed'
                game.completed_at = timezone.now()
                await sync_to_async(game.save)()

                # 输家加时30分钟
                loser_lock_tasks = await sync_to_async(list)(
                    LockTask.objects.filter(user=loser, status='active')
                )
                for task in loser_lock_tasks:
                    previous_end_time = task.end_time
                    if task.end_time:
                        task.end_time += timedelta(minutes=30)
                    else:
                        task.end_time = timezone.now() + timedelta(minutes=30)
                    await sync_to_async(task.save)()

                    # 创建时间线事件记录游戏加时
                    await sync_to_async(TaskTimelineEvent.objects.create)(
                        task=task,
                        event_type='overtime_added',
                        user=None,
                        time_change_minutes=30,
                        previous_end_time=previous_end_time,
                        new_end_time=task.end_time,
                        description=f'游戏失败加时: {loser.username} 在石头剪刀布游戏中败给 {winner.username}，增加30分钟锁时间',
                        metadata={
                            'game_id': str(game.id),
                            'game_type': 'rock_paper_scissors',
                            'winner': winner.username,
                            'loser': loser.username,
                            'penalty_minutes': 30
                        }
                    )

                # 给获胜者发送胜利通知
                display_loser = loser.telegram_username or loser.username
                await sync_to_async(Notification.create_notification)(
                    recipient=winner,
                    notification_type='game_result',
                    actor=loser,
                    title='石头剪刀布获胜',
                    message=f'恭喜！您在与 {display_loser} 的石头剪刀布游戏中获胜',
                    related_object_type='game',
                    related_object_id=game.id,
                    extra_data={
                        'game_type': 'rock_paper_scissors',
                        'result': 'win',
                        'your_choice': game.result['winner_choice'],
                        'opponent_choice': game.result['loser_choice'],
                        'opponent_username': loser.username,
                        'opponent_id': loser.id,
                        'bet_amount': game.bet_amount,
                        'time_penalty_minutes': 30
                    },
                    priority='normal'
                )

                # 给失败者发送失败通知
                display_winner = winner.telegram_username or winner.username
                await sync_to_async(Notification.create_notification)(
                    recipient=loser,
                    notification_type='game_result',
                    actor=winner,
                    title='石头剪刀布失败',
                    message=f'很遗憾，您在与 {display_winner} 的石头剪刀布游戏中失败，锁时间增加30分钟',
                    related_object_type='game',
                    related_object_id=game.id,
                    extra_data={
                        'game_type': 'rock_paper_scissors',
                        'result': 'lose',
                        'your_choice': game.result['loser_choice'],
                        'opponent_choice': game.result['winner_choice'],
                        'opponent_username': winner.username,
                        'opponent_id': winner.id,
                        'bet_amount': game.bet_amount,
                        'time_penalty_minutes': 30
                    },
                    priority='normal'
                )

                display_winner = winner.telegram_username or winner.username
                display_loser = loser.telegram_username or loser.username

                return {
                    'success': True,
                    'message': f"🎉 {display_winner} 获胜！{display_loser} 增加30分钟锁时间",
                    'should_edit_message': True,
                    'new_message': f"🎮 游戏结束！\n\n{display_winner} 获胜！\n{display_loser} 锁时间增加30分钟"
                }

        except Exception as e:
            logger.error(f"石头剪刀布游戏处理出错: {e}", exc_info=True)
            return {
                'success': False,
                'message': "游戏结算时出现错误",
                'should_edit_message': False
            }

    @staticmethod
    async def _handle_dice_game(game: Game, user: User) -> Dict[str, Any]:
        """处理掷骰子游戏 - 完全复用原有逻辑"""
        try:
            # 获取参与者和其猜测
            participant = await sync_to_async(GameParticipant.objects.get)(game=game, user=user)
            participant_guess = participant.action.get('guess', 'big')

            # 获取预先掷好的骰子结果
            game_data = await sync_to_async(lambda: game.game_data)()
            dice_result = game_data.get('dice_result', random.randint(1, 6))

            # 判断大小 (4,5,6为大，1,2,3为小)
            is_big = dice_result >= 4
            is_correct = (participant_guess == 'big' and is_big) or (participant_guess == 'small' and not is_big)

            # 创建者总是获得参与费用
            creator = await sync_to_async(lambda: game.creator)()
            creator.coins += game.bet_amount
            await sync_to_async(creator.save)()

            # 处理物品奖励转移
            item_transferred = False
            item_reward_details = None

            if is_correct and game_data.get('item_reward_id'):
                try:
                    # 验证物品仍然存在且在游戏中
                    reward_item = await sync_to_async(Item.objects.get)(
                        id=game_data['item_reward_id'],
                        owner=creator,
                        status='in_game'
                    )

                    # 获取参与者背包
                    participant_inventory, _ = await sync_to_async(UserInventory.objects.get_or_create)(user=user)

                    # 转移物品给获胜者
                    reward_item.owner = user
                    reward_item.inventory = participant_inventory
                    reward_item.status = 'available'
                    await sync_to_async(reward_item.save)()
                    item_transferred = True
                    item_reward_details = game_data.get('item_reward_details')

                    # 记录物品转移到游戏会话中
                    await sync_to_async(GameSession.objects.create)(
                        user=user,
                        game_type='dice',
                        bet_amount=game.bet_amount,
                        result_data={
                            'dice_result': dice_result,
                            'guess': participant_guess,
                            'is_correct': is_correct,
                            'item_received': item_reward_details,
                            'creator': creator.username
                        }
                    )

                except Item.DoesNotExist:
                    pass

            # 如果有奖励物品但参与者没猜中，归还物品给创建者
            if not is_correct and game_data.get('item_reward_id'):
                try:
                    reward_item = await sync_to_async(Item.objects.get)(
                        id=game_data['item_reward_id'],
                        owner=creator,
                        status='in_game'
                    )
                    # 归还给创建者
                    creator_inventory, _ = await sync_to_async(UserInventory.objects.get_or_create)(user=creator)
                    reward_item.inventory = creator_inventory
                    reward_item.status = 'available'
                    await sync_to_async(reward_item.save)()
                except Item.DoesNotExist:
                    pass

            # 记录创建者的游戏会话
            await sync_to_async(GameSession.objects.create)(
                user=creator,
                game_type='dice',
                bet_amount=game.bet_amount,
                result_data={
                    'dice_result': dice_result,
                    'participant_guess': participant_guess,
                    'participant_won': is_correct,
                    'coins_earned': game.bet_amount,
                    'item_given': item_transferred,
                    'participant': user.username
                }
            )

            # 完成游戏
            game.status = 'completed'
            game.completed_at = timezone.now()
            game.result = {
                'dice_result': dice_result,
                'participant_guess': participant_guess,
                'is_correct': is_correct,
                'creator': creator.username,
                'participant': user.username,
                'item_transferred': item_transferred,
                'item_details': item_reward_details
            }
            await sync_to_async(game.save)()

            # 发送通知给参与者
            display_creator = creator.telegram_username or creator.username
            if is_correct:
                title = '掷骰子获胜'
                message = f'恭喜！您猜{participant_guess}，骰子结果是{dice_result}，猜中了！'
                if item_transferred:
                    message += f'获得奖励物品：{item_reward_details["display_name"]}'
            else:
                title = '掷骰子失败'
                message = f'很遗憾，您猜{participant_guess}，骰子结果是{dice_result}，没有猜中。'

            await sync_to_async(Notification.create_notification)(
                recipient=user,
                notification_type='game_result',
                actor=creator,
                title=title,
                message=message,
                related_object_type='game',
                related_object_id=game.id,
                extra_data={
                    'game_type': 'dice',
                    'dice_result': dice_result,
                    'guess': participant_guess,
                    'is_correct': is_correct,
                    'item_received': item_reward_details if item_transferred else None,
                    'creator_username': creator.username,
                    'creator_id': creator.id,
                    'bet_amount': game.bet_amount
                },
                priority='normal'
            )

            # 发送通知给创建者
            display_user = user.telegram_username or user.username
            creator_message = f'{display_user} 参与了您的掷骰子游戏，猜{participant_guess}，'
            creator_message += f'骰子结果{dice_result}，{"猜中了" if is_correct else "没猜中"}，'
            creator_message += f'您获得了 {game.bet_amount} 积分'
            if item_transferred:
                creator_message += f'，奖励物品已转移给对方'

            await sync_to_async(Notification.create_notification)(
                recipient=creator,
                notification_type='game_result',
                actor=user,
                title='掷骰子游戏完成',
                message=creator_message,
                related_object_type='game',
                related_object_id=game.id,
                extra_data={
                    'game_type': 'dice',
                    'dice_result': dice_result,
                    'participant_guess': participant_guess,
                    'participant_won': is_correct,
                    'coins_earned': game.bet_amount,
                    'item_given': item_transferred,
                    'participant_username': user.username,
                    'participant_id': user.id,
                    'bet_amount': game.bet_amount
                },
                priority='normal'
            )

            # 构建返回消息
            result_map = {1: '⚀ 一点', 2: '⚁ 二点', 3: '⚂ 三点', 4: '⚃ 四点', 5: '⚄ 五点', 6: '⚅ 六点'}
            if is_correct:
                message = f"🎉 恭喜！您猜{participant_guess}，骰子结果是{dice_result} ({result_map[dice_result]})，猜中了！"
                if item_transferred:
                    message += f"\n🎁 获得奖励物品：{item_reward_details['display_name']}"
            else:
                message = f"😔 很遗憾，您猜{participant_guess}，骰子结果是{dice_result} ({result_map[dice_result]})，没有猜中。"

            return {
                'success': True,
                'message': message,
                'should_edit_message': True,
                'new_message': f"🎲 掷骰子结果：{dice_result}\n\n{message}\n\n{display_creator} 获得了 {game.bet_amount} 积分"
            }

        except Exception as e:
            logger.error(f"掷骰子游戏处理出错: {e}", exc_info=True)
            return {
                'success': False,
                'message': "游戏结算时出现错误",
                'should_edit_message': False
            }


# 全局实例
telegram_game_sharing = TelegramGameSharing()
