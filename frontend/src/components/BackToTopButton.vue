<template>
  <Transition name="back-to-top">
    <button
      v-if="showButton"
      @click="handleBackToTop"
      class="back-to-top-btn"
      :class="{ 'refreshing': isRefreshing }"
      :disabled="isRefreshing"
      title="🔄 点击刷新数据并回到顶部"
    >
      <div class="btn-content">
        <span v-if="isRefreshing" class="refresh-icon">🔄</span>
        <span v-else class="arrow-icon">⬆️</span>
        <span class="refresh-hint" v-if="!isRefreshing">🔄</span>
      </div>
    </button>
  </Transition>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

// Props
interface Props {
  scrollThreshold?: number // 显示按钮的滚动阈值
  refreshCallback?: () => Promise<void> // 刷新数据的回调函数
}

const props = withDefaults(defineProps<Props>(), {
  scrollThreshold: 300
})

// State
const showButton = ref(false)
const isRefreshing = ref(false)

// Emits
const emit = defineEmits<{
  refresh: []
  scrollToTop: []
}>()

// 处理滚动事件
const handleScroll = () => {
  showButton.value = window.scrollY > props.scrollThreshold
}

// 处理回到顶部点击
const handleBackToTop = async () => {
  if (isRefreshing.value) return

  try {
    isRefreshing.value = true

    // 发出刷新事件
    emit('refresh')

    // 如果有刷新回调函数，执行它
    if (props.refreshCallback) {
      await props.refreshCallback()
    }

    // 等待一小段时间让用户看到刷新动画
    await new Promise(resolve => setTimeout(resolve, 500))

    // 平滑滚动到顶部
    window.scrollTo({
      top: 0,
      behavior: 'smooth'
    })

    // 发出滚动到顶部事件
    emit('scrollToTop')

  } catch (error) {
    console.error('刷新数据失败:', error)
  } finally {
    // 延迟一点时间再隐藏加载状态，确保滚动完成
    setTimeout(() => {
      isRefreshing.value = false
    }, 800)
  }
}

// 生命周期
onMounted(() => {
  window.addEventListener('scroll', handleScroll, { passive: true })
  // 初始检查
  handleScroll()
})

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll)
})
</script>

<style scoped>
/* Neo-Brutalism风格的回到顶部按钮 */
.back-to-top-btn {
  position: fixed;
  bottom: 24px;
  right: 24px;
  width: 68px;
  height: 68px;
  background: linear-gradient(135deg, #ff6b6b, #ee5a52);
  border: 4px solid #000;
  border-radius: 12px;
  box-shadow: 6px 6px 0 #000;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
  transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
  z-index: 1000;
  color: white;
  font-weight: 900;
  overflow: hidden;
  backdrop-filter: blur(8px);
}

.back-to-top-btn:hover:not(:disabled) {
  transform: translate(-3px, -3px);
  box-shadow: 9px 9px 0 #000;
  background: linear-gradient(135deg, #ee5a52, #dc3545);
  border-color: #000;
}

.back-to-top-btn:active:not(:disabled) {
  transform: translate(1px, 1px);
  box-shadow: 3px 3px 0 #000;
}

.back-to-top-btn:disabled {
  cursor: not-allowed;
  background: linear-gradient(135deg, #6c757d, #5a6268);
  opacity: 0.7;
}

.back-to-top-btn.refreshing {
  background: linear-gradient(135deg, #17a2b8, #138496);
  transform: scale(0.98);
}

/* 按钮内容容器 */
.btn-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  position: relative;
  width: 100%;
  height: 100%;
}

.arrow-icon {
  display: inline-block;
  font-size: 1.5rem;
  line-height: 1;
  transition: transform 0.2s ease;
}

.refresh-icon {
  display: inline-block;
  font-size: 1.25rem;
  line-height: 1;
  animation: spin 1s linear infinite;
}

.refresh-hint {
  display: inline-block;
  font-size: 0.75rem;
  line-height: 1;
  position: absolute;
  bottom: 8px;
  right: 8px;
  opacity: 0.8;
  transition: opacity 0.2s ease;
}

.back-to-top-btn:hover .refresh-hint {
  opacity: 1;
}

.back-to-top-btn:hover .arrow-icon {
  transform: translateY(-2px);
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* 过渡动画 */
.back-to-top-enter-active,
.back-to-top-leave-active {
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.back-to-top-enter-from {
  opacity: 0;
  transform: translateY(20px) scale(0.8);
}

.back-to-top-leave-to {
  opacity: 0;
  transform: translateY(20px) scale(0.8);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .back-to-top-btn {
    bottom: 20px;
    right: 20px;
    width: 52px;
    height: 52px;
    border: 3px solid #000;
    box-shadow: 4px 4px 0 #000;
  }

  .back-to-top-btn:hover:not(:disabled) {
    transform: translate(-2px, -2px);
    box-shadow: 6px 6px 0 #000;
  }

  .back-to-top-btn:active:not(:disabled) {
    transform: translate(1px, 1px);
    box-shadow: 2px 2px 0 #000;
  }

  .arrow-icon {
    font-size: 1.25rem;
  }

  .refresh-icon {
    font-size: 1rem;
  }

  .refresh-hint {
    font-size: 0.625rem;
    bottom: 6px;
    right: 6px;
  }
}

@media (max-width: 480px) {
  .back-to-top-btn {
    bottom: 16px;
    right: 16px;
    width: 48px;
    height: 48px;
    border-radius: 10px;
  }

  .arrow-icon {
    font-size: 1.125rem;
  }

  .refresh-icon {
    font-size: 0.875rem;
  }

  .refresh-hint {
    font-size: 0.5rem;
    bottom: 4px;
    right: 4px;
  }
}

/* 确保按钮不会被其他元素遮挡 */
.back-to-top-btn {
  z-index: 9999;
}

/* 暗色主题适配 */
@media (prefers-color-scheme: dark) {
  .back-to-top-btn {
    border-color: #fff;
    box-shadow: 6px 6px 0 #fff;
    backdrop-filter: blur(12px);
  }

  .back-to-top-btn:hover:not(:disabled) {
    box-shadow: 9px 9px 0 #fff;
  }

  .back-to-top-btn:active:not(:disabled) {
    box-shadow: 3px 3px 0 #fff;
  }

  @media (max-width: 768px) {
    .back-to-top-btn:hover:not(:disabled) {
      box-shadow: 6px 6px 0 #fff;
    }

    .back-to-top-btn:active:not(:disabled) {
      box-shadow: 2px 2px 0 #fff;
    }
  }
}
</style>