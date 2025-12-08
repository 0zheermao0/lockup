<template>
  <div class="task-broadcast">
    <div class="broadcast-container" v-if="taskUpdates.length > 0">
      <div class="broadcast-icon">📢</div>
      <div class="broadcast-content">
        <div
          class="broadcast-item"
          :class="{ active: currentIndex === index }"
          v-for="(update, index) in taskUpdates"
          :key="update.id"
          @click="goToTask(update.task_id)"
        >
          <span class="broadcast-text">{{ update.message }}</span>
        </div>
      </div>
    </div>

    <!-- Fallback when no updates -->
    <div class="broadcast-container fallback" v-else-if="!isLoading">
      <div class="broadcast-icon">💭</div>
      <div class="broadcast-content">
        <div class="broadcast-item active">
          <span class="broadcast-text">暂无最新任务动态，快来创建第一个带锁任务吧！</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { tasksApi } from '../lib/api-tasks'
import { formatDistanceToNow } from '../lib/utils'

interface TaskUpdate {
  id: string
  task_id: string
  task_title: string
  status: string
  message: string
  created_at: string
}

const router = useRouter()
const taskUpdates = ref<TaskUpdate[]>([])
const currentIndex = ref(0)
const intervalId = ref<number>()
const fetchIntervalId = ref<number>()
const isLoading = ref(true)

// 轮播间隔时间（毫秒）
const CAROUSEL_INTERVAL = 4000
// 数据刷新间隔时间（毫秒）
const FETCH_INTERVAL = 30000

const formatTime = (dateTime: string) => {
  return formatDistanceToNow(dateTime)
}

const goToTask = (taskId: string) => {
  router.push({ name: 'task-detail', params: { id: taskId } })
}

const fetchTaskUpdates = async () => {
  try {
    isLoading.value = true

    // 获取最新的lock任务列表，筛选出状态变化的任务
    const tasks = await tasksApi.getTasksList({
      task_type: 'lock',
      page_size: 20
    })

    if (!Array.isArray(tasks)) {
      console.warn('Tasks response is not an array:', tasks)
      return
    }

    // 生成广播消息
    const updates: TaskUpdate[] = []

    for (const task of tasks) {
      // 确保任务有必要的字段
      if (!task || !task.id || !task.title || !task.user?.username) {
        continue
      }

      let message = ''

      if (task.status === 'active') {
        // 检查任务是否是最近开始的（24小时内）
        const startTime = task.start_time ? new Date(task.start_time).getTime() : new Date(task.updated_at).getTime()
        const twentyFourHoursAgo = Date.now() - 24 * 60 * 60 * 1000
        if (startTime > twentyFourHoursAgo) {
          message = `🚀 ${task.user.username} 的任务「${task.title}」正在进行中`
        }
      } else if (task.status === 'voting') {
        // 投票期任务
        message = `🗳️ 任务「${task.title}」进入投票期，快来参与投票！`
      } else if (task.status === 'completed') {
        // 只显示最近完成的任务（1小时内）
        const completedTime = new Date(task.completed_at || task.updated_at).getTime()
        const oneHourAgo = Date.now() - 60 * 60 * 1000
        if (completedTime > oneHourAgo) {
          message = `🎉 恭喜 ${task.user.username} 完成了任务「${task.title}」！`
        }
      }

      if (message) {
        updates.push({
          id: `${task.id}-${task.status}`,
          task_id: task.id,
          task_title: task.title,
          status: task.status,
          message,
          created_at: task.updated_at || task.created_at
        })
      }
    }

    // 按时间排序，最新的在前
    updates.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())

    // 只保留最新的3条
    const newUpdates = updates.slice(0, 3)

    // 检查是否有新的更新
    const hasNewUpdates = JSON.stringify(newUpdates) !== JSON.stringify(taskUpdates.value)

    if (hasNewUpdates) {
      taskUpdates.value = newUpdates

      // 重置轮播索引
      if (taskUpdates.value.length > 0) {
        currentIndex.value = 0
      }
    }

    console.log('Task updates fetched:', taskUpdates.value.length, 'updates')
  } catch (error) {
    console.error('Error fetching task updates:', error)
    // 在错误情况下不清空现有数据，保持用户体验
  } finally {
    isLoading.value = false
  }
}

const startCarousel = () => {
  if (taskUpdates.value.length <= 1) return

  intervalId.value = window.setInterval(() => {
    currentIndex.value = (currentIndex.value + 1) % taskUpdates.value.length
  }, CAROUSEL_INTERVAL)
}

const stopCarousel = () => {
  if (intervalId.value) {
    clearInterval(intervalId.value)
    intervalId.value = undefined
  }
}

const startFetchInterval = () => {
  fetchIntervalId.value = window.setInterval(() => {
    fetchTaskUpdates()
  }, FETCH_INTERVAL)
}

const stopFetchInterval = () => {
  if (fetchIntervalId.value) {
    clearInterval(fetchIntervalId.value)
    fetchIntervalId.value = undefined
  }
}

// 监听任务更新数量变化，重新启动轮播
const restartCarousel = () => {
  stopCarousel()
  if (taskUpdates.value.length > 1) {
    startCarousel()
  }
}

// 监听taskUpdates变化
const unwatchTaskUpdates = computed(() => taskUpdates.value.length)
const watchTaskUpdates = () => {
  restartCarousel()
}

onMounted(async () => {
  // 初始化获取数据
  await fetchTaskUpdates()

  // 启动轮播
  restartCarousel()

  // 启动定期刷新
  startFetchInterval()
})

onUnmounted(() => {
  stopCarousel()
  stopFetchInterval()
})

// 监听数据变化重启轮播
const prevLength = ref(0)
const checkForUpdates = () => {
  if (taskUpdates.value.length !== prevLength.value) {
    prevLength.value = taskUpdates.value.length
    restartCarousel()
  }
}

// 使用 watch 替代 computed 来监听变化
import { watch } from 'vue'
watch(() => taskUpdates.value.length, () => {
  restartCarousel()
})
</script>

<style scoped>
.task-broadcast {
  /* 移除margin，让父容器控制布局 */
}

.broadcast-container {
  background: linear-gradient(135deg, #667eea, #764ba2);
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

.broadcast-container.fallback {
  background: linear-gradient(135deg, #95a5a6, #7f8c8d);
  opacity: 0.8;
}

.broadcast-icon {
  font-size: 1rem;
  flex-shrink: 0;
  animation: pulse 2s infinite;
  line-height: 1;
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.1);
  }
}

.broadcast-content {
  flex: 1;
  position: relative;
  height: 100%;
  overflow: hidden;
}

.broadcast-item {
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

.broadcast-item.active {
  opacity: 1;
  transform: translateY(0);
}

.broadcast-item:hover {
  background-color: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  padding: 0 0.4rem;
  margin: 0 -0.4rem;
}

.broadcast-text {
  color: white;
  font-weight: 600;
  font-size: 0.85rem;
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  width: 100%;
}

/* 移动端响应式 */
@media (max-width: 768px) {
  .broadcast-container {
    padding: 0.35rem 0.6rem;
    height: 28px;
    gap: 0.5rem;
    width: 100%;
    min-width: auto;
  }

  .broadcast-icon {
    font-size: 0.9rem;
  }

  .broadcast-content {
    flex: 1;
    min-width: 0;
  }

  .broadcast-text {
    font-size: 0.75rem;
    line-height: 1.1;
  }
}

/* 超小屏幕优化 */
@media (max-width: 480px) {
  .broadcast-container {
    padding: 0.3rem 0.5rem;
    height: 26px;
    gap: 0.4rem;
    width: 100%;
    min-width: auto;
  }

  .broadcast-icon {
    font-size: 0.8rem;
  }

  .broadcast-content {
    flex: 1;
    min-width: 0;
  }

  .broadcast-text {
    font-size: 0.7rem;
    line-height: 1.1;
  }
}
</style>