<template>
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="isVisible"
        class="modal-overlay"
        :class="overlayClass"
        @click="handleOverlayClick"
      >
        <div
          class="action-modal"
          :class="[modalClass, sizeClass]"
          @click.stop
        >
          <!-- Header -->
          <div class="modal-header" :class="headerClass">
            <div class="modal-header-content">
              <span v-if="icon" class="modal-icon">{{ icon }}</span>
              <h3 class="modal-title">{{ title }}</h3>
            </div>
            <button
              v-if="showCloseButton"
              class="modal-close"
              @click="handleClose"
              aria-label="关闭"
            >
              ×
            </button>
          </div>

          <!-- Body -->
          <div class="modal-body" :class="bodyClass">
            <slot name="body">
              <p v-if="message" class="modal-message">{{ message }}</p>
            </slot>
          </div>

          <!-- Footer -->
          <div v-if="$slots.footer || showDefaultFooter" class="modal-footer" :class="footerClass">
            <slot name="footer">
              <button
                v-if="showCancelButton"
                class="modal-btn secondary"
                @click="handleClose"
              >
                {{ cancelText }}
              </button>
              <button
                v-if="showConfirmButton"
                class="modal-btn primary"
                :disabled="confirmDisabled || isProcessing"
                @click="handleConfirm"
              >
                <span v-if="isProcessing">{{ processingText }}</span>
                <span v-else>{{ confirmText }}</span>
              </button>
            </slot>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, watch, onMounted, onUnmounted } from 'vue'

interface Props {
  /** Control modal visibility */
  isVisible: boolean
  /** Modal title */
  title: string
  /** Optional icon to display before title */
  icon?: string
  /** Message to display in body (can use slot instead) */
  message?: string
  /** Modal size variant */
  size?: 'small' | 'medium' | 'large' | 'full'
  /** Whether to show close button */
  showCloseButton?: boolean
  /** Whether to show default footer with cancel/confirm buttons */
  showDefaultFooter?: boolean
  /** Whether to show cancel button in default footer */
  showCancelButton?: boolean
  /** Whether to show confirm button in default footer */
  showConfirmButton?: boolean
  /** Text for cancel button */
  cancelText?: string
  /** Text for confirm button */
  confirmText?: string
  /** Text to show when processing */
  processingText?: string
  /** Whether confirm button is disabled */
  confirmDisabled?: boolean
  /** Whether action is processing */
  isProcessing?: boolean
  /** Whether to close on overlay click */
  closeOnOverlayClick?: boolean
  /** Whether to close on escape key */
  closeOnEscape?: boolean
  /** Custom overlay class */
  overlayClass?: string
  /** Custom modal class */
  modalClass?: string
  /** Custom header class */
  headerClass?: string
  /** Custom body class */
  bodyClass?: string
  /** Custom footer class */
  footerClass?: string
}

const props = withDefaults(defineProps<Props>(), {
  size: 'medium',
  showCloseButton: true,
  showDefaultFooter: true,
  showCancelButton: true,
  showConfirmButton: true,
  cancelText: '取消',
  confirmText: '确认',
  processingText: '处理中...',
  confirmDisabled: false,
  isProcessing: false,
  closeOnOverlayClick: true,
  closeOnEscape: true,
  icon: '',
  message: '',
  overlayClass: '',
  modalClass: '',
  headerClass: '',
  bodyClass: '',
  footerClass: ''
})

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'confirm'): void
  (e: 'update:isVisible', value: boolean): void
}>()

// Size class mapping
const sizeClass = computed(() => {
  const sizeMap = {
    small: 'modal-small',
    medium: 'modal-medium',
    large: 'modal-large',
    full: 'modal-full'
  }
  return sizeMap[props.size]
})

// Handle close action
const handleClose = () => {
  emit('close')
  emit('update:isVisible', false)
}

// Handle confirm action
const handleConfirm = () => {
  if (props.isProcessing || props.confirmDisabled) return
  emit('confirm')
}

// Handle overlay click
const handleOverlayClick = () => {
  if (props.closeOnOverlayClick && !props.isProcessing) {
    handleClose()
  }
}

// Handle escape key
const handleEscapeKey = (e: KeyboardEvent) => {
  if (e.key === 'Escape' && props.closeOnEscape && !props.isProcessing) {
    handleClose()
  }
}

// Lock body scroll when modal is open
watch(() => props.isVisible, (isVisible) => {
  if (typeof document !== 'undefined') {
    if (isVisible) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
  }
}, { immediate: true })

// Add/remove escape key listener
onMounted(() => {
  if (props.closeOnEscape) {
    document.addEventListener('keydown', handleEscapeKey)
  }
})

onUnmounted(() => {
  if (props.closeOnEscape) {
    document.removeEventListener('keydown', handleEscapeKey)
  }
  // Ensure body scroll is restored
  if (typeof document !== 'undefined') {
    document.body.style.overflow = ''
  }
})
</script>

<style scoped>
/* Modal Overlay */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  padding: 1rem;
  overflow: hidden;
}

/* Modal Container */
.action-modal {
  background: white;
  border: 4px solid #000;
  border-radius: 12px;
  box-shadow: 8px 8px 0 #000;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  max-height: 90vh;
  animation: modal-pop 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

/* Size variants */
.modal-small {
  max-width: 360px;
  width: 90%;
}

.modal-medium {
  max-width: 480px;
  width: 90%;
}

.modal-large {
  max-width: 640px;
  width: 95%;
}

.modal-full {
  max-width: 100%;
  width: 95%;
  height: 90vh;
}

/* Modal Header */
.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1.25rem;
  background: linear-gradient(135deg, #007bff, #0056b3);
  color: white;
  border-bottom: 3px solid #000;
}

.modal-header-content {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex: 1;
  min-width: 0;
}

.modal-icon {
  font-size: 1.5rem;
  flex-shrink: 0;
}

.modal-title {
  font-size: 1.1rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.modal-close {
  background: rgba(0, 0, 0, 0.2);
  border: 2px solid #000;
  border-radius: 50%;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-weight: 900;
  font-size: 1.5rem;
  line-height: 1;
  color: inherit;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.modal-close:hover {
  background: rgba(0, 0, 0, 0.3);
  transform: scale(1.1);
}

/* Modal Body */
.modal-body {
  padding: 1.5rem;
  overflow-y: auto;
  flex: 1;
  background: white;
}

.modal-message {
  font-size: 1rem;
  line-height: 1.6;
  color: #333;
  margin: 0;
}

/* Modal Footer */
.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  padding: 1rem 1.5rem;
  background: linear-gradient(135deg, #f8f9fa, #e9ecef);
  border-top: 3px solid #000;
}

/* Buttons */
.modal-btn {
  padding: 0.75rem 1.5rem;
  font-size: 0.9rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border: 3px solid #000;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 3px 3px 0 #000;
  min-width: 100px;
}

.modal-btn:hover:not(:disabled) {
  transform: translate(-1px, -1px);
  box-shadow: 4px 4px 0 #000;
}

.modal-btn:active:not(:disabled) {
  transform: translate(1px, 1px);
  box-shadow: 1px 1px 0 #000;
}

.modal-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
  box-shadow: 3px 3px 0 #000;
}

.modal-btn.primary {
  background: linear-gradient(135deg, #28a745, #218838);
  color: white;
}

.modal-btn.primary:hover:not(:disabled) {
  background: linear-gradient(135deg, #218838, #1e7e34);
}

.modal-btn.secondary {
  background: linear-gradient(135deg, #6c757d, #5a6268);
  color: white;
}

.modal-btn.secondary:hover:not(:disabled) {
  background: linear-gradient(135deg, #5a6268, #495057);
}

.modal-btn.danger {
  background: linear-gradient(135deg, #dc3545, #c82333);
  color: white;
}

.modal-btn.danger:hover:not(:disabled) {
  background: linear-gradient(135deg, #c82333, #bd2130);
}

/* Modal Transitions */
.modal-enter-active,
.modal-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .action-modal,
.modal-leave-to .action-modal {
  transform: scale(0.9) translateY(-20px);
  opacity: 0;
}

/* Animations */
@keyframes modal-pop {
  0% {
    transform: scale(0.8) rotate(-1deg);
    opacity: 0;
  }
  50% {
    transform: scale(1.02) rotate(0.5deg);
  }
  100% {
    transform: scale(1) rotate(0deg);
    opacity: 1;
  }
}

/* Mobile Responsive */
@media (max-width: 768px) {
  .modal-overlay {
    align-items: flex-end;
    padding: 0;
    padding-bottom: env(safe-area-inset-bottom, 0);
  }

  .action-modal {
    width: 100%;
    max-width: 100%;
    max-height: 85vh;
    border-radius: 20px 20px 0 0;
    border-width: 3px 3px 0 3px;
    box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.3);
    animation: modal-slide-up 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
  }

  .modal-small,
  .modal-medium,
  .modal-large,
  .modal-full {
    max-width: 100%;
    width: 100%;
  }

  .modal-header {
    padding: 1rem 1.25rem;
    position: relative;
  }

  /* Drag handle for mobile */
  .modal-header::before {
    content: '';
    position: absolute;
    top: 0.5rem;
    left: 50%;
    transform: translateX(-50%);
    width: 40px;
    height: 4px;
    background: rgba(0, 0, 0, 0.2);
    border-radius: 2px;
  }

  .modal-title {
    font-size: 1rem;
    margin-top: 0.5rem;
  }

  .modal-icon {
    font-size: 1.25rem;
    margin-top: 0.5rem;
  }

  .modal-body {
    padding: 1.25rem;
    max-height: 60vh;
  }

  .modal-footer {
    flex-direction: column;
    gap: 0.75rem;
    padding: 1rem 1.25rem;
    padding-bottom: calc(1rem + env(safe-area-inset-bottom, 0));
  }

  .modal-btn {
    width: 100%;
    padding: 1rem;
    font-size: 1rem;
  }

  @keyframes modal-slide-up {
    0% {
      transform: translateY(100%);
      opacity: 0;
    }
    100% {
      transform: translateY(0);
      opacity: 1;
    }
  }
}

/* Reduced motion preference */
@media (prefers-reduced-motion: reduce) {
  .action-modal {
    animation: none;
  }

  .modal-enter-active,
  .modal-leave-active {
    transition: opacity 0.2s ease;
  }

  .modal-enter-from .action-modal,
  .modal-leave-to .action-modal {
    transform: none;
  }

  .modal-btn:hover {
    transform: none;
  }
}
</style>
