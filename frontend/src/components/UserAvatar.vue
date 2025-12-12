<template>
  <div
    :class="[
      'user-avatar',
      sizeClass,
      { 'clickable': clickable }
    ]"
    @click="handleClick"
    :title="title"
  >
    <!-- User Avatar Image -->
    <img
      v-if="user?.avatar"
      :src="user.avatar"
      :alt="user.username || 'User Avatar'"
      class="avatar-image"
      @error="handleImageError"
    />

    <!-- Fallback Initial Avatar -->
    <div
      v-else
      class="avatar-fallback"
      :style="{ background: avatarGradient }"
    >
      {{ avatarInitial }}
    </div>

    <!-- Lock Indicator (if user has active lock task) -->
    <LockIndicator
      v-if="showLockIndicator && user?.active_lock_task"
      :user="user"
      :size="lockIndicatorSize"
      :show-time="false"
      class="avatar-lock-indicator"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import LockIndicator from './LockIndicator.vue'
import type { User } from '../types'

interface Props {
  user?: User | null
  size?: 'mini' | 'small' | 'normal' | 'large' | 'xl'
  clickable?: boolean
  showLockIndicator?: boolean
  title?: string
}

const props = withDefaults(defineProps<Props>(), {
  size: 'normal',
  clickable: false,
  showLockIndicator: true
})

const emit = defineEmits<{
  click: []
}>()

// Computed properties
const avatarInitial = computed(() => {
  if (!props.user?.username) return 'U'
  return props.user.username.charAt(0).toUpperCase()
})

const sizeClass = computed(() => `avatar-${props.size}`)

const lockIndicatorSize = computed(() => {
  const sizeMap = {
    mini: 'mini',
    small: 'mini',
    normal: 'small',
    large: 'normal',
    xl: 'normal'
  }
  return sizeMap[props.size] as 'mini' | 'small' | 'normal'
})

// Generate consistent gradient based on username
const avatarGradient = computed(() => {
  if (!props.user?.username) {
    return 'linear-gradient(135deg, #667eea, #764ba2)'
  }

  const username = props.user.username
  const gradients = [
    'linear-gradient(135deg, #667eea, #764ba2)',
    'linear-gradient(135deg, #f093fb, #f5576c)',
    'linear-gradient(135deg, #4facfe, #00f2fe)',
    'linear-gradient(135deg, #43e97b, #38f9d7)',
    'linear-gradient(135deg, #fa709a, #fee140)',
    'linear-gradient(135deg, #a8edea, #fed6e3)',
    'linear-gradient(135deg, #ff9a9e, #fecfef)',
    'linear-gradient(135deg, #ffecd2, #fcb69f)',
    'linear-gradient(135deg, #a18cd1, #fbc2eb)',
    'linear-gradient(135deg, #fad0c4, #ffd1ff)'
  ]

  // Simple hash function to get consistent gradient based on username
  let hash = 0
  for (let i = 0; i < username.length; i++) {
    const char = username.charCodeAt(i)
    hash = ((hash << 5) - hash) + char
    hash = hash & hash // Convert to 32-bit integer
  }

  const index = Math.abs(hash) % gradients.length
  return gradients[index]
})

// Methods
const handleClick = () => {
  if (props.clickable) {
    emit('click')
  }
}

const handleImageError = (event: Event) => {
  // Hide the broken image and show fallback
  const img = event.target as HTMLImageElement
  img.style.display = 'none'
}
</script>

<style scoped>
.user-avatar {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  border: 2px solid #000;
  box-shadow: 2px 2px 0 rgba(0, 0, 0, 0.2);
  transition: all 0.2s ease;
  overflow: visible;
  flex-shrink: 0;
}

.user-avatar.clickable {
  cursor: pointer;
}

.user-avatar.clickable:hover {
  transform: translateY(-1px);
  box-shadow: 3px 3px 0 rgba(0, 0, 0, 0.3);
}

/* Size variants */
.avatar-mini {
  width: 24px;
  height: 24px;
  border-width: 1px;
}

.avatar-small {
  width: 32px;
  height: 32px;
  border-width: 2px;
}

.avatar-normal {
  width: 40px;
  height: 40px;
  border-width: 2px;
}

.avatar-large {
  width: 80px;
  height: 80px;
  border-width: 3px;
}

.avatar-xl {
  width: 120px;
  height: 120px;
  border-width: 3px;
}

/* Avatar image */
.avatar-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 50%;
  overflow: hidden;
}

/* Fallback avatar */
.avatar-fallback {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: 900;
  text-transform: uppercase;
  border-radius: 50%;
  overflow: hidden;
}

/* Font sizes for different avatar sizes */
.avatar-mini .avatar-fallback {
  font-size: 0.6rem;
}

.avatar-small .avatar-fallback {
  font-size: 0.75rem;
}

.avatar-normal .avatar-fallback {
  font-size: 1rem;
}

.avatar-large .avatar-fallback {
  font-size: 2rem;
}

.avatar-xl .avatar-fallback {
  font-size: 3rem;
}

/* Lock indicator positioning */
.avatar-lock-indicator {
  position: absolute;
  z-index: 2;
}

.avatar-mini .avatar-lock-indicator {
  top: -4px;
  right: -4px;
}

.avatar-small .avatar-lock-indicator {
  top: -6px;
  right: -6px;
}

.avatar-normal .avatar-lock-indicator {
  top: -6px;
  right: -6px;
}

.avatar-large .avatar-lock-indicator {
  top: -8px;
  right: -8px;
}

.avatar-xl .avatar-lock-indicator {
  top: -8px;
  right: -8px;
}

/* Neo-Brutalism hover effects */
.user-avatar.clickable:hover .avatar-fallback {
  background: linear-gradient(135deg, #f093fb, #f5576c) !important;
}

.user-avatar.clickable:active {
  transform: translateY(0);
  box-shadow: 1px 1px 0 rgba(0, 0, 0, 0.2);
}
</style>