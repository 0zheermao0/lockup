<template>
  <button
    class="mobile-action-btn"
    :class="{
      'is-processing': isProcessing,
      'is-touch': isTouchDevice,
      [`btn-${variant}`]: true
    }"
    :disabled="disabled || isProcessing"
    @touchstart="handleTouchStart"
    @touchend="handleTouchEnd"
    @click="handleClick"
  >
    <span v-if="isProcessing" class="btn-spinner">
      <svg class="spinner-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
        <circle cx="12" cy="12" r="10" stroke-width="2" opacity="0.25" />
        <path d="M12 2a10 10 0 0 1 10 10" stroke-width="2" stroke-linecap="round" />
      </svg>
    </span>
    <span class="btn-content" :class="{ 'is-hidden': isProcessing }">
      <slot />
    </span>
  </button>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

interface Props {
  /** Disable the button */
  disabled?: boolean
  /** Show processing state */
  processing?: boolean
  /** Button variant */
  variant?: 'primary' | 'secondary' | 'danger' | 'success' | 'warning'
  /** Prevent default on touch events */
  preventDefault?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  disabled: false,
  processing: false,
  variant: 'primary',
  preventDefault: true
})

const emit = defineEmits<{
  (e: 'action'): void
  (e: 'touchstart', event: TouchEvent): void
  (e: 'touchend', event: TouchEvent): void
  (e: 'click', event: MouseEvent): void
}>()

// State
const isProcessing = ref(props.processing)
const isTouchDevice = ref(false)
let touchStarted = false
let touchEndTimeout: number | null = null
let clickPrevented = false

// Check if device supports touch
onMounted(() => {
  isTouchDevice.value = 'ontouchstart' in window || navigator.maxTouchPoints > 0
})

/**
 * Handle touch start event
 * Prevents default to avoid double-firing with click
 */
const handleTouchStart = (e: TouchEvent) => {
  touchStarted = true

  if (props.preventDefault) {
    // Don't prevent default immediately to allow scrolling
    // Only prevent if we're sure it's a tap
  }

  emit('touchstart', e)
}

/**
 * Handle touch end event
 * Triggers the action after a small delay to ensure it's a tap not a scroll
 */
const handleTouchEnd = (e: TouchEvent) => {
  if (!touchStarted) return

  touchStarted = false

  if (props.preventDefault) {
    e.preventDefault()
  }

  emit('touchend', e)

  // Clear any existing timeout
  if (touchEndTimeout) {
    clearTimeout(touchEndTimeout)
  }

  // Mark that touch was handled to prevent subsequent click event
  clickPrevented = true

  // Small delay to separate from click event and ensure DOM is ready
  touchEndTimeout = window.setTimeout(() => {
    if (!props.disabled && !isProcessing.value) {
      emit('action')
    }
    // Reset clickPrevented after click would have fired (300ms is the typical touch delay)
    window.setTimeout(() => {
      clickPrevented = false
    }, 350)
  }, 10)
}

/**
 * Handle click event
 * Ignored on touch devices to prevent double-firing
 */
const handleClick = (e: MouseEvent) => {
  // On touch devices, ignore click if touch was handled
  if (isTouchDevice.value && clickPrevented) {
    e.preventDefault()
    e.stopPropagation()
    return
  }

  emit('click', e)

  if (!props.disabled && !isProcessing.value) {
    emit('action')
  }
}

// Expose processing state for parent control
defineExpose({
  isProcessing,
  setProcessing: (value: boolean) => {
    isProcessing.value = value
  }
})
</script>

<style scoped>
.mobile-action-btn {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  font-size: 0.85rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border: 3px solid #000;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
  box-shadow: 3px 3px 0 #000;
  min-width: 80px;
  min-height: 40px;
  white-space: nowrap;
  -webkit-tap-highlight-color: transparent;
  touch-action: manipulation;
  user-select: none;
  -webkit-user-select: none;
}

/* Prevent text selection on mobile */
.mobile-action-btn * {
  user-select: none;
  -webkit-user-select: none;
}

/* Variant styles */
.btn-primary {
  background: linear-gradient(135deg, #28a745, #218838);
  color: white;
}

.btn-secondary {
  background: linear-gradient(135deg, #6c757d, #5a6268);
  color: white;
}

.btn-danger {
  background: linear-gradient(135deg, #dc3545, #c82333);
  color: white;
}

.btn-success {
  background: linear-gradient(135deg, #28a745, #218838);
  color: white;
}

.btn-warning {
  background: linear-gradient(135deg, #ffc107, #fd7e14);
  color: #000;
}

/* Hover effects - only on non-touch devices */
@media (hover: hover) {
  .mobile-action-btn:hover:not(:disabled) {
    transform: translate(-2px, -2px);
    box-shadow: 5px 5px 0 #000;
  }
}

/* Active/pressed state */
.mobile-action-btn:active:not(:disabled) {
  transform: translate(1px, 1px);
  box-shadow: 1px 1px 0 #000;
}

/* Disabled state */
.mobile-action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
  box-shadow: 3px 3px 0 #000;
}

/* Processing state */
.mobile-action-btn.is-processing {
  cursor: wait;
}

/* Button content */
.btn-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  transition: opacity 0.2s ease;
}

.btn-content.is-hidden {
  opacity: 0;
}

/* Spinner */
.btn-spinner {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.spinner-icon {
  width: 20px;
  height: 20px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* Touch device optimizations */
@media (pointer: coarse) {
  .mobile-action-btn {
    min-height: 48px; /* Larger touch target for coarse pointers */
    padding: 0.875rem 1.5rem;
  }

  /* Remove hover effects on touch devices */
  .mobile-action-btn:hover {
    transform: none;
    box-shadow: 3px 3px 0 #000;
  }

  /* Enhance active state feedback */
  .mobile-action-btn:active:not(:disabled) {
    transform: scale(0.98);
    box-shadow: 1px 1px 0 #000;
  }
}

/* Mobile responsive */
@media (max-width: 768px) {
  .mobile-action-btn {
    width: 100%;
    min-height: 48px;
    font-size: 1rem;
    padding: 1rem;
  }
}

/* Reduced motion preference */
@media (prefers-reduced-motion: reduce) {
  .mobile-action-btn {
    transition: none;
  }

  .spinner-icon {
    animation: none;
    opacity: 0.5;
  }
}
</style>
