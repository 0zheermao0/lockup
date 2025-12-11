<template>
  <div v-if="isVisible" class="overtime-notification-overlay" @click="closeModal">
    <div class="overtime-notification-modal" @click.stop>
      <!-- Header -->
      <div class="notification-header" :class="notificationTypeClass">
        <div class="header-content">
          <div class="notification-icon">{{ notificationIcon }}</div>
          <h3 class="notification-title">{{ notificationTitle }}</h3>
        </div>
        <button @click="closeModal" class="close-btn">×</button>
      </div>

      <!-- Body -->
      <div class="notification-body">
        <div class="message-content">
          <div class="primary-message">{{ primaryMessage }}</div>
          <div v-if="secondaryMessage" class="secondary-message">{{ secondaryMessage }}</div>
        </div>

        <!-- Success specific content -->
        <div v-if="isSuccess && overtimeMinutes" class="success-details">
          <div class="time-display">
            <div class="time-icon">⏰</div>
            <div class="time-info">
              <div class="time-value">+{{ overtimeMinutes }} 分钟</div>
              <div class="time-label">随机加时</div>
            </div>
          </div>
          <div v-if="newEndTime" class="end-time-info">
            <span class="end-time-label">新的结束时间：</span>
            <span class="end-time-value">{{ formatDateTime(newEndTime) }}</span>
          </div>
        </div>

        <!-- Error specific content -->
        <div v-if="!isSuccess && errorCode" class="error-details">
          <div class="error-code">错误代码: {{ errorCode }}</div>
          <div class="error-suggestion">{{ getErrorSuggestion(errorCode) }}</div>
        </div>
      </div>

      <!-- Footer -->
      <div class="notification-footer">
        <button @click="closeModal" class="confirm-btn" :class="buttonClass">
          {{ confirmButtonText }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  isVisible: boolean
  isSuccess: boolean
  primaryMessage: string
  secondaryMessage?: string
  overtimeMinutes?: number
  newEndTime?: string
  errorCode?: string
  autoClose?: boolean
  autoCloseDelay?: number
}

const props = withDefaults(defineProps<Props>(), {
  autoClose: true,
  autoCloseDelay: 3000
})

const emit = defineEmits<{
  close: []
}>()

// Computed properties for styling
const notificationTypeClass = computed(() => {
  return props.isSuccess ? 'success-header' : 'error-header'
})

const notificationIcon = computed(() => {
  return props.isSuccess ? '🎉' : '❌'
})

const notificationTitle = computed(() => {
  return props.isSuccess ? '加时成功！' : '加时失败'
})

const buttonClass = computed(() => {
  return props.isSuccess ? 'success-btn' : 'error-btn'
})

const confirmButtonText = computed(() => {
  return props.isSuccess ? '太好了！' : '我知道了'
})

// Methods
const closeModal = () => {
  emit('close')
}

const formatDateTime = (dateTime: string) => {
  return new Date(dateTime).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

const getErrorSuggestion = (errorCode: string) => {
  const suggestions: Record<string, string> = {
    '404': '任务可能已被删除，请刷新页面重试',
    '403': '请检查您的权限或登录状态',
    '500': '服务器暂时繁忙，请稍后重试',
    'network': '请检查网络连接后重试'
  }
  return suggestions[errorCode] || '请稍后重试或联系管理员'
}

// Auto close functionality
if (props.autoClose && props.isSuccess) {
  setTimeout(() => {
    closeModal()
  }, props.autoCloseDelay)
}
</script>

<style scoped>
/* Neo-Brutalism Overtime Notification Styles */
.overtime-notification-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: 1rem;
  animation: overlay-fade-in 0.2s ease-out;
}

@keyframes overlay-fade-in {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.overtime-notification-modal {
  background: white;
  border: 4px solid #000;
  max-width: 500px;
  width: 100%;
  box-shadow: 12px 12px 0 #000;
  animation: modal-slide-in 0.3s ease-out;
  overflow: hidden;
}

@keyframes modal-slide-in {
  from {
    transform: translateY(-20px) scale(0.95);
    opacity: 0;
  }
  to {
    transform: translateY(0) scale(1);
    opacity: 1;
  }
}

/* Header Styles */
.notification-header {
  padding: 2rem;
  border-bottom: 3px solid #000;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.notification-header.success-header {
  background: linear-gradient(135deg, #d4edda, #c3e6cb);
  color: #155724;
}

.notification-header.error-header {
  background: linear-gradient(135deg, #f8d7da, #f5c6cb);
  color: #721c24;
}

.header-content {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.notification-icon {
  font-size: 2rem;
  animation: icon-bounce 0.6s ease-out;
}

@keyframes icon-bounce {
  0%, 20%, 50%, 80%, 100% {
    transform: translateY(0);
  }
  40% {
    transform: translateY(-8px);
  }
  60% {
    transform: translateY(-4px);
  }
}

.notification-title {
  font-size: 1.5rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0;
}

.close-btn {
  background: transparent;
  border: 3px solid currentColor;
  color: inherit;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  font-size: 1.5rem;
  font-weight: 900;
  cursor: pointer;
  box-shadow: 3px 3px 0 rgba(0, 0, 0, 0.3);
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover {
  transform: translate(-1px, -1px);
  box-shadow: 4px 4px 0 rgba(0, 0, 0, 0.3);
}

/* Body Styles */
.notification-body {
  padding: 2rem;
  background: white;
}

.message-content {
  margin-bottom: 2rem;
}

.primary-message {
  font-size: 1.125rem;
  font-weight: 700;
  color: #333;
  margin-bottom: 0.75rem;
  line-height: 1.4;
}

.secondary-message {
  font-size: 0.875rem;
  font-weight: 500;
  color: #666;
  line-height: 1.4;
}

/* Success Details */
.success-details {
  background: linear-gradient(135deg, #f8f9fa, #e9ecef);
  border: 3px solid #28a745;
  padding: 1.5rem;
  box-shadow: 4px 4px 0 #28a745;
  margin-bottom: 1.5rem;
}

.time-display {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
}

.time-icon {
  font-size: 2.5rem;
  animation: time-pulse 2s infinite;
}

@keyframes time-pulse {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.1);
  }
}

.time-info {
  flex: 1;
}

.time-value {
  font-size: 2rem;
  font-weight: 900;
  color: #28a745;
  text-transform: uppercase;
  letter-spacing: 1px;
  text-shadow: 2px 2px 0 rgba(0, 0, 0, 0.1);
}

.time-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.end-time-info {
  padding: 1rem;
  background: rgba(255, 255, 255, 0.8);
  border: 2px solid #000;
  border-radius: 4px;
  font-size: 0.875rem;
}

.end-time-label {
  font-weight: 600;
  color: #666;
}

.end-time-value {
  font-weight: 700;
  color: #333;
  font-family: 'Courier New', monospace;
}

/* Error Details */
.error-details {
  background: linear-gradient(135deg, #fff3cd, #ffeaa7);
  border: 3px solid #ffc107;
  padding: 1.5rem;
  box-shadow: 4px 4px 0 #ffc107;
  margin-bottom: 1.5rem;
}

.error-code {
  font-size: 0.875rem;
  font-weight: 700;
  color: #856404;
  margin-bottom: 0.5rem;
  font-family: 'Courier New', monospace;
}

.error-suggestion {
  font-size: 0.875rem;
  font-weight: 500;
  color: #856404;
  line-height: 1.4;
}

/* Footer Styles */
.notification-footer {
  padding: 1.5rem 2rem;
  border-top: 3px solid #000;
  background: #f8f9fa;
  display: flex;
  justify-content: center;
}

.confirm-btn {
  padding: 1rem 2rem;
  border: 3px solid #000;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  cursor: pointer;
  box-shadow: 4px 4px 0 #000;
  transition: all 0.2s ease;
  font-size: 1rem;
  min-width: 120px;
}

.confirm-btn.success-btn {
  background: #28a745;
  color: white;
}

.confirm-btn.error-btn {
  background: #dc3545;
  color: white;
}

.confirm-btn:hover {
  transform: translate(-2px, -2px);
  box-shadow: 6px 6px 0 #000;
}

.confirm-btn:active {
  transform: translate(0, 0);
  box-shadow: 2px 2px 0 #000;
}

/* Mobile Responsive */
@media (max-width: 768px) {
  .overtime-notification-modal {
    margin: 1rem;
    max-width: none;
    width: calc(100% - 2rem);
  }

  .notification-header {
    padding: 1.5rem;
    flex-direction: column;
    gap: 1rem;
    text-align: center;
  }

  .header-content {
    flex-direction: column;
    gap: 0.75rem;
  }

  .notification-icon {
    font-size: 3rem;
  }

  .notification-title {
    font-size: 1.25rem;
  }

  .close-btn {
    position: absolute;
    top: 1rem;
    right: 1rem;
    width: 35px;
    height: 35px;
    font-size: 1.25rem;
  }

  .notification-body {
    padding: 1.5rem;
  }

  .time-display {
    flex-direction: column;
    text-align: center;
    gap: 0.75rem;
  }

  .time-value {
    font-size: 1.75rem;
  }

  .success-details,
  .error-details {
    padding: 1rem;
  }

  .notification-footer {
    padding: 1rem 1.5rem;
  }

  .confirm-btn {
    width: 100%;
    padding: 0.875rem 1.5rem;
    font-size: 0.875rem;
  }
}

/* Small mobile */
@media (max-width: 480px) {
  .overtime-notification-overlay {
    padding: 0.5rem;
  }

  .overtime-notification-modal {
    margin: 0.5rem;
    width: calc(100% - 1rem);
  }

  .notification-header {
    padding: 1rem;
  }

  .notification-title {
    font-size: 1.125rem;
  }

  .notification-body {
    padding: 1rem;
  }

  .time-value {
    font-size: 1.5rem;
  }
}
</style>