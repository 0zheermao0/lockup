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
              <span class="count-badge">{{ taskCounts?.lock_tasks?.all || 0 }}</span>
            </button>
            <button
              @click="activeTaskType = 'board'"
              :class="['task-type-tab', { active: activeTaskType === 'board' }]"
            >
              📋 任务板
              <span class="count-badge">{{ taskCounts?.board_tasks?.all || 0 }}</span>
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

            <!-- Sorting Dropdown -->
            <div class="sort-dropdown" @click.stop>
              <button
                @click="showSortDropdown = !showSortDropdown"
                class="sort-btn"
                :class="{ active: showSortDropdown }"
              >
                <span class="sort-icon">⚡</span>
                <span class="sort-text">{{ getSortLabel() }}</span>
                <span class="dropdown-arrow" :class="{ rotated: showSortDropdown }">▼</span>
              </button>

              <div v-if="showSortDropdown" class="sort-options">
                <div class="sort-section">
                  <div class="sort-section-title">排序方式</div>
                  <button
                    @click="setSortBy('remaining_time')"
                    :class="['sort-option', { active: sortBy === 'remaining_time' }]"
                  >
                    ⏰ 剩余时间
                  </button>
                  <button
                    @click="setSortBy('created_time')"
                    :class="['sort-option', { active: sortBy === 'created_time' }]"
                  >
                    📅 创建时间
                  </button>
                  <button
                    @click="setSortBy('end_time')"
                    :class="['sort-option', { active: sortBy === 'end_time' }]"
                  >
                    🏁 结束时间
                  </button>
                </div>

                <div class="sort-divider"></div>

                <div class="sort-section">
                  <div class="sort-section-title">排序顺序</div>
                  <button
                    @click="toggleSortOrder()"
                    class="sort-order-btn"
                  >
                    <span v-if="sortOrder === 'desc'">📉 降序 (大到小)</span>
                    <span v-else>📈 升序 (小到大)</span>
                  </button>
                </div>
              </div>
            </div>
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
                    v-if="canAddOvertime(task)"
                    @click="addOvertime(task, $event)"
                    class="overtime-btn"
                    title="随机加时"
                  >
                    ⏰
                  </button>
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
                <!-- 剩余时间显示 -->
                <div v-if="getTimeRemaining(task) > 0" class="task-time-remaining">
                  <span class="label">剩余时间:</span>
                  <span class="value countdown" :class="{ 'overtime': getTimeRemaining(task) <= 0 }">
                    {{ formatTimeRemaining(getTimeRemaining(task)) }}
                  </span>
                </div>
                <div v-else-if="(task.status === 'active' && task.task_type === 'lock') || (task.status === 'taken' && task.task_type === 'board')" class="task-time-remaining">
                  <span class="label">状态:</span>
                  <span class="value overtime">倒计时已结束</span>
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
import { ref, onMounted, computed, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useTasksStore } from '../stores/tasks'
import { useInfiniteScroll } from '../composables/useInfiniteScroll'
import { formatDistanceToNow } from '../lib/utils'
import { tasksApi } from '../lib/api-tasks'
import { smartGoBack } from '../utils/navigation'
import CreateTaskModal from '../components/CreateTaskModal.vue'
import NotificationBell from '../components/NotificationBell.vue'
import type { Task } from '../types/index.js'
import type { LockTask } from '../types'

const router = useRouter()
const authStore = useAuthStore()
const tasksStore = useTasksStore()

// State
const showCreateModal = ref(false)
const activeFilter = ref('active')
const activeTaskType = ref<'lock' | 'board'>('lock')
const currentTime = ref(Date.now())
const progressInterval = ref<number>()
const taskCounts = ref<any>(null)
const countsLoading = ref(false)

// Sorting state
const sortBy = ref<'remaining_time' | 'created_time' | 'end_time'>('created_time')
const sortOrder = ref<'asc' | 'desc'>('desc')
const showSortDropdown = ref(false)

// Create a function to get the appropriate API call based on current filters
const getFilteredTasks = async (page: number, pageSize: number) => {
  const extraFilters: any = {
    task_type: activeTaskType.value
  }

  // Apply filter based on activeFilter
  if (activeFilter.value === 'active') {
    extraFilters.status = 'active'
  } else if (activeFilter.value === 'voting') {
    extraFilters.status = 'voting'
  } else if (activeFilter.value === 'completed') {
    extraFilters.status = 'completed'
  } else if (activeFilter.value === 'my-tasks') {
    extraFilters.my_tasks = true
  } else if (activeFilter.value === 'open') {
    extraFilters.status = 'open'
  } else if (activeFilter.value === 'taken') {
    extraFilters.status = 'taken'
  } else if (activeFilter.value === 'submitted') {
    extraFilters.status = 'submitted'
  } else if (activeFilter.value === 'my-published') {
    extraFilters.my_tasks = true
  } else if (activeFilter.value === 'my-taken') {
    extraFilters.my_taken = true
  }
  // 'all' doesn't need additional filters

  try {
    const response = await tasksStore.getPaginatedTasks(page, pageSize, extraFilters)
    return response
  } catch (error) {
    console.error('API error:', error)
    throw error
  }
}

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
  getFilteredTasks,
  {
    initialPageSize: 10,
    threshold: 200,
    loadDelay: 300
  }
)

// For display purposes, use all tasks since they're already filtered
const currentTasks = computed(() => tasks.value)
const lockTasks = computed(() => tasks.value) // Not needed anymore since we filter server-side
const boardTasks = computed(() => tasks.value) // Not needed anymore since we filter server-side

// Filter tabs based on task type
const lockFilterTabs = computed(() => {
  if (!taskCounts.value) {
    // Fallback to showing counts without numbers when API data is not available
    return [
      { key: 'all', label: '全部', count: 0 },
      { key: 'active', label: '进行中', count: 0 },
      { key: 'voting', label: '投票中', count: 0 },
      { key: 'completed', label: '已完成', count: 0 },
      { key: 'my-tasks', label: '我的任务', count: 0 }
    ]
  }
  return [
    { key: 'all', label: '全部', count: taskCounts.value.lock_tasks.all },
    { key: 'active', label: '进行中', count: taskCounts.value.lock_tasks.active },
    { key: 'voting', label: '投票中', count: taskCounts.value.lock_tasks.voting },
    { key: 'completed', label: '已完成', count: taskCounts.value.lock_tasks.completed },
    { key: 'my-tasks', label: '我的任务', count: taskCounts.value.lock_tasks.my_tasks }
  ]
})

const boardFilterTabs = computed(() => {
  if (!taskCounts.value) {
    // Fallback to showing counts without numbers when API data is not available
    return [
      { key: 'all', label: '全部', count: 0 },
      { key: 'open', label: '开放中', count: 0 },
      { key: 'taken', label: '已接取', count: 0 },
      { key: 'submitted', label: '已提交', count: 0 },
      { key: 'completed', label: '已完成', count: 0 },
      { key: 'my-published', label: '我发布的', count: 0 },
      { key: 'my-taken', label: '我接取的', count: 0 }
    ]
  }
  return [
    { key: 'all', label: '全部', count: taskCounts.value.board_tasks.all },
    { key: 'open', label: '开放中', count: taskCounts.value.board_tasks.open },
    { key: 'taken', label: '已接取', count: taskCounts.value.board_tasks.taken },
    { key: 'submitted', label: '已提交', count: taskCounts.value.board_tasks.submitted },
    { key: 'completed', label: '已完成', count: taskCounts.value.board_tasks.completed },
    { key: 'my-published', label: '我发布的', count: taskCounts.value.board_tasks.my_published },
    { key: 'my-taken', label: '我接取的', count: taskCounts.value.board_tasks.my_taken }
  ]
})

const currentFilterTabs = computed(() => {
  return activeTaskType.value === 'lock' ? lockFilterTabs.value : boardFilterTabs.value
})

// Since we're using server-side filtering, we only need to sort the tasks
const filteredTasks = computed(() => {
  // Tasks are already filtered server-side, just apply sorting
  return sortTasks(currentTasks.value)
})

// Sorting functions
const sortTasks = (tasks: Task[]) => {
  const sorted = [...tasks].sort((a, b) => {
    let aValue: number
    let bValue: number

    switch (sortBy.value) {
      case 'remaining_time':
        aValue = getTimeRemaining(a)
        bValue = getTimeRemaining(b)
        // For tasks with no remaining time (completed/ended), put them at the end
        if (aValue === 0 && bValue === 0) return 0
        if (aValue === 0) return 1
        if (bValue === 0) return -1
        break

      case 'created_time':
        aValue = new Date(a.created_at).getTime()
        bValue = new Date(b.created_at).getTime()
        break

      case 'end_time':
        // Handle tasks without end_time
        const aEndTime = getTaskEndTime(a)
        const bEndTime = getTaskEndTime(b)
        if (!aEndTime && !bEndTime) return 0
        if (!aEndTime) return 1
        if (!bEndTime) return -1
        aValue = aEndTime
        bValue = bEndTime
        break

      default:
        return 0
    }

    return sortOrder.value === 'asc' ? aValue - bValue : bValue - aValue
  })

  return sorted
}

const getTaskEndTime = (task: Task) => {
  if (task.task_type === 'lock') {
    const lockTask = task as any
    return lockTask.end_time ? new Date(lockTask.end_time).getTime() : null
  } else if (task.task_type === 'board') {
    const boardTask = task as any
    return boardTask.deadline ? new Date(boardTask.deadline).getTime() : null
  }
  return null
}

const toggleSortOrder = () => {
  sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
}

const setSortBy = (criteria: 'remaining_time' | 'created_time' | 'end_time') => {
  sortBy.value = criteria
  showSortDropdown.value = false
}

const getSortLabel = () => {
  const labels = {
    remaining_time: '剩余时间',
    created_time: '创建时间',
    end_time: '结束时间'
  }
  const orderLabel = sortOrder.value === 'asc' ? '升序' : '降序'
  return `${labels[sortBy.value]} (${orderLabel})`
}

const goBack = () => {
  smartGoBack(router, { defaultRoute: 'home' })
}

const openCreateModal = () => {
  showCreateModal.value = true
}

const closeCreateModal = () => {
  showCreateModal.value = false
}

// Fetch task counts
const fetchTaskCounts = async () => {
  if (countsLoading.value) return

  countsLoading.value = true
  try {
    taskCounts.value = await tasksApi.getTaskCounts()
  } catch (error) {
    console.error('Failed to fetch task counts:', error)
  } finally {
    countsLoading.value = false
  }
}

const handleTaskCreated = async () => {
  // Refresh the task list
  refresh()

  // Refresh task counts
  await fetchTaskCounts()

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
    // Refresh task counts after deletion
    await fetchTaskCounts()
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
  const now = currentTime.value

  if (now <= start) return 0
  if (now >= end) return 100

  return ((now - start) / (end - start)) * 100
}

// Time remaining calculation
const getTimeRemaining = (task: Task) => {
  if (!task) return 0

  // Lock tasks time remaining
  if (task.task_type === 'lock' && task.status === 'active') {
    const lockTask = task as any
    if (lockTask.end_time) {
      const end = new Date(lockTask.end_time).getTime()
      const now = currentTime.value
      return Math.max(0, end - now)
    }
  }

  // Board tasks time remaining
  if (task.task_type === 'board' && task.status === 'taken') {
    const boardTask = task as any
    if (boardTask.deadline) {
      const end = new Date(boardTask.deadline).getTime()
      const now = currentTime.value
      return Math.max(0, end - now)
    }
  }

  return 0
}

// Format time remaining
const formatTimeRemaining = (milliseconds: number) => {
  const hours = Math.floor(milliseconds / (1000 * 60 * 60))
  const minutes = Math.floor((milliseconds % (1000 * 60 * 60)) / (1000 * 60))
  const seconds = Math.floor((milliseconds % (1000 * 60)) / 1000)

  if (hours > 0) {
    return `${hours}小时${minutes}分钟`
  } else if (minutes > 0) {
    return `${minutes}分钟${seconds}秒`
  } else {
    return `${seconds}秒`
  }
}

// Check if task can have overtime added
const canAddOvertime = (task: Task) => {
  if (!task) return false
  // Can add overtime if it's a lock task, status is active, and not own task
  return task.task_type === 'lock' &&
         task.status === 'active' &&
         task.user.id !== authStore.user?.id
}

// Add overtime function
const addOvertime = async (task: Task, event: Event) => {
  event.stopPropagation() // Prevent card click

  if (!task || !canAddOvertime(task)) return

  try {
    const result = await tasksApi.addOvertime(task.id)

    // Update the task's end time in the local list
    const lockTask = task as any
    if (result.new_end_time && lockTask) {
      lockTask.end_time = result.new_end_time
    }

    // Refresh user data to update lock status
    authStore.refreshUser()

    // Show success message
    alert(`成功为任务加时 ${result.overtime_minutes} 分钟！`)
    console.log('任务加时成功:', result)
  } catch (error: any) {
    console.error('Error adding overtime:', error)

    // Handle specific error messages
    let errorMessage = '加时失败，请重试'

    // Check for specific error messages in the response data
    if (error.data?.error) {
      errorMessage = error.data.error
    } else if (error.status === 404) {
      errorMessage = '任务不存在或已被删除'
    } else if (error.status === 403) {
      errorMessage = '您没有权限为此任务加时'
    } else if (error.status === 500) {
      errorMessage = '服务器内部错误，请稍后重试'
    } else if (error.message && !error.message.includes('HTTP')) {
      errorMessage = error.message
    } else if (error.message) {
      errorMessage = `网络错误：${error.message}`
    }

    alert(`❌ ${errorMessage}`)
  }
}

// Start progress update timer
const startProgressUpdate = () => {
  // Clear any existing interval
  if (progressInterval.value) {
    clearInterval(progressInterval.value)
  }

  progressInterval.value = window.setInterval(() => {
    currentTime.value = Date.now()
  }, 1000)
}

// Close dropdown when clicking outside
const handleClickOutside = (event: Event) => {
  const target = event.target as HTMLElement
  if (!target.closest('.sort-dropdown')) {
    showSortDropdown.value = false
  }
}

// Watch for task type changes and reset filter accordingly
watch(activeTaskType, (newType) => {
  if (newType === 'lock') {
    activeFilter.value = 'active'  // 带锁任务默认显示"进行中"
  } else {
    activeFilter.value = 'all'     // 任务板默认显示"全部"
  }
  // Refresh tasks when task type changes
  refresh()
})

// Watch for filter changes and refresh tasks
watch(activeFilter, () => {
  refresh()
})

onMounted(async () => {
  // Initialize task list and counts in parallel
  await Promise.all([
    initialize(),
    fetchTaskCounts()
  ])

  startProgressUpdate()
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  if (progressInterval.value) {
    clearInterval(progressInterval.value)
  }
  document.removeEventListener('click', handleClickOutside)
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

.delete-btn, .overtime-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.5rem;
  border-radius: 4px;
  background-color: #f8f9fa;
  margin-left: 0.5rem;
}

.delete-btn:hover {
  background-color: #dc3545;
  color: white;
}

.overtime-btn {
  background-color: #fd7e14;
  color: white;
  font-size: 1rem;
}

.overtime-btn:hover {
  background-color: #e76500;
  transform: scale(1.1);
}

.task-actions {
  display: flex;
  align-items: center;
}

.countdown {
  font-weight: bold;
  color: #007bff;
  animation: pulse-countdown 2s infinite;
}

.countdown.overtime {
  color: #dc3545;
  animation: pulse-danger 1s infinite;
}

.overtime {
  color: #dc3545;
  font-weight: bold;
}

@keyframes pulse-countdown {
  0% { opacity: 1; }
  50% { opacity: 0.7; }
  100% { opacity: 1; }
}

@keyframes pulse-danger {
  0% { opacity: 1; }
  50% { opacity: 0.5; }
  100% { opacity: 1; }
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

.task-duration, .task-time, .task-time-remaining {
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

/* Sorting dropdown styles */
.sort-dropdown {
  position: relative;
  margin-left: auto;
}

.sort-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: white;
  border: 2px solid #007bff;
  border-radius: 20px;
  padding: 0.5rem 1rem;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 500;
  color: #007bff;
  transition: all 0.2s;
}

.sort-btn:hover,
.sort-btn.active {
  background-color: #007bff;
  color: white;
}

.sort-icon {
  font-size: 1rem;
}

.sort-text {
  font-weight: 600;
}

.dropdown-arrow {
  font-size: 0.75rem;
  transition: transform 0.2s;
}

.dropdown-arrow.rotated {
  transform: rotate(180deg);
}

.sort-options {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  background: white;
  border: 2px solid #000;
  border-radius: 8px;
  box-shadow: 4px 4px 0 #000;
  min-width: 200px;
  z-index: 1000;
  overflow: hidden;
}

.sort-section {
  padding: 0.75rem;
}

.sort-section-title {
  font-size: 0.75rem;
  font-weight: bold;
  text-transform: uppercase;
  color: #666;
  margin-bottom: 0.5rem;
  letter-spacing: 0.5px;
}

.sort-option,
.sort-order-btn {
  display: block;
  width: 100%;
  background: none;
  border: none;
  padding: 0.5rem 0.75rem;
  text-align: left;
  cursor: pointer;
  border-radius: 4px;
  margin-bottom: 0.25rem;
  font-size: 0.875rem;
  transition: all 0.2s;
}

.sort-option:hover,
.sort-order-btn:hover {
  background-color: #f8f9fa;
}

.sort-option.active {
  background-color: #007bff;
  color: white;
  font-weight: 600;
}

.sort-order-btn {
  background-color: #28a745;
  color: white;
  font-weight: 600;
  text-align: center;
}

.sort-order-btn:hover {
  background-color: #218838;
}

.sort-divider {
  height: 1px;
  background-color: #e9ecef;
  margin: 0 0.75rem;
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

  .filter-tabs {
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .sort-dropdown {
    margin-left: 0;
    margin-top: 0.5rem;
    width: 100%;
  }

  .sort-btn {
    width: 100%;
    justify-content: center;
  }

  .sort-options {
    right: auto;
    left: 0;
    width: 100%;
  }
}
</style>