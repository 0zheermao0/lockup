<template>
  <div class="task-view">
    <!-- Header -->
    <header class="header">
      <div class="header-content">
        <button @click="goBack" class="back-btn">← 返回</button>
        <h1>任务管理</h1>
        <button @click="openCreateModal" class="create-btn">创建任务</button>
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
          <div v-if="loading" class="loading">
            加载中...
          </div>

          <div v-else-if="error" class="error">
            {{ error }}
          </div>

          <div v-else-if="filteredTasks.length === 0" class="empty">
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
                    <span v-if="task.difficulty" class="task-difficulty" :class="task.difficulty">
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
                <div v-if="task.start_time" class="task-time">
                  <span class="label">开始时间:</span>
                  <span class="value">{{ formatDateTime(task.start_time) }}</span>
                </div>
                <div v-if="task.end_time" class="task-time">
                  <span class="label">结束时间:</span>
                  <span class="value">{{ formatDateTime(task.end_time) }}</span>
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
import { formatDistanceToNow } from '../lib/utils'
import { tasksApi } from '../lib/api-tasks'
import CreateTaskModal from '../components/CreateTaskModal.vue'
import type { LockTask } from '../types/index.js'

const router = useRouter()
const authStore = useAuthStore()

// State
const tasks = ref<LockTask[]>([])
const loading = ref(true)
const error = ref('')
const showCreateModal = ref(false)
const activeFilter = ref('all')
const activeTaskType = ref<'lock' | 'board'>('lock')

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
  { key: 'pending', label: '待开始', count: lockTasks.value.filter(t => t.status === 'pending').length },
  { key: 'active', label: '进行中', count: lockTasks.value.filter(t => t.status === 'active').length },
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
      case 'pending':
        return tasks.filter(task => task.status === 'pending')
      case 'active':
        return tasks.filter(task => task.status === 'active')
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
        return tasks.filter(task => task.taker?.id === authStore.user?.id)
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

const handleTaskCreated = () => {
  fetchTasks()
}

const fetchTasks = async () => {
  loading.value = true
  try {
    const response = await tasksApi.getTasks()
    tasks.value = response.results || response

    // 备用模拟数据 - 带锁任务和任务板（如果API返回空数据）
    if (!tasks.value || tasks.value.length === 0) {
      tasks.value = [
      // 带锁任务
      {
        id: '1',
        task_type: 'lock' as const,
        user: { id: 1, username: 'testuser', email: 'test@example.com', level: 1, activity_score: 100, last_active: '2024-01-01', location_precision: 1, coins: 50, bio: '', total_posts: 5, total_likes_received: 10, total_tasks_completed: 2, created_at: '2024-01-01', updated_at: '2024-01-01' },
        title: '工作日专注训练',
        description: '在工作时间保持专注，完成重要任务。这是一个带锁任务，需要严格按照设定时间执行。',
        duration_type: 'fixed' as const,
        duration_value: 480, // 8小时
        difficulty: 'normal' as const,
        unlock_type: 'time' as const,
        start_time: '2024-01-01T09:00:00Z',
        end_time: '2024-01-01T17:00:00Z',
        status: 'completed' as const,
        created_at: '2024-01-01T08:00:00Z',
        updated_at: '2024-01-01T17:00:00Z'
      },
      {
        id: '2',
        task_type: 'lock' as const,
        user: { id: 1, username: 'testuser', email: 'test@example.com', level: 1, activity_score: 100, last_active: '2024-01-01', location_precision: 1, coins: 50, bio: '', total_posts: 5, total_likes_received: 10, total_tasks_completed: 2, created_at: '2024-01-01', updated_at: '2024-01-01' },
        title: '投票解锁挑战',
        description: '需要社区投票才能解锁的高难度挑战任务',
        duration_type: 'random' as const,
        duration_value: 720, // 12小时
        duration_max: 1440, // 24小时
        difficulty: 'hard' as const,
        unlock_type: 'vote' as const,
        vote_threshold: 5,
        vote_agreement_ratio: 0.6, // 60%同意率
        start_time: '2024-01-02T10:00:00Z',
        status: 'active' as const,
        created_at: '2024-01-02T09:00:00Z',
        updated_at: '2024-01-02T10:00:00Z'
      },
      {
        id: '3',
        task_type: 'lock' as const,
        user: { id: 2, username: 'otheruser', email: 'other@example.com', level: 2, activity_score: 200, last_active: '2024-01-01', location_precision: 2, coins: 100, bio: '挑战者', total_posts: 10, total_likes_received: 20, total_tasks_completed: 5, created_at: '2024-01-01', updated_at: '2024-01-01' },
        title: '地狱级耐力测试',
        description: '极限挑战，只有意志坚强的人才能完成',
        duration_type: 'fixed' as const,
        duration_value: 2880, // 48小时
        difficulty: 'hell' as const,
        unlock_type: 'vote' as const,
        vote_threshold: 10,
        vote_agreement_ratio: 0.8, // 80%同意率
        overtime_multiplier: 5,
        overtime_duration: 360, // 6小时
        status: 'pending' as const,
        created_at: '2024-01-03T08:00:00Z',
        updated_at: '2024-01-03T08:00:00Z'
      },
      // 任务板
      {
        id: '4',
        task_type: 'board' as const,
        user: { id: 3, username: 'publisher', email: 'pub@example.com', level: 3, activity_score: 300, last_active: '2024-01-01', location_precision: 1, coins: 200, bio: '任务发布者', total_posts: 15, total_likes_received: 50, total_tasks_completed: 8, created_at: '2024-01-01', updated_at: '2024-01-01' },
        title: '设计logo和UI界面',
        description: '为我的新项目设计一套完整的视觉系统，包括logo、配色方案和主要界面设计',
        reward: 500,
        deadline: '2024-01-15T23:59:59Z',
        max_duration: 72, // 3天
        status: 'open' as const,
        created_at: '2024-01-05T10:00:00Z',
        updated_at: '2024-01-05T10:00:00Z'
      },
      {
        id: '5',
        task_type: 'board' as const,
        user: { id: 4, username: 'client', email: 'client@example.com', level: 2, activity_score: 150, last_active: '2024-01-01', location_precision: 3, coins: 300, bio: '需求方', total_posts: 8, total_likes_received: 15, total_tasks_completed: 3, created_at: '2024-01-01', updated_at: '2024-01-01' },
        title: '撰写技术博客文章',
        description: '需要一篇关于Vue 3最佳实践的技术文章，3000字以上，包含代码示例',
        reward: 200,
        deadline: '2024-01-10T18:00:00Z',
        max_duration: 48, // 2天
        status: 'taken' as const,
        taker: { id: 1, username: 'testuser', email: 'test@example.com', level: 1, activity_score: 100, last_active: '2024-01-01', location_precision: 1, coins: 50, bio: '', total_posts: 5, total_likes_received: 10, total_tasks_completed: 2, created_at: '2024-01-01', updated_at: '2024-01-01' },
        taken_at: '2024-01-06T14:00:00Z',
        created_at: '2024-01-06T10:00:00Z',
        updated_at: '2024-01-06T14:00:00Z'
      },
      {
        id: '6',
        task_type: 'board' as const,
        user: { id: 1, username: 'testuser', email: 'test@example.com', level: 1, activity_score: 100, last_active: '2024-01-01', location_precision: 1, coins: 50, bio: '', total_posts: 5, total_likes_received: 10, total_tasks_completed: 2, created_at: '2024-01-01', updated_at: '2024-01-01' },
        title: '数据分析报告',
        description: '分析用户行为数据，提供详细的数据分析报告和优化建议',
        reward: 800,
        deadline: '2024-01-20T17:00:00Z',
        max_duration: 120, // 5天
        status: 'completed' as const,
        taker: { id: 5, username: 'analyst', email: 'analyst@example.com', level: 4, activity_score: 500, last_active: '2024-01-01', location_precision: 2, coins: 1000, bio: '数据专家', total_posts: 20, total_likes_received: 100, total_tasks_completed: 15, created_at: '2024-01-01', updated_at: '2024-01-01' },
        taken_at: '2024-01-04T09:00:00Z',
        completed_at: '2024-01-07T16:30:00Z',
        completion_proof: '已完成数据分析报告，包含详细的用户行为分析和优化建议。',
        created_at: '2024-01-04T08:00:00Z',
        updated_at: '2024-01-07T16:30:00Z'
      }
      ]
    }
  } catch (err: any) {
    error.value = '加载任务失败'
    console.error('Error fetching tasks:', err)
  } finally {
    loading.value = false
  }
}

const canDeleteTask = (task: LockTask) => {
  return authStore.user?.id === task.user.id || authStore.user?.is_superuser
}

const deleteTask = async (task: LockTask) => {
  if (!confirm('确定要删除这个任务吗？')) {
    return
  }

  try {
    await tasksApi.deleteTask(task.id)
    tasks.value = tasks.value.filter(t => t.id !== task.id)
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
    completed: '已完成',
    failed: '已失败',
    open: '开放中',
    taken: '已接取',
    submitted: '已提交'
  }
  return texts[status as keyof typeof texts] || status
}

const formatDuration = (task: LockTask) => {
  // For board tasks, show max_duration instead of duration_value
  if (task.task_type === 'board' && task.max_duration) {
    return `最长 ${task.max_duration} 小时`
  }

  // For lock tasks
  if (!task.duration_value) return '-'

  const hours = Math.floor(task.duration_value / 60)
  const minutes = task.duration_value % 60

  if (task.duration_type === 'random' && task.duration_max) {
    const maxHours = Math.floor(task.duration_max / 60)
    const maxMinutes = task.duration_max % 60
    return `${hours}小时${minutes}分钟 - ${maxHours}小时${maxMinutes}分钟`
  }

  return `${hours}小时${minutes}分钟`
}

const formatDateTime = (dateTime: string) => {
  return new Date(dateTime).toLocaleString('zh-CN')
}

const getProgressPercent = (task: LockTask) => {
  if (task.status !== 'active' || !task.start_time || !task.end_time) {
    return 0
  }

  const start = new Date(task.start_time).getTime()
  const end = new Date(task.end_time).getTime()
  const now = new Date().getTime()

  if (now <= start) return 0
  if (now >= end) return 100

  return ((now - start) / (end - start)) * 100
}

onMounted(() => {
  fetchTasks()
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

.loading, .error, .empty {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  border: 2px solid #000;
  box-shadow: 4px 4px 0 #000;
  text-align: center;
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

.task-status.pending {
  background-color: #6c757d;
  color: white;
}

.task-status.active {
  background-color: #007bff;
  color: white;
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