<template>
  <div class="task-status-card" :class="statusClass">
    <div class="status-main">
      <div class="status-badge">
        <span class="status-dot"></span>
        <span class="status-text">{{ statusText }}</span>
      </div>

      <div v-if="showCountdown" class="countdown-display" :class="{ 'urgent': isUrgent }">
        <span class="countdown-icon">⏰</span>
        <span class="countdown-value">{{ formattedTimeRemaining }}</span>
      </div>

      <div v-else-if="taskStatus === 'completed'" class="status-message success">
        <span class="message-icon">🎉</span>
        <span>任务已完成</span>
      </div>

      <div v-else-if="taskStatus === 'failed'" class="status-message danger">
        <span class="message-icon">❌</span>
        <span>任务已失败</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  taskType: 'lock' | 'board'
  taskStatus: string
  timeRemaining?: number // in milliseconds
}

const props = withDefaults(defineProps<Props>(), {
  timeRemaining: 0
})

// Status text mapping
const statusTextMap: Record<string, string> = {
  pending: '待开始',
  active: '进行中',
  voting: '投票期',
  voting_passed: '投票已通过',
  completed: '已完成',
  failed: '已失败',
  open: '开放中',
  taken: '已接取',
  submitted: '已提交'
}

const statusText = computed(() => statusTextMap[props.taskStatus] || props.taskStatus)

// Status class for styling
const statusClass = computed(() => {
  const classes: Record<string, string> = {
    pending: 'status-pending',
    active: 'status-active',
    voting: 'status-voting',
    voting_passed: 'status-voting-passed',
    completed: 'status-completed',
    failed: 'status-failed',
    open: 'status-open',
    taken: 'status-taken',
    submitted: 'status-submitted'
  }
  return classes[props.taskStatus] || 'status-default'
})

// Show countdown for active lock tasks
const showCountdown = computed(() => {
  return props.taskType === 'lock' &&
    (props.taskStatus === 'active' || props.taskStatus === 'voting_passed') &&
    props.timeRemaining !== undefined
})

// Check if time is urgent (less than 10 minutes)
const isUrgent = computed(() => {
  return props.timeRemaining > 0 && props.timeRemaining < 10 * 60 * 1000
})

// Format time remaining
const formattedTimeRemaining = computed(() => {
  const ms = props.timeRemaining
  if (ms <= 0) return '已结束'

  const hours = Math.floor(ms / (1000 * 60 * 60))
  const minutes = Math.floor((ms % (1000 * 60 * 60)) / (1000 * 60))
  const seconds = Math.floor((ms % (1000 * 60)) / 1000)

  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
  }
  return `${minutes}:${seconds.toString().padStart(2, '0')}`
})
</script>

<style scoped>
.task-status-card {
  background: white;
  border: 3px solid #000;
  border-radius: 12px;
  box-shadow: 6px 6px 0 #000;
  padding: 1rem 1.25rem;
  margin-bottom: 1rem;
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  animation: card-enter 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
}

@keyframes card-enter {
  0% {
    opacity: 0;
    transform: translateY(20px) scale(0.98);
  }
  100% {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

/* Status-specific border colors */
.task-status-card.status-active {
  border-color: #10b981;
  box-shadow: 6px 6px 0 #10b981;
}

.task-status-card.status-voting {
  border-color: #8b5cf6;
  box-shadow: 6px 6px 0 #8b5cf6;
}

.task-status-card.status-voting-passed {
  border-color: #10b981;
  box-shadow: 6px 6px 0 #10b981;
}

.task-status-card.status-completed {
  border-color: #64748b;
  box-shadow: 6px 6px 0 #64748b;
}

.task-status-card.status-failed {
  border-color: #ef4444;
  box-shadow: 6px 6px 0 #ef4444;
}

.task-status-card.status-pending,
.task-status-card.status-open {
  border-color: #f59e0b;
  box-shadow: 6px 6px 0 #f59e0b;
}

.status-main {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.status-badge {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: currentColor;
  animation: pulse-dot 2s ease-in-out infinite;
}

.status-active .status-dot {
  background: #10b981;
}

.status-voting .status-dot {
  background: #8b5cf6;
}

.status-voting-passed .status-dot {
  background: #10b981;
}

.status-completed .status-dot {
  background: #64748b;
  animation: none;
}

.status-failed .status-dot {
  background: #ef4444;
  animation: none;
}

.status-pending .status-dot,
.status-open .status-dot {
  background: #f59e0b;
}

@keyframes pulse-dot {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.6;
    transform: scale(1.2);
  }
}

.status-text {
  font-weight: 800;
  font-size: 1rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Countdown Display */
.countdown-display {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: linear-gradient(135deg, #f8fafc, #f1f5f9);
  padding: 0.375rem 0.75rem;
  border: 2px solid #000;
  border-radius: 8px;
  box-shadow: 3px 3px 0 #000;
}

.countdown-display.urgent {
  background: linear-gradient(135deg, #fef2f2, #fee2e2);
  border-color: #ef4444;
  box-shadow: 3px 3px 0 #ef4444;
  animation: urgent-pulse 1s ease-in-out infinite;
}

@keyframes urgent-pulse {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.03);
  }
}

.countdown-icon {
  font-size: 1.1rem;
}

.countdown-value {
  font-family: 'Courier New', monospace;
  font-weight: 900;
  font-size: 1.1rem;
  color: #000;
}

.countdown-display.urgent .countdown-value {
  color: #ef4444;
}

/* Status Messages */
.status-message {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem 0.75rem;
  border: 2px solid #000;
  border-radius: 8px;
  box-shadow: 3px 3px 0 #000;
  font-weight: 700;
  font-size: 0.9rem;
}

.status-message.success {
  background: linear-gradient(135deg, #d1fae5, #a7f3d0);
  color: #065f46;
}

.status-message.danger {
  background: linear-gradient(135deg, #fee2e2, #fecaca);
  color: #991b1b;
}

.message-icon {
  font-size: 1.1rem;
}

/* Responsive */
@media (max-width: 768px) {
  .task-status-card {
    padding: 0.75rem 1rem;
    border-width: 2px;
    box-shadow: 4px 4px 0 #000;
    margin-bottom: 0.75rem;
  }

  .task-status-card.status-active,
  .task-status-card.status-voting,
  .task-status-card.status-voting-passed,
  .task-status-card.status-completed,
  .task-status-card.status-failed,
  .task-status-card.status-pending,
  .task-status-card.status-open {
    box-shadow: 4px 4px 0 currentColor;
  }

  .status-main {
    flex-direction: row;
    gap: 0.5rem;
  }

  .countdown-display {
    padding: 0.25rem 0.5rem;
  }

  .countdown-value {
    font-size: 1rem;
  }

  .countdown-icon {
    font-size: 1rem;
  }

  .status-text {
    font-size: 0.9rem;
  }

  .status-message {
    padding: 0.25rem 0.5rem;
    font-size: 0.85rem;
  }
}
</style>
