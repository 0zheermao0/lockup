<template>
  <div class="notification-bell" @click="toggleDropdown">
    <!-- 通知铃铛图标 -->
    <div class="bell-icon" :class="{ 'has-notifications': unreadCount > 0 }">
      🔔
      <!-- 未读数量徽章 -->
      <div v-if="unreadCount > 0" class="notification-badge">
        {{ formatBadgeCount(unreadCount) }}
      </div>
    </div>

    <!-- 移动端遮罩层 -->
    <Transition name="fade">
      <div v-if="showDropdown" class="mobile-overlay" @click="showDropdown = false"></div>
    </Transition>

    <!-- 通知下拉列表 -->
    <Transition name="dropdown">
      <div v-if="showDropdown" class="notification-dropdown" @click.stop>
      <div class="dropdown-header">
        <h3>通知</h3>
        <div class="header-actions">
          <button
            v-if="hasUnreadNotifications"
            @click="markAllAsRead"
            class="mark-all-btn"
          >
            全部已读
          </button>
        </div>
      </div>

      <!-- 通知列表 -->
      <div class="notification-list" ref="notificationListRef">
        <div v-if="loading && notifications.length === 0" class="loading">
          <div class="spinner">⏳</div>
          <span>加载中...</span>
        </div>

        <div v-else-if="!hasNotifications" class="empty-state">
          <div class="empty-icon">📭</div>
          <p>暂无通知</p>
        </div>

        <div v-else>
          <div
            v-for="notification in notifications"
            :key="notification.id"
            :class="['notification-item', { 'is-read': notification.is_read }]"
            @click="handleNotificationClick(notification)"
          >
            <!-- 通知图标和优先级指示器 -->
            <div class="notification-icon">
              <div class="priority-indicator" :class="notification.priority"></div>
              <span class="type-icon">{{ getNotificationIcon(notification.notification_type) }}</span>
            </div>

            <!-- 通知内容 -->
            <div class="notification-content">
              <div class="notification-title">{{ notification.title }}</div>
              <div class="notification-message">
                <!-- 特殊处理游戏结果通知 -->
                <template v-if="notification.notification_type === 'game_result'">
                  <div class="game-result-content">
                    <p>{{ notification.message }}</p>

                    <!-- 游戏详情 -->
                    <div v-if="notification.extra_data" class="game-details">
                      <div v-if="notification.extra_data.your_choice && notification.extra_data.opponent_choice" class="game-choices">
                        <span class="choice-item">你的出拳: {{ getChoiceEmoji(notification.extra_data.your_choice) }}</span>
                        <span class="vs-text">VS</span>
                        <span class="choice-item">对手出拳: {{ getChoiceEmoji(notification.extra_data.opponent_choice) }}</span>
                      </div>

                      <!-- 可点击的对手用户名 -->
                      <div v-if="notification.extra_data.opponent_username" class="opponent-info">
                        对手:
                        <span
                          class="opponent-username clickable-username"
                          @click.stop="openOpponentProfile(notification.extra_data.opponent_id, notification.extra_data.opponent_username)"
                        >
                          {{ notification.extra_data.opponent_username }}
                        </span>
                      </div>

                      <!-- 积分变化信息 -->
                      <div v-if="notification.extra_data.bet_amount" class="bet-info">
                        下注积分: {{ notification.extra_data.bet_amount }}
                      </div>
                      <div v-if="notification.extra_data.coins_change" class="coins-change" :class="{ positive: notification.extra_data.coins_change > 0, negative: notification.extra_data.coins_change < 0 }">
                        积分变化: {{ notification.extra_data.coins_change > 0 ? '+' : '' }}{{ notification.extra_data.coins_change }}
                      </div>
                      <div v-if="notification.extra_data.time_penalty_minutes" class="time-penalty">
                        时间惩罚: +{{ notification.extra_data.time_penalty_minutes }} 分钟
                      </div>
                    </div>
                  </div>
                </template>

                <!-- 特殊处理任务审核通过通知 -->
                <template v-else-if="notification.notification_type === 'task_board_approved'">
                  <div class="task-approved-content">
                    <p>{{ notification.message }}</p>

                    <!-- 任务详情 -->
                    <div v-if="notification.extra_data" class="task-approval-details">
                      <div v-if="notification.extra_data.task_title" class="task-info">
                        <div class="task-title">{{ notification.extra_data.task_title }}</div>
                      </div>

                      <!-- 奖励信息 -->
                      <div v-if="notification.extra_data.reward_amount" class="reward-info">
                        <div class="reward-amount">
                          💰 奖励: {{ notification.extra_data.reward_amount }} 积分
                        </div>

                        <!-- 区分单人任务和多人任务的到账情况 -->
                        <div class="payment-status">
                          <template v-if="notification.extra_data.is_multi_participant && !notification.extra_data.task_completed">
                            <div class="pending-payment">
                              ⏳ 等待任务结束后统一发放奖励
                            </div>
                            <div v-if="notification.extra_data.other_participants_count" class="participants-info">
                              还有 {{ notification.extra_data.other_participants_count }} 人参与中
                            </div>
                          </template>
                          <template v-else-if="notification.extra_data.is_multi_participant && notification.extra_data.task_completed">
                            <div class="completed-payment">
                              ✅ 任务已结束，奖励已发放
                            </div>
                          </template>
                          <template v-else>
                            <div class="immediate-payment">
                              ✅ 奖励已立即到账
                            </div>
                          </template>
                        </div>
                      </div>

                      <!-- 审核时间 -->
                      <div v-if="notification.extra_data.approved_at" class="approval-time">
                        审核时间: {{ new Date(notification.extra_data.approved_at).toLocaleString('zh-CN') }}
                      </div>
                    </div>
                  </div>
                </template>

                <!-- 特殊处理物品分享通知 -->
                <template v-else-if="notification.notification_type === 'item_shared'">
                  <div class="item-shared-content">
                    <!-- 基础消息，但将用户名替换为可点击的链接 -->
                    <p v-if="notification.extra_data && notification.extra_data.claimer_username">
                      <span
                        class="claimer-username clickable-username"
                        @click.prevent.stop="openClaimerProfile(notification.extra_data.claimer_id, notification.extra_data.claimer_username)"
                      >
                        {{ notification.extra_data.claimer_username }}
                      </span>
                      领取了您分享的
                      <span class="item-name">{{ notification.extra_data.item_display_name }}</span>
                    </p>
                    <p v-else>{{ notification.message }}</p>

                    <!-- 物品详情 -->
                    <div v-if="notification.extra_data" class="item-details">
                      <div v-if="notification.extra_data.item_display_name" class="item-info">
                        物品: {{ notification.extra_data.item_display_name }}
                      </div>
                      <div v-if="notification.extra_data.claimed_at" class="claimed-time">
                        领取时间: {{ new Date(notification.extra_data.claimed_at).toLocaleString('zh-CN') }}
                      </div>
                    </div>
                  </div>
                </template>

                <!-- 特殊处理严格模式自动冻结通知 -->
                <template v-else-if="notification.notification_type === 'task_frozen_auto_strict'">
                  <div class="auto-freeze-content">
                    <p class="freeze-message">{{ notification.message }}</p>

                    <!-- 任务详情 -->
                    <div v-if="notification.extra_data" class="freeze-details">
                      <div class="task-info">
                        <div class="task-title">
                          任务: {{ notification.extra_data.task_title || '未知任务' }}
                        </div>
                        <div class="freeze-reason">
                          原因: 24小时内未发布打卡动态
                        </div>
                        <div v-if="notification.extra_data.frozen_at" class="freeze-time">
                          冻结时间: {{ new Date(notification.extra_data.frozen_at).toLocaleString('zh-CN') }}
                        </div>
                      </div>

                      <!-- 解冻提示 -->
                      <div class="unfreeze-hint">
                        💡 提示：需要钥匙持有者解冻任务才能继续
                      </div>
                    </div>
                  </div>
                </template>

                <!-- 普通通知内容 -->
                <template v-else>
                  {{ notification.message }}
                </template>
              </div>

              <!-- 通知元信息 -->
              <div class="notification-meta">
                <span class="time">{{ notification.time_ago }}</span>
                <span
                  v-if="notification.actor"
                  class="actor clickable-actor"
                  :class="getLevelCSSClass(notification.actor.level || 1)"
                  :style="{ color: getLevelUsernameColor(notification.actor.level || 1) }"
                  @click.stop="openActorProfile(notification.actor.id, notification.actor.username, $event)"
                  :title="`查看 ${notification.actor.username} 的个人资料 (${getLevelDisplayName(notification.actor.level || 1)}) - Ctrl+点击发送私信`"
                >
                  {{ notification.actor.username }}
                </span>
                <span v-if="getNotificationPriorityClass(notification.priority)"
                      :class="['priority-badge', getNotificationPriorityClass(notification.priority)]">
                  {{ getPriorityText(notification.priority) }}
                </span>
              </div>
            </div>

            <!-- 操作按钮 -->
            <div class="notification-actions">
              <button
                v-if="!notification.is_read"
                @click.stop="markAsRead(notification.id)"
                class="action-btn mark-read-btn"
                title="标记为已读"
              >
                ✅
              </button>
              <button
                @click.stop="deleteNotification(notification.id)"
                class="action-btn delete-btn"
                title="删除通知"
              >
                ❌
              </button>
            </div>
          </div>

          <!-- 懒加载控制区域 -->
          <div v-if="hasMore" class="load-more-section">
            <button
              v-if="!isLoadingMore"
              @click="loadMoreNotifications"
              class="load-more-btn"
            >
              加载更多通知...
            </button>
            <div v-else class="loading-more">
              <div class="spinner">⏳</div>
              <span>加载中...</span>
            </div>
          </div>

          <div v-else-if="notifications.length > 0" class="no-more">
            已显示所有通知
          </div>
        </div>
      </div>

    </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useNotificationStore } from '../stores/notifications'
import { useMessagingStore } from '../stores/messaging'
import { getLevelCSSClass, getLevelDisplayName, getLevelUsernameColor } from '../lib/level-colors'
import type { NotificationItem } from '../types/index'

const router = useRouter()
const notificationStore = useNotificationStore()
const messagingStore = useMessagingStore()

// 响应式数据
const showDropdown = ref(false)
const notificationListRef = ref<HTMLElement>()

// 使用store的状态和计算属性
const notifications = computed(() => notificationStore.notifications)
const hasMore = computed(() => notificationStore.hasMore)
const isLoadingMore = computed(() => notificationStore.isLoadingMore)
const loading = computed(() => notificationStore.isLoading)

const unreadCount = computed(() => {
  // 使用store中的unreadCount，确保即使没有加载通知列表也能显示正确的未读数量
  return notificationStore.unreadCount
})

const hasNotifications = computed(() => notifications.value.length > 0)
const hasUnreadNotifications = computed(() => unreadCount.value > 0)

// 通知图标映射
const getNotificationIcon = (type: string) => {
  const iconMap: Record<string, string> = {
    post_liked: '❤️',
    post_commented: '💬',
    comment_liked: '👍',
    comment_replied: '↩️',
    task_overtime_added: '⏰',
    task_board_taken: '📋',
    task_board_submitted: '📤',
    task_board_approved: '✅',
    task_board_rejected: '❌',
    coins_earned_hourly: '💰',
    coins_earned_daily_login: '🎁',
    coins_earned_daily_board_post: '📋💰',
    coins_earned_task_reward: '🏆',
    coins_spent_task_creation: '💸',
    treasure_found: '💎',
    photo_viewed: '📷',
    drift_bottle_found: '🍾',
    item_received: '🎁',
    item_shared: '🔗',
    friend_request: '👋',
    friend_accepted: '🤝',
    private_message: '💬',
    level_upgraded: '⬆️',
    system_announcement: '📢',
    game_result: '🎮',
    task_frozen_auto_strict: '🧊'
  }
  return iconMap[type] || '📢'
}

const getPriorityText = (priority: string) => {
  const priorityMap: Record<string, string> = {
    low: '低',
    normal: '普通',
    high: '高',
    urgent: '紧急'
  }
  return priorityMap[priority] || priority
}

const getNotificationPriorityClass = (priority: string) => {
  return priority !== 'normal' ? priority : ''
}

const formatBadgeCount = (count: number) => {
  if (count > 99) return '99+'
  return count.toString()
}

// 方法
const toggleDropdown = async () => {
  showDropdown.value = !showDropdown.value

  if (showDropdown.value) {
    // 每次打开铃铛时刷新通知统计和列表
    try {
      await notificationStore.fetchNotificationStats()
      await loadNotifications()
    } catch (error) {
      console.error('刷新通知失败:', error)
    }
  }
}

const loadNotifications = async () => {
  try {
    // 重置并加载第一页通知（包括已读和未读）
    await notificationStore.fetchNotificationsPage({
      reset: true
    })
  } catch (error) {
    console.error('加载通知失败:', error)
    // 如果加载失败，可能是认证问题或网络问题
    // 可以在这里添加错误处理逻辑
  }
}

const loadMoreNotifications = async () => {
  try {
    await notificationStore.loadMoreNotifications()
  } catch (error) {
    console.error('加载更多通知失败:', error)
  }
}


const handleNotificationClick = async (notification: NotificationItem) => {
  // 如果通知未读，标记为已读
  if (!notification.is_read) {
    await markAsRead(notification.id)
  }

  // 处理私信通知 - 打开聊天弹窗
  if (notification.notification_type === 'private_message') {
    const senderId = notification.extra_data?.sender_id || notification.actor?.id
    const senderUsername = notification.extra_data?.sender_username || notification.actor?.username
    if (senderId) {
      messagingStore.openChatModal(senderId, senderUsername)
      showDropdown.value = false
      return
    }
  }

  // 如果有目标链接，跳转
  if (notification.target_url) {
    router.push(notification.target_url)
    showDropdown.value = false
  }
}

const openOpponentProfile = (opponentId: string, opponentUsername: string) => {
  // 打开对手的个人资料页面
  router.push({ name: 'profile', params: { id: opponentId } })
  showDropdown.value = false
}

const openClaimerProfile = (claimerId: string, claimerUsername: string) => {
  console.log('openClaimerProfile called:', claimerId, claimerUsername)
  // 打开物品领取者的个人资料页面
  router.push({ name: 'profile', params: { id: claimerId } })
  showDropdown.value = false
}

const openActorProfile = (actorId: number, actorUsername: string, event?: MouseEvent) => {
  console.log('openActorProfile called:', actorId, actorUsername)
  // Ctrl/Cmd + 点击打开私信弹窗
  if (event && (event.ctrlKey || event.metaKey)) {
    messagingStore.openChatModal(actorId, actorUsername)
    showDropdown.value = false
    return
  }
  // 打开通知触发者的个人资料页面
  router.push({ name: 'profile', params: { id: actorId.toString() } })
  showDropdown.value = false
}

const getChoiceEmoji = (choice: string) => {
  const choiceMap: Record<string, string> = {
    rock: '🪨 石头',
    paper: '📄 布',
    scissors: '✂️ 剪刀'
  }
  return choiceMap[choice] || choice
}

const markAsRead = async (notificationId: string) => {
  try {
    await notificationStore.markAsRead(notificationId)
    // Store中的markAsRead已经更新了本地状态，无需手动更新
  } catch (error) {
    console.error('标记已读失败:', error)
  }
}

const markAllAsRead = async () => {
  try {
    await notificationStore.markAllAsRead()
    // Store中的markAllAsRead已经更新了本地状态，无需手动更新
  } catch (error) {
    console.error('标记全部已读失败:', error)
  }
}

const deleteNotification = async (notificationId: string) => {
  try {
    await notificationStore.deleteNotification(notificationId)
    // Store中的deleteNotification已经更新了本地状态，无需手动更新
  } catch (error) {
    console.error('删除通知失败:', error)
  }
}


// 点击外部关闭下拉
const handleClickOutside = (event: MouseEvent) => {
  if (!event.target || !(event.target as Element).closest('.notification-bell')) {
    showDropdown.value = false
  }
}

// 生命周期
onMounted(() => {
  document.addEventListener('click', handleClickOutside)

  // 定期刷新未读数量
  const interval = setInterval(async () => {
    if (!showDropdown.value) {
      try {
        await notificationStore.fetchNotificationStats()
        // 如果下拉框未打开，只刷新统计信息，不刷新通知列表
        // 通知列表会在用户打开下拉框时重新加载
      } catch (error) {
        console.error('刷新通知失败:', error)
      }
    }
  }, 30000) // 30秒刷新一次
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
/* Dropdown animation */
.dropdown-enter-active {
  transition: all var(--duration-fast, 200ms) var(--ease-bounce, cubic-bezier(0.175, 0.885, 0.32, 1.275));
  transform-origin: top right;
}

.dropdown-leave-active {
  transition: all var(--duration-fast, 200ms) var(--ease-accelerate, cubic-bezier(0.4, 0.0, 1, 1));
  transform-origin: top right;
}

.dropdown-enter-from {
  opacity: 0;
  transform: translateY(-10px) scale(0.95);
}

.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-10px) scale(0.95);
}

/* Fade animation for overlay */
.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--duration-fast, 200ms) ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.notification-bell {
  position: relative;
  display: inline-block;
}

.bell-icon {
  position: relative;
  cursor: pointer;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, #ffd93d, #ffb347);
  border: 2px solid #000;
  box-shadow: 2px 2px 0 rgba(0, 0, 0, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
  transition: all 0.2s ease;
}

.bell-icon:hover {
  transform: translateY(-1px);
  box-shadow: 3px 3px 0 rgba(0, 0, 0, 0.3);
  background: linear-gradient(135deg, #ff6b6b, #ee5a24);
}

.bell-icon.has-notifications {
  animation: bell-ring 2s infinite;
  background: linear-gradient(135deg, #ff6b6b, #ee5a24);
}

.notification-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  min-width: 16px;
  height: 16px;
  background: linear-gradient(135deg, #dc3545, #c82333);
  color: white;
  font-size: 0.6rem;
  font-weight: 700;
  border-radius: 50%;
  border: 2px solid #000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 2px;
  box-shadow: 1px 1px 0 rgba(0, 0, 0, 0.2);
  text-transform: uppercase;
  letter-spacing: 0.2px;
}

.mobile-overlay {
  display: none;
}

.notification-dropdown {
  position: absolute;
  top: 100%;
  right: 0;
  min-width: 420px;
  max-width: 480px;
  max-height: 480px;
  background: white;
  border: 2px solid #000;
  border-radius: 8px;
  box-shadow: 4px 4px 0 #000;
  z-index: 1000;
  overflow: hidden;
  margin-top: 0.5rem;
}

.dropdown-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: linear-gradient(135deg, #f8f9fa, #e9ecef);
  border-bottom: 2px solid #000;
}

.dropdown-header h3 {
  margin: 0;
  font-size: 1.125rem;
  font-weight: bold;
}

.header-actions {
  display: flex;
  gap: 0.5rem;
}

.mark-all-btn, .clear-btn {
  padding: 0.375rem 0.75rem;
  font-size: 0.75rem;
  font-weight: 500;
  border: 1px solid #000;
  border-radius: 4px;
  background: white;
  cursor: pointer;
  transition: all 0.2s ease;
}

.mark-all-btn:hover, .clear-btn:hover {
  transform: translateY(-1px);
  box-shadow: 2px 2px 0 #000;
}

.notification-list {
  max-height: 380px;
  overflow-y: auto;
}

.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 2rem;
  color: #6c757d;
}

.spinner {
  animation: spin 1s linear infinite;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  color: #6c757d;
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: 0.5rem;
}

.notification-item {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 1rem;
  border-bottom: 1px solid #e9ecef;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
}

.notification-item:hover {
  background: #f8f9fa;
}

.notification-item.is-read {
  background: #fafafa;
  opacity: 0.7;
}

.notification-item:not(.is-read):before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: linear-gradient(135deg, #007bff, #0056b3);
}

.notification-icon {
  position: relative;
  flex-shrink: 0;
  font-size: 1.25rem;
}

.priority-indicator {
  position: absolute;
  top: -2px;
  right: -2px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  border: 1px solid #000;
}

.priority-indicator.low {
  background: #28a745;
}

.priority-indicator.normal {
  background: #6c757d;
}

.priority-indicator.high {
  background: #ffc107;
}

.priority-indicator.urgent {
  background: #dc3545;
  animation: pulse-danger 1s infinite;
}

.notification-content {
  flex: 1;
  min-width: 0;
}

.notification-title {
  font-weight: 600;
  margin-bottom: 0.25rem;
  color: #212529;
}

.notification-message {
  font-size: 0.875rem;
  color: #6c757d;
  margin-bottom: 0.5rem;
  line-height: 1.4;
}

.notification-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.75rem;
  color: #adb5bd;
}

.time {
  font-family: 'Courier New', monospace;
}

.actor {
  color: #007bff;
  font-weight: 500;
}

.clickable-actor {
  cursor: pointer;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  margin-left: 0.25rem;
  transition: all 0.2s ease;
  display: inline-block;
  position: relative;
  z-index: 10;
  pointer-events: auto;
  border: 2px solid transparent;
  text-decoration: underline;
}

.clickable-actor:hover {
  color: white;
  transform: translate(-1px, -1px);
  box-shadow: 2px 2px 0 #000;
  text-decoration: none;
  border-color: #000;
}

/* Level-specific hover effects for actor */
.clickable-actor.level-1:hover {
  background-color: #6c757d !important;
  color: white !important;
}

.clickable-actor.level-2:hover {
  background-color: #17a2b8 !important;
  color: white !important;
}

.clickable-actor.level-3:hover {
  background-color: #ffc107 !important;
  color: white !important;
}

.clickable-actor.level-4:hover {
  background-color: #fd7e14 !important;
  color: white !important;
}

.priority-badge {
  padding: 0.125rem 0.375rem;
  border-radius: 12px;
  font-size: 0.625rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.priority-badge.low {
  background: rgba(40, 167, 69, 0.1);
  color: #28a745;
}

.priority-badge.high {
  background: rgba(255, 193, 7, 0.1);
  color: #856404;
}

.priority-badge.urgent {
  background: rgba(220, 53, 69, 0.1);
  color: #721c24;
}

.notification-actions {
  display: flex;
  gap: 0.25rem;
  flex-shrink: 0;
}

.action-btn {
  width: 24px;
  height: 24px;
  border: 1px solid #000;
  border-radius: 4px;
  background: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  transition: all 0.2s ease;
}

.action-btn:hover {
  transform: translateY(-1px);
  box-shadow: 1px 1px 0 #000;
}

.mark-read-btn:hover {
  background: #28a745;
  color: white;
}

.delete-btn:hover {
  background: #dc3545;
  color: white;
}


@keyframes bell-ring {
  0%, 10%, 20%, 30%, 40%, 50%, 60%, 70%, 80%, 90%, 100% {
    transform: rotate(0deg);
  }
  5%, 15%, 25%, 35%, 45%, 55%, 65%, 75%, 85%, 95% {
    transform: rotate(10deg);
  }
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

@keyframes pulse-danger {
  0% {
    opacity: 1;
  }
  50% {
    opacity: 0.6;
  }
  100% {
    opacity: 1;
  }
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Game result notification styles */
.game-result-content {
  margin-top: 0.5rem;
}

.game-details {
  margin-top: 0.75rem;
  padding: 0.75rem;
  background: linear-gradient(135deg, #f8f9fa, #e9ecef);
  border: 2px solid #000;
  border-radius: 6px;
  font-size: 0.8rem;
}

.game-choices {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.5rem;
  flex-wrap: wrap;
}

.choice-item {
  background: white;
  padding: 0.375rem 0.75rem;
  border: 2px solid #000;
  border-radius: 4px;
  font-weight: 600;
  white-space: nowrap;
}

.vs-text {
  font-weight: 900;
  color: #dc3545;
  font-size: 0.9rem;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.opponent-info {
  margin: 0.5rem 0;
  font-weight: 500;
}

.clickable-username {
  color: #007bff;
  font-weight: 700;
  text-decoration: underline;
  cursor: pointer;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  margin-left: 0.25rem;
  transition: all 0.2s ease;
  display: inline-block;
  position: relative;
  z-index: 10;
  pointer-events: auto;
  border: 2px solid transparent;
}

.clickable-username:hover {
  color: white;
  transform: translate(-1px, -1px);
  box-shadow: 2px 2px 0 #000;
  text-decoration: none;
  border-color: #000;
}

/* Level-specific hover effects for username */
.clickable-username.level-1:hover {
  background-color: #6c757d !important;
  color: white !important;
}

.clickable-username.level-2:hover {
  background-color: #17a2b8 !important;
  color: white !important;
}

.clickable-username.level-3:hover {
  background-color: #ffc107 !important;
  color: white !important;
}

.clickable-username.level-4:hover {
  background-color: #fd7e14 !important;
  color: white !important;
}

/* Task approval notification styles */
.task-approved-content {
  margin-top: 0.5rem;
}

.task-approval-details {
  margin-top: 0.75rem;
  padding: 0.75rem;
  background: linear-gradient(135deg, #f8f9fa, #e9ecef);
  border: 2px solid #000;
  border-radius: 6px;
  font-size: 0.8rem;
}

.task-title {
  font-weight: 700;
  color: #333;
  margin-bottom: 0.5rem;
  padding: 0.25rem 0.5rem;
  background: white;
  border: 2px solid #000;
  border-radius: 4px;
}

.reward-info {
  margin: 0.5rem 0;
}

.reward-amount {
  font-weight: 700;
  color: #ffc107;
  margin-bottom: 0.5rem;
  padding: 0.375rem 0.75rem;
  background: rgba(255, 193, 7, 0.1);
  border: 2px solid #ffc107;
  border-radius: 4px;
  text-align: center;
}

.payment-status {
  margin-top: 0.5rem;
}

.pending-payment {
  background: rgba(255, 193, 7, 0.1);
  color: #856404;
  padding: 0.375rem 0.75rem;
  border: 2px solid #ffc107;
  border-radius: 4px;
  font-weight: 600;
  text-align: center;
  margin-bottom: 0.25rem;
}

.participants-info {
  background: rgba(23, 162, 184, 0.1);
  color: #0c5460;
  padding: 0.25rem 0.5rem;
  border: 1px solid #17a2b8;
  border-radius: 3px;
  font-size: 0.75rem;
  text-align: center;
  font-weight: 500;
}

.completed-payment,
.immediate-payment {
  background: rgba(40, 167, 69, 0.1);
  color: #155724;
  padding: 0.375rem 0.75rem;
  border: 2px solid #28a745;
  border-radius: 4px;
  font-weight: 600;
  text-align: center;
}

.approval-time {
  margin-top: 0.5rem;
  padding: 0.25rem 0.5rem;
  background: rgba(108, 117, 125, 0.1);
  border-left: 3px solid #6c757d;
  font-size: 0.75rem;
  color: #6c757d;
  font-weight: 500;
}

/* Item shared notification styles */
.item-shared-content {
  padding: 0.5rem 0;
  position: relative;
}

.item-shared-content p {
  position: relative;
  z-index: 1;
}

.item-shared-content .item-name {
  font-weight: 700;
  color: #17a2b8;
  padding: 0.125rem 0.25rem;
  border-radius: 3px;
  background-color: rgba(23, 162, 184, 0.1);
}

.item-shared-content .item-details {
  margin-top: 0.5rem;
  padding: 0.5rem;
  background-color: #f8f9fa;
  border-radius: 4px;
  border-left: 3px solid #17a2b8;
}

.item-shared-content .item-info,
.item-shared-content .claimed-time {
  margin: 0.25rem 0;
  font-size: 0.875rem;
  color: #666;
  font-weight: 500;
}

.bet-info,
.coins-change,
.time-penalty {
  margin: 0.25rem 0;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-weight: 600;
  font-size: 0.75rem;
}

.bet-info {
  background: rgba(255, 193, 7, 0.1);
  color: #856404;
  border: 1px solid #ffc107;
}

.coins-change {
  border: 1px solid #28a745;
}

.coins-change.positive {
  background: rgba(40, 167, 69, 0.1);
  color: #28a745;
}

.coins-change.negative {
  background: rgba(220, 53, 69, 0.1);
  color: #dc3545;
  border-color: #dc3545;
}

.time-penalty {
  background: rgba(220, 53, 69, 0.1);
  color: #dc3545;
  border: 1px solid #dc3545;
}

/* Auto-freeze notification styles */
.auto-freeze-content {
  padding: 0.5rem 0;
  position: relative;
}

.freeze-message {
  font-weight: 600;
  color: #dc3545;
  margin-bottom: 0.5rem;
  position: relative;
  z-index: 1;
}

.freeze-details {
  margin-top: 0.5rem;
  padding: 0.75rem;
  background: linear-gradient(135deg, #ffe6e6, #fff0f0);
  border: 2px solid #dc3545;
  border-radius: 6px;
  box-shadow: 2px 2px 0 rgba(220, 53, 69, 0.2);
}

.task-info {
  margin-bottom: 0.5rem;
}

.task-title {
  font-weight: 700;
  color: #721c24;
  margin-bottom: 0.25rem;
  font-size: 0.9rem;
}

.freeze-reason {
  color: #856404;
  font-weight: 600;
  margin-bottom: 0.25rem;
  font-size: 0.85rem;
  padding: 0.25rem 0.5rem;
  background: rgba(255, 193, 7, 0.1);
  border: 1px solid #ffc107;
  border-radius: 4px;
  display: inline-block;
}

.freeze-time {
  color: #6c757d;
  font-size: 0.8rem;
  font-weight: 500;
  margin-top: 0.25rem;
}

.unfreeze-hint {
  margin-top: 0.5rem;
  padding: 0.5rem;
  background: rgba(23, 162, 184, 0.1);
  border: 2px solid #17a2b8;
  border-radius: 4px;
  color: #0c5460;
  font-weight: 600;
  font-size: 0.85rem;
  text-align: center;
  box-shadow: 1px 1px 0 rgba(23, 162, 184, 0.2);
}

/* 懒加载相关样式 */
.load-more-section {
  padding: 1rem;
  text-align: center;
  border-top: 1px solid #e9ecef;
}

.load-more-btn {
  background: linear-gradient(135deg, #007bff, #0056b3);
  color: white;
  border: none;
  border-radius: 4px;
  padding: 0.5rem 1rem;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.2s ease;
  font-size: 0.875rem;
}

.load-more-btn:hover {
  transform: translateY(-1px);
  box-shadow: 2px 2px 0 #000;
}

.loading-more {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  color: #6c757d;
  font-size: 0.875rem;
}

.no-more {
  text-align: center;
  padding: 1rem;
  color: #6c757d;
  font-size: 0.875rem;
  border-top: 1px solid #e9ecef;
}

.notification-list {
  max-height: 400px;  /* 增加高度以适应更多通知 */
  overflow-y: auto;
}

/* 滚动条样式 */
.notification-list::-webkit-scrollbar {
  width: 6px;
}

.notification-list::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.notification-list::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.notification-list::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

/* 移动端响应式 */
@media (max-width: 768px) {
  .notification-bell {
    position: static;
  }

  .mobile-overlay {
    display: block;
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.3);
    z-index: 9998;
    backdrop-filter: blur(2px);
    -webkit-backdrop-filter: blur(2px);
  }

  .notification-dropdown {
    position: fixed;
    top: 80px;
    left: 1rem;
    right: 1rem;
    width: auto;
    max-width: 420px;
    min-width: 320px;
    margin: 0 auto;
    max-height: calc(100vh - 120px);
    z-index: 99999;
    animation: slideDown 0.3s ease-out;
  }

  .notification-list {
    max-height: calc(100vh - 160px);
  }

  .notification-item {
    padding: 1rem;
    gap: 0.75rem;
  }

  .notification-title {
    font-size: 0.9rem;
    line-height: 1.4;
  }

  .notification-message {
    font-size: 0.85rem;
    line-height: 1.5;
  }

  .header-actions {
    flex-direction: column;
    gap: 0.25rem;
  }

  .mark-all-btn, .clear-btn {
    font-size: 0.625rem;
    padding: 0.25rem 0.5rem;
  }

  .dropdown-header {
    padding: 1rem;
  }

  .dropdown-header h3 {
    font-size: 1.1rem;
  }

  .game-choices {
    flex-direction: column;
    gap: 0.5rem;
    align-items: flex-start;
  }

  .choice-item {
    padding: 0.25rem 0.5rem;
    font-size: 0.75rem;
  }

  .vs-text {
    align-self: center;
    font-size: 0.8rem;
  }

  .notification-actions {
    flex-direction: column;
    gap: 0.25rem;
  }

  .action-btn {
    width: 28px;
    height: 28px;
    font-size: 0.8rem;
  }

  /* 移动端懒加载样式 */
  .load-more-section {
    padding: 0.75rem;
  }

  .load-more-btn {
    width: 100%;
    padding: 0.625rem 1rem;
    font-size: 0.8rem;
  }

  .loading-more {
    font-size: 0.8rem;
  }

  .no-more {
    padding: 0.75rem;
    font-size: 0.8rem;
  }
}

/* 超小屏幕优化 */
@media (max-width: 480px) {
  .notification-dropdown {
    top: 70px;
    left: 0.5rem;
    right: 0.5rem;
    width: auto;
    max-width: 380px;
    min-width: 300px;
    margin: 0 auto;
    max-height: calc(100vh - 110px);
    z-index: 99999;
  }

  .notification-list {
    max-height: calc(100vh - 155px);
  }

  .dropdown-header {
    padding: 0.75rem;
  }

  .dropdown-header h3 {
    font-size: 1rem;
  }

  .notification-item {
    padding: 0.75rem;
    gap: 0.5rem;
  }

  .notification-icon {
    font-size: 1.1rem;
  }

  .notification-title {
    font-size: 0.85rem;
  }

  .notification-message {
    font-size: 0.8rem;
  }

  .notification-meta {
    font-size: 0.7rem;
    gap: 0.25rem;
  }

  .mark-all-btn, .clear-btn {
    font-size: 0.6rem;
    padding: 0.2rem 0.4rem;
  }

  .game-details {
    padding: 0.5rem;
    font-size: 0.75rem;
  }

  .choice-item {
    padding: 0.2rem 0.4rem;
    font-size: 0.7rem;
  }

  .clickable-username {
    padding: 0.2rem 0.4rem;
    font-size: 0.75rem;
  }

  .clickable-actor {
    padding: 0.2rem 0.4rem;
    font-size: 0.7rem;
    margin-left: 0.125rem;
  }

  /* Task approval notification mobile styles */
  .task-approval-details {
    padding: 0.5rem;
    font-size: 0.75rem;
  }

  .task-title {
    padding: 0.2rem 0.4rem;
    font-size: 0.75rem;
    margin-bottom: 0.375rem;
  }

  .reward-amount {
    padding: 0.25rem 0.5rem;
    font-size: 0.75rem;
  }

  .pending-payment,
  .completed-payment,
  .immediate-payment {
    padding: 0.25rem 0.5rem;
    font-size: 0.7rem;
  }

  .participants-info {
    padding: 0.2rem 0.4rem;
    font-size: 0.7rem;
  }

  .approval-time {
    padding: 0.2rem 0.4rem;
    font-size: 0.7rem;
  }

  /* 超小屏幕懒加载样式 */
  .load-more-section {
    padding: 0.5rem;
  }

  .load-more-btn {
    width: 100%;
    padding: 0.5rem 0.75rem;
    font-size: 0.75rem;
  }

  .loading-more {
    font-size: 0.75rem;
  }

  .no-more {
    padding: 0.5rem;
    font-size: 0.75rem;
  }
}

/* ===========================================
 * 液态玻璃主题样式覆盖
 * =========================================== */

/* 液态玻璃主题下的铃铛图标 */
.theme-liquid-glass .bell-icon {
  background: var(--theme-modal-bg) !important;
  backdrop-filter: var(--theme-backdrop-filter) !important;
  -webkit-backdrop-filter: var(--theme-backdrop-filter) !important;
  border: 1px solid rgba(255, 255, 255, 0.2) !important;
  border-radius: 50% !important;
  box-shadow: var(--theme-shadow-small), var(--theme-inner-glow) !important;
  color: var(--theme-text-primary) !important;
  transition: all var(--theme-transition-fast) !important;
}

.theme-liquid-glass .bell-icon:hover {
  transform: translateY(-1px) scale(1.05) !important;
  box-shadow: var(--theme-hover-lift), var(--theme-inner-glow-strong) !important;
  backdrop-filter: blur(20px) saturate(200%) brightness(1.2) !important;
  -webkit-backdrop-filter: blur(20px) saturate(200%) brightness(1.2) !important;
  background: var(--theme-card-bg) !important;
  border-color: rgba(255, 255, 255, 0.3) !important;
}

.theme-liquid-glass .bell-icon.has-notifications {
  background: rgba(255, 107, 107, 0.15) !important;
  border-color: rgba(255, 107, 107, 0.3) !important;
  box-shadow: 0 0 20px rgba(255, 107, 107, 0.2), var(--theme-inner-glow) !important;
  animation: liquid-bell-ring 2s infinite;
}

@keyframes liquid-bell-ring {
  0%, 10%, 20%, 30%, 40%, 50%, 60%, 70%, 80%, 90%, 100% {
    transform: rotate(0deg);
  }
  5%, 15%, 25%, 35%, 45%, 55%, 65%, 75%, 85%, 95% {
    transform: rotate(10deg);
  }
}

/* 液态玻璃主题下的通知徽章 */
.theme-liquid-glass .notification-badge {
  background: rgba(220, 53, 69, 0.8) !important;
  backdrop-filter: var(--theme-glass-light) !important;
  -webkit-backdrop-filter: var(--theme-glass-light) !important;
  border: 1px solid rgba(220, 53, 69, 0.5) !important;
  border-radius: 50% !important;
  color: var(--theme-text-inverted) !important;
  box-shadow: 0 0 10px rgba(220, 53, 69, 0.3), var(--theme-inner-glow) !important;
}

/* 液态玻璃主题下的移动端遮罩 */
.theme-liquid-glass .mobile-overlay {
  background: rgba(0, 0, 0, 0.3) !important;
  backdrop-filter: blur(8px) !important;
  -webkit-backdrop-filter: blur(8px) !important;
}

/* 液态玻璃主题下的下拉框 */
.theme-liquid-glass .notification-dropdown {
  background: var(--theme-modal-bg) !important;
  backdrop-filter: var(--theme-backdrop-filter) !important;
  -webkit-backdrop-filter: var(--theme-backdrop-filter) !important;
  border: 1px solid rgba(255, 255, 255, 0.2) !important;
  border-radius: var(--theme-border-radius-large) !important;
  box-shadow: var(--theme-shadow-large), var(--theme-glow), var(--theme-inner-glow-strong) !important;
  z-index: 1000 !important;
}

/* 液态玻璃主题下的下拉框头部 */
.theme-liquid-glass .dropdown-header {
  background: var(--theme-card-bg) !important;
  backdrop-filter: var(--theme-glass-filter) !important;
  -webkit-backdrop-filter: var(--theme-glass-filter) !important;
  border: none !important;
  border-bottom: 1px solid rgba(255, 255, 255, 0.15) !important;
  border-radius: var(--theme-border-radius-large) var(--theme-border-radius-large) 0 0 !important;
}

.theme-liquid-glass .dropdown-header h3 {
  color: var(--theme-text-primary) !important;
}

/* 液态玻璃主题下的按钮 */
.theme-liquid-glass .mark-all-btn,
.theme-liquid-glass .clear-btn {
  background: var(--theme-tertiary-bg) !important;
  backdrop-filter: var(--theme-glass-light) !important;
  -webkit-backdrop-filter: var(--theme-glass-light) !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
  border-radius: var(--theme-border-radius-small) !important;
  color: var(--theme-text-primary) !important;
  box-shadow: var(--theme-inner-glow) !important;
  transition: all var(--theme-transition-fast) !important;
}

.theme-liquid-glass .mark-all-btn:hover,
.theme-liquid-glass .clear-btn:hover {
  transform: translateY(-1px) scale(1.02) !important;
  box-shadow: var(--theme-shadow-small), var(--theme-inner-glow-strong) !important;
  background: var(--theme-card-bg) !important;
  border-color: rgba(255, 255, 255, 0.2) !important;
}

/* 液态玻璃主题下的通知列表 */
.theme-liquid-glass .notification-list {
  background: transparent !important;
}

/* 液态玻璃主题下的通知项 */
.theme-liquid-glass .notification-item {
  background: transparent !important;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1) !important;
  transition: all var(--theme-transition-fast) !important;
}

.theme-liquid-glass .notification-item:hover {
  background: var(--theme-tertiary-bg) !important;
  backdrop-filter: var(--theme-glass-light) !important;
  -webkit-backdrop-filter: var(--theme-glass-light) !important;
}

.theme-liquid-glass .notification-item.is-read {
  background: var(--theme-secondary-bg) !important;
  opacity: 0.7;
}

.theme-liquid-glass .notification-item:not(.is-read):before {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.8), rgba(59, 130, 246, 0.6)) !important;
}

/* 液态玻璃主题下的通知内容 */
.theme-liquid-glass .notification-title {
  color: var(--theme-text-primary) !important;
}

.theme-liquid-glass .notification-message {
  color: var(--theme-text-secondary) !important;
}

.theme-liquid-glass .notification-meta {
  color: var(--theme-text-muted) !important;
}

.theme-liquid-glass .time {
  color: var(--theme-text-muted) !important;
}

/* 液态玻璃主题下的可点击元素 */
.theme-liquid-glass .clickable-actor,
.theme-liquid-glass .clickable-username {
  color: rgba(59, 130, 246, 0.9) !important;
  background: transparent !important;
  border: 1px solid transparent !important;
  backdrop-filter: var(--theme-glass-light) !important;
  -webkit-backdrop-filter: var(--theme-glass-light) !important;
  transition: all var(--theme-transition-fast) !important;
}

.theme-liquid-glass .clickable-actor:hover,
.theme-liquid-glass .clickable-username:hover {
  color: var(--theme-text-inverted) !important;
  background: rgba(59, 130, 246, 0.8) !important;
  border-color: rgba(59, 130, 246, 0.5) !important;
  backdrop-filter: var(--theme-glass-filter) !important;
  -webkit-backdrop-filter: var(--theme-glass-filter) !important;
  box-shadow: 0 0 15px rgba(59, 130, 246, 0.2), var(--theme-inner-glow) !important;
  transform: translateY(-1px) scale(1.02) !important;
}

/* 液态玻璃主题下的操作按钮 */
.theme-liquid-glass .action-btn {
  background: var(--theme-tertiary-bg) !important;
  backdrop-filter: var(--theme-glass-light) !important;
  -webkit-backdrop-filter: var(--theme-glass-light) !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
  border-radius: var(--theme-border-radius-small) !important;
  color: var(--theme-text-primary) !important;
  box-shadow: var(--theme-inner-glow) !important;
  transition: all var(--theme-transition-fast) !important;
}

.theme-liquid-glass .action-btn:hover {
  transform: translateY(-1px) scale(1.05) !important;
  box-shadow: var(--theme-shadow-small), var(--theme-inner-glow-strong) !important;
  backdrop-filter: var(--theme-glass-filter) !important;
  -webkit-backdrop-filter: var(--theme-glass-filter) !important;
}

.theme-liquid-glass .mark-read-btn:hover {
  background: rgba(40, 167, 69, 0.8) !important;
  color: var(--theme-text-inverted) !important;
  border-color: rgba(40, 167, 69, 0.5) !important;
  box-shadow: 0 0 15px rgba(40, 167, 69, 0.2), var(--theme-inner-glow-strong) !important;
}

.theme-liquid-glass .delete-btn:hover {
  background: rgba(220, 53, 69, 0.8) !important;
  color: var(--theme-text-inverted) !important;
  border-color: rgba(220, 53, 69, 0.5) !important;
  box-shadow: 0 0 15px rgba(220, 53, 69, 0.2), var(--theme-inner-glow-strong) !important;
}

/* 液态玻璃主题下的懒加载样式 */
.theme-liquid-glass .load-more-section {
  background: transparent !important;
  border-top: 1px solid rgba(255, 255, 255, 0.1) !important;
}

.theme-liquid-glass .load-more-btn {
  background: rgba(59, 130, 246, 0.15) !important;
  backdrop-filter: var(--theme-glass-filter) !important;
  -webkit-backdrop-filter: var(--theme-glass-filter) !important;
  border: 1px solid rgba(59, 130, 246, 0.2) !important;
  border-radius: var(--theme-border-radius-small) !important;
  color: var(--theme-text-primary) !important;
  box-shadow: 0 0 15px rgba(59, 130, 246, 0.2), var(--theme-inner-glow) !important;
  transition: all var(--theme-transition-fast) !important;
}

.theme-liquid-glass .load-more-btn:hover {
  transform: translateY(-1px) scale(1.02) !important;
  box-shadow: 0 0 25px rgba(59, 130, 246, 0.3), var(--theme-hover-lift) !important;
  background: rgba(59, 130, 246, 0.8) !important;
  color: var(--theme-text-inverted) !important;
}

.theme-liquid-glass .loading-more {
  color: var(--theme-text-secondary) !important;
}

.theme-liquid-glass .no-more {
  color: var(--theme-text-muted) !important;
  border-top: 1px solid rgba(255, 255, 255, 0.1) !important;
}

.theme-liquid-glass .loading {
  color: var(--theme-text-secondary) !important;
}

.theme-liquid-glass .empty-state {
  color: var(--theme-text-secondary) !important;
}

/* 移动端液态玻璃优化 */
@media (max-width: 768px) {
  .theme-liquid-glass .notification-dropdown {
    /* 完全继承原始UI的移动端定位 */
    position: fixed !important;
    top: 80px !important;
    left: 1rem !important;
    right: 1rem !important;
    width: auto !important;
    max-width: 420px !important;
    min-width: 320px !important;
    margin: 0 auto !important;
    max-height: calc(100vh - 120px) !important;
    z-index: 99999 !important;
    animation: slideDown 0.3s ease-out !important;
    border-radius: var(--theme-border-radius) !important;
  }

  .theme-liquid-glass .dropdown-header {
    border-radius: var(--theme-border-radius) var(--theme-border-radius) 0 0 !important;
  }
}

@media (max-width: 480px) {
  .theme-liquid-glass .notification-dropdown {
    /* 完全继承原始UI的超小屏移动端定位 */
    position: fixed !important;
    top: 70px !important;
    left: 0.5rem !important;
    right: 0.5rem !important;
    width: auto !important;
    max-width: 380px !important;
    min-width: 300px !important;
    margin: 0 auto !important;
    max-height: calc(100vh - 110px) !important;
    z-index: 99999 !important;
    border-radius: var(--theme-border-radius-small) !important;
  }

  .theme-liquid-glass .dropdown-header {
    border-radius: var(--theme-border-radius-small) var(--theme-border-radius-small) 0 0 !important;
  }
}
</style>