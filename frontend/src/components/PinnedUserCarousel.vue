<template>
  <!-- Compact mode for HomeView -->
  <div v-if="compact" class="pinned-carousel-compact">
    <div class="compact-container" :class="{ empty: pinnedTasks.length === 0 }">
      <div v-if="pinnedTasks.length === 0" class="compact-empty">
        <div class="compact-icon">👑</div>
        <div class="compact-text">暂无置顶用户</div>
      </div>
      <div v-else class="compact-content">
        <div
          v-for="(task, index) in pinnedTasks"
          :key="task.id"
          v-show="index === currentIndex"
          class="compact-slide"
          :class="{ active: index === currentIndex }"
          @click="goToTask(task.task.id)"
        >
          <div class="compact-icon">📌</div>
          <div class="compact-info">
            <span class="compact-text">{{ task.pinned_user.username }} 的任务「{{ task.task.title }}」被置顶</span>
          </div>
        </div>
        <!-- Navigation dots for compact mode -->
        <div v-if="pinnedTasks.length > 1" class="compact-dots">
          <span
            v-for="(_, index) in pinnedTasks"
            :key="index"
            @click="goToSlide(index)"
            :class="['compact-dot', { active: index === currentIndex }]"
          />
        </div>
      </div>
    </div>
  </div>

  <!-- Full mode for TaskView -->
  <div v-else class="pinned-carousel">
    <div class="carousel-header">
      <h3 class="carousel-title">🔥 置顶惩罚榜</h3>
      <div class="carousel-status">
        <span v-if="pinnedTasks.length > 0" class="status-active">
          {{ pinnedTasks.length }} 人被置顶
        </span>
        <span v-else class="status-empty">
          暂无置顶用户
        </span>
      </div>
    </div>

    <div class="carousel-container">
      <div v-if="pinnedTasks.length === 0" class="empty-state">
        <div class="empty-icon">👑</div>
        <div class="empty-text">暂无置顶用户</div>
        <div class="empty-subtitle">钥匙持有者可以置顶任务创建者</div>
      </div>

      <div v-else class="carousel-content">
        <div
          v-for="(task, index) in pinnedTasks"
          :key="task.id"
          v-show="index === currentIndex"
          class="carousel-slide"
          @click="goToTask(task.task.id)"
        >
          <div class="slide-content">
            <!-- Position Badge -->
            <div class="position-indicator" :class="`position-${task.position}`">
              <span class="position-number">{{ task.position }}</span>
              <span class="position-crown">👑</span>
            </div>

            <!-- User Info -->
            <div class="user-section">
              <UserAvatar
                :user="task.pinned_user as any"
                size="large"
                :clickable="false"
              />
              <div class="user-details">
                <div class="username">{{ task.pinned_user.username }}</div>
                <div class="user-badge">被置顶用户</div>
              </div>
            </div>

            <!-- Task Info -->
            <div class="task-section">
              <div class="task-title">{{ task.task.title }}</div>
              <div class="task-meta">
                <span class="task-type">🔒 {{ getDifficultyText(task.task.difficulty) }}</span>
                <span class="task-status" :class="task.task.status">
                  {{ getStatusText(task.task.status) }}
                </span>
              </div>
            </div>

            <!-- Pinning Info -->
            <div class="pinning-section">
              <div class="time-remaining">
                <span class="time-icon">⏰</span>
                <span class="time-text">{{ formatTimeRemaining(task.time_remaining) }}</span>
              </div>
              <div class="key-holder">
                <span class="key-icon">🔑</span>
                <span class="holder-text">{{ task.key_holder.username }}</span>
              </div>
            </div>

            <!-- Click Indicator -->
            <div class="click-indicator">
              <span class="click-text">点击进入任务</span>
              <span class="click-arrow">→</span>
            </div>
          </div>
        </div>

        <!-- Navigation Dots -->
        <div v-if="pinnedTasks.length > 1" class="carousel-dots">
          <button
            v-for="(_, index) in pinnedTasks"
            :key="index"
            @click="goToSlide(index)"
            :class="['dot', { active: index === currentIndex }]"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { tasksApi } from '../lib/api-tasks'
import UserAvatar from './UserAvatar.vue'
import type { PinningCarouselData } from '../types/index'

// Props
interface Props {
  compact?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  compact: false
})

const router = useRouter()

// State
const pinnedTasks = ref<PinningCarouselData[]>([])
const currentIndex = ref(0)
const loading = ref(false)
const autoPlayInterval = ref<number>()
const refreshInterval = ref<number>()

// Auto-play timing (4 seconds like the task carousel)
const AUTO_PLAY_INTERVAL = 4000
const REFRESH_INTERVAL = 30000 // 30 seconds

// Computed
const hasMultipleSlides = computed(() => pinnedTasks.value.length > 1)

// Methods
const fetchPinnedTasks = async () => {
  if (loading.value) return

  loading.value = true
  try {
    const response = await tasksApi.getPinnedTasksForCarousel()
    pinnedTasks.value = response.pinned_tasks || []

    // Reset current index if it's out of bounds
    if (currentIndex.value >= pinnedTasks.value.length) {
      currentIndex.value = 0
    }
  } catch (error) {
    console.error('Failed to fetch pinned tasks for carousel:', error)
    pinnedTasks.value = []
  } finally {
    loading.value = false
  }
}

const goToSlide = (index: number) => {
  currentIndex.value = index
  resetAutoPlay()
}

const nextSlide = () => {
  if (pinnedTasks.value.length === 0) return
  currentIndex.value = (currentIndex.value + 1) % pinnedTasks.value.length
}

const goToTask = (taskId: string) => {
  router.push({ name: 'task-detail', params: { id: taskId } })
}

const startAutoPlay = () => {
  if (!hasMultipleSlides.value) return

  autoPlayInterval.value = window.setInterval(() => {
    nextSlide()
  }, AUTO_PLAY_INTERVAL)
}

const stopAutoPlay = () => {
  if (autoPlayInterval.value) {
    clearInterval(autoPlayInterval.value)
    autoPlayInterval.value = undefined
  }
}

const resetAutoPlay = () => {
  stopAutoPlay()
  startAutoPlay()
}

const startRefresh = () => {
  refreshInterval.value = window.setInterval(() => {
    fetchPinnedTasks()
  }, REFRESH_INTERVAL)
}

const stopRefresh = () => {
  if (refreshInterval.value) {
    clearInterval(refreshInterval.value)
    refreshInterval.value = undefined
  }
}

// Utility functions
const getDifficultyText = (difficulty: string) => {
  const texts = {
    easy: '简单',
    normal: '普通',
    hard: '困难',
    hell: '地狱'
  }
  return texts[difficulty as keyof typeof texts] || difficulty
}

const getStatusText = (status: string) => {
  const texts = {
    pending: '待开始',
    active: '进行中',
    voting: '投票中',
    completed: '已完成',
    failed: '已失败'
  }
  return texts[status as keyof typeof texts] || status
}

const formatTimeRemaining = (timeRemaining: number): string => {
  if (timeRemaining <= 0) return '已过期'

  const minutes = Math.floor(timeRemaining / 60000)
  const seconds = Math.floor((timeRemaining % 60000) / 1000)

  if (minutes > 0) {
    return `${minutes}分${seconds}秒`
  } else {
    return `${seconds}秒`
  }
}

// Lifecycle
onMounted(async () => {
  await fetchPinnedTasks()
  startAutoPlay()
  startRefresh()
})

onUnmounted(() => {
  stopAutoPlay()
  stopRefresh()
})
</script>

<style scoped>
/* Compact mode styles - matching TaskBroadcast exactly */
.pinned-carousel-compact {
  /* Remove margin, let parent container control layout */
}

.compact-container {
  background: linear-gradient(135deg, #ff6b6b, #ee5a52);
  border: 2px solid #000;
  border-radius: 6px;
  box-shadow: 3px 3px 0 #000;
  padding: 0.4rem 0.8rem;
  display: flex;
  align-items: center;
  gap: 0.6rem;
  overflow: hidden;
  position: relative;
  height: 32px;
}

.compact-container.empty {
  background: linear-gradient(135deg, #95a5a6, #7f8c8d);
  opacity: 0.8;
}

.compact-empty {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  width: 100%;
}

.compact-icon {
  font-size: 1rem;
  flex-shrink: 0;
  animation: pulse 2s infinite;
  line-height: 1;
}

.compact-text {
  color: white;
  font-weight: 600;
  font-size: 0.85rem;
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  width: 100%;
}

.compact-content {
  flex: 1;
  position: relative;
  height: 100%;
  overflow: hidden;
}

.compact-slide {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  opacity: 0;
  transform: translateY(10px);
  transition: all 0.5s ease;
  cursor: pointer;
  padding: 0;
}

.compact-slide.active {
  opacity: 1;
  transform: translateY(0);
}

.compact-slide:hover {
  background-color: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  padding: 0 0.4rem;
  margin: 0 -0.4rem;
}

.compact-info {
  flex: 1;
  min-width: 0;
}

.compact-text {
  color: white;
  font-weight: 600;
  font-size: 0.85rem;
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  width: 100%;
}

.compact-dots {
  display: flex;
  gap: 0.25rem;
  align-items: center;
  margin-left: auto;
}

.compact-dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.5);
  cursor: pointer;
  transition: all 0.2s ease;
}

.compact-dot.active {
  background: white;
  width: 6px;
  height: 6px;
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.1);
  }
}

/* Mobile responsive for compact mode - matching TaskBroadcast exactly */
@media (max-width: 768px) {
  .compact-container {
    padding: 0.35rem 0.6rem;
    height: 28px;
    gap: 0.5rem;
    width: 100%;
    min-width: auto;
  }

  .compact-icon {
    font-size: 0.9rem;
  }

  .compact-content {
    flex: 1;
    min-width: 0;
  }

  .compact-text {
    font-size: 0.75rem;
    line-height: 1.1;
  }
}

/* Extra small screens optimization - matching TaskBroadcast exactly */
@media (max-width: 480px) {
  .compact-container {
    padding: 0.3rem 0.5rem;
    height: 26px;
    gap: 0.4rem;
    width: 100%;
    min-width: auto;
  }

  .compact-icon {
    font-size: 0.8rem;
  }

  .compact-content {
    flex: 1;
    min-width: 0;
  }

  .compact-text {
    font-size: 0.7rem;
    line-height: 1.1;
  }
}

/* Full mode styles */
.pinned-carousel {
  background: linear-gradient(135deg, #ff6b6b, #ee5a52);
  border: 4px solid #000;
  border-radius: 12px;
  box-shadow: 6px 6px 0 #000;
  padding: 1rem;
  height: 300px;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
}

.pinned-carousel::before {
  content: '';
  position: absolute;
  top: -2px;
  left: -2px;
  right: -2px;
  bottom: -2px;
  background: linear-gradient(45deg, #000, #333);
  z-index: -1;
  border-radius: 16px;
}

.carousel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.carousel-title {
  font-size: 1.25rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: white;
  text-shadow: 2px 2px 0 #000;
  margin: 0;
}

.carousel-status {
  display: flex;
  align-items: center;
}

.status-active {
  background: white;
  color: #ff6b6b;
  border: 2px solid #000;
  border-radius: 6px;
  padding: 0.25rem 0.75rem;
  font-weight: 900;
  font-size: 0.75rem;
  box-shadow: 2px 2px 0 #000;
}

.status-empty {
  background: #6c757d;
  color: white;
  border: 2px solid #000;
  border-radius: 6px;
  padding: 0.25rem 0.75rem;
  font-weight: 900;
  font-size: 0.75rem;
  box-shadow: 2px 2px 0 #000;
}

.carousel-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 0.75rem;
  text-align: center;
}

.empty-icon {
  font-size: 3rem;
  opacity: 0.7;
}

.empty-text {
  font-size: 1.25rem;
  font-weight: 900;
  color: white;
  text-shadow: 2px 2px 0 #000;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.empty-subtitle {
  font-size: 0.875rem;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.8);
  text-shadow: 1px 1px 0 #000;
}

.carousel-content {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.carousel-slide {
  flex: 1;
  cursor: pointer;
  transition: all 0.3s ease;
}

.carousel-slide:hover .slide-content {
  transform: translateY(-2px);
  box-shadow: 4px 4px 0 #000;
}

.slide-content {
  background: white;
  border: 3px solid #000;
  border-radius: 8px;
  box-shadow: 3px 3px 0 #000;
  padding: 1rem;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  position: relative;
  transition: all 0.2s ease;
}

.position-indicator {
  position: absolute;
  top: -8px;
  right: -8px;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 2px solid #000;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 900;
  font-size: 0.875rem;
  z-index: 2;
}

.position-indicator.position-1 {
  background: linear-gradient(135deg, #ffd700, #ffed4e);
}

.position-indicator.position-2 {
  background: linear-gradient(135deg, #c0c0c0, #e8e8e8);
}

.position-indicator.position-3 {
  background: linear-gradient(135deg, #cd7f32, #daa520);
}

.position-crown {
  position: absolute;
  top: -8px;
  right: -8px;
  font-size: 1rem;
}

.user-section {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.user-details {
  flex: 1;
}

.username {
  font-size: 1rem;
  font-weight: 900;
  color: #000;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 0.25rem;
}

.user-badge {
  background: linear-gradient(135deg, #ff6b6b, #ee5a52);
  color: white;
  border: 1px solid #000;
  border-radius: 4px;
  padding: 0.125rem 0.5rem;
  font-size: 0.625rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.task-section {
  flex: 1;
}

.task-title {
  font-size: 0.875rem;
  font-weight: 700;
  color: #333;
  margin-bottom: 0.5rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-meta {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.task-type {
  background: #17a2b8;
  color: white;
  border: 1px solid #000;
  border-radius: 4px;
  padding: 0.125rem 0.5rem;
  font-size: 0.625rem;
  font-weight: 700;
  text-transform: uppercase;
}

.task-status {
  border: 1px solid #000;
  border-radius: 4px;
  padding: 0.125rem 0.5rem;
  font-size: 0.625rem;
  font-weight: 700;
  text-transform: uppercase;
}

.task-status.active {
  background: #007bff;
  color: white;
}

.task-status.voting {
  background: #ffc107;
  color: #000;
}

.task-status.completed {
  background: #28a745;
  color: white;
}

.pinning-section {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.time-remaining,
.key-holder {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: rgba(0, 0, 0, 0.05);
  border: 1px solid #000;
  border-radius: 4px;
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  font-weight: 700;
}

.time-icon,
.key-icon {
  font-size: 0.875rem;
}

.time-text,
.holder-text {
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  font-size: 0.625rem;
}

.click-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  background: linear-gradient(135deg, #28a745, #20c997);
  color: white;
  border: 2px solid #000;
  border-radius: 6px;
  padding: 0.5rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  font-size: 0.75rem;
  margin-top: auto;
}

.click-arrow {
  font-size: 1rem;
  font-weight: 900;
}

.carousel-dots {
  display: flex;
  justify-content: center;
  gap: 0.5rem;
  margin-top: 0.75rem;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  border: 2px solid #000;
  background: rgba(255, 255, 255, 0.5);
  cursor: pointer;
  transition: all 0.2s ease;
}

.dot.active {
  background: white;
  box-shadow: 2px 2px 0 #000;
}

.dot:hover {
  background: white;
  transform: scale(1.2);
}

/* Mobile responsive */
@media (max-width: 768px) {
  .pinned-carousel {
    height: 280px;
    padding: 0.75rem;
    border-width: 3px;
    box-shadow: 4px 4px 0 #000;
  }

  .carousel-title {
    font-size: 1rem;
    letter-spacing: 0.5px;
  }

  .slide-content {
    padding: 0.75rem;
    gap: 0.5rem;
    border-width: 2px;
    box-shadow: 2px 2px 0 #000;
  }

  .position-indicator {
    width: 28px;
    height: 28px;
    font-size: 0.75rem;
    top: -6px;
    right: -6px;
  }

  .position-crown {
    font-size: 0.875rem;
    top: -6px;
    right: -6px;
  }

  .username {
    font-size: 0.875rem;
  }

  .task-title {
    font-size: 0.75rem;
  }

  .empty-text {
    font-size: 1rem;
  }

  .empty-subtitle {
    font-size: 0.75rem;
  }
}
</style>