<template>
  <div class="task-detail">
    <!-- Header -->
    <header class="header">
      <div class="header-content">
        <button @click="goBack" class="back-btn">← 返回</button>
        <h1>任务详情</h1>
        <div class="header-actions">
          <button
            v-if="canDeleteTask"
            @click="deleteTask"
            class="delete-btn"
            title="删除任务"
          >
            🗑️ 删除
          </button>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="main-content">
      <div class="container">
        <!-- Loading -->
        <div v-if="loading" class="loading">
          加载中...
        </div>

        <!-- Error -->
        <div v-else-if="error" class="error">
          {{ error }}
        </div>

        <!-- Task Detail -->
        <div v-else-if="task" class="task-detail-content">
          <!-- Task Info Card -->
          <section class="task-card">
            <div class="task-header">
              <div class="task-basic-info">
                <h2 class="task-title">{{ task.title }}</h2>
                <div class="task-meta">
                  <span class="task-type">{{ getTaskTypeText(task.unlock_type) }}</span>
                  <span class="task-difficulty" :class="task.difficulty">
                    {{ getDifficultyText(task.difficulty) }}
                  </span>
                  <span class="task-status" :class="task.status">
                    {{ getStatusText(task.status) }}
                  </span>
                </div>
              </div>
              <div class="task-user">
                <div class="avatar">
                  {{ task.user.username.charAt(0).toUpperCase() }}
                </div>
                <div class="user-info">
                  <div class="username">{{ task.user.username }}</div>
                  <div class="create-time">创建于 {{ formatDateTime(task.created_at) }}</div>
                </div>
              </div>
            </div>

            <div class="task-description">
              <h3>任务描述</h3>
              <p>{{ task.description }}</p>
            </div>

            <!-- Task Details Grid -->
            <div class="task-details-grid">
              <div class="detail-item">
                <span class="label">持续时间</span>
                <span class="value">{{ formatDuration(task) }}</span>
              </div>
              <div class="detail-item">
                <span class="label">难度等级</span>
                <span class="value">{{ getDifficultyText(task.difficulty) }}</span>
              </div>
              <div class="detail-item">
                <span class="label">解锁方式</span>
                <span class="value">{{ getTaskTypeText(task.unlock_type) }}</span>
              </div>
              <div v-if="task.vote_threshold" class="detail-item">
                <span class="label">投票门槛</span>
                <span class="value">{{ task.vote_threshold }} 票</span>
              </div>
            </div>

            <!-- Task Timeline -->
            <div v-if="task.start_time || task.end_time" class="task-timeline">
              <h3>任务时间线</h3>
              <div class="timeline-item" v-if="task.start_time">
                <div class="timeline-dot start"></div>
                <div class="timeline-content">
                  <div class="timeline-title">任务开始</div>
                  <div class="timeline-time">{{ formatDateTime(task.start_time) }}</div>
                </div>
              </div>
              <div class="timeline-item" v-if="task.end_time">
                <div class="timeline-dot end"></div>
                <div class="timeline-content">
                  <div class="timeline-title">任务结束</div>
                  <div class="timeline-time">{{ formatDateTime(task.end_time) }}</div>
                </div>
              </div>
            </div>

            <!-- Progress Bar for Active Lock Tasks or Taken Board Tasks -->
            <div v-if="(task.task_type === 'lock' && task.status === 'active') || (task.task_type === 'board' && task.status === 'taken')" class="task-progress-section">
              <h3>进度</h3>
              <div class="progress-container">
                <div class="progress-bar">
                  <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
                </div>
                <div class="progress-text">{{ progressPercent.toFixed(1) }}% 完成</div>
              </div>
              <div class="time-remaining">
                <span v-if="timeRemaining > 0">剩余时间: {{ formatTimeRemaining(timeRemaining) }}</span>
                <span v-else class="overtime">任务已结束</span>
              </div>

              <!-- 带锁任务完成提示 -->
              <div v-if="task.task_type === 'lock' && task.status === 'active' && canManageTask" class="completion-hint">
                <div v-if="timeRemaining > 0" class="hint-waiting">
                  ⏳ 带锁任务需要等待倒计时结束后才能完成
                </div>
                <div v-else class="hint-ready">
                  ✅ 倒计时已结束，现在可以完成任务了！
                </div>
              </div>
            </div>
          </section>

          <!-- Action Buttons -->
          <section v-if="canManageTask || canClaimTask || canSubmitProof || canReviewTask || canAddOvertime" class="actions-section">
            <div class="action-buttons">
              <!-- Lock task actions -->
              <button
                v-if="task.status === 'pending' && canManageTask"
                @click="startTask"
                class="action-btn start-btn"
              >
                🚀 开始任务
              </button>
              <button
                v-if="task.status === 'active' && canManageTask && canCompleteTask"
                @click="completeTask"
                class="action-btn complete-btn"
              >
                ✅ 完成任务
              </button>
              <button
                v-if="task.status === 'active' && canManageTask"
                @click="stopTask"
                class="action-btn stop-btn"
              >
                ⏹️ 停止任务
              </button>

              <!-- Overtime action for active lock tasks (others only) -->
              <button
                v-if="canAddOvertime"
                @click="addOvertime"
                class="action-btn overtime-btn"
              >
                ⏰ 随机加时
              </button>

              <!-- Board task actions -->
              <button
                v-if="canClaimTask"
                @click="claimTask"
                class="action-btn claim-btn"
              >
                📋 揭榜任务
              </button>
              <button
                v-if="canSubmitProof"
                @click="submitProof"
                class="action-btn submit-btn"
              >
                📤 提交完成证明
              </button>
              <button
                v-if="canReviewTask"
                @click="approveTask"
                class="action-btn approve-btn"
              >
                ✅ 审核通过
              </button>
              <button
                v-if="canReviewTask"
                @click="rejectTask"
                class="action-btn reject-btn"
              >
                ❌ 审核拒绝
              </button>
            </div>
          </section>

          <!-- Voting Section for Vote-based Tasks -->
          <section v-if="task.unlock_type === 'vote' && task.status === 'active'" class="voting-section">
            <h3>投票解锁</h3>
            <div class="vote-info">
              <div class="vote-count">
                当前票数: <strong>{{ currentVotes }}</strong> / {{ task.vote_threshold }}
              </div>
              <div class="vote-progress">
                <div class="vote-bar">
                  <div
                    class="vote-fill"
                    :style="{ width: (currentVotes / task.vote_threshold * 100) + '%' }"
                  ></div>
                </div>
              </div>
            </div>
            <button
              v-if="!hasVoted && !isOwnTask"
              @click="submitVote"
              class="vote-btn"
            >
              🗳️ 投票解锁
            </button>
            <div v-else-if="hasVoted" class="voted-message">
              ✅ 你已投票
            </div>
          </section>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { tasksApi } from '../lib/api-tasks'
import type { LockTask } from '../types/index.js'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

// State
const task = ref<LockTask | null>(null)
const loading = ref(true)
const error = ref('')
const currentVotes = ref(0)
const hasVoted = ref(false)
const progressInterval = ref<number>()

// Computed properties
const canDeleteTask = computed(() => {
  if (!task.value) return false
  return authStore.user?.id === task.value.user.id || authStore.user?.is_superuser
})

const canManageTask = computed(() => {
  if (!task.value) return false
  return authStore.user?.id === task.value.user.id
})

const isOwnTask = computed(() => {
  if (!task.value) return false
  return authStore.user?.id === task.value.user.id
})

const canClaimTask = computed(() => {
  if (!task.value) return false
  // Can claim if it's a board task, status is open, and not own task
  return task.value.task_type === 'board' &&
         task.value.status === 'open' &&
         !isOwnTask.value
})

const canSubmitProof = computed(() => {
  if (!task.value) return false
  // Can submit proof if it's a board task taken by current user
  return task.value.task_type === 'board' &&
         task.value.status === 'taken' &&
         task.value.taker?.id === authStore.user?.id
})

const canReviewTask = computed(() => {
  if (!task.value) return false
  // Can review if it's a board task, submitted status, and user is the publisher
  return task.value.task_type === 'board' &&
         task.value.status === 'submitted' &&
         task.value.user.id === authStore.user?.id
})

const canAddOvertime = computed(() => {
  if (!task.value) return false
  // Can add overtime if it's a lock task, status is active, and not own task
  return task.value.task_type === 'lock' &&
         task.value.status === 'active' &&
         !isOwnTask.value
})

const canCompleteTask = computed(() => {
  if (!task.value) return false

  // For lock tasks, can only complete after countdown ends
  if (task.value.task_type === 'lock' && task.value.end_time) {
    const now = new Date().getTime()
    const endTime = new Date(task.value.end_time).getTime()
    return now >= endTime
  }

  // For board tasks, can complete anytime when active
  return true
})

const progressPercent = computed(() => {
  if (!task.value) return 0

  // Lock tasks progress
  if (task.value.task_type === 'lock' && task.value.status === 'active' && task.value.start_time && task.value.end_time) {
    const start = new Date(task.value.start_time).getTime()
    const end = new Date(task.value.end_time).getTime()
    const now = new Date().getTime()

    if (now <= start) return 0
    if (now >= end) return 100

    return ((now - start) / (end - start)) * 100
  }

  // Board tasks progress
  if (task.value.task_type === 'board' && task.value.status === 'taken' && task.value.taken_at && task.value.deadline) {
    const start = new Date(task.value.taken_at).getTime()
    const end = new Date(task.value.deadline).getTime()
    const now = new Date().getTime()

    if (now <= start) return 0
    if (now >= end) return 100

    return ((now - start) / (end - start)) * 100
  }

  return 0
})

const timeRemaining = computed(() => {
  if (!task.value) return 0

  // Lock tasks time remaining
  if (task.value.task_type === 'lock' && task.value.status === 'active' && task.value.end_time) {
    const end = new Date(task.value.end_time).getTime()
    const now = new Date().getTime()
    return Math.max(0, end - now)
  }

  // Board tasks time remaining
  if (task.value.task_type === 'board' && task.value.status === 'taken' && task.value.deadline) {
    const end = new Date(task.value.deadline).getTime()
    const now = new Date().getTime()
    return Math.max(0, end - now)
  }

  return 0
})

// Methods
const goBack = () => {
  router.back()
}

const fetchTask = async () => {
  const taskId = route.params.id as string
  if (!taskId) {
    error.value = '无效的任务ID'
    loading.value = false
    return
  }

  try {
    const fetchedTask = await tasksApi.getTask(taskId)
    task.value = fetchedTask

    // 模拟投票数据
    currentVotes.value = fetchedTask.vote_count || 1

    // 检查是否已投票（简单模拟）
    hasVoted.value = false

    // 如果是活跃任务或已接取的任务板，启动进度更新
    if ((task.value.task_type === 'lock' && task.value.status === 'active') ||
        (task.value.task_type === 'board' && task.value.status === 'taken')) {
      startProgressUpdate()
    }

  } catch (err: any) {
    // 使用模拟数据作为备用
    const mockTask: LockTask = {
      id: taskId,
      user: {
        id: 1,
        username: 'testuser',
        email: 'test@example.com',
        level: 2,
        activity_score: 150,
        last_active: '2024-01-01',
        location_precision: 1,
        coins: 75,
        bio: '热爱挑战的用户',
        total_posts: 8,
        total_likes_received: 25,
        total_tasks_completed: 5,
        created_at: '2023-12-01',
        updated_at: '2024-01-01'
      },
      title: '专注学习挑战',
      description: '在学习期间保持专注，不使用社交媒体和娱乐应用。这是一个测试意志力和自律能力的挑战任务。完成后将获得成就感和积分奖励。',
      duration_type: 'fixed' as const,
      duration_value: 240, // 4小时
      difficulty: 'normal' as const,
      unlock_type: 'vote' as const,
      vote_threshold: 3,
      start_time: new Date(Date.now() - 60 * 60 * 1000).toISOString(), // 1小时前开始
      end_time: new Date(Date.now() + 3 * 60 * 60 * 1000).toISOString(), // 3小时后结束
      status: 'active' as const,
      created_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(), // 1天前创建
      updated_at: new Date(Date.now() - 60 * 60 * 1000).toISOString()
    }

    task.value = mockTask
    currentVotes.value = 1 // 模拟当前投票数

    // 如果是活跃任务或已接取的任务板，启动进度更新
    if ((task.value.task_type === 'lock' && task.value.status === 'active') ||
        (task.value.task_type === 'board' && task.value.status === 'taken')) {
      startProgressUpdate()
    }

    // Log the error for debugging
    if (err.status === 404) {
      console.log('Task not found, using mock data')
    } else {
      console.error('Error fetching task, using mock data:', err)
    }
  } finally {
    loading.value = false
  }
}

const startProgressUpdate = () => {
  progressInterval.value = window.setInterval(() => {
    // Force reactivity update for time-based progress
    if (task.value?.status === 'active') {
      // Progress is computed, just trigger an update
    }
  }, 1000)
}

const deleteTask = async () => {
  if (!task.value || !confirm('确定要删除这个任务吗？')) {
    return
  }

  try {
    await tasksApi.deleteTask(task.value.id)
    console.log('任务删除成功')
    router.push({ name: 'tasks' })
  } catch (error) {
    console.error('Error deleting task:', error)
    alert('删除失败，请重试')
  }
}

const startTask = async () => {
  if (!task.value) return

  try {
    const updatedTask = await tasksApi.startTask(task.value.id)
    task.value = updatedTask
    console.log('任务已开始')
    startProgressUpdate()
  } catch (error) {
    console.error('Error starting task:', error)
    alert('开始任务失败，请重试')
  }
}

const completeTask = async () => {
  if (!task.value) return

  // 第一次确认
  if (!confirm('确定要标记任务为已完成吗？')) {
    return
  }

  // 第二次确认（更加严重的提醒）
  if (!confirm('⚠️ 请再次确认：一旦标记为完成，此操作无法撤销！\n\n确定要完成这个任务吗？')) {
    return
  }

  try {
    const updatedTask = await tasksApi.completeTask(task.value.id)
    task.value = updatedTask
    console.log('任务已完成')
    if (progressInterval.value) {
      clearInterval(progressInterval.value)
    }
    alert('✅ 任务已成功完成！')
  } catch (error: any) {
    console.error('Error completing task:', error)

    // 处理特定错误消息
    if (error.response?.data?.error) {
      alert(`完成失败：${error.response.data.error}`)
    } else {
      alert('完成任务失败，请重试')
    }
  }
}

const stopTask = async () => {
  if (!task.value) return

  // 第一次确认
  if (!confirm('确定要停止这个任务吗？任务将标记为失败。')) {
    return
  }

  // 第二次确认（更加严重的提醒）
  if (!confirm('⚠️ 请再次确认：停止任务将标记为失败，此操作无法撤销！\n\n确定要停止这个任务吗？')) {
    return
  }

  try {
    const updatedTask = await tasksApi.stopTask(task.value.id)
    task.value = updatedTask
    console.log('任务已停止')
    if (progressInterval.value) {
      clearInterval(progressInterval.value)
    }
    alert('⚠️ 任务已停止并标记为失败')
  } catch (error: any) {
    console.error('Error stopping task:', error)

    // 处理特定错误消息
    if (error.response?.data?.error) {
      alert(`停止失败：${error.response.data.error}`)
    } else {
      alert('停止任务失败，请重试')
    }
  }
}

const submitVote = async () => {
  if (!task.value || hasVoted.value) return

  try {
    await tasksApi.voteTask(task.value.id, true)
    currentVotes.value += 1
    hasVoted.value = true
    console.log('投票成功')

    // 检查是否达到解锁门槛
    if (currentVotes.value >= (task.value.vote_threshold || 0)) {
      console.log('投票门槛已达到，任务可以解锁')
    }
  } catch (error) {
    console.error('Error voting:', error)
    alert('投票失败，请重试')
  }
}

const claimTask = async () => {
  if (!task.value || !canClaimTask.value) return

  if (!confirm('确定要揭榜这个任务吗？揭榜后需要在规定时间内完成。')) {
    return
  }

  try {
    const updatedTask = await tasksApi.takeTask(task.value.id)
    task.value = updatedTask
    console.log('任务揭榜成功')
    startProgressUpdate() // 开始进度更新
  } catch (error) {
    console.error('Error claiming task:', error)
    alert('揭榜失败，请重试')
  }
}

const submitProof = async () => {
  if (!task.value || !canSubmitProof.value) return

  const completionProof = prompt('请输入完成证明：')
  if (!completionProof || !completionProof.trim()) {
    alert('请提供完成证明')
    return
  }

  try {
    const updatedTask = await tasksApi.submitTask(task.value.id, completionProof.trim())
    task.value = updatedTask
    console.log('任务提交成功')
    if (progressInterval.value) {
      clearInterval(progressInterval.value)
    }
  } catch (error) {
    console.error('Error submitting task:', error)
    alert('提交失败，请重试')
  }
}

const approveTask = async () => {
  if (!task.value || !canReviewTask.value) return

  if (!confirm('确定要审核通过这个任务吗？')) {
    return
  }

  try {
    const updatedTask = await tasksApi.approveTask(task.value.id)
    task.value = updatedTask
    console.log('任务审核通过')
  } catch (error) {
    console.error('Error approving task:', error)
    alert('审核失败，请重试')
  }
}

const rejectTask = async () => {
  if (!task.value || !canReviewTask.value) return

  const rejectReason = prompt('请输入拒绝原因（可选）：')

  if (!confirm('确定要审核拒绝这个任务吗？')) {
    return
  }

  try {
    const updatedTask = await tasksApi.rejectTask(task.value.id, rejectReason || '')
    task.value = updatedTask
    console.log('任务审核拒绝')
  } catch (error) {
    console.error('Error rejecting task:', error)
    alert('审核失败，请重试')
  }
}

const addOvertime = async () => {
  if (!task.value || !canAddOvertime.value) return

  if (!confirm('确定要为这个任务随机加时吗？加时力度基于任务难度等级。')) {
    return
  }

  try {
    const result = await tasksApi.addOvertime(task.value.id)

    // 更新任务结束时间
    if (result.new_end_time) {
      task.value.end_time = result.new_end_time
    }

    // 显示加时信息
    alert(`成功为任务加时 ${result.overtime_minutes} 分钟！`)
    console.log('任务加时成功:', result)
  } catch (error) {
    console.error('Error adding overtime:', error)
    alert('加时失败，请重试')
  }
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

onMounted(() => {
  fetchTask()
})

onUnmounted(() => {
  if (progressInterval.value) {
    clearInterval(progressInterval.value)
  }
})
</script>

<style scoped>
.task-detail {
  min-height: 100vh;
  background-color: #f5f5f5;
}

.header {
  background: white;
  border-bottom: 2px solid #000;
  padding: 1rem 0;
}

.header-content {
  max-width: 1000px;
  margin: 0 auto;
  padding: 0 1rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.back-btn, .delete-btn {
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

.delete-btn {
  background-color: #dc3545;
  color: white;
  border-color: #dc3545;
}

.delete-btn:hover {
  background-color: #c82333;
}

.header h1 {
  font-size: 1.5rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0;
}

.main-content {
  max-width: 1000px;
  margin: 0 auto;
  padding: 2rem 1rem;
}

.loading, .error {
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

.task-detail-content {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.task-card, .actions-section, .voting-section {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  border: 2px solid #000;
  box-shadow: 4px 4px 0 #000;
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 2px solid #e9ecef;
}

.task-title {
  font-size: 1.5rem;
  font-weight: bold;
  margin: 0 0 0.5rem 0;
  color: #333;
}

.task-meta {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.task-type, .task-difficulty, .task-status {
  padding: 0.25rem 0.75rem;
  border-radius: 4px;
  font-size: 0.875rem;
  font-weight: bold;
  text-transform: uppercase;
}

.task-type {
  background-color: #17a2b8;
  color: white;
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

.task-user {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background-color: #007bff;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 1.2rem;
}

.username {
  font-weight: bold;
  font-size: 1.1rem;
}

.create-time {
  font-size: 0.875rem;
  color: #666;
}

.task-description {
  margin-bottom: 2rem;
}

.task-description h3 {
  margin: 0 0 1rem 0;
  font-size: 1.2rem;
  font-weight: bold;
}

.task-description p {
  line-height: 1.6;
  color: #555;
}

.task-details-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
  padding: 1rem;
  background-color: #f8f9fa;
  border-radius: 4px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.label {
  font-weight: 500;
  color: #666;
  font-size: 0.875rem;
}

.value {
  font-weight: bold;
  color: #333;
}

.task-timeline {
  margin-bottom: 2rem;
}

.task-timeline h3 {
  margin: 0 0 1rem 0;
  font-size: 1.2rem;
  font-weight: bold;
}

.timeline-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
}

.timeline-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  flex-shrink: 0;
}

.timeline-dot.start {
  background-color: #28a745;
}

.timeline-dot.end {
  background-color: #dc3545;
}

.timeline-title {
  font-weight: bold;
}

.timeline-time {
  font-size: 0.875rem;
  color: #666;
}

.task-progress-section {
  margin-bottom: 2rem;
}

.task-progress-section h3 {
  margin: 0 0 1rem 0;
  font-size: 1.2rem;
  font-weight: bold;
}

.progress-container {
  margin-bottom: 1rem;
}

.progress-bar {
  width: 100%;
  height: 20px;
  background-color: #e9ecef;
  border-radius: 10px;
  overflow: hidden;
  margin-bottom: 0.5rem;
}

.progress-fill {
  height: 100%;
  background-color: #007bff;
  transition: width 0.5s ease;
}

.progress-text {
  font-weight: bold;
  color: #007bff;
}

.time-remaining {
  font-size: 1.1rem;
  font-weight: 500;
}

.overtime {
  color: #dc3545;
}

.completion-hint {
  margin-top: 1rem;
  padding: 0.75rem;
  border-radius: 4px;
  font-weight: 500;
  text-align: center;
}

.hint-waiting {
  background-color: #fff3cd;
  border: 1px solid #ffeaa7;
  color: #856404;
}

.hint-ready {
  background-color: #d4edda;
  border: 1px solid #c3e6cb;
  color: #155724;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
  100% {
    opacity: 1;
  }
}

.action-buttons {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.action-btn {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 600;
  font-size: 1rem;
  color: white;
}

.start-btn {
  background-color: #28a745;
}

.start-btn:hover {
  background-color: #218838;
}

.complete-btn {
  background-color: #007bff;
}

.complete-btn:hover {
  background-color: #0056b3;
}

.stop-btn {
  background-color: #dc3545;
}

.stop-btn:hover {
  background-color: #c82333;
}

.claim-btn {
  background-color: #ffc107;
  color: #212529;
}

.claim-btn:hover {
  background-color: #e0a800;
}

.submit-btn {
  background-color: #17a2b8;
  color: white;
}

.submit-btn:hover {
  background-color: #138496;
}

.approve-btn {
  background-color: #28a745;
  color: white;
}

.approve-btn:hover {
  background-color: #218838;
}

.reject-btn {
  background-color: #dc3545;
  color: white;
}

.reject-btn:hover {
  background-color: #c82333;
}

.overtime-btn {
  background-color: #fd7e14;
  color: white;
}

.overtime-btn:hover {
  background-color: #e76500;
}

.voting-section h3 {
  margin: 0 0 1rem 0;
  font-size: 1.2rem;
  font-weight: bold;
}

.vote-info {
  margin-bottom: 1rem;
}

.vote-count {
  font-size: 1.1rem;
  margin-bottom: 0.5rem;
}

.vote-bar {
  width: 100%;
  height: 16px;
  background-color: #e9ecef;
  border-radius: 8px;
  overflow: hidden;
}

.vote-fill {
  height: 100%;
  background-color: #ffc107;
  transition: width 0.3s ease;
}

.vote-btn {
  background-color: #ffc107;
  color: #212529;
  border: none;
  border-radius: 4px;
  padding: 0.75rem 1.5rem;
  cursor: pointer;
  font-weight: 600;
  font-size: 1rem;
}

.vote-btn:hover {
  background-color: #e0a800;
}

.voted-message {
  color: #28a745;
  font-weight: 500;
  font-size: 1.1rem;
}

/* Mobile responsive */
@media (max-width: 768px) {
  .header-content {
    padding: 0 1rem;
  }

  .main-content {
    padding: 1rem;
  }

  .task-card, .actions-section, .voting-section {
    padding: 1rem;
  }

  .task-header {
    flex-direction: column;
    gap: 1rem;
    align-items: flex-start;
  }

  .task-details-grid {
    grid-template-columns: 1fr;
  }

  .action-buttons {
    flex-direction: column;
  }

  .action-btn {
    width: 100%;
  }
}
</style>