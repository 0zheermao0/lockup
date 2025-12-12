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
                  <button
                    @click="setSortBy('user_activity')"
                    :class="['sort-option', { active: sortBy === 'user_activity' }]"
                  >
                    ⚡ 用户活跃度
                  </button>
                  <button
                    @click="setSortBy('difficulty')"
                    :class="['sort-option', { active: sortBy === 'difficulty' }]"
                  >
                    🔥 难度等级
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
                    v-if="canDeleteTask(task)"
                    @click.stop="deleteTask(task)"
                    class="action-btn delete-btn"
                    title="删除任务"
                  >
                    🗑️ 删除
                  </button>
                </div>
              </div>

              <!-- Quick Actions for Task Card -->
              <div v-if="canAddOvertime(task)" class="task-quick-actions">
                <button
                  @click="addOvertime(task, $event)"
                  class="task-quick-btn overtime-btn"
                  title="随机加时"
                >
                  ⏰ 随机加时
                </button>
              </div>

              <div class="task-content">
                <p class="task-description">{{ task.description }}</p>
              </div>

              <div class="task-details">
                <div class="task-duration">
                  <span class="label">持续时间:</span>
                  <span class="value">{{ formatDuration(task) }}</span>
                </div>
                <!-- 隐藏时间相关信息当 time_display_hidden 为 true 时 -->
                <div v-if="task.task_type === 'lock' && (task as any).started_at && !isTaskTimeHidden(task)" class="task-time">
                  <span class="label">开始时间:</span>
                  <span class="value">{{ formatDateTime((task as any).started_at) }}</span>
                </div>
                <div v-if="task.task_type === 'lock' && (task as any).end_time && !isTaskTimeHidden(task)" class="task-time">
                  <span class="label">结束时间:</span>
                  <span class="value">{{ formatDateTime((task as any).end_time) }}</span>
                </div>
                <!-- 剩余时间显示 - 隐藏时间时不显示 -->
                <div v-if="getTimeRemaining(task) > 0 && !isTaskTimeHidden(task)" class="task-time-remaining">
                  <span class="label">剩余时间:</span>
                  <span class="value countdown" :class="{ 'overtime': getTimeRemaining(task) <= 0 }">
                    {{ formatTimeRemaining(getTimeRemaining(task)) }}
                  </span>
                </div>
                <div v-else-if="(task.status === 'active' && task.task_type === 'lock') || (task.status === 'taken' && task.task_type === 'board')" class="task-time-remaining">
                  <span class="label">状态:</span>
                  <span v-if="!isTaskTimeHidden(task)" class="value overtime">倒计时已结束</span>
                  <span v-else class="value time-hidden-placeholder">
                    <span class="hidden-time-indicator">🔒 时间已隐藏</span>
                  </span>
                </div>
              </div>

              <div class="task-progress">
                <!-- 隐藏进度条当时间被隐藏时 -->
                <div v-if="((task.task_type === 'lock' && task.status === 'active') || (task.task_type === 'board' && task.status === 'taken')) && !isTaskTimeHidden(task)" class="progress-bar mobile-progress-container">
                  <div
                    class="progress-fill mobile-progress-fill"
                    :class="getProgressColorClass(task)"
                    :style="{
                      width: Math.max(10, getProgressPercent(task)) + '%',
                      '--mobile-progress': Math.max(10, getProgressPercent(task)) + '%'
                    }"
                    :title="`进度: ${getProgressPercent(task).toFixed(1)}% - ${getProgressColorClass(task)}`"
                  ></div>
                  <!-- 移动端调试显示 -->
                  <div class="mobile-debug-info">
                    {{ getProgressPercent(task).toFixed(1) }}% {{ getProgressColorClass(task) }}
                  </div>
                </div>
                <!-- 时间隐藏时显示占位符 -->
                <div v-else-if="((task.task_type === 'lock' && task.status === 'active') || (task.task_type === 'board' && task.status === 'taken')) && isTaskTimeHidden(task)" class="progress-hidden-placeholder">
                  <span class="hidden-time-indicator">🔒 进度已隐藏</span>
                </div>
                <div class="task-user">
                  <UserAvatar
                    :user="task.user"
                    size="small"
                    :clickable="false"
                    :show-lock-indicator="true"
                  />
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

    <!-- Notification Toast -->
    <NotificationToast
      :is-visible="showToast"
      :type="toastData.type"
      :title="toastData.title"
      :message="toastData.message"
      :secondary-message="toastData.secondaryMessage"
      :details="toastData.details"
      @close="showToast = false"
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
import NotificationToast from '../components/NotificationToast.vue'
import UserAvatar from '../components/UserAvatar.vue'
import type { Task } from '../types/index'
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

// Toast notification state
const showToast = ref(false)
const toastData = ref<{
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  message: string
  secondaryMessage?: string
  details?: Record<string, any>
}>({
  type: 'info',
  title: '',
  message: ''
})

// Sorting state
const sortBy = ref<'remaining_time' | 'created_time' | 'end_time' | 'user_activity' | 'difficulty'>('created_time')
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

// 无限滚动设置 - 一行三个卡片，4行=12个任务
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
    initialPageSize: 12, // 4行 × 3列 = 12个任务
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

      case 'user_activity':
        // Sort by user activity score
        aValue = a.user.activity_score || 0
        bValue = b.user.activity_score || 0
        break

      case 'difficulty':
        // Sort by difficulty level
        aValue = getDifficultyValue(a)
        bValue = getDifficultyValue(b)
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

// Convert difficulty to numerical value for sorting
const getDifficultyValue = (task: Task) => {
  if (task.task_type === 'lock') {
    const lockTask = task as any
    const difficultyMap: Record<string, number> = {
      'easy': 1,
      'normal': 2,
      'hard': 3,
      'hell': 4
    }
    return difficultyMap[lockTask.difficulty as string] || 0
  } else if (task.task_type === 'board') {
    const boardTask = task as any
    // For board tasks, use reward amount as difficulty indicator
    // Higher reward = higher difficulty
    return boardTask.reward || 0
  }
  return 0
}

const toggleSortOrder = () => {
  sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
}

const setSortBy = (criteria: 'remaining_time' | 'created_time' | 'end_time' | 'user_activity' | 'difficulty') => {
  sortBy.value = criteria
  showSortDropdown.value = false
}

const getSortLabel = () => {
  const labels = {
    remaining_time: '剩余时间',
    created_time: '创建时间',
    end_time: '结束时间',
    user_activity: '用户活跃度',
    difficulty: '难度等级'
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
  // Handle lock tasks
  if (task.task_type === 'lock' && task.status === 'active') {
    const lockTask = task as any
    if (!lockTask.start_time || !lockTask.end_time) {
      return 0
    }

    const start = new Date(lockTask.start_time).getTime()
    const end = new Date(lockTask.end_time).getTime()
    const now = currentTime.value

    if (now <= start) return 0
    if (now >= end) return 100

    return ((now - start) / (end - start)) * 100
  }

  // Handle board tasks
  if (task.task_type === 'board' && task.status === 'taken') {
    const boardTask = task as any
    if (!boardTask.taken_at || !boardTask.deadline) {
      return 0
    }

    const start = new Date(boardTask.taken_at).getTime()
    const end = new Date(boardTask.deadline).getTime()
    const now = currentTime.value

    if (now <= start) return 0
    if (now >= end) return 100

    return ((now - start) / (end - start)) * 100
  }

  return 0
}

// Get progress color class based on time remaining
const getProgressColorClass = (task: Task) => {
  // Check if task is active (lock tasks) or taken (board tasks)
  const isProgressActive = (task.task_type === 'lock' && task.status === 'active') ||
                          (task.task_type === 'board' && task.status === 'taken')

  if (!isProgressActive) {
    return 'progress-green'
  }

  const timeRemaining = getTimeRemaining(task)
  const thirtyMinutes = 30 * 60 * 1000 // 30 minutes in milliseconds
  const progressPercent = getProgressPercent(task)

  // Last 30 minutes - red
  if (timeRemaining > 0 && timeRemaining <= thirtyMinutes) {
    return 'progress-red'
  }
  // Over 50% completed - orange
  else if (progressPercent > 50) {
    return 'progress-orange'
  }
  // Initial/early stage - green
  else {
    return 'progress-green'
  }
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

// Check if task time display is hidden
const isTaskTimeHidden = (task: Task) => {
  if (!task || task.task_type !== 'lock') return false
  return (task as any).time_display_hidden || false
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

    // Show success notification
    showToast.value = true
    toastData.value = {
      type: 'success',
      title: '随机加时成功',
      message: `成功为任务加时 ${result.overtime_minutes} 分钟！`,
      secondaryMessage: '任务时间已延长，继续加油吧！',
      details: {
        '加时时长': `${result.overtime_minutes} 分钟`,
        '新的结束时间': formatDateTime(result.new_end_time)
      }
    }
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

    // Show error notification
    showToast.value = true
    toastData.value = {
      type: 'error',
      title: '随机加时失败',
      message: errorMessage,
      secondaryMessage: '请稍后重试或联系管理员'
    }
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
  width: 100%;
  overflow-x: hidden;
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
  width: 100%;
  box-sizing: border-box;
}

.container {
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
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
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
  width: 100%;
  margin-left: 0;
  margin-right: 0;
  box-sizing: border-box;
}

.task-card {
  background: white;
  padding: 1rem;
  border-radius: 8px;
  border: 2px solid #000;
  box-shadow: 4px 4px 0 #000;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  display: flex;
  flex-direction: column;
  height: auto;
  min-height: 300px;
  max-height: 400px;
  width: 100%;
  box-sizing: border-box;
  overflow: hidden;
}

.task-card:hover {
  transform: translateY(-2px);
  box-shadow: 6px 6px 0 #000;
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 0.75rem;
}

.task-title {
  font-size: 1.1rem;
  font-weight: bold;
  margin: 0 0 0.5rem 0;
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
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

/* Task Actions */
.task-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.action-btn {
  border: 2px solid #000;
  cursor: pointer;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  font-size: 0.75rem;
  box-shadow: 2px 2px 0 #000;
  transition: all 0.2s ease;
}

.action-btn.delete-btn {
  background-color: #dc3545;
  color: white;
}

.action-btn.delete-btn:hover {
  transform: translate(-1px, -1px);
  box-shadow: 3px 3px 0 #000;
  background-color: #c82333;
}

/* Task Quick Actions */
.task-quick-actions {
  display: flex;
  justify-content: center;
  padding: 0.75rem;
  border-top: 2px solid #e9ecef;
  margin-top: auto;
}

.task-quick-btn {
  background: #fd7e14;
  color: white;
  border: 3px solid #000;
  padding: 0.75rem 1.5rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  cursor: pointer;
  box-shadow: 4px 4px 0 #000;
  transition: all 0.2s ease;
  font-size: 0.875rem;
}

.task-quick-btn:hover {
  transform: translate(-2px, -2px);
  box-shadow: 6px 6px 0 #000;
  background-color: #e76500;
}

.task-quick-btn.overtime-btn {
  background: linear-gradient(135deg, #fd7e14, #ff6b35);
}

.task-quick-btn.overtime-btn:hover {
  background: linear-gradient(135deg, #e76500, #e55a2b);
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
  margin-bottom: 0.75rem;
  line-height: 1.4;
  font-size: 0.9rem;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.task-details {
  margin-bottom: 0.75rem;
  font-size: 0.8rem;
  flex: 1;
  overflow: hidden;
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
  gap: 1rem; /* 确保进度条和用户信息之间有间距 */
}

.progress-bar {
  flex: 1;
  height: 10px;
  background-color: #e9ecef;
  border: 2px solid #000;
  border-radius: 0;
  overflow: hidden;
  box-shadow: inset 2px 2px 4px rgba(0, 0, 0, 0.2);
  position: relative;
  max-width: 66.67%; /* 确保进度条最大占用2/3宽度，为用户名预留1/3空间 */
}

.progress-fill {
  height: 100%;
  background-color: #007bff;
  transition: width 0.3s ease, background-color 0.5s ease;
  position: relative;
  border-right: 1px solid rgba(0, 0, 0, 0.3);
  min-width: 2px; /* Ensure minimum visibility */
}

/* Progress color variations */
.progress-fill.progress-green {
  background: linear-gradient(90deg, #28a745, #20c997);
  box-shadow: inset 0 2px 4px rgba(255, 255, 255, 0.3);
}

.progress-fill.progress-orange {
  background: linear-gradient(90deg, #fd7e14, #ffc107);
  box-shadow: inset 0 2px 4px rgba(255, 255, 255, 0.3);
}

.progress-fill.progress-red {
  background: linear-gradient(90deg, #dc3545, #e74c3c);
  box-shadow: inset 0 2px 4px rgba(255, 255, 255, 0.3);
  animation: pulse-urgent 2s infinite;
}

@keyframes pulse-urgent {
  0%, 100% {
    box-shadow: inset 0 2px 4px rgba(255, 255, 255, 0.3);
    opacity: 1;
  }
  50% {
    box-shadow: inset 0 2px 4px rgba(255, 255, 255, 0.5);
    opacity: 0.8;
  }
}

.task-user {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  max-width: 33.33%; /* 限制用户区域最大宽度为卡片的1/3 */
  flex-shrink: 0;
}


.username {
  font-size: 0.875rem;
  color: #666;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  min-width: 0; /* 允许文本收缩 */
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

/* Tablet responsive */
@media (max-width: 1024px) and (min-width: 769px) {
  .tasks-list {
    max-width: 100%;
    gap: 1.25rem;
  }
}

/* Mobile responsive */
@media (max-width: 768px) {
  .header-content {
    padding: 0 1rem;
  }

  .main-content {
    padding: 1rem;
  }

  /* Change to 2 columns on mobile */
  .tasks-list {
    grid-template-columns: repeat(2, 1fr);
    gap: 1rem;
    max-width: 100%;
    margin-left: 0;
    margin-right: 0;
  }

  .task-card {
    padding: 0.75rem;
    min-height: 260px;
  }

  .task-header {
    flex-direction: column;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
  }

  .task-meta {
    gap: 0.5rem;
  }

  .task-description {
    font-size: 0.85rem;
    margin-bottom: 0.5rem;
  }

  .task-details {
    font-size: 0.75rem;
    margin-bottom: 0.5rem;
  }

  .task-progress {
    flex-direction: column;
    gap: 0.75rem;
    align-items: stretch;
  }

  /* 移动端专用进度条样式 - 使用新的类名避免冲突 */
  .mobile-progress-container {
    margin-right: 0 !important;
    height: 50px !important; /* 增加到50px */
    max-width: 100% !important;
    border: none !important;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2) !important;
    border-radius: 8px !important;
    background: linear-gradient(135deg, #e9ecef, #dee2e6) !important; /* 渐变背景更明显 */
    padding: 4px !important; /* 增加内边距 */
    overflow: hidden !important;
    flex: none !important;
    position: relative !important;
  }

  .mobile-progress-fill {
    min-width: 30px !important; /* 增加最小宽度 */
    border: none !important;
    border-radius: 4px !important;
    height: calc(100% - 8px) !important; /* 减去内边距 */
    margin: 4px !important;
    position: relative !important;
    display: block !important;
    transition: all 0.3s ease !important;
    background: linear-gradient(135deg, #007bff, #0056b3) !important; /* 默认渐变蓝色 */
    box-shadow: inset 0 2px 4px rgba(255, 255, 255, 0.3), 0 2px 4px rgba(0, 0, 0, 0.2) !important;
  }

  /* 移动端调试信息 */
  .mobile-debug-info {
    position: absolute !important;
    top: -25px !important;
    left: 0 !important;
    font-size: 11px !important;
    font-weight: bold !important;
    color: #dc3545 !important;
    background: rgba(255, 255, 255, 0.9) !important;
    padding: 2px 6px !important;
    border-radius: 3px !important;
    border: 1px solid #dc3545 !important;
    z-index: 1000 !important;
    white-space: nowrap !important;
  }

  .task-user {
    max-width: 100%; /* 移动端用户信息占满宽度 */
    justify-content: center; /* 居中显示用户信息 */
    margin-top: 0.5rem; /* 与进度条保持间距 */
  }

  .username {
    max-width: 200px; /* 设置最大宽度避免过长 */
    text-align: center; /* 居中显示用户名 */
    white-space: nowrap; /* 不允许换行 */
    overflow: hidden; /* 隐藏溢出内容 */
    text-overflow: ellipsis; /* 添加省略号 */
  }

  /* 移动端专用进度条颜色样式 */
  .mobile-progress-fill.progress-green {
    background: linear-gradient(135deg, #28a745, #20c997, #17a2b8) !important;
    box-shadow:
      inset 0 3px 6px rgba(255, 255, 255, 0.7),
      0 3px 6px rgba(40, 167, 69, 0.4) !important;
  }

  .mobile-progress-fill.progress-orange {
    background: linear-gradient(135deg, #fd7e14, #ffc107, #ff6b35) !important;
    box-shadow:
      inset 0 3px 6px rgba(255, 255, 255, 0.7),
      0 3px 6px rgba(253, 126, 20, 0.4) !important;
  }

  .mobile-progress-fill.progress-red {
    background: linear-gradient(135deg, #dc3545, #e74c3c, #ff6b6b) !important;
    box-shadow:
      inset 0 3px 6px rgba(255, 255, 255, 0.7),
      0 3px 6px rgba(220, 53, 69, 0.4) !important;
    animation: pulse-urgent-mobile 1.5s infinite;
  }

  @keyframes pulse-urgent-mobile {
    0%, 100% {
      opacity: 1;
      transform: scale(1);
      filter: brightness(1);
    }
    50% {
      opacity: 0.9;
      transform: scale(1.02);
      filter: brightness(1.2);
    }
  }

  .task-quick-actions {
    padding: 0.5rem;
  }

  .task-quick-btn {
    width: 100%;
    padding: 0.75rem;
    font-size: 0.875rem;
  }

  .action-btn {
    font-size: 0.625rem;
    padding: 0.375rem 0.75rem;
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

/* Small mobile - single column */
@media (max-width: 480px) {
  .tasks-list {
    grid-template-columns: 1fr;
  }

  .task-card {
    min-height: 240px;
  }

  /* 小屏幕专用进度条 - 进一步增强 */
  .mobile-progress-container {
    height: 60px !important; /* 小屏幕上更高 */
    border-radius: 12px !important;
    padding: 6px !important;
    box-shadow: 0 6px 12px rgba(0, 0, 0, 0.25) !important;
    background: linear-gradient(135deg, #e9ecef, #ced4da) !important;
  }

  .mobile-progress-fill {
    min-width: 40px !important; /* 小屏幕最小宽度更大 */
    border-radius: 6px !important;
    height: calc(100% - 12px) !important;
    margin: 6px !important;
  }

  /* 小屏幕进度条颜色最大化增强 */
  .mobile-progress-fill.progress-green {
    background: linear-gradient(135deg, #28a745, #20c997, #17a2b8, #4caf50) !important;
    box-shadow:
      inset 0 4px 8px rgba(255, 255, 255, 0.8),
      0 4px 8px rgba(40, 167, 69, 0.5) !important;
  }

  .mobile-progress-fill.progress-orange {
    background: linear-gradient(135deg, #fd7e14, #ffc107, #ff6b35, #ff9800) !important;
    box-shadow:
      inset 0 4px 8px rgba(255, 255, 255, 0.8),
      0 4px 8px rgba(253, 126, 20, 0.5) !important;
  }

  .mobile-progress-fill.progress-red {
    background: linear-gradient(135deg, #dc3545, #e74c3c, #ff6b6b, #f44336) !important;
    box-shadow:
      inset 0 4px 8px rgba(255, 255, 255, 0.8),
      0 4px 8px rgba(220, 53, 69, 0.5) !important;
    animation: pulse-urgent-small 1.5s infinite;
  }

  @keyframes pulse-urgent-small {
    0%, 100% {
      opacity: 1;
      transform: scale(1);
      filter: brightness(1);
    }
    50% {
      opacity: 0.95;
      transform: scale(1.03);
      filter: brightness(1.3);
    }
  }
}

/* 时间隐藏相关样式 */
.time-hidden-placeholder {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.hidden-time-indicator {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  background: linear-gradient(135deg, #343a40, #495057);
  color: white;
  border: 1px solid #000;
  border-radius: 4px;
  font-weight: 700;
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  box-shadow: 1px 1px 0 #000;
  animation: gentle-pulse 2s ease-in-out infinite;
}

.progress-hidden-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  height: 40px;
  background: linear-gradient(135deg, #f8f9fa, #e9ecef);
  border: 2px dashed #6c757d;
  border-radius: 6px;
  max-width: 66.67%;
}

@keyframes gentle-pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.8;
    transform: scale(1.02);
  }
}
</style>