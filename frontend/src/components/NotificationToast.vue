<template>
  <!-- Single root element wrapper to fix Transition warning -->
  <div class="notification-toast-wrapper">
    <!-- 液态玻璃主题下使用Teleport渲染到body，避免stacking context问题 -->
    <Teleport v-if="isLiquidGlassTheme" to="body">
      <transition :name="transitionName" @after-leave="$emit('closed')">
        <div v-if="isVisible" class="toast-overlay" :class="overlayClasses" @click="closeToast">
          <div class="toast-container" :class="containerClasses" @click.stop>
            <div class="toast-card" :class="cardClasses">
              <!-- Header -->
              <div class="toast-header">
                <div class="toast-icon">
                  {{ toastIcon }}
                </div>
                <div class="toast-title">
                  {{ title }}
                </div>
                <button @click="closeToast" class="toast-close-btn" title="关闭">
                  ✕
                </button>
              </div>

              <!-- Content -->
              <div class="toast-content" :class="contentClasses">
                <slot name="default">
                  <!-- Default content when no slot provided -->
                  <div v-if="message" class="toast-message">
                    {{ message }}
                  </div>
                  <div v-if="secondaryMessage" class="toast-secondary">
                    {{ secondaryMessage }}
                  </div>

                  <!-- Details Section -->
                  <div v-if="details" class="toast-details">
                    <div v-for="(value, key) in details" :key="key" class="detail-item">
                      <span class="detail-label">{{ key }}:</span>
                      <span class="detail-value">{{ value }}</span>
                    </div>
                  </div>
                </slot>
              </div>

              <!-- Action Buttons -->
              <div v-if="showActions || $slots.actions" class="toast-actions" :class="actionsClasses">
                <slot name="actions">
                  <button @click="closeToast" class="toast-action-btn primary">
                    确定
                  </button>
                </slot>
              </div>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>

    <!-- 非液态玻璃主题使用正常渲染 -->
    <transition v-else :name="transitionName" @after-leave="$emit('closed')">
      <div v-if="isVisible" class="toast-overlay" :class="overlayClasses" @click="closeToast">
        <div class="toast-container" :class="containerClasses" @click.stop>
          <div class="toast-card" :class="cardClasses">
            <!-- Header -->
            <div class="toast-header">
              <div class="toast-icon">
                {{ toastIcon }}
              </div>
              <div class="toast-title">
                {{ title }}
              </div>
              <button @click="closeToast" class="toast-close-btn" title="关闭">
                ✕
              </button>
            </div>

            <!-- Content -->
            <div class="toast-content" :class="contentClasses">
              <slot name="default">
                <!-- Default content when no slot provided -->
                <div v-if="message" class="toast-message">
                  {{ message }}
                </div>
                <div v-if="secondaryMessage" class="toast-secondary">
                  {{ secondaryMessage }}
                </div>

                <!-- Details Section -->
                <div v-if="details" class="toast-details">
                  <div v-for="(value, key) in details" :key="key" class="detail-item">
                    <span class="detail-label">{{ key }}:</span>
                    <span class="detail-value">{{ value }}</span>
                  </div>
                </div>
              </slot>
            </div>

            <!-- Action Buttons -->
            <div v-if="showActions || $slots.actions" class="toast-actions" :class="actionsClasses">
              <slot name="actions">
                <button @click="closeToast" class="toast-action-btn primary">
                  确定
                </button>
              </slot>
            </div>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onUnmounted, nextTick, onMounted } from 'vue'

// 检测当前是否为液态玻璃主题
const isLiquidGlassTheme = computed(() => {
  if (typeof document !== 'undefined') {
    return document.documentElement.classList.contains('theme-liquid-glass')
  }
  return false
})

interface Props {
  isVisible: boolean
  type?: 'success' | 'error' | 'warning' | 'info' | 'menu'
  title: string
  message?: string
  secondaryMessage?: string
  details?: Record<string, any>
  showActions?: boolean
  autoClose?: boolean
  autoCloseDelay?: number
  variant?: 'default' | 'menu' | 'drawer'
}

interface Emits {
  (e: 'close'): void
  (e: 'closed'): void
}

const props = withDefaults(defineProps<Props>(), {
  type: 'info',
  showActions: true,
  autoClose: false,
  autoCloseDelay: 5000,
  variant: 'default'
})

const emit = defineEmits<Emits>()

// Auto close timer
const autoCloseTimer = ref<number>()

// Computed properties
const toastTypeClass = computed(() => {
  return `toast-${props.type}`
})

const toastIcon = computed(() => {
  const icons = {
    success: '✅',
    error: '❌',
    warning: '⚠️',
    info: 'ℹ️',
    menu: '☰'
  }
  return icons[props.type] || icons.info
})

// Check if this is a menu variant
const isMenuVariant = computed(() => props.variant === 'menu' || props.variant === 'drawer')
const isDrawerVariant = computed(() => props.variant === 'drawer')

// Variant-based classes
const transitionName = computed(() => isDrawerVariant.value ? 'drawer' : 'toast')

const overlayClasses = computed(() => ({
  'liquid-glass-toast': isLiquidGlassTheme.value,
  'menu-overlay': isMenuVariant.value,
  'drawer-overlay': isDrawerVariant.value
}))

const containerClasses = computed(() => ({
  'menu-container': isMenuVariant.value,
  'drawer-container': isDrawerVariant.value
}))

const cardClasses = computed(() => [
  toastTypeClass.value,
  {
    'menu-card': isMenuVariant.value,
    'drawer-card': isDrawerVariant.value
  }
])

const contentClasses = computed(() => ({
  'menu-content': isMenuVariant.value,
  'drawer-content': isDrawerVariant.value
}))

const actionsClasses = computed(() => ({
  'menu-actions': isMenuVariant.value,
  'drawer-actions': isDrawerVariant.value
}))

// Methods
const closeToast = () => {
  if (autoCloseTimer.value) {
    clearTimeout(autoCloseTimer.value)
  }
  emit('close')
}

// Auto close functionality
watch(() => props.isVisible, (newVal) => {
  if (newVal) {
    // 禁用body滚动
    document.body.style.overflow = 'hidden'

    if (props.autoClose) {
      autoCloseTimer.value = window.setTimeout(() => {
        closeToast()
      }, props.autoCloseDelay)
    }
  } else {
    // 恢复body滚动
    document.body.style.overflow = ''

    if (autoCloseTimer.value) {
      clearTimeout(autoCloseTimer.value)
    }
  }
})

// Cleanup on unmount
onUnmounted(() => {
  if (autoCloseTimer.value) {
    clearTimeout(autoCloseTimer.value)
  }
  // 确保恢复body滚动
  document.body.style.overflow = ''
})
</script>

<style scoped>
/* Toast Transitions */
.toast-enter-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.toast-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.toast-enter-from {
  opacity: 0;
  transform: scale(0.9) translateY(-20px);
}

.toast-leave-to {
  opacity: 0;
  transform: scale(0.9) translateY(-20px);
}

/* Drawer Transitions */
.drawer-enter-active {
  transition: all 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.drawer-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.drawer-enter-from {
  opacity: 0;
}

.drawer-enter-from .toast-card {
  transform: translateY(100%);
}

.drawer-leave-to {
  opacity: 0;
}

.drawer-leave-to .toast-card {
  transform: translateY(100%);
}

/* Toast Overlay */
.toast-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center; /* 垂直居中，确保在可视区域内 */
  justify-content: center;
  z-index: 9999;
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  padding: 2rem; /* 四周留白而不是只有顶部 */
  overflow: hidden;
}

/* 移动端优化定位 */
@media (max-width: 768px) {
  .toast-overlay {
    align-items: center; /* 移动端也保持居中 */
    padding: 1rem; /* 移动端减少留白 */
  }
}

.toast-container {
  max-width: 500px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
}

/* Toast Card - Neo-Brutalism Style */
.toast-card {
  background: white;
  border: 4px solid #000;
  border-radius: 12px;
  box-shadow: 8px 8px 0 #000;
  overflow: hidden;
  position: relative;
  animation: toast-bounce 0.5s cubic-bezier(0.68, -0.55, 0.265, 1.55);
}

@keyframes toast-bounce {
  0% {
    transform: scale(0.8) rotate(-2deg);
    opacity: 0;
  }
  50% {
    transform: scale(1.05) rotate(1deg);
  }
  100% {
    transform: scale(1) rotate(0deg);
    opacity: 1;
  }
}

/* Toast Types */
.toast-success {
  border-color: #28a745;
}

.toast-success .toast-header {
  background: linear-gradient(135deg, #28a745, #20c997);
  color: white;
}

.toast-error {
  border-color: #dc3545;
}

.toast-error .toast-header {
  background: linear-gradient(135deg, #dc3545, #e74c3c);
  color: white;
}

.toast-warning {
  border-color: #ffc107;
}

.toast-warning .toast-header {
  background: linear-gradient(135deg, #ffc107, #fd7e14);
  color: #000;
}

.toast-info {
  border-color: #007bff;
}

.toast-info .toast-header {
  background: linear-gradient(135deg, #007bff, #17a2b8);
  color: white;
}

/* Menu type */
.toast-menu {
  border-color: #6366f1;
}

.toast-menu .toast-header {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white;
}

/* Toast Header */
.toast-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.5rem;
  border-bottom: 3px solid #000;
  position: relative;
}

.toast-icon {
  font-size: 1.5rem;
  flex-shrink: 0;
}

.toast-title {
  flex: 1;
  font-size: 1.25rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.toast-close-btn {
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
  font-size: 1rem;
  transition: all 0.2s ease;
  color: inherit;
}

.toast-close-btn:hover {
  background: rgba(0, 0, 0, 0.3);
  transform: scale(1.1);
}

/* Toast Content */
.toast-content {
  padding: 1.5rem;
  background: white;
}

.toast-message {
  font-size: 1.1rem;
  font-weight: 600;
  color: #333;
  margin-bottom: 0.75rem;
  line-height: 1.5;
}

.toast-secondary {
  font-size: 0.95rem;
  color: #666;
  margin-bottom: 1rem;
  line-height: 1.4;
}

/* Details Section */
.toast-details {
  background: linear-gradient(135deg, #f8f9fa, #e9ecef);
  border: 2px solid #000;
  border-radius: 6px;
  padding: 1rem;
  margin-top: 1rem;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0;
  border-bottom: 1px solid #dee2e6;
}

.detail-item:last-child {
  border-bottom: none;
}

.detail-label {
  font-weight: 700;
  color: #495057;
  font-size: 0.9rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.detail-value {
  font-weight: 600;
  color: #212529;
  font-size: 0.95rem;
}

/* Toast Actions */
.toast-actions {
  padding: 1rem 1.5rem;
  background: linear-gradient(135deg, #f8f9fa, #e9ecef);
  border-top: 3px solid #000;
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
}

.toast-action-btn {
  background: linear-gradient(135deg, #007bff, #0056b3);
  color: white;
  border: 3px solid #000;
  border-radius: 6px;
  padding: 0.75rem 1.5rem;
  font-weight: 800;
  font-size: 0.9rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  cursor: pointer;
  box-shadow: 3px 3px 0 #000;
  transition: all 0.2s ease;
  min-width: 100px;
}

.toast-action-btn:hover {
  transform: translate(-1px, -1px);
  box-shadow: 4px 4px 0 #000;
  background: linear-gradient(135deg, #0056b3, #004085);
}

.toast-action-btn:active {
  transform: translate(1px, 1px);
  box-shadow: 1px 1px 0 #000;
}

.toast-action-btn.primary {
  background: linear-gradient(135deg, #28a745, #218838);
}

.toast-action-btn.primary:hover {
  background: linear-gradient(135deg, #218838, #1e7e34);
}

/* Menu Variant Styles */
.menu-overlay {
  align-items: flex-start;
  padding-top: 5rem;
}

.menu-container {
  max-width: 420px;
}

.menu-card {
  border-width: 3px;
  box-shadow: 6px 6px 0 #000;
}

.menu-card .toast-header {
  padding: 1rem 1.25rem;
  border-bottom-width: 2px;
}

.menu-card .toast-title {
  font-size: 1.1rem;
}

.menu-content {
  padding: 1rem 1.25rem;
}

.menu-actions {
  padding: 1rem 1.25rem;
  border-top-width: 2px;
}

/* Drawer Variant Styles (Mobile Bottom Sheet) */
.drawer-overlay {
  align-items: flex-end;
  padding: 0;
  padding-bottom: env(safe-area-inset-bottom, 0);
}

.drawer-container {
  max-width: 100%;
  width: 100%;
  max-height: 85vh;
}

.drawer-card {
  border-width: 3px 3px 0 3px;
  border-radius: 20px 20px 0 0;
  box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.3);
  animation: drawer-slide-up 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
}

@keyframes drawer-slide-up {
  0% {
    transform: translateY(100%);
    opacity: 0;
  }
  100% {
    transform: translateY(0);
    opacity: 1;
  }
}

.drawer-card .toast-header {
  padding: 1.25rem;
  border-bottom-width: 2px;
  position: relative;
}

/* Drawer drag handle */
.drawer-card .toast-header::before {
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

.drawer-card .toast-title {
  font-size: 1.1rem;
  margin-top: 0.5rem;
}

.drawer-content {
  padding: 1rem 1.25rem;
  max-height: 60vh;
  overflow-y: auto;
}

.drawer-actions {
  padding: 1rem 1.25rem;
  border-top-width: 2px;
  flex-direction: column;
  gap: 0.75rem;
}

.drawer-actions .toast-action-btn {
  width: 100%;
  padding: 1rem;
  font-size: 1rem;
}

/* Menu item styles for Action Center */
.menu-item-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  background: white;
  border: 3px solid #000;
  border-radius: 10px;
  box-shadow: 3px 3px 0 #000;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
  text-align: left;
  width: 100%;
}

.menu-item:hover {
  transform: translate(-2px, -2px);
  box-shadow: 5px 5px 0 #000;
}

.menu-item:active {
  transform: translate(0, 0);
  box-shadow: 2px 2px 0 #000;
}

.menu-item-icon {
  font-size: 1.5rem;
  flex-shrink: 0;
}

.menu-item-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.menu-item-title {
  font-weight: 700;
  font-size: 1rem;
  color: #000;
}

.menu-item-desc {
  font-size: 0.85rem;
  color: #666;
}

.menu-item-cost {
  font-size: 0.75rem;
  font-weight: 700;
  color: #dc3545;
  background: rgba(220, 53, 69, 0.1);
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  white-space: nowrap;
}

/* Menu item variants */
.menu-item.primary {
  background: linear-gradient(135deg, #007bff, #0056b3);
  color: white;
}

.menu-item.primary .menu-item-title,
.menu-item.primary .menu-item-desc {
  color: white;
}

.menu-item.success {
  background: linear-gradient(135deg, #28a745, #218838);
  color: white;
}

.menu-item.success .menu-item-title,
.menu-item.success .menu-item-desc {
  color: white;
}

.menu-item.danger {
  background: linear-gradient(135deg, #dc3545, #c82333);
  color: white;
}

.menu-item.danger .menu-item-title,
.menu-item.danger .menu-item-desc {
  color: white;
}

.menu-item.warning {
  background: linear-gradient(135deg, #ffc107, #fd7e14);
  color: #000;
}

.menu-item.gold {
  background: linear-gradient(135deg, #fbbf24, #d97706);
  color: #000;
  border-color: #000;
}

.menu-item.gold .menu-item-title,
.menu-item.gold .menu-item-desc {
  color: #000;
}

.menu-item:disabled,
.menu-item.disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
  box-shadow: 3px 3px 0 #000;
}

/* Menu item animation */
.menu-item {
  animation: menu-item-pop 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) backwards;
}

.menu-item:nth-child(1) { animation-delay: 0.05s; }
.menu-item:nth-child(2) { animation-delay: 0.1s; }
.menu-item:nth-child(3) { animation-delay: 0.15s; }
.menu-item:nth-child(4) { animation-delay: 0.2s; }
.menu-item:nth-child(5) { animation-delay: 0.25s; }
.menu-item:nth-child(6) { animation-delay: 0.3s; }
.menu-item:nth-child(7) { animation-delay: 0.35s; }
.menu-item:nth-child(8) { animation-delay: 0.4s; }

@keyframes menu-item-pop {
  0% {
    opacity: 0;
    transform: scale(0.8) translateX(-20px);
  }
  100% {
    opacity: 1;
    transform: scale(1) translateX(0);
  }
}

/* Mobile responsive */
@media (max-width: 768px) {
  .toast-container {
    width: 95%;
    max-width: none;
  }

  .toast-card {
    border-width: 3px;
    box-shadow: 6px 6px 0 #000;
    border-radius: 8px;
  }


  .toast-header {
    padding: 1rem;
    gap: 0.75rem;
  }

  .toast-title {
    font-size: 1.1rem;
  }

  .toast-icon {
    font-size: 1.25rem;
  }

  .toast-close-btn {
    width: 32px;
    height: 32px;
    font-size: 0.9rem;
  }

  .toast-content {
    padding: 1rem;
  }

  .toast-message {
    font-size: 1rem;
  }

  .toast-actions {
    padding: 0.75rem 1rem;
    flex-direction: column;
  }

  .toast-action-btn {
    width: 100%;
    padding: 0.75rem;
  }

  .detail-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.25rem;
  }

  /* Menu variant mobile adjustments */
  .menu-overlay {
    padding-top: 3rem;
  }

  .menu-container {
    width: 95%;
  }

  .menu-card {
    border-width: 3px;
    box-shadow: 5px 5px 0 #000;
  }

  .menu-item {
    padding: 0.875rem;
    border-width: 2px;
    box-shadow: 2px 2px 0 #000;
  }

  .menu-item:hover {
    box-shadow: 3px 3px 0 #000;
  }

  .menu-item-icon {
    font-size: 1.25rem;
  }

  .menu-item-title {
    font-size: 0.95rem;
  }

  .menu-item-desc {
    font-size: 0.8rem;
  }

  /* Drawer variant is default on mobile */
  .drawer-card {
    border-radius: 16px 16px 0 0;
  }

  .drawer-card .toast-header {
    padding: 1.25rem 1rem 1rem;
  }

  .drawer-content {
    padding: 1rem;
  }

  .drawer-actions {
    padding: 1rem;
    padding-bottom: calc(1rem + env(safe-area-inset-bottom, 0));
  }
}

/* Accessibility */
@media (prefers-reduced-motion: reduce) {
  .toast-enter-active,
  .toast-leave-active {
    transition: opacity 0.2s ease;
  }

  .toast-card {
    animation: none;
  }

  .toast-action-btn:hover {
    transform: none;
  }
}

</style>