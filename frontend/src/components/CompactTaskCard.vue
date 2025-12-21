<template>
  <div
    class="compact-task-card"
    :class="{ 'clickable': clickable }"
    @click="handleClick"
  >
    <!-- Position Badge for Pinned Cards -->
    <div v-if="position" class="position-badge" :class="`position-${position}`">
      <span class="position-number">{{ position }}</span>
      <span class="position-crown">👑</span>
    </div>

    <!-- Pinning Time Remaining - New addition for pinned cards -->
    <div v-if="pinningInfo" class="pinning-time-section">
      <div class="pinning-time-remaining">
        <span class="pin-icon">📌</span>
        <span class="pin-label">置顶剩余:</span>
        <span class="pin-time-value">{{ formatPinTimeRemaining(pinningInfo) }}</span>
      </div>
      <div class="key-holder-info">
        <span class="key-icon">🔑</span>
        <span class="key-holder-name">{{ pinningInfo.key_holder.username }}</span>
      </div>
    </div>

    <!-- Task Header - Same as normal task card -->
    <div class="task-header">
      <div class="task-info">
        <h3 class="task-title">{{ task.title }}</h3>
        <div class="task-meta">
          <span v-if="task.task_type === 'lock' && (task as any).unlock_type" class="task-type">
            {{ getTaskTypeText((task as any).unlock_type) }}
          </span>
          <span v-if="task.task_type === 'board'" class="task-type">
            悬赏任务
          </span>
          <span v-if="task.task_type === 'lock' && task.difficulty" class="task-difficulty" :class="task.difficulty">
            {{ getDifficultyText(task.difficulty) }}
          </span>
          <span v-if="task.task_type === 'board' && (task as any).reward" class="task-reward">
            {{ (task as any).reward }} 积分
          </span>
          <span class="task-status" :class="task.status">
            {{ getStatusText(task.status) }}
          </span>
        </div>
      </div>
      <div class="task-actions">
        <!-- No delete button for pinned cards since they're view-only -->
      </div>
    </div>

    <!-- Quick Actions for Pinned Task Card -->
    <div v-if="canAddOvertime()" class="task-quick-actions">
      <button
        @click="handleOvertimeClick"
        class="task-quick-btn overtime-btn pinned-overtime"
        title="为置顶任务加时 (10倍效果)"
      >
        ⚡ 10倍加时
      </button>
    </div>

    <!-- Task Content - Same as normal task card -->
    <div class="task-content">
      <p v-if="task.description" class="task-description">{{ stripHtmlAndTruncate(task.description) }}</p>
    </div>

    <!-- Task Details - Same as normal task card -->
    <div class="task-details">
      <div class="task-duration">
        <span class="label">持续时间:</span>
        <span class="value">{{ formatDuration(task) }}</span>
      </div>
      <!-- Hide time-related information when time_display_hidden is true -->
      <div v-if="task.task_type === 'lock' && (task as any).started_at && !isTaskTimeHidden()" class="task-time">
        <span class="label">开始时间:</span>
        <span class="value">{{ formatDateTime((task as any).started_at) }}</span>
      </div>
      <div v-if="task.task_type === 'lock' && (task as any).end_time && !isTaskTimeHidden()" class="task-time">
        <span class="label">结束时间:</span>
        <span class="value">{{ formatDateTime((task as any).end_time) }}</span>
      </div>
      <!-- Remaining time display - hide when time is hidden -->
      <div v-if="getTimeRemaining() > 0 && !isTaskTimeHidden()" class="task-time-remaining">
        <span class="label">剩余时间:</span>
        <span class="value countdown" :class="{ 'overtime': getTimeRemaining() <= 0 }">
          {{ formatTimeRemaining(getTimeRemaining()) }}
        </span>
      </div>
      <div v-else-if="(task.status === 'active' && task.task_type === 'lock') || (task.status === 'taken' && task.task_type === 'board')" class="task-time-remaining">
        <span class="label">状态:</span>
        <span v-if="!isTaskTimeHidden()" class="value overtime">倒计时已结束</span>
        <span v-else class="value time-hidden-placeholder">
          <span class="hidden-time-indicator">🔒 时间已隐藏</span>
        </span>
      </div>

      <!-- Multi-person Task Participant Information - Simplified -->
      <div v-if="task.task_type === 'board' && (task as any).max_participants && (task as any).max_participants > 1" class="task-participants-compact">
        <div class="participants-summary">
          <span class="participants-count">👥 {{ (task as any).participant_count || 0 }}/{{ (task as any).max_participants }}</span>
          <span v-if="(task as any).submitted_count && (task as any).submitted_count > 0" class="submitted-count">📤 {{ (task as any).submitted_count }}</span>
          <span v-if="(task as any).approved_count && (task as any).approved_count > 0" class="approved-count">✅ {{ (task as any).approved_count }}</span>
        </div>
        <div v-if="(task as any).reward && (task as any).max_participants > 1" class="reward-compact">
          💰 {{ Math.ceil((task as any).reward / (task as any).max_participants) }}/人
        </div>
      </div>
    </div>

    <!-- Task Progress - Same as normal task card -->
    <div class="task-progress">
      <!-- Hide progress bar when time is hidden -->
      <div v-if="((task.task_type === 'lock' && task.status === 'active') || (task.task_type === 'board' && task.status === 'taken')) && !isTaskTimeHidden()" class="progress-bar mobile-progress-container">
        <div
          class="progress-fill mobile-progress-fill"
          :class="getProgressColorClass()"
          :style="{
            width: Math.max(10, getProgressPercent()) + '%',
            '--mobile-progress': Math.max(10, getProgressPercent()) + '%'
          }"
          :title="`进度: ${getProgressPercent().toFixed(1)}% - ${getProgressColorClass()}`"
        ></div>
        <!-- Mobile debug display -->
        <div class="mobile-debug-info">
          {{ getProgressPercent().toFixed(1) }}% {{ getProgressColorClass() }}
        </div>
      </div>
      <!-- Show placeholder when time is hidden -->
      <div v-else-if="((task.task_type === 'lock' && task.status === 'active') || (task.task_type === 'board' && task.status === 'taken')) && isTaskTimeHidden()" class="progress-hidden-placeholder">
        <span class="hidden-time-indicator">🔒 进度已隐藏</span>
      </div>
      <div class="task-user">
        <UserAvatar
          v-if="task.user"
          :user="task.user"
          size="small"
          :clickable="false"
          :show-lock-indicator="true"
        />
        <div v-else class="user-placeholder">👤</div>
        <span class="username">{{ task.user?.username || '未知用户' }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import UserAvatar from './UserAvatar.vue'
import type { Task } from '../types/index'

// Props
interface Props {
  task: Task
  position?: number // For pinned cards (1, 2, 3)
  pinningInfo?: {
    expires_at: string // ISO timestamp
    time_remaining: number // in seconds
    key_holder: { username: string }
  }
  clickable?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  clickable: true
})

// Auth store
const authStore = useAuthStore()

// Reactive current time for real-time updates
const currentTime = ref(Date.now())
const timeInterval = ref<number>()

// Emits
const emit = defineEmits<{
  click: [task: Task]
  overtime: [task: Task, event: Event]
}>()

// Methods
const handleClick = () => {
  if (props.clickable) {
    emit('click', props.task)
  }
}

const getTaskTypeText = (type: string) => {
  const texts = {
    time: '定时解锁',
    vote: '投票解锁'
  }
  return texts[type as keyof typeof texts] || type
}

const getDifficultyText = (difficulty: string) => {
  const texts = {
    easy: '简单',
    normal: '普通',
    hard: '困难',
    hell: '地狱'
  }
  return texts[difficulty as keyof typeof texts] || difficulty
}

const getStatusText = (status: string) => {
  const texts = {
    pending: '待开始',
    active: '进行中',
    voting: '投票中',
    completed: '已完成',
    failed: '已失败',
    open: '开放中',
    taken: '已接取',
    submitted: '已提交'
  }
  return texts[status as keyof typeof texts] || status
}

const isTaskTimeHidden = () => {
  if (!props.task || props.task.task_type !== 'lock') return false
  return (props.task as any).time_display_hidden || false
}

const getTimeRemaining = () => {
  if (!props.task) return 0

  const now = currentTime.value

  // Lock tasks
  if (props.task.task_type === 'lock' && props.task.status === 'active') {
    const lockTask = props.task as any
    if (lockTask.end_time) {
      const end = new Date(lockTask.end_time).getTime()
      return Math.max(0, end - now)
    }
  }

  // Board tasks
  if (props.task.task_type === 'board' && props.task.status === 'taken') {
    const boardTask = props.task as any
    if (boardTask.deadline) {
      const end = new Date(boardTask.deadline).getTime()
      return Math.max(0, end - now)
    }
  }

  return 0
}

const getProgressPercent = () => {
  if (!props.task) return 0

  const now = currentTime.value

  // Lock tasks
  if (props.task.task_type === 'lock' && props.task.status === 'active') {
    const lockTask = props.task as any
    if (!lockTask.start_time || !lockTask.end_time) return 0

    const start = new Date(lockTask.start_time).getTime()
    const end = new Date(lockTask.end_time).getTime()

    if (now <= start) return 0
    if (now >= end) return 100

    return ((now - start) / (end - start)) * 100
  }

  // Board tasks
  if (props.task.task_type === 'board' && props.task.status === 'taken') {
    const boardTask = props.task as any
    if (!boardTask.taken_at || !boardTask.deadline) return 0

    const start = new Date(boardTask.taken_at).getTime()
    const end = new Date(boardTask.deadline).getTime()

    if (now <= start) return 0
    if (now >= end) return 100

    return ((now - start) / (end - start)) * 100
  }

  return 0
}

const getProgressColorClass = () => {
  const timeRemaining = getTimeRemaining()
  const thirtyMinutes = 30 * 60 * 1000
  const progressPercent = getProgressPercent()

  // Last 30 minutes - red
  if (timeRemaining > 0 && timeRemaining <= thirtyMinutes) {
    return 'progress-red'
  }
  // Over 50% completed - orange
  else if (progressPercent > 50) {
    return 'progress-orange'
  }
  // Initial/early stage - green
  else {
    return 'progress-green'
  }
}

const formatTimeRemaining = (milliseconds: number) => {
  const hours = Math.floor(milliseconds / (1000 * 60 * 60))
  const minutes = Math.floor((milliseconds % (1000 * 60 * 60)) / (1000 * 60))
  const seconds = Math.floor((milliseconds % (1000 * 60)) / 1000)

  if (hours > 0) {
    return `${hours}小时${minutes}分钟`
  } else if (minutes > 0) {
    return `${minutes}分钟${seconds}秒`
  } else {
    return `${seconds}秒`
  }
}

const formatDuration = (task: Task) => {
  // For board tasks, show max_duration instead of duration_value
  if (task.task_type === 'board' && 'max_duration' in task && (task as any).max_duration) {
    return `最长 ${(task as any).max_duration} 小时`
  }

  // For lock tasks
  if (task.task_type === 'lock' && 'duration_value' in task) {
    if (!(task as any).duration_value) return '-'

    const hours = Math.floor((task as any).duration_value / 60)
    const minutes = (task as any).duration_value % 60

    if ((task as any).duration_type === 'random' && 'duration_max' in task && (task as any).duration_max) {
      const maxDuration = (task as any).duration_max as number
      const maxHours = Math.floor(maxDuration / 60)
      const maxMinutes = maxDuration % 60
      return `${hours}小时${minutes}分钟 - ${maxHours}小时${maxMinutes}分钟`
    }

    return `${hours}小时${minutes}分钟`
  }

  return '-'
}

const formatDateTime = (dateTime: string) => {
  return new Date(dateTime).toLocaleString('zh-CN')
}

const stripHtmlAndTruncate = (html: string, maxLength: number = 100): string => {
  if (!html) return ''

  // Create a temporary div to strip HTML tags
  const tempDiv = document.createElement('div')
  tempDiv.innerHTML = html
  const textContent = tempDiv.textContent || tempDiv.innerText || ''

  // Truncate text if it's too long
  if (textContent.length <= maxLength) {
    return textContent
  }

  return textContent.slice(0, maxLength) + '...'
}

const formatPinTimeRemaining = (pinningInfo: any): string => {
  if (!pinningInfo || !pinningInfo.expires_at) return '已过期'

  // Calculate remaining time in real-time using current time
  const expiresAt = new Date(pinningInfo.expires_at).getTime()
  const now = currentTime.value
  const timeRemainingMs = Math.max(0, expiresAt - now)

  if (timeRemainingMs <= 0) return '已过期'

  // Convert milliseconds to minutes and seconds
  const totalSeconds = Math.floor(timeRemainingMs / 1000)
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60

  if (minutes > 0) {
    return `${minutes}分${seconds}秒`
  } else {
    return `${seconds}秒`
  }
}

// Check if current user can add overtime to this task
const canAddOvertime = (): boolean => {
  if (!props.task || !props.pinningInfo) return false

  // Check if it's not the user's own task
  const currentUserId = authStore.user?.id
  const taskUserId = props.task.user?.id

  // Only allow overtime if:
  // 1. User is authenticated
  // 2. Task is active (lock) or taken (board)
  // 3. It's not the user's own task
  // 4. Task is currently pinned (pinningInfo exists)
  return currentUserId !== undefined &&
         taskUserId !== undefined &&
         currentUserId !== taskUserId &&
         ((props.task.task_type === 'lock' && props.task.status === 'active') ||
          (props.task.task_type === 'board' && props.task.status === 'taken'))
}

// Handle overtime button click
const handleOvertimeClick = (event: Event) => {
  event.stopPropagation() // Prevent card click
  emit('overtime', props.task, event)
}

// Lifecycle hooks for real-time updates
onMounted(() => {
  // Start timer for real-time updates
  timeInterval.value = window.setInterval(() => {
    currentTime.value = Date.now()
  }, 1000)
})

onUnmounted(() => {
  // Clean up timer
  if (timeInterval.value) {
    clearInterval(timeInterval.value)
  }
})
</script>

<style scoped>
/* Base card styling - matches normal task card */
.compact-task-card {
  background: white;
  border: 2px solid #000;
  border-radius: 8px;
  box-shadow: 4px 4px 0 #000;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  display: flex;
  flex-direction: column;
  height: auto;
  min-height: 300px;
  max-height: 400px;
  width: 100%;
  box-sizing: border-box;
  overflow: hidden;
  padding: 1rem;
  position: relative;
}

.compact-task-card.clickable {
  cursor: pointer;
}

.compact-task-card.clickable:hover {
  transform: translateY(-2px);
  box-shadow: 6px 6px 0 #000;
}

/* Position Badge - for pinned positions */
.position-badge {
  position: absolute;
  top: -8px;
  right: -8px;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 2px solid #000;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 900;
  font-size: 0.875rem;
  z-index: 2;
  box-shadow: 2px 2px 0 rgba(0, 0, 0, 0.3);
}

.position-badge.position-1 {
  background: linear-gradient(135deg, #ffd700, #ffed4e);
  color: #000;
}

.position-badge.position-2 {
  background: linear-gradient(135deg, #c0c0c0, #e8e8e8);
  color: #000;
}

.position-badge.position-3 {
  background: linear-gradient(135deg, #cd7f32, #daa520);
  color: #000;
}

.position-crown {
  position: absolute;
  top: -8px;
  right: -8px;
  font-size: 1rem;
  z-index: 3;
}

/* Pinning Time Section - NEW addition for pinned cards */
.pinning-time-section {
  background: linear-gradient(135deg, #ff6b6b, #ee5a52);
  border: 2px solid #000;
  border-radius: 6px;
  padding: 0.75rem;
  margin-bottom: 1rem;
  box-shadow: 2px 2px 0 #000;
}

.pinning-time-remaining {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.pin-icon {
  font-size: 1rem;
}

.pin-label {
  font-weight: 700;
  color: white;
  font-size: 0.875rem;
}

.pin-time-value {
  font-weight: 900;
  color: white;
  font-size: 0.875rem;
  background: rgba(0, 0, 0, 0.2);
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  border: 1px solid rgba(0, 0, 0, 0.3);
}

.key-holder-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.key-icon {
  font-size: 1rem;
}

.key-holder-name {
  font-weight: 700;
  color: white;
  font-size: 0.875rem;
  background: rgba(0, 0, 0, 0.2);
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  border: 1px solid rgba(0, 0, 0, 0.3);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Task Header - matches normal task card */
.task-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 0.75rem;
}

.task-info {
  flex: 1;
  min-width: 0;
}

.task-title {
  font-size: 1.1rem;
  font-weight: bold;
  margin: 0 0 0.5rem 0;
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}

.task-meta {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.task-type, .task-difficulty, .task-status, .task-reward {
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: bold;
  text-transform: uppercase;
}

.task-type {
  background-color: #17a2b8;
  color: white;
}

.task-reward {
  background-color: #ffc107;
  color: #212529;
}

.task-difficulty.easy {
  background-color: #28a745;
  color: white;
}

.task-difficulty.normal {
  background-color: #ffc107;
  color: #212529;
}

.task-difficulty.hard {
  background-color: #fd7e14;
  color: white;
}

.task-difficulty.hell {
  background-color: #dc3545;
  color: white;
}

.task-status.active {
  background-color: #007bff;
  color: white;
}

.task-status.voting {
  background-color: #ffc107;
  color: #212529;
  animation: pulse 2s infinite;
}

.task-status.completed {
  background-color: #28a745;
  color: white;
}

.task-status.failed {
  background-color: #dc3545;
  color: white;
}

.task-status.open {
  background-color: #28a745;
  color: white;
}

.task-status.taken {
  background-color: #fd7e14;
  color: white;
}

.task-status.submitted {
  background-color: #6f42c1;
  color: white;
}

/* Task Actions */
.task-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

/* Quick Actions - matches normal task card but with pinned styling */
.task-quick-actions {
  display: flex;
  justify-content: center;
  padding: 0.75rem;
  border-top: 2px solid #e9ecef;
  margin-top: auto;
}

.task-quick-btn {
  background: #fd7e14;
  color: white;
  border: 3px solid #000;
  padding: 0.75rem 1.5rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  cursor: pointer;
  box-shadow: 4px 4px 0 #000;
  transition: all 0.2s ease;
  font-size: 0.875rem;
  border-radius: 4px;
}

.task-quick-btn:hover {
  transform: translate(-2px, -2px);
  box-shadow: 6px 6px 0 #000;
  background-color: #e76500;
}

.task-quick-btn.pinned-overtime {
  background: linear-gradient(135deg, #fd7e14, #ff6b35);
}

.task-quick-btn.pinned-overtime:hover {
  background: linear-gradient(135deg, #e76500, #e55a2b);
}

/* Task Content - matches normal task card */
.task-content {
  margin-bottom: 0.75rem;
}

.task-description {
  color: #666;
  margin-bottom: 0.75rem;
  line-height: 1.4;
  font-size: 0.9rem;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

/* Task Details - matches normal task card */
.task-details {
  margin-bottom: 0.75rem;
  font-size: 0.8rem;
  flex: 1;
  overflow: hidden;
}

.task-duration, .task-time, .task-time-remaining {
  margin-bottom: 0.5rem;
}

.label {
  font-weight: 500;
  color: #666;
}

.value {
  color: #333;
  margin-left: 0.5rem;
}

.countdown {
  font-weight: bold;
  color: #007bff;
  animation: pulse-countdown 2s infinite;
}

.countdown.overtime {
  color: #dc3545;
  animation: pulse-danger 1s infinite;
}

.overtime {
  color: #dc3545;
  font-weight: bold;
}

@keyframes pulse-countdown {
  0% { opacity: 1; }
  50% { opacity: 0.7; }
  100% { opacity: 1; }
}

@keyframes pulse-danger {
  0% { opacity: 1; }
  50% { opacity: 0.5; }
  100% { opacity: 1; }
}

/* Time Hidden Styles */
.time-hidden-placeholder {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.hidden-time-indicator {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  background: linear-gradient(135deg, #343a40, #495057);
  color: white;
  border: 1px solid #000;
  border-radius: 4px;
  font-weight: 700;
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  box-shadow: 1px 1px 0 #000;
  animation: gentle-pulse 2s ease-in-out infinite;
}

@keyframes gentle-pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.8;
    transform: scale(1.02);
  }
}

/* Multi-person Task Participants - matches normal task card */
.task-participants-compact {
  margin: 0.5rem 0;
  padding: 0.5rem;
  background: #f8f9fa;
  border-radius: 4px;
  border: 1px solid #dee2e6;
}

.participants-summary {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  flex-wrap: wrap;
}

.participants-count,
.submitted-count,
.approved-count {
  font-size: 0.75rem;
  font-weight: 600;
  color: #495057;
  white-space: nowrap;
}

.reward-compact {
  margin-top: 0.25rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: #28a745;
}

/* Task Progress - matches normal task card */
.task-progress {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 1rem;
  border-top: 1px solid #e9ecef;
  gap: 1rem;
}

.progress-bar {
  flex: 1;
  height: 10px;
  background-color: #e9ecef;
  border: 2px solid #000;
  border-radius: 0;
  overflow: hidden;
  box-shadow: inset 2px 2px 4px rgba(0, 0, 0, 0.2);
  position: relative;
  max-width: 66.67%;
}

.progress-fill {
  height: 100%;
  background-color: #007bff;
  transition: width 0.3s ease, background-color 0.5s ease;
  position: relative;
  border-right: 1px solid rgba(0, 0, 0, 0.3);
  min-width: 2px;
}

.progress-fill.progress-green {
  background: linear-gradient(90deg, #28a745, #20c997);
  box-shadow: inset 0 2px 4px rgba(255, 255, 255, 0.3);
}

.progress-fill.progress-orange {
  background: linear-gradient(90deg, #fd7e14, #ffc107);
  box-shadow: inset 0 2px 4px rgba(255, 255, 255, 0.3);
}

.progress-fill.progress-red {
  background: linear-gradient(90deg, #dc3545, #e74c3c);
  box-shadow: inset 0 2px 4px rgba(255, 255, 255, 0.3);
  animation: pulse-urgent 2s infinite;
}

@keyframes pulse-urgent {
  0%, 100% {
    box-shadow: inset 0 2px 4px rgba(255, 255, 255, 0.3);
    opacity: 1;
  }
  50% {
    box-shadow: inset 0 2px 4px rgba(255, 255, 255, 0.5);
    opacity: 0.8;
  }
}

.progress-hidden-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  height: 40px;
  background: linear-gradient(135deg, #f8f9fa, #e9ecef);
  border: 2px dashed #6c757d;
  border-radius: 6px;
  max-width: 66.67%;
}

.task-user {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  max-width: 33.33%;
  flex-shrink: 0;
}

.user-placeholder {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, #e9ecef, #dee2e6);
  border: 2px solid #6c757d;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
  color: #6c757d;
  flex-shrink: 0;
}

.username {
  font-size: 0.875rem;
  color: #666;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  min-width: 0;
}

/* Mobile Debug Info */
.mobile-debug-info {
  position: absolute;
  top: -25px;
  left: 0;
  font-size: 11px;
  font-weight: bold;
  color: #dc3545;
  background: rgba(255, 255, 255, 0.9);
  padding: 2px 6px;
  border-radius: 3px;
  border: 1px solid #dc3545;
  z-index: 1000;
  white-space: nowrap;
}

/* Mobile Responsive */
@media (max-width: 768px) {
  .compact-task-card {
    min-height: 280px;
    padding: 0.75rem;
  }

  .position-badge {
    width: 28px;
    height: 28px;
    font-size: 0.75rem;
    top: -6px;
    right: -6px;
  }

  .position-crown {
    font-size: 0.875rem;
    top: -6px;
    right: -6px;
  }

  .pinning-time-section {
    padding: 0.5rem;
    margin-bottom: 0.75rem;
  }

  .pin-label,
  .pin-time-value,
  .key-holder-name {
    font-size: 0.8rem;
  }

  .task-title {
    font-size: 0.875rem;
  }

  .task-meta {
    gap: 0.375rem;
  }

  .task-type,
  .task-difficulty,
  .task-status,
  .task-reward {
    font-size: 0.65rem;
    padding: 0.15rem 0.3rem;
  }

  .task-description {
    font-size: 0.85rem;
    margin-bottom: 0.375rem;
    line-height: 1.3;
  }

  .task-details {
    font-size: 0.75rem;
    margin-bottom: 0.375rem;
  }

  .task-progress {
    flex-direction: column;
    gap: 0.5rem;
    align-items: stretch;
    margin-top: auto;
  }

  .mobile-progress-container {
    margin-right: 0 !important;
    height: 32px !important;
    max-width: 100% !important;
    border: none !important;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.15) !important;
    border-radius: 6px !important;
    background: linear-gradient(135deg, #e9ecef, #dee2e6) !important;
    padding: 3px !important;
    overflow: hidden !important;
    flex: none !important;
    position: relative !important;
  }

  .mobile-progress-fill {
    min-width: 24px !important;
    border: none !important;
    border-radius: 3px !important;
    height: calc(100% - 6px) !important;
    margin: 3px !important;
    position: relative !important;
    display: block !important;
    transition: all 0.3s ease !important;
    background: linear-gradient(135deg, #007bff, #0056b3) !important;
    box-shadow: inset 0 1px 2px rgba(255, 255, 255, 0.3), 0 1px 2px rgba(0, 0, 0, 0.2) !important;
  }

  .mobile-progress-fill.progress-green {
    background: linear-gradient(135deg, #28a745, #20c997, #17a2b8) !important;
    box-shadow:
      inset 0 3px 6px rgba(255, 255, 255, 0.7),
      0 3px 6px rgba(40, 167, 69, 0.4) !important;
  }

  .mobile-progress-fill.progress-orange {
    background: linear-gradient(135deg, #fd7e14, #ffc107, #ff6b35) !important;
    box-shadow:
      inset 0 3px 6px rgba(255, 255, 255, 0.7),
      0 3px 6px rgba(253, 126, 20, 0.4) !important;
  }

  .mobile-progress-fill.progress-red {
    background: linear-gradient(135deg, #dc3545, #e74c3c, #ff6b6b) !important;
    box-shadow:
      inset 0 3px 6px rgba(255, 255, 255, 0.7),
      0 3px 6px rgba(220, 53, 69, 0.4) !important;
    animation: pulse-urgent-mobile 1.5s infinite;
  }

  @keyframes pulse-urgent-mobile {
    0%, 100% {
      opacity: 1;
      transform: scale(1);
      filter: brightness(1);
    }
    50% {
      opacity: 0.9;
      transform: scale(1.02);
      filter: brightness(1.2);
    }
  }

  .task-user {
    max-width: 100%;
    justify-content: center;
    margin-top: 0.25rem;
    padding-top: 0.25rem;
  }

  .username {
    max-width: 200px;
    text-align: center;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .task-quick-actions {
    padding: 0.5rem;
  }

  .task-quick-btn {
    width: 100%;
    padding: 0.75rem;
    font-size: 0.875rem;
  }

  .task-participants-compact {
    padding: 0.375rem;
    margin: 0.375rem 0;
  }

  .participants-summary {
    gap: 0.5rem;
  }

  .participants-count,
  .submitted-count,
  .approved-count {
    font-size: 0.7rem;
  }

  .reward-compact {
    font-size: 0.7rem;
  }
}

@media (max-width: 480px) {
  .compact-task-card {
    min-height: 260px;
    padding: 0.6rem;
  }

  .task-title {
    font-size: 0.8rem;
  }

  .username {
    font-size: 0.75rem;
  }

  .pinning-time-section {
    padding: 0.4rem;
  }

  .pin-label,
  .pin-time-value,
  .key-holder-name {
    font-size: 0.75rem;
  }

  .mobile-progress-container {
    height: 36px !important;
    border-radius: 8px !important;
    padding: 4px !important;
    box-shadow: 0 3px 6px rgba(0, 0, 0, 0.2) !important;
    background: linear-gradient(135deg, #e9ecef, #ced4da) !important;
  }

  .mobile-progress-fill {
    min-width: 28px !important;
    border-radius: 4px !important;
    height: calc(100% - 8px) !important;
    margin: 4px !important;
  }

  .mobile-progress-fill.progress-green {
    background: linear-gradient(135deg, #28a745, #20c997, #17a2b8, #4caf50) !important;
    box-shadow:
      inset 0 4px 8px rgba(255, 255, 255, 0.8),
      0 4px 8px rgba(40, 167, 69, 0.5) !important;
  }

  .mobile-progress-fill.progress-orange {
    background: linear-gradient(135deg, #fd7e14, #ffc107, #ff6b35, #ff9800) !important;
    box-shadow:
      inset 0 4px 8px rgba(255, 255, 255, 0.8),
      0 4px 8px rgba(253, 126, 20, 0.5) !important;
  }

  .mobile-progress-fill.progress-red {
    background: linear-gradient(135deg, #dc3545, #e74c3c, #ff6b6b, #f44336) !important;
    box-shadow:
      inset 0 4px 8px rgba(255, 255, 255, 0.8),
      0 4px 8px rgba(220, 53, 69, 0.5) !important;
    animation: pulse-urgent-small 1.5s infinite;
  }

  @keyframes pulse-urgent-small {
    0%, 100% {
      opacity: 1;
      transform: scale(1);
      filter: brightness(1);
    }
    50% {
      opacity: 0.95;
      transform: scale(1.03);
      filter: brightness(1.3);
    }
  }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}
</style>