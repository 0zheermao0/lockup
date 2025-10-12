<template>
  <div
    v-if="shouldShowIndicator"
    class="lock-indicator"
    :class="[
      indicatorType,
      size,
      { 'with-time': showTime && timeRemaining > 0, 'clickable': isClickable }
    ]"
    :title="clickableTooltipText"
    @click="handleClick"
  >
    <span class="lock-icon">{{ lockIcon }}</span>
    <span v-if="showTime && timeRemaining > 0" class="time-text">
      {{ formatTimeShort(timeRemaining) }}
    </span>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { authApi } from '../lib/api'
import type { User } from '../types'

interface Props {
  userId?: number
  user?: User
  size?: 'mini' | 'small' | 'normal'
  showTime?: boolean
  refreshInterval?: number
}

const props = withDefaults(defineProps<Props>(), {
  size: 'small',
  showTime: false,
  refreshInterval: 30000 // 30 seconds default
})

// Router
const router = useRouter()

// State
const currentTime = ref(Date.now())
const userLockTask = ref<any>(null)
const loading = ref(false)
const updateInterval = ref<number>()

// Computed properties
const shouldShowIndicator = computed(() => {
  // Show indicator if user has an active lock task
  // Check both status field (from task API) and is_expired field (from user profile API)
  if (!userLockTask.value) return false

  // If it has a status field, check if it's active
  if (userLockTask.value.status) {
    return userLockTask.value.status === 'active'
  }

  // If no status field, check if it's not expired (from user profile API)
  if (userLockTask.value.hasOwnProperty('is_expired')) {
    return !userLockTask.value.is_expired
  }

  // Default: assume active if task exists
  return true
})

const indicatorType = computed(() => {
  if (!userLockTask.value) return 'unlocked'

  // Check if task is active (either by status field or not expired)
  const isActive = userLockTask.value.status === 'active' ||
                  (userLockTask.value.hasOwnProperty('is_expired') && !userLockTask.value.is_expired)

  if (isActive) {
    // Check if time is running out (less than 30 minutes)
    if (timeRemaining.value > 0 && timeRemaining.value < 30 * 60 * 1000) {
      return 'locked-urgent'
    }
    return 'locked'
  }

  return 'unlocked'
})

const timeRemaining = computed(() => {
  if (!userLockTask.value || !userLockTask.value.end_time) return 0

  const endTime = new Date(userLockTask.value.end_time).getTime()
  const now = currentTime.value
  return Math.max(0, endTime - now)
})

const lockIcon = computed(() => {
  switch (indicatorType.value) {
    case 'locked':
      return '🔒'
    case 'locked-urgent':
      return '⏰'
    default:
      return ''
  }
})

const tooltipText = computed(() => {
  if (!userLockTask.value) return ''

  // Check if task is active (either by status field or not expired)
  const isActive = userLockTask.value.status === 'active' ||
                  (userLockTask.value.hasOwnProperty('is_expired') && !userLockTask.value.is_expired)

  if (isActive) {
    const timeText = timeRemaining.value > 0
      ? `剩余 ${formatTimeShort(timeRemaining.value)}`
      : '时间已到'
    return `${userLockTask.value.title} - ${timeText}`
  }

  return ''
})

// Check if the indicator should be clickable
const isClickable = computed(() => {
  return userLockTask.value && userLockTask.value.id && shouldShowIndicator.value
})

// Enhanced tooltip with click instruction
const clickableTooltipText = computed(() => {
  const baseTooltip = tooltipText.value
  if (isClickable.value && baseTooltip) {
    return `${baseTooltip}\n\n点击查看任务详情`
  }
  return baseTooltip
})

// Methods
const formatTimeShort = (milliseconds: number): string => {
  const hours = Math.floor(milliseconds / (1000 * 60 * 60))
  const minutes = Math.floor((milliseconds % (1000 * 60 * 60)) / (1000 * 60))

  if (hours > 0) {
    return `${hours}h${minutes}m`
  } else if (minutes > 0) {
    return `${minutes}m`
  } else {
    const seconds = Math.floor((milliseconds % (1000 * 60)) / 1000)
    return `${seconds}s`
  }
}

const handleClick = (event: Event) => {
  if (!isClickable.value) return

  // Prevent event bubbling
  event.stopPropagation()

  // Navigate to task detail page
  const taskId = userLockTask.value.id
  if (taskId) {
    console.log(`LockIndicator: Navigating to task detail page for task ${taskId}`)
    router.push({ name: 'task-detail', params: { id: taskId } })
  }
}

const fetchUserLockStatus = async () => {
  if (loading.value) return

  // If user object is provided and has active_lock_task, use it
  if (props.user?.active_lock_task) {
    console.log(`LockIndicator: User ${props.user.username} has active_lock_task:`, props.user.active_lock_task)
    userLockTask.value = props.user.active_lock_task
    return
  }

  // For debugging: log when user doesn't have active_lock_task
  if (props.user) {
    console.log(`LockIndicator: User ${props.user.username} has no active_lock_task field. User object:`, props.user)
  }

  // If user has an ID but no lock task data, and it's the current user,
  // try to get lock status from authStore
  if (props.user?.id && !props.user.active_lock_task) {
    // Import authStore to check if this user is the current user
    try {
      const { useAuthStore } = await import('../stores/auth')
      const authStore = useAuthStore()

      // If this is the current user, use their lock task from authStore
      if (authStore.user?.id === props.user.id && authStore.user?.active_lock_task) {
        console.log(`LockIndicator: Using current user's lock task from authStore:`, authStore.user.active_lock_task)
        userLockTask.value = authStore.user.active_lock_task
        return
      }
    } catch (error) {
      console.error('Error accessing authStore:', error)
    }
  }

  // For other users, we'd need an API endpoint to get their lock status
  // For now, just log that we don't have the data
  if (props.user && props.user.id) {
    console.log(`LockIndicator: No lock status available for user ${props.user.username} (ID: ${props.user.id})`)
  }
}

const startRealTimeUpdates = () => {
  if (updateInterval.value) return

  updateInterval.value = window.setInterval(() => {
    currentTime.value = Date.now()

    // Refresh user lock status periodically
    if (props.refreshInterval > 0) {
      fetchUserLockStatus()
    }
  }, 1000) // Update every second for real-time countdown
}

const stopRealTimeUpdates = () => {
  if (updateInterval.value) {
    clearInterval(updateInterval.value)
    updateInterval.value = undefined
  }
}

// Lifecycle
onMounted(() => {
  fetchUserLockStatus()
  startRealTimeUpdates()
})

onUnmounted(() => {
  stopRealTimeUpdates()
})

// Watch for user changes
import { watch } from 'vue'
watch(() => props.user, () => {
  fetchUserLockStatus()
}, { deep: true })
</script>

<style scoped>
.lock-indicator {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.125rem 0.25rem;
  border-radius: 4px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border: 2px solid #000;
  box-shadow: 2px 2px 0 #000;
  font-size: 0.625rem;
  line-height: 1;
  transition: all 0.2s ease;
}

/* Size variants */
.lock-indicator.mini {
  padding: 0.0625rem 0.125rem;
  font-size: 0.5rem;
  border-width: 1px;
  box-shadow: 1px 1px 0 #000;
}

.lock-indicator.mini .lock-icon {
  font-size: 0.625rem;
}

.lock-indicator.small {
  padding: 0.125rem 0.25rem;
  font-size: 0.625rem;
}

.lock-indicator.normal {
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
}

/* Type variants */
.lock-indicator.locked {
  background: linear-gradient(135deg, #dc3545, #c82333);
  color: white;
  animation: pulse-locked 3s infinite;
}

.lock-indicator.locked-urgent {
  background: linear-gradient(135deg, #fd7e14, #e76500);
  color: white;
  animation: pulse-urgent 1s infinite;
}

.lock-indicator.unlocked {
  background: linear-gradient(135deg, #28a745, #218838);
  color: white;
}

/* With time display */
.lock-indicator.with-time {
  gap: 0.375rem;
}

.lock-indicator.with-time.mini {
  gap: 0.25rem;
}

.lock-indicator.with-time.normal {
  gap: 0.5rem;
}

/* Icon styles */
.lock-icon {
  display: inline-block;
  line-height: 1;
}

.time-text {
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', monospace;
  font-weight: 900;
  white-space: nowrap;
}

/* Animations */
@keyframes pulse-locked {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.8;
    transform: scale(0.98);
  }
}

@keyframes pulse-urgent {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
    box-shadow: 2px 2px 0 #000;
  }
  50% {
    opacity: 0.9;
    transform: scale(1.05);
    box-shadow: 3px 3px 0 #000;
  }
}

/* Clickable styles */
.lock-indicator.clickable {
  cursor: pointer;
  transition: all 0.2s ease;
}

.lock-indicator.clickable:hover {
  transform: translate(-1px, -1px);
  box-shadow: 3px 3px 0 #000;
}

.lock-indicator.clickable.mini:hover {
  box-shadow: 2px 2px 0 #000;
}

.lock-indicator.clickable:active {
  transform: translate(0, 0);
  box-shadow: 2px 2px 0 #000;
}

.lock-indicator.clickable.mini:active {
  box-shadow: 1px 1px 0 #000;
}

/* Hover effects for non-clickable indicators */
.lock-indicator:not(.clickable):hover {
  transform: translate(-1px, -1px);
  box-shadow: 3px 3px 0 #000;
}

.lock-indicator:not(.clickable).mini:hover {
  box-shadow: 2px 2px 0 #000;
}

/* Mobile responsive */
@media (max-width: 768px) {
  .lock-indicator {
    font-size: 0.5rem;
    padding: 0.0625rem 0.125rem;
  }

  .lock-indicator.normal {
    font-size: 0.625rem;
    padding: 0.125rem 0.25rem;
  }

  .time-text {
    display: none; /* Hide time text on mobile for space */
  }
}
</style>