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
    <div v-if="showDropdown" class="mobile-overlay" @click="showDropdown = false"></div>

    <!-- 通知下拉列表 -->
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
          <button
            v-if="hasNotifications"
            @click="clearReadNotifications"
            class="clear-btn"
          >
            清理已读
          </button>
        </div>
      </div>

      <!-- 通知列表 -->
      <div class="notification-list">
        <div v-if="loading" class="loading">
          <div class="spinner">⏳</div>
          <span>加载中...</span>
        </div>

        <div v-else-if="!hasNotifications" class="empty-state">
          <div class="empty-icon">📭</div>
          <p>暂无通知</p>
        </div>

        <div v-else>
          <div
            v-for="notification in displayNotifications"
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
                  @click.stop="openActorProfile(notification.actor.id, notification.actor.username)"
                  :title="`查看 ${notification.actor.username} 的个人资料`"
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
        </div>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useNotificationStore } from '../stores/notifications'
import type { NotificationItem } from '../types/index'

const router = useRouter()
const notificationStore = useNotificationStore()

// 响应式数据
const showDropdown = ref(false)
const loading = ref(false)
const notifications = ref<NotificationItem[]>([])
const limit = ref(10)

// 计算属性
const unreadCount = computed(() => {
  // 使用store中的unreadCount，确保即使没有加载通知列表也能显示正确的未读数量
  return notificationStore.unreadCount
})

const hasNotifications = computed(() => notifications.value.length > 0)
const hasUnreadNotifications = computed(() => unreadCount.value > 0)

const displayNotifications = computed(() => {
  return notifications.value.slice(0, limit.value)
})

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
    coins_earned_task_reward: '🏆',
    coins_spent_task_creation: '💸',
    treasure_found: '💎',
    photo_viewed: '📷',
    drift_bottle_found: '🍾',
    item_received: '🎁',
    item_shared: '🔗',
    friend_request: '👋',
    friend_accepted: '🤝',
    level_upgraded: '⬆️',
    system_announcement: '📢',
    game_result: '🎮'
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
  if (loading.value) return

  loading.value = true
  try {
    const newNotifications = await notificationStore.fetchNotifications({
      limit: limit.value,
      is_read: 'false' // 优先加载未读通知
    })

    if (newNotifications.length < limit.value) {
      // 如果未读通知不足，加载已读通知
      const readNotifications = await notificationStore.fetchNotifications({
        limit: limit.value - newNotifications.length,
        is_read: 'true'
      })
      notifications.value = [...newNotifications, ...readNotifications]
    } else {
      notifications.value = newNotifications
    }

  } catch (error) {
    console.error('加载通知失败:', error)
  } finally {
    loading.value = false
  }
}


const handleNotificationClick = async (notification: NotificationItem) => {
  // 如果通知未读，标记为已读
  if (!notification.is_read) {
    await markAsRead(notification.id)
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

const openActorProfile = (actorId: number, actorUsername: string) => {
  console.log('openActorProfile called:', actorId, actorUsername)
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
    const notification = notifications.value.find(n => n.id === notificationId)
    if (notification) {
      notification.is_read = true
      notification.read_at = new Date().toISOString()
    }
  } catch (error) {
    console.error('标记已读失败:', error)
  }
}

const markAllAsRead = async () => {
  try {
    await notificationStore.markAllAsRead()
    notifications.value.forEach(n => {
      n.is_read = true
      n.read_at = new Date().toISOString()
    })
  } catch (error) {
    console.error('标记全部已读失败:', error)
  }
}

const deleteNotification = async (notificationId: string) => {
  try {
    await notificationStore.deleteNotification(notificationId)
    notifications.value = notifications.value.filter(n => n.id !== notificationId)
  } catch (error) {
    console.error('删除通知失败:', error)
  }
}

const clearReadNotifications = async () => {
  try {
    await notificationStore.clearReadNotifications()
    notifications.value = notifications.value.filter(n => !n.is_read)
  } catch (error) {
    console.error('清理已读通知失败:', error)
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
        const stats = await notificationStore.fetchNotificationStats()
        // 更新徽章数量（通过重新加载少量通知）
        if (stats.unread_notifications > 0) {
          const unreadNotifications = await notificationStore.fetchNotifications({
            limit: Math.min(stats.unread_notifications, 5),
            is_read: 'false'
          })
          const existingIds = new Set(notifications.value.map(n => n.id))
          unreadNotifications.forEach(n => {
            if (!existingIds.has(n.id)) {
              notifications.value.unshift(n)
            }
          })
        }
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
  min-width: 400px;
  max-width: 500px;
  max-height: 500px;
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
  max-height: 350px;
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
  background-color: #007bff;
  color: white;
  transform: translate(-1px, -1px);
  box-shadow: 2px 2px 0 #000;
  text-decoration: none;
  border-color: #000;
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
  background-color: #007bff;
  color: white;
  transform: translate(-1px, -1px);
  box-shadow: 2px 2px 0 #000;
  text-decoration: none;
  border-color: #000;
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
    top: 60px;
    right: 0.5rem;
    left: 0.5rem;
    width: auto;
    min-width: unset;
    max-width: unset;
    transform: none;
    margin-top: 0;
    max-height: calc(100vh - 80px);
    z-index: 9999;
    animation: slideDown 0.3s ease-out;
  }

  .notification-list {
    max-height: calc(100vh - 140px);
  }

  .notification-item {
    padding: 0.75rem;
    gap: 0.5rem;
  }

  .notification-title {
    font-size: 0.875rem;
    line-height: 1.3;
  }

  .notification-message {
    font-size: 0.8rem;
    line-height: 1.4;
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
    padding: 0.75rem;
  }

  .dropdown-header h3 {
    font-size: 1rem;
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
}

/* 超小屏幕优化 */
@media (max-width: 480px) {
  .notification-dropdown {
    top: 55px;
    right: 0.25rem;
    left: 0.25rem;
    max-height: calc(100vh - 75px);
  }

  .notification-list {
    max-height: calc(100vh - 135px);
  }

  .dropdown-header {
    padding: 0.5rem;
  }

  .dropdown-header h3 {
    font-size: 0.9rem;
  }

  .notification-item {
    padding: 0.5rem;
    gap: 0.375rem;
  }

  .notification-icon {
    font-size: 1rem;
  }

  .notification-title {
    font-size: 0.8rem;
  }

  .notification-message {
    font-size: 0.75rem;
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
}
</style>