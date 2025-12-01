<template>
  <div class="task-view">
    <!-- Header -->
    <header class="header">
      <div class="header-content">
        <button @click="goBack" class="back-btn">← 返回</button>
        <h1>任务管理</h1>
        <div class="header-actions">
          <NotificationBell />
          <button @click="openCreateModal" class="create-btn">创建任务</button>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="main-content">
      <div class="container">
        <!-- Task Type Tabs -->
        <section class="task-type-section">
          <div class="task-type-tabs">
            <button
              @click="activeTaskType = 'lock'"
              :class="['task-type-tab', { active: activeTaskType === 'lock' }]"
            >
              🔒 带锁任务
              <span class="count-badge">{{ lockTasks.length }}</span>
            </button>
            <button
              @click="activeTaskType = 'board'"
              :class="['task-type-tab', { active: activeTaskType === 'board' }]"
            >
              📋 任务板
              <span class="count-badge">{{ boardTasks.length }}</span>
            </button>
          </div>
        </section>

        <!-- Task Filters -->
        <section class="filters-section">
          <div class="filter-tabs">
            <button
              v-for="tab in currentFilterTabs"
              :key="tab.key"
              @click="activeFilter = tab.key"
              :class="['filter-tab', { active: activeFilter === tab.key }]"
            >
              {{ tab.label }}
              <span v-if="tab.count" class="count-badge">{{ tab.count }}</span>
            </button>
          </div>
        </section>

        <!-- Tasks List -->
        <section class="tasks-section">
          <div v-if="isInitialLoading" class="loading">
            加载中...
          </div>

          <div v-else-if="error" class="error">
            {{ error }}
          </div>

          <div v-else-if="isEmpty" class="empty">
            <div class="empty-icon">📋</div>
            <div class="empty-text">还没有任务</div>
            <button @click="openCreateModal" class="create-first-btn">创建第一个任务</button>
          </div>

          <div v-else class="tasks-list">
            <div
              v-for="task in filteredTasks"
              :key="task.id"
              class="task-card"
              @click="goToTaskDetail(task.id)"
            >
              <div class="task-header">
                <div class="task-info">
                  <h3 class="task-title">{{ task.title }}</h3>
                  <div class="task-meta">
                    <span v-if="task.task_type === 'lock' && task.unlock_type" class="task-type">
                      {{ getTaskTypeText(task.unlock_type) }}
                    </span>
                    <span v-if="task.task_type === 'board'" class="task-type">
                      悬赏任务
                    </span>
                    <span v-if="task.task_type === 'lock' && task.difficulty" class="task-difficulty" :class="task.difficulty">
                      {{ getDifficultyText(task.difficulty) }}
                    </span>
                    <span v-if="task.task_type === 'board' && task.reward" class="task-reward">
                      {{ task.reward }} 积分
                    </span>
                    <span class="task-status" :class="task.status">
                      {{ getStatusText(task.status) }}
                    </span>
                  </div>
                </div>
                <div class="task-actions">
                  <button
                    v-if="canDeleteTask(task)"
                    @click.stop="deleteTask(task)"
                    class="delete-btn"
                    title="删除任务"
                  >
                    🗑️
                  </button>
                </div>
              </div>

              <div class="task-content">
                <p class="task-description">{{ task.description }}</p>
              </div>

              <div class="task-details">
                <div class="task-duration">
                  <span class="label">持续时间:</span>
                  <span class="value">{{ formatDuration(task) }}</span>
                </div>
                <div v-if="task.task_type === 'lock' && (task as any).started_at" class="task-time">
                  <span class="label">开始时间:</span>
                  <span class="value">{{ formatDateTime((task as any).started_at) }}</span>
                </div>
                <div v-if="task.task_type === 'lock' && (task as any).end_time" class="task-time">
                  <span class="label">结束时间:</span>
                  <span class="value">{{ formatDateTime((task as any).end_time) }}</span>
                </div>
              </div>

              <div class="task-progress">
                <div v-if="task.status === 'active'" class="progress-bar">
                  <div class="progress-fill" :style="{ width: getProgressPercent(task) + '%' }"></div>
                </div>
                <div class="task-user">
                  <div class="avatar">
                    {{ task.user.username.charAt(0).toUpperCase() }}
                  </div>
                  <span class="username">{{ task.user.username }}</span>
                </div>
              </div>
            </div>

            <!-- 加载更多指示器 -->
            <div v-if="isLoadingMore" class="loading-more">
              正在加载更多任务...
            </div>

            <!-- 没有更多内容提示 -->
            <div v-else-if="!hasMore && tasks.length > 0" class="no-more">
              没有更多任务了
            </div>
          </div>
        </section>
      </div>
    </main>

    <!-- Create Task Modal -->
    <CreateTaskModal
      :is-visible="showCreateModal"
      @close="closeCreateModal"
      @success="handleTaskCreated"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useTasksStore } from '../stores/tasks'
import { useInfiniteScroll } from '../composables/useInfiniteScroll'
import { formatDistanceToNow } from '../lib/utils'
import CreateTaskModal from '../components/CreateTaskModal.vue'
import NotificationBell from '../components/NotificationBell.vue'
import type { Task } from '../types/index.js'
import type { LockTask } from '../types'

const router = useRouter()
const authStore = useAuthStore()
const tasksStore = useTasksStore()

// State
const showCreateModal = ref(false)
const activeFilter = ref('all')
const activeTaskType = ref<'lock' | 'board'>('lock')

// 无限滚动设置
const {
  items: tasks,
  loading,
  error,
  hasMore,
  isEmpty,
  isLoadingMore,
  isInitialLoading,
  initialize,
  refresh
} = useInfiniteScroll(
  tasksStore.getPaginatedTasks,
  {
    initialPageSize: 20,
    threshold: 200,
    loadDelay: 300
  }
)

// Task type separation
const lockTasks = computed(() => tasks.value.filter(task => task.task_type === 'lock'))
const boardTasks = computed(() => tasks.value.filter(task => task.task_type === 'board'))

// Current tasks based on active type
const currentTasks = computed(() => {
  return activeTaskType.value === 'lock' ? lockTasks.value : boardTasks.value
})

// Filter tabs based on task type
const lockFilterTabs = computed(() => [
  { key: 'all', label: '全部', count: lockTasks.value.length },
  { key: 'active', label: '进行中', count: lockTasks.value.filter(t => t.status === 'active').length },
  { key: 'voting', label: '投票中', count: lockTasks.value.filter(t => t.status === 'voting').length },
  { key: 'completed', label: '已完成', count: lockTasks.value.filter(t => t.status === 'completed').length },
  { key: 'my-tasks', label: '我的任务', count: lockTasks.value.filter(t => t.user.id === authStore.user?.id).length }
])

const boardFilterTabs = computed(() => [
  { key: 'all', label: '全部', count: boardTasks.value.length },
  { key: 'open', label: '开放中', count: boardTasks.value.filter(t => t.status === 'open').length },
  { key: 'taken', label: '已接取', count: boardTasks.value.filter(t => t.status === 'taken').length },
  { key: 'submitted', label: '已提交', count: boardTasks.value.filter(t => t.status === 'submitted').length },
  { key: 'completed', label: '已完成', count: boardTasks.value.filter(t => t.status === 'completed').length },
  { key: 'my-published', label: '我发布的', count: boardTasks.value.filter(t => t.user.id === authStore.user?.id).length },
  { key: 'my-taken', label: '我接取的', count: boardTasks.value.filter(t => t.taker?.id === authStore.user?.id).length }
])

const currentFilterTabs = computed(() => {
  return activeTaskType.value === 'lock' ? lockFilterTabs.value : boardFilterTabs.value
})

// Filtered tasks
const filteredTasks = computed(() => {
  const tasks = currentTasks.value

  if (activeTaskType.value === 'lock') {
    switch (activeFilter.value) {
      case 'active':
        return tasks.filter(task => task.status === 'active')
      case 'voting':
        return tasks.filter(task => task.status === 'voting')
      case 'completed':
        return tasks.filter(task => task.status === 'completed')
      case 'my-tasks':
        return tasks.filter(task => task.user.id === authStore.user?.id)
      default:
        return tasks
    }
  } else {
    switch (activeFilter.value) {
      case 'open':
        return tasks.filter(task => task.status === 'open')
      case 'taken':
        return tasks.filter(task => task.status === 'taken')
      case 'submitted':
        return tasks.filter(task => task.status === 'submitted')
      case 'completed':
        return tasks.filter(task => task.status === 'completed')
      case 'my-published':
        return tasks.filter(task => task.user.id === authStore.user?.id)
      case 'my-taken':
        return tasks.filter(task => task.task_type === 'board' && task.taker?.id === authStore.user?.id)
      default:
        return tasks
    }
  }
})

const goBack = () => {
  router.back()
}

const openCreateModal = () => {
  showCreateModal.value = true
}

const closeCreateModal = () => {
  showCreateModal.value = false
}

const handleTaskCreated = async () => {
  // Refresh the task list
  refresh()

  // Refresh user data to update lock status on homepage/profile
  try {
    await authStore.refreshUser()
  } catch (error) {
    console.error('Failed to refresh user data after task creation:', error)
  }
}

const canDeleteTask = (task: Task) => {
  return authStore.user?.id === task.user.id || authStore.user?.is_superuser
}

const deleteTask = async (task: Task) => {
  if (!confirm('确定要删除这个任务吗？')) {
    return
  }

  try {
    await tasksStore.deleteTask(task.id)
    console.log('任务删除成功')
  } catch (error) {
    console.error('Error deleting task:', error)
    alert('删除失败，请重试')
  }
}

const goToTaskDetail = (taskId: string) => {
  router.push({ name: 'task-detail', params: { id: taskId } })
}

const getTaskTypeText = (type: string) => {
  const texts = {
    time: '定时解锁',
    vote: '投票解锁'
  }
  return texts[type as keyof typeof texts] || type
}

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
    failed: '已失败',
    open: '开放中',
    taken: '已接取',
    submitted: '已提交'
  }
  return texts[status as keyof typeof texts] || status
}

const formatDuration = (task: Task) => {
  // For board tasks, show max_duration instead of duration_value
  if (task.task_type === 'board' && 'max_duration' in task && task.max_duration) {
    return `最长 ${task.max_duration} 小时`
  }

  // For lock tasks
  if (task.task_type === 'lock' && 'duration_value' in task) {
    if (!task.duration_value) return '-'

    const hours = Math.floor(task.duration_value / 60)
    const minutes = task.duration_value % 60

    if (task.duration_type === 'random' && 'duration_max' in task && task.duration_max) {
      const maxDuration = task.duration_max as number
      const maxHours = Math.floor(maxDuration / 60)
      const maxMinutes = maxDuration % 60
      return `${hours}小时${minutes}分钟 - ${maxHours}小时${maxMinutes}分钟`
    }

    return `${hours}小时${minutes}分钟`
  }

  return '-'
}

const formatDateTime = (dateTime: string) => {
  return new Date(dateTime).toLocaleString('zh-CN')
}

const getProgressPercent = (task: Task) => {
  if (task.status !== 'active' || task.task_type !== 'lock') {
    return 0
  }

  const lockTask = task as any
  if (!lockTask.started_at || !lockTask.end_time) {
    return 0
  }

  const start = new Date(lockTask.started_at).getTime()
  const end = new Date(lockTask.end_time).getTime()
  const now = new Date().getTime()

  if (now <= start) return 0
  if (now >= end) return 100

  return ((now - start) / (end - start)) * 100
}

onMounted(() => {
  initialize()
})
</script>

<style scoped>
.task-view {
  min-height: 100vh;
  background-color: #f5f5f5;
}

.header {
  background: white;
  border-bottom: 2px solid #000;
  padding: 1rem 0;
}

.header-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.back-btn, .create-btn {
  background: none;
  border: 1px solid #666;
  border-radius: 4px;
  padding: 0.5rem 1rem;
  cursor: pointer;
  font-size: 0.875rem;
}

.back-btn:hover {
  background-color: #f8f9fa;
}

.create-btn {
  background-color: #28a745;
  color: white;
  border-color: #28a745;
}

.create-btn:hover {
  background-color: #218838;
}

.header h1 {
  font-size: 1.5rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0;
}

.main-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem 1rem;
}

.task-type-section {
  margin-bottom: 2rem;
}

.task-type-tabs {
  display: flex;
  gap: 1rem;
}

.task-type-tab {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: white;
  border: 2px solid #000;
  border-radius: 8px;
  padding: 1rem 1.5rem;
  cursor: pointer;
  font-weight: 600;
  font-size: 1rem;
  transition: all 0.2s;
  box-shadow: 4px 4px 0 #000;
}

.task-type-tab:hover {
  transform: translateY(-2px);
  box-shadow: 6px 6px 0 #000;
}

.task-type-tab.active {
  background-color: #007bff;
  color: white;
  border-color: #007bff;
}

.filters-section {
  background: white;
  padding: 1rem;
  border-radius: 8px;
  border: 2px solid #000;
  box-shadow: 4px 4px 0 #000;
  margin-bottom: 2rem;
}

.filter-tabs {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.filter-tab {
  background: none;
  border: 1px solid #ddd;
  border-radius: 20px;
  padding: 0.5rem 1rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  transition: all 0.2s;
}

.filter-tab:hover {
  background-color: #f8f9fa;
}

.filter-tab.active {
  background-color: #007bff;
  color: white;
  border-color: #007bff;
}

.count-badge {
  background-color: rgba(255, 255, 255, 0.2);
  border-radius: 10px;
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  font-weight: bold;
}

.filter-tab.active .count-badge {
  background-color: rgba(255, 255, 255, 0.3);
}

.loading, .error, .empty, .loading-more, .no-more {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  border: 2px solid #000;
  box-shadow: 4px 4px 0 #000;
  text-align: center;
}

.loading-more {
  margin-top: 1.5rem;
  background-color: #f8f9fa;
  color: #666;
  padding: 1rem;
  font-size: 0.875rem;
}

.no-more {
  margin-top: 1.5rem;
  background-color: #e9ecef;
  color: #666;
  padding: 1rem;
  font-size: 0.875rem;
  font-style: italic;
}

.error {
  color: #dc3545;
  background-color: #f8d7da;
  border-color: #dc3545;
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.empty-text {
  font-size: 1.1rem;
  color: #666;
  margin-bottom: 1.5rem;
}

.create-first-btn {
  background-color: #28a745;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 0.75rem 1.5rem;
  cursor: pointer;
  font-weight: 600;
}

.create-first-btn:hover {
  background-color: #218838;
}

.tasks-list {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.task-card {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  border: 2px solid #000;
  box-shadow: 4px 4px 0 #000;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.task-card:hover {
  transform: translateY(-2px);
  box-shadow: 6px 6px 0 #000;
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.task-title {
  font-size: 1.1rem;
  font-weight: bold;
  margin: 0 0 0.5rem 0;
  color: #333;
}

.task-meta {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.task-type, .task-difficulty, .task-status, .task-reward {
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: bold;
  text-transform: uppercase;
}

.task-type {
  background-color: #17a2b8;
  color: white;
}

.task-reward {
  background-color: #ffc107;
  color: #212529;
}

.task-difficulty.easy {
  background-color: #28a745;
  color: white;
}

.task-difficulty.normal {
  background-color: #ffc107;
  color: #212529;
}

.task-difficulty.hard {
  background-color: #fd7e14;
  color: white;
}

.task-difficulty.hell {
  background-color: #dc3545;
  color: white;
}

.task-status.active {
  background-color: #007bff;
  color: white;
}

.task-status.voting {
  background-color: #ffc107;
  color: #212529;
  animation: pulse 2s infinite;
}

.task-status.completed {
  background-color: #28a745;
  color: white;
}

.task-status.failed {
  background-color: #dc3545;
  color: white;
}

.task-status.open {
  background-color: #28a745;
  color: white;
}

.task-status.taken {
  background-color: #fd7e14;
  color: white;
}

.task-status.submitted {
  background-color: #6f42c1;
  color: white;
}

.delete-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.5rem;
  border-radius: 4px;
  background-color: #f8f9fa;
}

.delete-btn:hover {
  background-color: #dc3545;
  color: white;
}

.task-description {
  color: #666;
  margin-bottom: 1rem;
  line-height: 1.5;
}

.task-details {
  margin-bottom: 1rem;
  font-size: 0.875rem;
}

.task-duration, .task-time {
  margin-bottom: 0.5rem;
}

.label {
  font-weight: 500;
  color: #666;
}

.value {
  color: #333;
  margin-left: 0.5rem;
}

.task-progress {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 1rem;
  border-top: 1px solid #e9ecef;
}

.progress-bar {
  flex: 1;
  height: 8px;
  background-color: #e9ecef;
  border-radius: 4px;
  overflow: hidden;
  margin-right: 1rem;
}

.progress-fill {
  height: 100%;
  background-color: #007bff;
  transition: width 0.3s ease;
}

.task-user {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.avatar {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background-color: #007bff;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 0.75rem;
}

.username {
  font-size: 0.875rem;
  color: #666;
}

/* Mobile responsive */
@media (max-width: 768px) {
  .header-content {
    padding: 0 1rem;
  }

  .main-content {
    padding: 1rem;
  }

  .task-header {
    flex-direction: column;
    gap: 0.5rem;
  }

  .task-meta {
    gap: 0.5rem;
  }

  .task-progress {
    flex-direction: column;
    gap: 1rem;
    align-items: stretch;
  }

  .progress-bar {
    margin-right: 0;
  }
}
</style>