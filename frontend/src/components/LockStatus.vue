<template>
  <div
    v-if="lockTask"
    class="lock-status-link"
    @click="handleClick"
  >
    <div class="lock-status" :class="{ 'is-expired': lockTask.is_expired }">
      <div class="lock-icon">
        🔒
      </div>
      <div class="lock-info">
        <div class="lock-title">{{ lockTask.title }}</div>
        <div class="lock-meta">
          <span class="difficulty" :class="lockTask.difficulty">
            {{ getDifficultyText(lockTask.difficulty) }}
          </span>
          <span class="separator">•</span>
          <span class="countdown" :class="{ 'expired': lockTask.is_expired }">
            <span v-if="lockTask.time_display_hidden" class="time-hidden">
              🔒 时间已隐藏
            </span>
            <span v-else>
              {{ lockTask.is_expired ? '时间已到' : formatTimeRemaining(timeRemaining) }}
            </span>
          </span>
        </div>
        <div v-if="lockTask.duration_value" class="duration-info">
          持续时间: {{ formatDuration(lockTask.duration_value, lockTask.duration_type, lockTask.duration_max) }}
        </div>
        <div v-if="showActions && lockTask.can_complete" class="lock-actions">
          <span class="complete-hint">
            ✅ 点击前往完成任务
          </span>
        </div>
        <div v-else class="click-hint">
          👆 点击查看任务详情
        </div>
      </div>
    </div>
  </div>
  <div v-else-if="showWhenFree" class="no-lock-status">
    <div class="free-icon">🔓</div>
    <div class="free-text">当前未处于带锁状态</div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import type { ActiveLockTask } from '../types/index'

interface Props {
  lockTask?: ActiveLockTask | null
  showActions?: boolean
  showWhenFree?: boolean
  size?: 'small' | 'normal' | 'large'
}

const props = withDefaults(defineProps<Props>(), {
  showActions: true,
  showWhenFree: false,
  size: 'normal'
})

const emit = defineEmits<{
  navigate: [taskId: string]
}>()

const router = useRouter()

// Reactive countdown
const currentTime = ref(Date.now())
const updateInterval = ref<number>()

const timeRemaining = computed(() => {
  if (!props.lockTask?.time_remaining_ms || props.lockTask.is_expired) {
    return 0
  }

  // Calculate time remaining based on current time and end time
  if (props.lockTask.end_time) {
    const endTime = new Date(props.lockTask.end_time).getTime()
    const remaining = endTime - currentTime.value
    return Math.max(0, remaining)
  }

  return props.lockTask.time_remaining_ms
})

const handleClick = (event: Event) => {
  if (!props.lockTask?.id) return

  // Prevent event bubbling
  event.stopPropagation()

  const taskId = props.lockTask.id
  console.log(`LockStatus: Requesting navigation to task detail page for task ${taskId}`)

  // Emit navigation event first (allows parent components like modals to close)
  emit('navigate', taskId)

  // Use longer delay and force navigation with replace
  setTimeout(() => {
    console.log(`LockStatus: Navigating to task detail page for task ${taskId}`)
    // Use replace to force a fresh navigation
    router.replace({ name: 'task-detail', params: { id: taskId } })
      .then(() => {
        console.log(`LockStatus: Navigation completed to task ${taskId}`)
      })
      .catch((error) => {
        console.error('LockStatus: Navigation failed:', error)
        // Fallback: try push if replace fails
        router.push({ name: 'task-detail', params: { id: taskId } })
      })
  }, 200)
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

const formatTimeRemaining = (milliseconds: number) => {
  if (milliseconds <= 0) return '已结束'

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

const formatDuration = (durationMinutes: number, durationType?: string, durationMax?: number) => {
  const hours = Math.floor(durationMinutes / 60)
  const minutes = durationMinutes % 60

  if (durationType === 'random' && durationMax) {
    const maxHours = Math.floor(durationMax / 60)
    const maxMinutes = durationMax % 60
    return `${hours}小时${minutes}分钟 - ${maxHours}小时${maxMinutes}分钟`
  }

  return `${hours}小时${minutes}分钟`
}

const startCountdown = () => {
  if (updateInterval.value) {
    clearInterval(updateInterval.value)
  }

  updateInterval.value = window.setInterval(() => {
    currentTime.value = Date.now()
  }, 1000)
}

onMounted(() => {
  if (props.lockTask && !props.lockTask.is_expired) {
    startCountdown()
  }
})

onUnmounted(() => {
  if (updateInterval.value) {
    clearInterval(updateInterval.value)
  }
})

// Watch for changes to lockTask prop and restart countdown if needed
watch(
  () => props.lockTask,
  (newTask, oldTask) => {
    // If task changed or end_time changed, restart countdown
    if (newTask && !newTask.is_expired) {
      // Check if this is a new task or if the end_time has changed
      const hasChanged = !oldTask ||
                        newTask.id !== oldTask.id ||
                        newTask.end_time !== oldTask.end_time

      if (hasChanged) {
        console.log('LockStatus: Task data changed, restarting countdown', {
          oldEndTime: oldTask?.end_time,
          newEndTime: newTask.end_time,
          taskId: newTask.id
        })
        // Update current time immediately to reflect new countdown
        currentTime.value = Date.now()
        startCountdown()
      }
    } else if (!newTask || newTask.is_expired) {
      // Stop countdown if no task or task expired
      if (updateInterval.value) {
        clearInterval(updateInterval.value)
        updateInterval.value = undefined
      }
    }
  },
  { deep: true }
)
</script>

<style scoped>
.lock-status-link {
  text-decoration: none;
  color: inherit;
  display: block;
  transition: all 0.2s ease;
  cursor: pointer;
}

.lock-status-link:hover .lock-status {
  transform: translateY(-2px);
  box-shadow: 6px 6px 0 #000;
}

.lock-status {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  background: linear-gradient(135deg, #ff6b6b, #ee5a24);
  border-radius: 8px;
  border: 2px solid #000;
  box-shadow: 4px 4px 0 #000;
  color: white;
  position: relative;
  overflow: hidden;
  cursor: pointer;
}

.lock-status.is-expired {
  background: linear-gradient(135deg, #28a745, #20c997);
  animation: pulse-ready 2s infinite;
}

.lock-icon {
  font-size: 2rem;
  flex-shrink: 0;
}

.lock-info {
  flex: 1;
  min-width: 0;
}

.lock-title {
  font-weight: bold;
  font-size: 1.1rem;
  margin-bottom: 0.25rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.lock-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  margin-bottom: 0.5rem;
}

.difficulty {
  padding: 0.125rem 0.5rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: bold;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.difficulty.easy {
  background-color: rgba(255, 255, 255, 0.3);
}

.difficulty.normal {
  background-color: rgba(255, 193, 7, 0.8);
  color: #212529;
}

.difficulty.hard {
  background-color: rgba(253, 126, 20, 0.8);
}

.difficulty.hell {
  background-color: rgba(220, 53, 69, 0.8);
}

.separator {
  opacity: 0.7;
}

.countdown {
  font-weight: bold;
  font-family: 'Courier New', monospace;
}

.countdown.expired {
  animation: pulse-danger 1s infinite;
}

.time-hidden {
  color: rgba(255, 255, 255, 0.9);
  font-style: italic;
}

.duration-info {
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.8);
  margin-top: 0.25rem;
}

.lock-actions {
  margin-top: 0.5rem;
}

.complete-hint {
  display: inline-block;
  padding: 0.5rem 1rem;
  background-color: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 20px;
  color: white;
  text-decoration: none;
  font-size: 0.875rem;
  font-weight: 500;
  transition: all 0.2s ease;
}

.complete-hint:hover {
  background-color: rgba(255, 255, 255, 0.3);
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.click-hint {
  display: inline-block;
  padding: 0.5rem 1rem;
  background-color: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 20px;
  color: rgba(255, 255, 255, 0.9);
  font-size: 0.875rem;
  font-weight: 500;
  margin-top: 0.5rem;
}

.no-lock-status {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  background: linear-gradient(135deg, #f8f9fa, #e9ecef);
  border-radius: 8px;
  border: 2px solid #dee2e6;
  color: #6c757d;
}

.free-icon {
  font-size: 2rem;
  flex-shrink: 0;
}

.free-text {
  font-weight: 500;
}

@keyframes pulse-ready {
  0% {
    opacity: 1;
  }
  50% {
    opacity: 0.8;
  }
  100% {
    opacity: 1;
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

/* Size variants */
.lock-status.size-small {
  padding: 0.75rem;
  gap: 0.75rem;
}

.lock-status.size-small .lock-icon {
  font-size: 1.5rem;
}

.lock-status.size-small .lock-title {
  font-size: 1rem;
}

.lock-status.size-small .lock-meta {
  font-size: 0.75rem;
}

.lock-status.size-large {
  padding: 1.5rem;
  gap: 1.5rem;
}

.lock-status.size-large .lock-icon {
  font-size: 2.5rem;
}

.lock-status.size-large .lock-title {
  font-size: 1.25rem;
}

.lock-status.size-large .lock-meta {
  font-size: 1rem;
}

/* Mobile responsive */
@media (max-width: 768px) {
  .lock-status {
    padding: 0.75rem;
    gap: 0.75rem;
  }

  .lock-icon {
    font-size: 1.5rem;
  }

  .lock-title {
    font-size: 1rem;
  }

  .lock-meta {
    font-size: 0.75rem;
    flex-wrap: wrap;
  }

  .complete-hint {
    padding: 0.375rem 0.75rem;
    font-size: 0.75rem;
  }
}
</style>