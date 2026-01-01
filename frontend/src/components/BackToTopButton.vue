<template>
  <Transition name="back-to-top">
    <button
      v-if="showButton"
      @click="handleBackToTop"
      class="back-to-top-btn"
      :class="{ 'refreshing': isRefreshing }"
      :disabled="isRefreshing"
      title="刷新数据并回到顶部"
    >
      <span v-if="isRefreshing" class="refresh-icon">🔄</span>
      <span v-else class="arrow-icon">⬆️</span>
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
  width: 56px;
  height: 56px;
  background: linear-gradient(135deg, #ff6b6b, #ee5a52);
  border: 4px solid #000;
  border-radius: 0;
  box-shadow: 6px 6px 0 #000;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
  transition: all 0.2s ease;
  z-index: 1000;
  color: white;
  font-weight: 900;
}

.back-to-top-btn:hover:not(:disabled) {
  transform: translate(-2px, -2px);
  box-shadow: 8px 8px 0 #000;
  background: linear-gradient(135deg, #ee5a52, #dc3545);
}

.back-to-top-btn:active:not(:disabled) {
  transform: translate(2px, 2px);
  box-shadow: 2px 2px 0 #000;
}

.back-to-top-btn:disabled {
  cursor: not-allowed;
  background: linear-gradient(135deg, #6c757d, #5a6268);
}

.back-to-top-btn.refreshing {
  background: linear-gradient(135deg, #17a2b8, #138496);
}

.arrow-icon {
  display: inline-block;
  font-size: 1.5rem;
  line-height: 1;
}

.refresh-icon {
  display: inline-block;
  font-size: 1.25rem;
  line-height: 1;
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
    width: 48px;
    height: 48px;
    border: 3px solid #000;
    box-shadow: 4px 4px 0 #000;
  }

  .back-to-top-btn:hover:not(:disabled) {
    transform: translate(-1px, -1px);
    box-shadow: 5px 5px 0 #000;
  }

  .back-to-top-btn:active:not(:disabled) {
    transform: translate(1px, 1px);
    box-shadow: 1px 1px 0 #000;
  }

  .arrow-icon {
    font-size: 1.25rem;
  }

  .refresh-icon {
    font-size: 1rem;
  }
}

@media (max-width: 480px) {
  .back-to-top-btn {
    bottom: 16px;
    right: 16px;
    width: 44px;
    height: 44px;
  }

  .arrow-icon {
    font-size: 1.125rem;
  }

  .refresh-icon {
    font-size: 0.875rem;
  }
}

/* 确保按钮不会被其他元素遮挡 */
.back-to-top-btn {
  z-index: 9999;
}

/* 暗色主题适配（如果需要） */
@media (prefers-color-scheme: dark) {
  .back-to-top-btn {
    border-color: #fff;
    box-shadow: 6px 6px 0 #fff;
  }

  .back-to-top-btn:hover:not(:disabled) {
    box-shadow: 8px 8px 0 #fff;
  }

  .back-to-top-btn:active:not(:disabled) {
    box-shadow: 2px 2px 0 #fff;
  }

  @media (max-width: 768px) {
    .back-to-top-btn:hover:not(:disabled) {
      box-shadow: 5px 5px 0 #fff;
    }

    .back-to-top-btn:active:not(:disabled) {
      box-shadow: 1px 1px 0 #fff;
    }
  }
}
</style>