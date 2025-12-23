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
                :class="{ active: showSortDropdown, loading: sortingLoading }"
                :disabled="sortingLoading"
              >
                <span v-if="sortingLoading" class="sort-icon">🔄</span>
                <span v-else class="sort-icon">⚡</span>
                <span class="sort-text">{{ sortingLoading ? '排序中...' : getSortLabel() }}</span>
                <span v-if="!sortingLoading" class="dropdown-arrow" :class="{ rotated: showSortDropdown }">▼</span>
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
                    ⚡ 活跃度
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
            <!-- Integrated pinned and regular tasks -->
            <template v-for="(task, index) in integratedTasksList" :key="task.id + (task.isPinned ? '-pinned' : '')">
              <!-- Task card (both pinned and regular use same structure) -->
              <div
                class="task-card"
                :class="{ 'pinned-task-card': task.isPinned }"
                :data-position="task.isPinned ? task.position : undefined"
                @click="goToTaskDetail(task.id)"
              >
                <!-- Position Badge for Pinned Cards -->
                <div v-if="task.isPinned && task.position" class="position-badge" :class="`position-${task.position}`">
                  <span class="position-number">{{ task.position }}</span>
                  <span class="position-crown">👑</span>
                </div>

                <!-- Pinning Time Info for Pinned Cards - Compact Single Line -->
                <div v-if="task.isPinned && task.pinningInfo" class="pinning-time-info">
                  <div class="pinning-compact-display">
                    <span class="pin-icon">📌</span>
                    <span class="pin-label">置顶剩余:</span>
                    <span class="pin-time-value">{{ formatPinTimeRemaining(task.pinningInfo) }}</span>
                    <span class="key-icon">🔑</span>
                    <span class="key-holder-name">{{ task.pinningInfo.key_holder.username }}</span>
                  </div>
                </div>
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
                  <!-- Pinned task overtime button (10x effect) -->
                  <button
                    v-if="task.isPinned"
                    @click="addOvertimeForPinnedTask(task, $event)"
                    class="task-quick-btn overtime-btn pinned-overtime"
                    title="为置顶任务加时 (10倍效果)"
                  >
                    ⚡ 10倍加时
                  </button>
                  <!-- Regular task overtime button -->
                  <button
                    v-else
                    @click="addOvertime(task, $event)"
                    class="task-quick-btn overtime-btn"
                    title="随机加时"
                  >
                    ⏰ 随机加时
                  </button>
                </div>

                <div class="task-content">
                  <p v-if="task.description" class="task-description">{{ stripHtmlAndTruncate(task.description, 150) }}</p>
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
                  <!-- 剩余时间显示 - 优先检查冻结，然后时间隐藏 -->
                  <div v-if="getTimeRemaining(task) > 0 && !isTaskFrozen(task) && !isTaskTimeHidden(task)" class="task-time-remaining">
                    <span class="label">剩余时间:</span>
                    <span class="value countdown" :class="{ 'overtime': getTimeRemaining(task) <= 0 }">
                      {{ formatTimeRemaining(getTimeRemaining(task)) }}
                    </span>
                  </div>
                  <div v-else-if="(task.status === 'active' && task.task_type === 'lock') || (task.status === 'taken' && task.task_type === 'board')" class="task-time-remaining">
                    <span class="label">状态:</span>
                    <span v-if="isTaskFrozen(task)" class="value frozen-time-placeholder">
                      <span class="frozen-time-indicator">❄️ 已冻结</span>
                    </span>
                    <span v-else-if="isTaskTimeHidden(task)" class="value time-hidden-placeholder">
                      <span class="hidden-time-indicator">🔒 时间已隐藏</span>
                    </span>
                    <span v-else class="value overtime">倒计时已结束</span>
                  </div>

                  <!-- Multi-person Task Participant Information - Simplified -->
                  <div v-if="task.task_type === 'board' && task.max_participants && task.max_participants > 1" class="task-participants-compact">
                    <div class="participants-summary">
                      <span class="participants-count">👥 {{ task.participant_count || 0 }}/{{ task.max_participants }}</span>
                      <span v-if="task.submitted_count && task.submitted_count > 0" class="submitted-count">📤 {{ task.submitted_count }}</span>
                      <span v-if="task.approved_count && task.approved_count > 0" class="approved-count">✅ {{ task.approved_count }}</span>
                    </div>
                    <div v-if="task.reward && task.max_participants > 1" class="reward-compact">
                      💰 {{ Math.ceil(task.reward / task.max_participants) }}/人
                    </div>
                  </div>
                </div>

                <div class="task-progress">
                  <!-- 显示进度条当任务未冻结且时间未隐藏时 -->
                  <div v-if="((task.task_type === 'lock' && task.status === 'active') || (task.task_type === 'board' && task.status === 'taken')) && !isTaskFrozen(task) && !isTaskTimeHidden(task)" class="progress-bar mobile-progress-container">
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
                  <!-- 冻结或时间隐藏时显示占位符 -->
                  <div v-else-if="((task.task_type === 'lock' && task.status === 'active') || (task.task_type === 'board' && task.status === 'taken'))" class="progress-hidden-placeholder">
                    <span v-if="(task as any).is_frozen" class="frozen-time-indicator">❄️ 进度已冻结</span>
                    <span v-else class="hidden-time-indicator">🔒 进度已隐藏</span>
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
            </template>

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
      :initial-task-type="activeTaskType"
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
import { ref, onMounted, computed, onUnmounted, watch, onActivated, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useTasksStore } from '../stores/tasks'
import { useInfiniteScroll } from '../composables/useInfiniteScroll'
import { formatDistanceToNow } from '../lib/utils'
import { tasksApi } from '../lib/api-tasks'
import { smartGoBack } from '../utils/navigation'
import { useNavigationStore } from '../stores/navigation'
import CreateTaskModal from '../components/CreateTaskModal.vue'
import NotificationBell from '../components/NotificationBell.vue'
import NotificationToast from '../components/NotificationToast.vue'
import UserAvatar from '../components/UserAvatar.vue'
import type { Task, PinningQueueStatus, PinnedUser, User } from '../types/index'
import type { LockTask } from '../types'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const tasksStore = useTasksStore()
const navigationStore = useNavigationStore()

// State
const showCreateModal = ref(false)
const activeFilter = ref('can-overtime')
const activeTaskType = ref<'lock' | 'board'>('lock')
const currentTime = ref(Date.now())
const progressInterval = ref<number>()
const taskCounts = ref<any>(null)
const countsLoading = ref(false)
const isRestoringState = ref(false) // 标志位：是否正在恢复状态

// Pinning state
const pinnedStatus = ref<PinningQueueStatus | null>(null)
const pinnedUsers = ref<PinnedUser[]>([])
const pinningLoading = ref(false)
const pinningInterval = ref<number>()

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
const sortBy = ref<'remaining_time' | 'created_time' | 'end_time' | 'user_activity' | 'difficulty'>('user_activity')
const sortOrder = ref<'asc' | 'desc'>('desc')
const showSortDropdown = ref(false)
const sortingLoading = ref(false)

// Create a function to get the appropriate API call based on current filters
const getFilteredTasks = async (page: number, pageSize: number) => {
  const extraFilters: any = {
    task_type: activeTaskType.value,
    sort_by: sortBy.value,
    sort_order: sortOrder.value
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
  } else if (activeFilter.value === 'can-overtime') {
    extraFilters.can_overtime = true
  } else if (activeFilter.value === 'available') {
    extraFilters.status = 'available'
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

// Helper function to validate cached state
const isStateValid = (state: any): boolean => {
  if (!state) return false

  const now = Date.now()
  const stateAge = now - state.lastFetchTime
  const MAX_STATE_AGE = 10 * 60 * 1000 // 10 minutes

  return stateAge < MAX_STATE_AGE && state.tasks && state.tasks.length > 0
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
  refresh,
  getCurrentState
} = useInfiniteScroll(
  getFilteredTasks,
  {
    initialPageSize: 12, // 4行 × 3列 = 12个任务
    threshold: 200,
    loadDelay: 300,
    initialData: (() => {
      // Try to restore from navigation store
      const savedState = navigationStore.getTasksViewState()
      if (savedState && isStateValid(savedState)) {
        // Check if current filters match saved state
        const filtersMatch =
          savedState.activeTaskType === activeTaskType.value &&
          savedState.activeFilter === activeFilter.value &&
          savedState.sortBy === sortBy.value &&
          savedState.sortOrder === sortOrder.value

        if (filtersMatch) {
          console.log('🔄 Restoring tasks from navigation store')
          return {
            items: savedState.tasks || [],
            currentPage: savedState.currentPage || 1,
            totalCount: savedState.totalCount || 0,
            hasMore: savedState.hasMore || false
          }
        }
      }
      return undefined
    })()
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
      { key: 'my-tasks', label: '我的任务', count: 0 },
      { key: 'can-overtime', label: '可以加时的绒布球', count: 0 }
    ]
  }
  return [
    { key: 'all', label: '全部', count: taskCounts.value.lock_tasks.all },
    { key: 'active', label: '进行中', count: taskCounts.value.lock_tasks.active },
    { key: 'voting', label: '投票中', count: taskCounts.value.lock_tasks.voting },
    { key: 'completed', label: '已完成', count: taskCounts.value.lock_tasks.completed },
    { key: 'my-tasks', label: '我的任务', count: taskCounts.value.lock_tasks.my_tasks },
    { key: 'can-overtime', label: '可以加时的绒布球', count: taskCounts.value.lock_tasks.can_overtime || 0 }
  ]
})

const boardFilterTabs = computed(() => {
  if (!taskCounts.value) {
    // Fallback to showing counts without numbers when API data is not available
    return [
      { key: 'all', label: '全部', count: 0 },
      { key: 'available', label: '可接取', count: 0 },
      { key: 'my-published', label: '我发布的', count: 0 },
      { key: 'my-taken', label: '我接取的', count: 0 }
    ]
  }
  return [
    { key: 'all', label: '全部', count: taskCounts.value.board_tasks.all },
    { key: 'available', label: '可接取', count: taskCounts.value.board_tasks.open },
    { key: 'my-published', label: '我发布的', count: taskCounts.value.board_tasks.my_published },
    { key: 'my-taken', label: '我接取的', count: taskCounts.value.board_tasks.my_taken }
  ]
})

const currentFilterTabs = computed(() => {
  return activeTaskType.value === 'lock' ? lockFilterTabs.value : boardFilterTabs.value
})


// Tasks are already filtered and sorted server-side, no need for client-side processing
const filteredTasks = computed(() => {
  return currentTasks.value
})

// Integrated tasks list - pinned users first (up to 3 positions), then regular tasks
const integratedTasksList = computed(() => {
  const integrated: any[] = []

  // Only add pinned tasks for lock task type
  if (activeTaskType.value === 'lock' && pinnedStatus.value && pinnedStatus.value.active_count > 0) {
    // Add pinned tasks to the first 3 positions
    for (let position = 1; position <= 3; position++) {
      const pinnedUser = getPinnedUserAtPosition(position)
      if (pinnedUser) {
        const pinnedTask = createTaskForPinnedUser(pinnedUser)
        if (pinnedTask) {
          integrated.push({
            ...pinnedTask,
            isPinned: true,
            position: position,
            pinningInfo: {
              expires_at: pinnedUser.expires_at,
              time_remaining: pinnedUser.time_remaining || 0,
              key_holder: pinnedUser.key_holder || { username: '未知' }
            }
          })
        }
      }
    }
  }

  // Add regular tasks
  for (const task of filteredTasks.value) {
    integrated.push({
      ...task,
      isPinned: false
    })
  }

  return integrated
})

const toggleSortOrder = async () => {
  sortingLoading.value = true
  sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
  // Refresh tasks with new sort order
  try {
    await refresh()
  } finally {
    sortingLoading.value = false
  }
}

const setSortBy = async (criteria: 'remaining_time' | 'created_time' | 'end_time' | 'user_activity' | 'difficulty') => {
  sortingLoading.value = true
  sortBy.value = criteria
  showSortDropdown.value = false
  // Refresh tasks with new sorting
  try {
    await refresh()
  } finally {
    sortingLoading.value = false
  }
}

const getSortLabel = () => {
  const labels = {
    remaining_time: '剩余时间',
    created_time: '创建时间',
    end_time: '结束时间',
    user_activity: '活跃度',
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

// Fetch pinning status
const fetchPinningStatus = async () => {
  if (pinningLoading.value) return

  pinningLoading.value = true
  try {
    const status = await tasksApi.getPinningStatus()
    pinnedStatus.value = status
    pinnedUsers.value = status.active_pins || []
    console.log('📌 Pinning status updated:', {
      active_count: status.active_count,
      queue_count: status.queue_count,
      active_pins: status.active_pins?.length || 0,
      positions: status.active_pins?.map(pin => pin.position) || []
    })
  } catch (error) {
    console.error('Failed to fetch pinning status:', error)
  } finally {
    pinningLoading.value = false
  }
}

// Get pinned user at specific position
const getPinnedUserAtPosition = (position: number): PinnedUser | null => {
  return pinnedUsers.value.find(user => user.position === position) || null
}

// Create a proper Task object for pinned users
const createTaskForPinnedUser = (pinnedUser: PinnedUser | null): Task | null => {
  if (!pinnedUser) return null

  // Create a minimal User object from pinned_user data
  const user = {
    id: parseInt(pinnedUser.pinned_user.id),
    username: pinnedUser.pinned_user.username,
    email: '',
    level: 1 as const,
    activity_score: 0,
    last_active: pinnedUser.created_at,
    location_precision: 0,
    coins: 0,
    avatar: undefined,
    bio: '',
    total_posts: 0,
    total_likes_received: 0,
    total_tasks_completed: 0,
    total_lock_duration: 0,
    task_completion_rate: 0,
    created_at: pinnedUser.created_at,
    updated_at: pinnedUser.created_at,
    active_lock_task: null,
    is_superuser: false,
    is_staff: false
  } as User

  return {
    ...pinnedUser.task,
    user,
    // Keep original task timestamps, don't override with pinning timestamps
    // created_at: pinnedUser.created_at,
    // updated_at: pinnedUser.created_at,
    // Keep original task properties, don't override
    // duration_type: 'fixed' as const,
    // duration_value: pinnedUser.duration_minutes,
    // Keep original description, don't override
    // description: `置顶任务 - ${pinnedUser.pinned_user.username}`
  } as unknown as Task
}

// Format pinning time remaining - real-time calculation
const formatPinTimeRemaining = (pinningInfo: any): string => {
  if (!pinningInfo || !pinningInfo.expires_at) return '已过期'

  // Calculate remaining time in real-time using current time
  const expiresAt = new Date(pinningInfo.expires_at).getTime()
  const now = currentTime.value
  const timeRemainingMs = Math.max(0, expiresAt - now)

  if (timeRemainingMs <= 0) return '已过期'

  // Convert milliseconds to minutes and seconds
  const totalSeconds = Math.floor(timeRemainingMs / 1000)
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60

  if (minutes > 0) {
    return `${minutes}分${seconds}秒`
  } else {
    return `${seconds}秒`
  }
}

// Start pinning status update timer
const startPinningUpdate = () => {
  // Clear any existing interval
  if (pinningInterval.value) {
    clearInterval(pinningInterval.value)
  }

  // Update every 5 seconds for more responsive pinning updates
  pinningInterval.value = window.setInterval(() => {
    if (activeTaskType.value === 'lock') {
      fetchPinningStatus()
    }
  }, 5000)
}

const handleTaskCreated = async () => {
  // Clear cache and refresh since new content was added
  navigationStore.clearTasksViewState()
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
  return authStore.user?.is_staff || authStore.user?.is_superuser
}

const deleteTask = async (task: Task) => {
  if (!confirm('确定要删除这个任务吗？')) {
    return
  }

  try {
    await tasksStore.deleteTask(task.id)
    // Clear navigation state since task list has changed
    navigationStore.clearTasksViewState()
    // Refresh task counts after deletion
    await fetchTaskCounts()
    console.log('任务删除成功')
  } catch (error) {
    console.error('Error deleting task:', error)
    alert('删除失败，请重试')
  }
}

const goToTaskDetail = (taskId: string) => {
  // Save current scroll position
  const scrollPosition = window.pageYOffset || document.documentElement.scrollTop

  // Save current tasks view state
  const currentState = getCurrentState()
  navigationStore.saveTasksViewState({
    tasks: currentState.items,
    currentPage: currentState.currentPage,
    totalCount: currentState.totalCount,
    hasMore: currentState.hasMore,
    scrollPosition,
    lastFetchTime: Date.now(),
    // Store filter context to ensure we restore the right data
    activeTaskType: activeTaskType.value,
    activeFilter: activeFilter.value,
    sortBy: sortBy.value,
    sortOrder: sortOrder.value
  })

  console.log('💾 Saved tasks state before navigation')
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

const stripHtmlAndTruncate = (html: string, maxLength: number = 150): string => {
  if (!html) return ''

  // Create a temporary div to strip HTML tags
  const tempDiv = document.createElement('div')
  tempDiv.innerHTML = html
  const textContent = tempDiv.textContent || tempDiv.innerText || ''

  // Truncate text if it's too long
  if (textContent.length <= maxLength) {
    return textContent
  }

  return textContent.slice(0, maxLength) + '...'
}

const getProgressPercent = (task: Task) => {
  // Handle lock tasks
  if (task.task_type === 'lock' && task.status === 'active') {
    const lockTask = task as any

    // If task is frozen, show progress based on frozen state
    if (lockTask.is_frozen) {
      return 0 // Frozen tasks show no progress
    }

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
  // Check if task is frozen
  const lockTask = task as any
  if (task.task_type === 'lock' && lockTask.is_frozen) {
    return 'progress-frozen'
  }

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

    // If task is frozen, show the frozen time remaining
    if (lockTask.is_frozen && lockTask.frozen_end_time && lockTask.frozen_at) {
      const frozenEndTime = new Date(lockTask.frozen_end_time).getTime()
      const frozenAt = new Date(lockTask.frozen_at).getTime()
      return Math.max(0, frozenEndTime - frozenAt)
    }

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
  const lockTask = task as any
  return lockTask.time_display_hidden || false
}

const isTaskFrozen = (task: Task) => {
  if (!task || task.task_type !== 'lock') return false
  const lockTask = task as any
  return lockTask.is_frozen || false
}

// Add overtime function
const addOvertime = async (task: Task, event: Event) => {
  event.stopPropagation() // Prevent card click

  if (!task || !canAddOvertime(task)) return

  try {
    const result = await tasksApi.addOvertime(task.id)

    // Check if we're in the "can-overtime" filter and need to remove the task
    if (activeFilter.value === 'can-overtime') {
      // Remove the task from the infinite scroll's local tasks array immediately
      const taskIndex = tasks.value.findIndex(t => t.id === task.id)
      if (taskIndex !== -1) {
        tasks.value.splice(taskIndex, 1)
      }

      // Also refresh task counts to update the filter badge
      await fetchTaskCounts()
    } else {
      // Update the task's end time in the local list for other filters
      const lockTask = task as any
      if (result.new_end_time && lockTask) {
        lockTask.end_time = result.new_end_time
      }
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

// Add overtime for pinned task with 10x effect
const addOvertimeForPinnedTask = async (task: Task, event: Event) => {
  event.stopPropagation() // Prevent card click

  if (!task || !canAddOvertime(task)) return

  try {
    const result = await tasksApi.addOvertime(task.id)

    // Show success notification with 10x effect emphasis
    showToast.value = true
    toastData.value = {
      type: 'success',
      title: '🔥 置顶任务10倍加时成功！',
      message: `成功为置顶任务加时 ${result.overtime_minutes} 分钟！`,
      secondaryMessage: '置顶用户享受10倍加时效果！',
      details: {
        '加时时长': `${result.overtime_minutes} 分钟`,
        '10倍效果': '置顶用户专享',
        '新的结束时间': formatDateTime(result.new_end_time)
      }
    }
    console.log('置顶任务加时成功:', result)

    // Refresh pinning status and task counts
    await Promise.all([
      fetchPinningStatus(),
      fetchTaskCounts()
    ])

    // Refresh user data to update lock status
    authStore.refreshUser()

  } catch (error: any) {
    console.error('Error adding overtime to pinned task:', error)

    // Handle specific error messages
    let errorMessage = '置顶任务加时失败，请重试'

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
      title: '置顶任务加时失败',
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
  // Skip filter reset if we're currently restoring state
  if (isRestoringState.value) {
    console.log('🔄 Skipping filter reset during state restoration')
    return
  }

  if (newType === 'lock') {
    activeFilter.value = 'can-overtime'  // 带锁任务默认显示"可以加时的绒布球"
    // Fetch pinning status for lock tasks
    fetchPinningStatus()
  } else {
    activeFilter.value = 'available'     // 任务板默认显示"可接取"
  }
  // Refresh tasks when task type changes
  refresh()
})

// Watch for filter changes and refresh tasks
watch(activeFilter, () => {
  // Skip refresh if we're currently restoring state
  if (isRestoringState.value) {
    console.log('🔄 Skipping filter refresh during state restoration')
    return
  }
  refresh()
})

// Restore state from TasksViewState
const restoreStateFromTasksView = () => {
  const savedState = navigationStore.getTasksViewState()

  if (savedState && isStateValid(savedState)) {
    console.log('🔄 Restoring state from TasksViewState:', savedState)

    // Set flag to prevent watchers from interfering
    isRestoringState.value = true

    // Restore task type
    activeTaskType.value = savedState.activeTaskType
    console.log('🔄 Restored activeTaskType:', activeTaskType.value)

    // Restore filter
    activeFilter.value = savedState.activeFilter
    console.log('🔄 Restored activeFilter:', activeFilter.value)

    // Restore sort by
    sortBy.value = savedState.sortBy
    console.log('🔄 Restored sortBy:', sortBy.value)

    // Restore sort order
    sortOrder.value = savedState.sortOrder
    console.log('🔄 Restored sortOrder:', sortOrder.value)

    // Reset flag after restoration is complete
    setTimeout(() => {
      isRestoringState.value = false
      console.log('🔄 State restoration completed, flag reset')
    }, 100)

    return true // Indicate that state was restored
  }
  return false // No state to restore
}

// Restore state from query parameters (fallback)
const restoreStateFromQuery = () => {
  const query = route.query

  console.log('🔄 Restoring state from query parameters:', query)

  // Set flag to prevent watchers from interfering
  isRestoringState.value = true

  // Restore task type
  if (query.type && ['lock', 'board'].includes(query.type as string)) {
    activeTaskType.value = query.type as 'lock' | 'board'
    console.log('🔄 Restored activeTaskType:', activeTaskType.value)
  }

  // Restore filter
  if (query.filter && typeof query.filter === 'string') {
    activeFilter.value = query.filter
    console.log('🔄 Restored activeFilter:', activeFilter.value)
  }

  // Restore sort by
  if (query.sortBy && ['remaining_time', 'created_time', 'end_time', 'user_activity', 'difficulty'].includes(query.sortBy as string)) {
    sortBy.value = query.sortBy as 'remaining_time' | 'created_time' | 'end_time' | 'user_activity' | 'difficulty'
    console.log('🔄 Restored sortBy:', sortBy.value)
  }

  // Restore sort order
  if (query.sortOrder && ['asc', 'desc'].includes(query.sortOrder as string)) {
    sortOrder.value = query.sortOrder as 'asc' | 'desc'
    console.log('🔄 Restored sortOrder:', sortOrder.value)
  }

  // Reset flag after restoration is complete
  setTimeout(() => {
    isRestoringState.value = false
    console.log('🔄 State restoration completed, flag reset')
  }, 100)

  // Clean up URL by removing query parameters after restoration
  if (Object.keys(query).length > 0) {
    router.replace({ name: 'tasks' })
    console.log('🔄 Cleaned up URL after state restoration')
  }
}

onMounted(async () => {
  // Priority 1: Restore state from TasksViewState (from navigation)
  // Priority 2: Restore state from query parameters (fallback)
  const stateRestored = restoreStateFromTasksView()
  if (!stateRestored) {
    restoreStateFromQuery()
  }

  // Initialize task list, counts, and pinning status in parallel
  await Promise.all([
    initialize(),
    fetchTaskCounts(),
    activeTaskType.value === 'lock' ? fetchPinningStatus() : Promise.resolve()
  ])

  // Restore scroll position if we have saved state
  const savedState = navigationStore.getTasksViewState()
  if (savedState && savedState.scrollPosition !== undefined) {
    nextTick(() => {
      console.log('📍 Restoring scroll position:', savedState.scrollPosition)
      window.scrollTo(0, savedState.scrollPosition)

      // Clear the saved state after restoration
      navigationStore.clearTasksViewState()
    })
  }

  startProgressUpdate()
  startPinningUpdate()
  document.addEventListener('click', handleClickOutside)

  // Add visibility change listener to refresh pinning status when user returns
  document.addEventListener('visibilitychange', handleVisibilityChange)
})

// Handle component activation (when navigating back from other routes)
onActivated(() => {
  if (activeTaskType.value === 'lock') {
    // Refresh pinning status when component is activated
    fetchPinningStatus()
  }
})

// Handle visibility change to refresh pinning status when user returns to tab
const handleVisibilityChange = () => {
  if (!document.hidden && activeTaskType.value === 'lock') {
    // Refresh pinning status when user returns to tab
    fetchPinningStatus()
  }
}

onUnmounted(() => {
  if (progressInterval.value) {
    clearInterval(progressInterval.value)
  }
  if (pinningInterval.value) {
    clearInterval(pinningInterval.value)
  }
  document.removeEventListener('click', handleClickOutside)
  document.removeEventListener('visibilitychange', handleVisibilityChange)
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

.progress-fill.progress-frozen {
  background: linear-gradient(90deg, #17a2b8, #20c3aa);
  box-shadow: inset 0 2px 4px rgba(255, 255, 255, 0.3);
  animation: pulse-frozen-progress 2s infinite;
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

@keyframes pulse-frozen-progress {
  0%, 100% {
    box-shadow: inset 0 2px 4px rgba(255, 255, 255, 0.3);
    opacity: 1;
  }
  50% {
    box-shadow: inset 0 2px 4px rgba(255, 255, 255, 0.5);
    opacity: 0.7;
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

.sort-btn.loading {
  opacity: 0.7;
  cursor: wait;
}

.sort-btn.loading .sort-icon {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
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
    min-height: 220px; /* 进一步减少最小高度，为紧凑布局预留空间 */
  }

  .task-header {
    flex-direction: column;
    gap: 0.375rem; /* 减少间距 */
    margin-bottom: 0.375rem; /* 减少底部间距 */
  }

  .task-meta {
    gap: 0.375rem; /* 减少间距 */
  }

  .task-description {
    font-size: 0.85rem;
    margin-bottom: 0.375rem; /* 减少底部间距 */
    line-height: 1.3; /* 优化行高 */
  }

  .task-details {
    font-size: 0.75rem;
    margin-bottom: 0.375rem; /* 减少底部间距 */
  }

  .task-progress {
    flex-direction: column;
    gap: 0.5rem; /* 减少间距 */
    align-items: stretch;
    margin-top: auto; /* 让进度条区域贴底 */
  }

  /* 移动端专用进度条样式 - 使用新的类名避免冲突 */
  .mobile-progress-container {
    margin-right: 0 !important;
    height: 32px !important; /* 减少高度以节省空间 */
    max-width: 100% !important;
    border: none !important;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.15) !important;
    border-radius: 6px !important;
    background: linear-gradient(135deg, #e9ecef, #dee2e6) !important; /* 渐变背景更明显 */
    padding: 3px !important; /* 减少内边距 */
    overflow: hidden !important;
    flex: none !important;
    position: relative !important;
  }

  .mobile-progress-fill {
    min-width: 24px !important; /* 减少最小宽度 */
    border: none !important;
    border-radius: 3px !important;
    height: calc(100% - 6px) !important; /* 减去内边距 */
    margin: 3px !important;
    position: relative !important;
    display: block !important;
    transition: all 0.3s ease !important;
    background: linear-gradient(135deg, #007bff, #0056b3) !important; /* 默认渐变蓝色 */
    box-shadow: inset 0 1px 2px rgba(255, 255, 255, 0.3), 0 1px 2px rgba(0, 0, 0, 0.2) !important;
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
    margin-top: 0.25rem; /* 减少与进度条的间距 */
    padding-top: 0.25rem; /* 添加少量内边距 */
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
    min-height: 200px; /* 小屏幕进一步减少高度 */
  }

  /* 小屏幕专用进度条 - 优化高度 */
  .mobile-progress-container {
    height: 36px !important; /* 减少小屏幕高度 */
    border-radius: 8px !important;
    padding: 4px !important;
    box-shadow: 0 3px 6px rgba(0, 0, 0, 0.2) !important;
    background: linear-gradient(135deg, #e9ecef, #ced4da) !important;
  }

  .mobile-progress-fill {
    min-width: 28px !important; /* 减少小屏幕最小宽度 */
    border-radius: 4px !important;
    height: calc(100% - 8px) !important;
    margin: 4px !important;
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

.frozen-time-placeholder {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

/* 冻结时间指示器样式 */
.frozen-time-indicator {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  background: linear-gradient(135deg, #17a2b8, #20c3aa);
  color: white;
  border: 2px solid #000;
  border-radius: 4px;
  font-weight: 600;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  box-shadow: 2px 2px 0 #000;
  animation: pulse-frozen 2s infinite;
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

.frozen-time-indicator {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  background: linear-gradient(135deg, #17a2b8, #20c3aa);
  color: white;
  border: 2px solid #000;
  border-radius: 4px;
  font-weight: 700;
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  box-shadow: 2px 2px 0 #000;
  animation: pulse-frozen-indicator 2s ease-in-out infinite;
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

@keyframes pulse-frozen-indicator {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.7;
    transform: scale(1.02);
  }
}

@keyframes pulse-frozen {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.7;
    transform: scale(0.98);
  }
}


/* Pinned task cards within the main grid */
.task-card.pinned-task-card {
  position: relative;
  overflow: visible;
}

/* Pinned task cards use normal styling - no special background colors */
.task-card.pinned-task-card[data-position="1"],
.task-card.pinned-task-card[data-position="2"],
.task-card.pinned-task-card[data-position="3"] {
  /* Use default task card styling - no special background or border colors */
}

/* Position Badge - 右上角排名小图标 */
.position-badge {
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
  box-shadow: 2px 2px 0 rgba(0, 0, 0, 0.3);
}

.position-badge.position-1 {
  background: linear-gradient(135deg, #ffd700, #ffed4e);
  color: #000;
}

.position-badge.position-2 {
  background: linear-gradient(135deg, #c0c0c0, #e8e8e8);
  color: #000;
}

.position-badge.position-3 {
  background: linear-gradient(135deg, #cd7f32, #daa520);
  color: #000;
}

.position-number {
  font-size: 0.75rem;
  font-weight: 900;
}

.position-crown {
  position: absolute;
  top: -8px;
  right: -8px;
  font-size: 1rem;
  z-index: 3;
}

/* Pinning Time Info - 置顶剩余时间信息 */
.pinning-time-info {
  background: linear-gradient(135deg, #ff6b6b, #ee5a52);
  border: 2px solid #000;
  border-radius: 6px;
  padding: 0.5rem;
  margin-bottom: 0.75rem;
  box-shadow: 2px 2px 0 #000;
}

.pinning-compact-display {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  flex-wrap: wrap;
}

.pin-icon,
.key-icon {
  font-size: 0.875rem;
}

.pin-label {
  font-weight: 700;
  color: white;
  font-size: 0.75rem;
}

.pin-time-value {
  font-weight: 900;
  color: white;
  font-size: 0.75rem;
  background: rgba(0, 0, 0, 0.2);
  padding: 0.125rem 0.375rem;
  border-radius: 3px;
  border: 1px solid rgba(0, 0, 0, 0.3);
}

.key-holder-name {
  font-weight: 700;
  color: white;
  font-size: 0.75rem;
  background: rgba(0, 0, 0, 0.2);
  padding: 0.125rem 0.375rem;
  border-radius: 3px;
  border: 1px solid rgba(0, 0, 0, 0.3);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 120px;
}

/* Pinned overtime button styling */
.task-quick-btn.pinned-overtime {
  background: linear-gradient(135deg, #fd7e14, #ff6b35);
}

.task-quick-btn.pinned-overtime:hover {
  background: linear-gradient(135deg, #e76500, #e55a2b);
}

/* Multi-person Task Participants Styles - Compact */
.task-participants-compact {
  margin: 0.5rem 0;
  padding: 0.5rem;
  background: #f8f9fa;
  border-radius: 4px;
  border: 1px solid #dee2e6;
}

.participants-summary {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  flex-wrap: wrap;
}

.participants-count,
.submitted-count,
.approved-count {
  font-size: 0.75rem;
  font-weight: 600;
  color: #495057;
  white-space: nowrap;
}

.reward-compact {
  margin-top: 0.25rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: #28a745;
}

.participants-stats {
  display: flex;
  gap: 1rem;
  margin-bottom: 0.75rem;
  flex-wrap: wrap;
}

.participant-stat {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  background: white;
  padding: 0.25rem 0.75rem;
  border: 2px solid #000;
  border-radius: 4px;
  box-shadow: 2px 2px 0 #000;
  font-size: 0.875rem;
}

.stat-icon {
  font-size: 1rem;
}

.stat-label {
  font-weight: 600;
  color: #333;
}

.stat-value {
  font-weight: 900;
  color: #007bff;
}

.participants-status {
  margin-bottom: 0.75rem;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  border: 2px solid #000;
  border-radius: 6px;
  box-shadow: 2px 2px 0 #000;
  font-size: 0.875rem;
  font-weight: 600;
}

.status-indicator.available {
  background: linear-gradient(135deg, #d4edda, #c3e6cb);
  border-color: #28a745;
  color: #155724;
}

.status-indicator.full {
  background: linear-gradient(135deg, #f8d7da, #f5c6cb);
  border-color: #dc3545;
  color: #721c24;
}

.status-indicator.reviewing {
  background: linear-gradient(135deg, #fff3cd, #ffeaa7);
  border-color: #ffc107;
  color: #856404;
}

.status-icon {
  font-size: 1.1rem;
  flex-shrink: 0;
}

.status-text {
  font-weight: 700;
}

.reward-distribution {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: linear-gradient(135deg, #e7f3ff, #b3d9ff);
  border: 2px solid #007bff;
  border-radius: 6px;
  box-shadow: 2px 2px 0 #000;
  font-size: 0.875rem;
}

.reward-label {
  font-weight: 600;
  color: #0066cc;
}

.reward-per-person {
  font-weight: 900;
  color: #004085;
  background: white;
  padding: 0.125rem 0.5rem;
  border: 1px solid #007bff;
  border-radius: 4px;
}

/* Mobile responsive for participants info */
@media (max-width: 768px) {
  .task-participants-compact {
    padding: 0.375rem;
    margin: 0.375rem 0;
  }

  .participants-summary {
    gap: 0.5rem;
  }

  .participants-count,
  .submitted-count,
  .approved-count {
    font-size: 0.7rem;
  }

  .reward-compact {
    font-size: 0.7rem;
  }

  .task-participants-info {
    padding: 0.75rem;
    margin: 0.75rem 0;
    border-width: 2px;
    box-shadow: 2px 2px 0 #000;
  }

  .participants-stats {
    flex-direction: column;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
  }

  .participant-stat {
    justify-content: space-between;
    padding: 0.5rem 0.75rem;
    border-width: 1px;
    box-shadow: 1px 1px 0 #000;
  }

  .status-indicator {
    padding: 0.375rem 0.75rem;
    border-width: 1px;
    box-shadow: 1px 1px 0 #000;
    font-size: 0.8rem;
  }

  .reward-distribution {
    flex-direction: column;
    align-items: stretch;
    gap: 0.25rem;
    padding: 0.5rem 0.75rem;
    border-width: 1px;
    box-shadow: 1px 1px 0 #000;
    text-align: center;
  }

  .reward-per-person {
    align-self: center;
  }

}

/* Small mobile - single column */
@media (max-width: 480px) {

  /* Mobile responsive for pinned task elements */
  .position-badge {
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

  .pinning-time-info {
    padding: 0.375rem;
    margin-bottom: 0.5rem;
    border-width: 1px;
    box-shadow: 1px 1px 0 #000;
  }

  .pinning-time-display {
    gap: 0.25rem;
    margin-bottom: 0.25rem;
  }

  .pin-label,
  .pin-time-value,
  .key-holder-name {
    font-size: 0.65rem;
    padding: 0.1rem 0.25rem;
  }

  .key-holder-name {
    max-width: 80px;
  }
}
</style>