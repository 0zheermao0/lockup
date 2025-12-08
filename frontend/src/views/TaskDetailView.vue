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
                  <span class="task-type">{{ getTaskTypeText(taskUnlockType) }}</span>
                  <span class="task-difficulty" :class="taskDifficulty">
                    {{ getDifficultyText(taskDifficulty) }}
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
                  <button
                    @click="openUserProfile(task.user.id)"
                    class="username-btn"
                    :title="`查看 ${task.user.username} 的资料`"
                  >
                    {{ task.user.username }}
                  </button>
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
              <div v-if="task.task_type === 'lock' && task.status === 'active'" class="detail-item">
                <span class="label">剩余时间</span>
                <span class="value countdown-display" :class="{ 'overtime': timeRemaining <= 0 }">
                  {{ timeRemaining > 0 ? formatTimeRemaining(timeRemaining) : '倒计时已结束' }}
                </span>
              </div>
              <div v-if="task.task_type === 'lock' && taskStartTime" class="detail-item">
                <span class="label">开始时间</span>
                <span class="value">{{ formatDateTime(taskStartTime) }}</span>
              </div>
              <div v-if="task.task_type === 'lock' && taskEndTime" class="detail-item">
                <span class="label">预计结束时间</span>
                <span class="value">{{ formatDateTime(taskEndTime) }}</span>
              </div>
              <div class="detail-item">
                <span class="label">难度等级</span>
                <span class="value">{{ getDifficultyText(taskDifficulty) }}</span>
              </div>
              <div class="detail-item">
                <span class="label">解锁方式</span>
                <span class="value">{{ getTaskTypeText(taskUnlockType) }}</span>
              </div>
              <div v-if="taskVoteThreshold" class="detail-item">
                <span class="label">投票门槛</span>
                <span class="value">{{ taskVoteThreshold }} 票</span>
              </div>
            </div>

            <!-- Task Timeline -->
            <div v-if="timeline.length > 0 || taskStartTime || taskEndTime" class="task-timeline">
              <div class="timeline-header">
                <h3>任务时间线</h3>
                <button
                  @click="refreshTimeline"
                  :disabled="timelineLoading"
                  class="refresh-timeline-btn"
                  title="刷新时间线"
                >
                  {{ timelineLoading ? '🔄' : '🔄' }} 刷新
                </button>
              </div>
              <div v-if="timelineLoading" class="timeline-loading">
                加载时间线中...
              </div>
              <div v-else class="timeline-container">
                <!-- Timeline events from API -->
                <div
                  v-for="event in timeline"
                  :key="event.id"
                  class="timeline-item"
                >
                  <div class="timeline-dot" :class="getEventTypeClass(event.event_type)"></div>
                  <div class="timeline-content">
                    <div class="timeline-title">{{ event.event_type_display }}</div>
                    <div class="timeline-description">{{ event.description }}</div>
                    <div class="timeline-time">{{ formatDateTime(event.created_at) }}</div>
                    <div v-if="event.user" class="timeline-user">
                      操作者:
                      <button
                        @click="openUserProfile(event.user.id)"
                        class="timeline-user-btn"
                        :title="`查看 ${event.user.username} 的资料`"
                      >
                        {{ event.user.username }}
                      </button>
                    </div>
                    <div v-if="event.time_change_minutes" class="timeline-time-change">
                      时间变化: {{ event.time_change_minutes > 0 ? '+' : '' }}{{ event.time_change_minutes }} 分钟
                    </div>
                    <div v-if="event.previous_end_time && event.new_end_time" class="timeline-times">
                      <div class="previous-time">原定结束: {{ formatDateTime(event.previous_end_time) }}</div>
                      <div class="new-time">新的结束: {{ formatDateTime(event.new_end_time) }}</div>
                    </div>
                  </div>
                </div>

                <!-- Fallback: Basic timeline if no API events -->
                <div v-if="timeline.length === 0 && taskStartTime" class="timeline-item">
                  <div class="timeline-dot start"></div>
                  <div class="timeline-content">
                    <div class="timeline-title">任务开始</div>
                    <div class="timeline-time">{{ formatDateTime(taskStartTime) }}</div>
                  </div>
                </div>
                <div v-if="timeline.length === 0 && taskEndTime" class="timeline-item">
                  <div class="timeline-dot end"></div>
                  <div class="timeline-content">
                    <div class="timeline-title">任务结束</div>
                    <div class="timeline-time">{{ formatDateTime(taskEndTime) }}</div>
                  </div>
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
                <span v-else class="overtime">倒计时已结束</span>
              </div>

              <!-- 带锁任务完成提示 -->
              <div v-if="task.task_type === 'lock' && task.status === 'active'" class="completion-hint">
                <!-- Key ownership requirement -->
                <div v-if="keyCheckLoading" class="hint-loading">
                  🔍 正在检查钥匙持有情况...
                </div>
                <div v-else-if="!hasTaskKey && authStore.isAuthenticated" class="hint-no-key">
                  🔑 您没有持有此任务的钥匙，无法完成任务。只有钥匙的当前持有者才能完成此任务。
                </div>
                <div v-else-if="hasTaskKey">
                  <!-- Unlock type specific hints for key holders -->
                  <div v-if="taskUnlockType === 'vote'" class="hint-vote">
                    <div v-if="!isVotingPassed">
                      🗳️ 投票解锁任务：倒计时结束后可发起投票，投票通过后等待实际时间结束才能完成
                    </div>
                    <div v-else-if="timeRemaining > 0" class="hint-waiting">
                      ✅ 投票已通过！等待倒计时结束后可手动完成任务：{{ formatTimeRemaining(timeRemaining) }}
                    </div>
                    <div v-else class="hint-ready">
                      🎉 投票已通过且倒计时已结束，您可以手动完成任务！
                    </div>
                  </div>
                  <div v-else-if="timeRemaining > 0" class="hint-waiting">
                    ⏳ 定时解锁任务：需要等待倒计时结束后才能手动完成
                  </div>
                  <div v-else class="hint-ready">
                    ✅ 倒计时已结束，您持有钥匙，可以手动完成任务
                  </div>

                  <!-- Key management section for key holders -->
                  <div v-if="taskKey && taskKey.original_owner && taskKey.original_owner.id !== authStore.user?.id" class="key-management">
                    <div class="key-return-info">
                      🔄 此钥匙原本属于 <strong>{{ taskKey.original_owner.username }}</strong>，您可以选择归还
                    </div>
                    <button
                      @click="returnKeyToOriginalOwner"
                      :disabled="returningKey"
                      class="return-key-btn"
                    >
                      {{ returningKey ? '归还中...' : '🔄 归还钥匙' }}
                    </button>
                  </div>
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
                v-if="task.status === 'active' && canCompleteTask"
                @click="completeTask"
                class="action-btn complete-btn"
              >
                ✅ 完成任务
              </button>
              <button
                v-if="(task.status === 'active' || task.status === 'voting') && canManageLockTask"
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
                @click="openSubmissionModal"
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
          <section v-if="taskUnlockType === 'vote' && (task.status === 'active' || task.status === 'voting')" class="voting-section">
            <h3>投票解锁</h3>

            <!-- Task in active state, waiting for countdown -->
            <div v-if="task.status === 'active'" class="voting-waiting">
              <div v-if="timeRemaining > 0" class="vote-countdown-notice">
                ⏳ 投票将在倒计时结束后开放: {{ formatTimeRemaining(timeRemaining) }}
              </div>
              <div v-else-if="isOwnTask" class="vote-ready-notice">
                ✅ 倒计时已结束，你可以发起投票！点击按钮开始10分钟投票期
              </div>
              <div v-else class="vote-waiting-notice">
                ⏳ 倒计时已结束，等待任务创建者发起投票...
              </div>
            </div>

            <!-- Task in voting period -->
            <div v-else-if="task.status === 'voting'" class="voting-active">
              <div class="voting-period-info">
                <h4>🗳️ 投票期进行中</h4>
                <div class="voting-countdown">
                  投票剩余时间: <strong>{{ formatVotingTimeRemaining() }}</strong>
                </div>
                <div class="voting-schedule">
                  投票开始: {{ formatDateTime(taskVotingStartTime || '') }}<br>
                  投票结束: {{ formatDateTime(taskVotingEndTime || '') }}
                </div>
              </div>
            </div>

            <!-- Vote statistics -->
            <div class="vote-info">
              <div class="vote-count">
                当前票数: <strong>{{ currentVotes }}</strong> 票
                <span v-if="taskVoteAgreementRatio">(需要 {{ (taskVoteAgreementRatio * 100).toFixed(0) }}% 同意率)</span>
              </div>
              <div v-if="currentVotes > 0" class="vote-breakdown">
                同意: {{ taskVoteAgreementCount }} 票 |
                反对: {{ currentVotes - taskVoteAgreementCount }} 票 |
                同意率: {{ (taskVoteAgreementCount / currentVotes * 100).toFixed(1) }}%
              </div>
            </div>

            <!-- Voting buttons -->
            <div class="vote-actions">
              <!-- Start voting button (only for task owner when countdown ends) -->
              <button
                v-if="canStartVoting"
                @click="startVoting"
                class="start-vote-btn"
              >
                🗳️ 发起投票
              </button>

              <!-- Vote button (for everyone during voting period) -->
              <button
                v-else-if="canVote"
                @click="openVoteModal"
                class="vote-btn"
              >
                🗳️ 参与投票
              </button>
            </div>

            <!-- Status messages -->
            <div v-if="hasVoted" class="voted-message">
              ✅ 你已投票
            </div>

            <!-- Voting results display for completed or active tasks -->
            <div v-if="showVotingResults" class="voting-results">
              <h4>🗳️ 投票结果</h4>
              <div class="voting-result-summary">
                <div class="result-item">
                  <span class="result-label">总票数:</span>
                  <span class="result-value">{{ currentVotes }} 票</span>
                </div>
                <div class="result-item">
                  <span class="result-label">同意票:</span>
                  <span class="result-value">{{ taskVoteAgreementCount }} 票</span>
                </div>
                <div class="result-item">
                  <span class="result-label">反对票:</span>
                  <span class="result-value">{{ currentVotes - taskVoteAgreementCount }} 票</span>
                </div>
                <div class="result-item">
                  <span class="result-label">同意率:</span>
                  <span class="result-value">{{ currentVotes > 0 ? (taskVoteAgreementCount / currentVotes * 100).toFixed(1) : 0 }}%</span>
                </div>
              </div>

              <div class="voting-conclusion">
                <div v-if="isTaskCompleted" class="voting-passed">
                  ✅ 投票通过！任务已完成。
                </div>
                <div v-else-if="isVotingPassed" class="voting-passed">
                  ✅ 投票通过！任务可完成。
                </div>
                <div v-else class="voting-failed">
                  ❌ 投票未通过，任务继续进行并已加时。
                  <div class="failure-reasons">
                    <div v-if="currentVotes < taskVoteThresholdValue">
                      • 票数不足（需要 {{ taskVoteThresholdValue }} 票，当前 {{ currentVotes }} 票）
                    </div>
                    <div v-if="taskVoteAgreementRatio && currentVotes > 0 && (taskVoteAgreementCount / currentVotes) < taskVoteAgreementRatio">
                      • 同意率不足（需要 {{ (taskVoteAgreementRatio * 100).toFixed(0) }}%，当前 {{ (taskVoteAgreementCount / currentVotes * 100).toFixed(1) }}%）
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>
        </div>
      </div>
    </main>

    <!-- Task Submission Modal -->
    <TaskSubmissionModal
      :is-visible="showSubmissionModal"
      :task="task as any"
      @close="closeSubmissionModal"
      @success="handleSubmissionSuccess"
    />

    <!-- Profile Modal -->
    <ProfileModal
      :is-visible="showProfileModal"
      :user-id="selectedUserId"
      @close="closeProfileModal"
    />

    <!-- Vote Confirmation Modal -->
    <VoteConfirmationModal
      :is-visible="showVoteModal"
      :task="task as any"
      @close="closeVoteModal"
      @vote="submitVote"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useTasksStore } from '../stores/tasks'
import { tasksApi } from '../lib/api-tasks'
import { storeApi } from '../lib/api'
import TaskSubmissionModal from '../components/TaskSubmissionModal.vue'
import ProfileModal from '../components/ProfileModal.vue'
import VoteConfirmationModal from '../components/VoteConfirmationModal.vue'
import type { Task } from '../types/index.js'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const tasksStore = useTasksStore()

// State
const task = ref<Task | null>(null)
const loading = ref(true)
const error = ref('')
const currentVotes = ref(0)
const hasVoted = ref(false)
const progressInterval = ref<number>()
const currentTime = ref(Date.now())
const timeline = ref<any[]>([])
const timelineLoading = ref(false)
const showSubmissionModal = ref(false)
const showProfileModal = ref(false)
const selectedUserId = ref<number | undefined>(undefined)
const showVoteModal = ref(false)
const votingProcessing = ref(false) // 防止重复处理投票结果
const userInventory = ref<any>(null)
const hasTaskKey = ref(false)
const keyCheckLoading = ref(false)
const taskKey = ref<any>(null)
const returningKey = ref(false)

// Computed properties for template access
const taskUnlockType = computed(() => {
  if (!task.value) return 'time'
  return task.value.task_type === 'lock' ? (task.value as any).unlock_type || 'time' : 'time'
})

const taskDifficulty = computed(() => {
  if (!task.value) return 'normal'
  return task.value.task_type === 'lock' ? (task.value as any).difficulty || 'normal' : 'normal'
})

const taskVoteThreshold = computed(() => {
  if (!task.value || task.value.task_type !== 'lock') return 0
  return (task.value as any).vote_threshold || 0
})

const taskStartTime = computed(() => {
  if (!task.value) return null
  return task.value.task_type === 'lock' ? (task.value as any).start_time : null
})

const taskVotingStartTime = computed(() => {
  if (!task.value || task.value.task_type !== 'lock') return null
  return (task.value as any).voting_start_time || null
})

const taskVotingEndTime = computed(() => {
  if (!task.value || task.value.task_type !== 'lock') return null
  return (task.value as any).voting_end_time || null
})

const taskVoteAgreementRatio = computed(() => {
  if (!task.value || task.value.task_type !== 'lock') return null
  return (task.value as any).vote_agreement_ratio || null
})

const taskVoteAgreementCount = computed(() => {
  if (!task.value || task.value.task_type !== 'lock') return 0
  return (task.value as any).vote_agreement_count || 0
})

const taskVoteThresholdValue = computed(() => {
  if (!task.value || task.value.task_type !== 'lock') return 0
  return (task.value as any).vote_threshold || 0
})

const isVotingPassed = computed(() => {
  if (!task.value || task.value.task_type !== 'lock' || taskUnlockType.value !== 'vote') {
    console.log('🗳️ isVotingPassed: false - not a vote unlock task')
    return false
  }

  const totalVotes = currentVotes.value
  const agreeVotes = taskVoteAgreementCount.value
  const requiredThreshold = taskVoteThresholdValue.value || 0
  const requiredRatio = taskVoteAgreementRatio.value || 0.5

  console.log('🗳️ isVotingPassed check:', {
    totalVotes,
    agreeVotes,
    requiredThreshold,
    requiredRatio,
    hasVotingTimes: !!(taskVotingStartTime.value && taskVotingEndTime.value)
  })

  // 检查是否经历了完整的投票流程
  if (!taskVotingStartTime.value || !taskVotingEndTime.value) {
    console.log('🗳️ isVotingPassed: false - no complete voting process')
    return false
  }

  // 检查投票数量是否达到门槛
  if (totalVotes < requiredThreshold) {
    console.log('🗳️ isVotingPassed: false - not enough votes:', totalVotes, '<', requiredThreshold)
    return false
  }

  // 检查同意比例是否达到要求
  const agreementRatio = totalVotes === 0 ? 0 : agreeVotes / totalVotes
  if (agreementRatio < requiredRatio) {
    console.log('🗳️ isVotingPassed: false - agreement ratio not met:', agreementRatio, '<', requiredRatio)
    return false
  }

  console.log('🗳️ isVotingPassed: true - all conditions met')
  return true
})

const taskEndTime = computed(() => {
  if (!task.value) return null
  if (task.value.task_type === 'lock') {
    return (task.value as any).end_time || null
  }
  return null
})

const canDeleteTask = computed(() => {
  if (!task.value) return false
  return authStore.user?.id === task.value.user.id || authStore.user?.is_superuser
})

const canManageTask = computed(() => {
  if (!task.value) return false
  const canManage = authStore.user?.id === task.value.user.id
  console.log('🔧 canManageTask:', canManage, 'for user:', authStore.user?.id, 'task owner:', task.value.user.id)
  return canManage
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
  if (task.value.task_type === 'board' && task.value.status === 'taken') {
    const boardTask = task.value as any // Type assertion for board task properties
    return boardTask.taker?.id === authStore.user?.id
  }
  return false
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

const canManageLockTask = computed(() => {
  if (!task.value) return false

  // For lock tasks, either the task owner OR the key holder can manage certain actions
  if (task.value.task_type === 'lock') {
    const isTaskOwner = authStore.user?.id === task.value.user.id
    const isKeyHolder = hasTaskKey.value && !keyCheckLoading.value

    console.log('🔐 canManageLockTask check:', {
      isTaskOwner,
      isKeyHolder,
      hasTaskKey: hasTaskKey.value,
      keyCheckLoading: keyCheckLoading.value
    })

    return isTaskOwner || isKeyHolder
  }

  // For non-lock tasks, use original logic
  return canManageTask.value
})

const canCompleteTask = computed(() => {
  if (!task.value) return false

  console.log('🎯 canCompleteTask check for task:', task.value.id, {
    taskType: task.value.task_type,
    status: task.value.status,
    unlockType: taskUnlockType.value,
    hasTaskKey: hasTaskKey.value,
    keyCheckLoading: keyCheckLoading.value
  })

  // For lock tasks, must have the task key to complete
  if (task.value.task_type === 'lock') {
    // If still checking key ownership, don't allow completion yet
    if (keyCheckLoading.value) {
      console.log('🎯 canCompleteTask: false - still checking key ownership')
      return false
    }

    // Must have the task key
    if (!hasTaskKey.value) {
      console.log('🎯 canCompleteTask: false - user does not have task key')
      return false
    }

    // For lock tasks with vote unlock type - can complete after voting passes AND countdown ends
    if (taskUnlockType.value === 'vote') {
      // Check if voting has passed
      if (!isVotingPassed.value) {
        console.log('🎯 canCompleteTask: false - voting has not passed yet')
        return false
      }

      // If voting passed, check if countdown has ended
      if (taskEndTime.value) {
        const now = currentTime.value
        const endTime = new Date(taskEndTime.value).getTime()
        const canComplete = now >= endTime
        console.log('🎯 canCompleteTask (vote unlock, voting passed, checking time):', canComplete, 'now:', now, 'endTime:', endTime)
        return canComplete
      }

      // If no end time, can complete immediately after voting passes
      console.log('🎯 canCompleteTask: true - voting passed and no countdown')
      return true
    }

    // For lock tasks with time unlock type, can only complete after countdown ends
    if (taskEndTime.value) {
      const now = currentTime.value
      const endTime = new Date(taskEndTime.value).getTime()
      const canComplete = now >= endTime
      console.log('🎯 canCompleteTask (time unlock with key):', canComplete, 'now:', now, 'endTime:', endTime)
      return canComplete
    }
  }

  // For board tasks, can complete anytime when active
  const canComplete = task.value.status === 'active'
  console.log('🎯 canCompleteTask (board task):', canComplete)
  return canComplete
})

const progressPercent = computed(() => {
  if (!task.value) return 0

  // Lock tasks progress
  if (task.value.task_type === 'lock' && task.value.status === 'active' && task.value.start_time && task.value.end_time) {
    const start = new Date(task.value.start_time).getTime()
    const end = new Date(task.value.end_time).getTime()
    const now = currentTime.value

    if (now <= start) return 0
    if (now >= end) return 100

    return ((now - start) / (end - start)) * 100
  }

  // Board tasks progress
  if (task.value.task_type === 'board' && task.value.status === 'taken') {
    const boardTask = task.value as any // Type assertion for board task properties
    if (boardTask.taken_at && boardTask.deadline) {
      const start = new Date(boardTask.taken_at).getTime()
      const end = new Date(boardTask.deadline).getTime()
      const now = currentTime.value

      if (now <= start) return 0
      if (now >= end) return 100

      return ((now - start) / (end - start)) * 100
    }
  }

  return 0
})

const timeRemaining = computed(() => {
  if (!task.value) return 0

  // Lock tasks time remaining
  if (task.value.task_type === 'lock' && task.value.status === 'active' && task.value.end_time) {
    const end = new Date(task.value.end_time).getTime()
    const now = currentTime.value
    return Math.max(0, end - now)
  }

  // Board tasks time remaining
  if (task.value.task_type === 'board' && task.value.status === 'taken') {
    const boardTask = task.value as any // Type assertion for board task properties
    if (boardTask.deadline) {
      const end = new Date(boardTask.deadline).getTime()
      const now = currentTime.value
      return Math.max(0, end - now)
    }
  }

  return 0
})

const votingTimeRemaining = computed(() => {
  if (!task.value || task.value.status !== 'voting' || !taskVotingEndTime.value) {
    return 0
  }

  const end = new Date(taskVotingEndTime.value).getTime()
  const now = currentTime.value
  return Math.max(0, end - now)
})

const canVote = computed(() => {
  if (!task.value || hasVoted.value) {
    return false
  }

  // Can vote if task is in voting period
  if (task.value.status === 'voting') {
    return votingTimeRemaining.value > 0
  }

  return false
})

const canStartVoting = computed(() => {
  if (!task.value || taskUnlockType.value !== 'vote') {
    return false
  }

  // 如果投票已经通过，不显示发起投票按钮
  if (isVotingPassed.value) {
    return false
  }

  // Either task owner or key holder can start voting
  const isTaskOwner = isOwnTask.value
  const isKeyHolder = hasTaskKey.value && !keyCheckLoading.value

  if (!isTaskOwner && !isKeyHolder) {
    return false
  }

  // Can start voting if task is active and countdown has ended
  if (task.value.status === 'active' && timeRemaining.value <= 0) {
    return true // Can always start voting when countdown is over
  }

  return false
})

// Helper computed for template type checking
const isTaskCompleted = computed(() => {
  return task.value?.status === 'completed'
})

const isTaskActive = computed(() => {
  return task.value?.status === 'active'
})

const showVotingResults = computed(() => {
  if (!task.value || taskUnlockType.value !== 'vote' || !taskVotingEndTime.value) {
    return false
  }
  return ['active', 'completed'].includes(task.value.status)
})

// Methods
const goBack = () => {
  router.back()
}

const checkUserHasTaskKey = async () => {
  if (!task.value || !authStore.isAuthenticated) {
    hasTaskKey.value = false
    return
  }

  try {
    keyCheckLoading.value = true
    userInventory.value = await storeApi.getUserInventory()

    // Check if user has a key for this specific task
    const foundTaskKey = userInventory.value.items.find((item: any) =>
      item.item_type.name === 'key' &&
      item.status === 'available' &&
      item.properties?.task_id === task.value?.id
    )

    hasTaskKey.value = !!foundTaskKey
    taskKey.value = foundTaskKey || null

    console.log('🔑 Key ownership check:', {
      taskId: task.value.id,
      hasKey: hasTaskKey.value,
      keyItem: taskKey.value?.id,
      totalItems: userInventory.value.items.length,
      keyItems: userInventory.value.items.filter((item: any) => item.item_type.name === 'key').length
    })

  } catch (error) {
    console.error('Error checking task key ownership:', error)
    hasTaskKey.value = false
  } finally {
    keyCheckLoading.value = false
  }
}

const fetchTimeline = async () => {
  const taskId = route.params.id as string
  if (!taskId || !task.value) return

  try {
    timelineLoading.value = true
    const timelineData = await tasksApi.getTaskTimeline(taskId)
    timeline.value = timelineData.timeline_events || []
  } catch (err: any) {
    console.error('Error fetching timeline:', err)
    // Timeline is optional, don't show error to user
  } finally {
    timelineLoading.value = false
  }
}

const refreshTimeline = async () => {
  console.log('Manual timeline refresh triggered')
  await fetchTimeline()
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

    // 获取实际投票数据
    currentVotes.value = (fetchedTask as any).vote_count || 0

    // 检查是否已投票（简单模拟）
    hasVoted.value = false

    // 如果是活跃任务或已接取的任务板，启动进度更新
    const taskValue = task.value as any
    if ((taskValue.task_type === 'lock' && taskValue.status === 'active') ||
        (taskValue.task_type === 'board' && taskValue.status === 'taken')) {
      startProgressUpdate()
    }

    // 获取任务时间线
    await fetchTimeline()

    // 检查钥匙持有情况（仅对带锁任务）
    if (fetchedTask.task_type === 'lock') {
      await checkUserHasTaskKey()
    }

  } catch (err: any) {
    // 使用模拟数据作为备用
    const mockTask: Task = {
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
        total_lock_duration: 0,
        created_at: '2023-12-01',
        updated_at: '2024-01-01'
      },
      title: '专注学习挑战',
      description: '在学习期间保持专注，不使用社交媒体和娱乐应用。这是一个测试意志力和自律能力的挑战任务。完成后将获得成就感和积分奖励。',
      task_type: 'lock' as const,
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
    const taskValue = task.value as any
    if ((taskValue.task_type === 'lock' && taskValue.status === 'active') ||
        (taskValue.task_type === 'board' && taskValue.status === 'taken')) {
      startProgressUpdate()
    }

    // 检查钥匙持有情况（仅对带锁任务）
    if (mockTask.task_type === 'lock') {
      await checkUserHasTaskKey()
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
  // Clear any existing interval
  if (progressInterval.value) {
    clearInterval(progressInterval.value)
  }

  progressInterval.value = window.setInterval(async () => {
    // Always update current time for reactive calculations
    currentTime.value = Date.now()

    // Check if voting period has ended and needs processing
    if (task.value?.status === 'voting' && taskVotingEndTime.value && !votingProcessing.value) {
      const now = currentTime.value
      const votingEndTime = new Date(taskVotingEndTime.value).getTime()

      console.log('⏰ Voting timer check:', {
        now: now,
        votingEndTime: votingEndTime,
        timeRemaining: votingEndTime - now,
        shouldProcess: now >= votingEndTime,
        alreadyProcessing: votingProcessing.value
      })

      if (now >= votingEndTime) {
        // 防止重复处理
        votingProcessing.value = true

        try {
          console.log('🗳️ Voting period ended, processing results...')

          let result = null
          let retryCount = 0
          const maxRetries = 3

          // 重试机制处理API调用
          while (retryCount < maxRetries && !result) {
            try {
              result = await tasksStore.processVotingResults()
              console.log('🗳️ Process voting results API response:', result)
              break
            } catch (apiError: any) {
              retryCount++
              console.warn(`⚠️ API call failed (attempt ${retryCount}/${maxRetries}):`, apiError)

              if (retryCount < maxRetries) {
                // 等待后重试
                await new Promise(resolve => setTimeout(resolve, 1000 * retryCount))
              } else {
                console.error('❌ All API retry attempts failed, will refresh task to check status')
              }
            }
          }

          // 无论API调用是否成功，都刷新任务状态
          await new Promise(resolve => setTimeout(resolve, 1000))
          await fetchTask()

          console.log('✅ Task status after voting period ended:', task.value?.status)

          const taskStatus = task.value?.status as string
          if (taskStatus === 'completed') {
            console.log('🎉 Task was auto-completed after voting passed!')

            // 停止进度更新定时器，因为任务已完成
            if (progressInterval.value) {
              clearInterval(progressInterval.value)
              progressInterval.value = undefined
            }

            // 刷新用户数据以更新lock status
            await authStore.refreshUser()

            // 刷新时间线以显示完成事件
            await fetchTimeline()

            // 显示完成提示
            alert('🎉 投票通过！任务已完成！')
          } else if (taskStatus === 'active') {
            console.log('⏰ Voting failed, task continues with penalty time')

            // 刷新时间线以显示失败事件
            await fetchTimeline()
          } else if (taskStatus === 'voting') {
            console.warn('⚠️ Task still in voting status, may need manual intervention')

            // 如果任务仍在投票状态，继续检查（可能是网络问题或其他临时问题）
            // 不重置 votingProcessing 标志，让下次定时器继续检查
            return
          }

          // Force a reactive update
          currentTime.value = Date.now()

          // Double check final state
          setTimeout(() => {
            console.log('🔘 Final state after voting ended:', {
              taskStatus: task.value?.status,
              canManageTask: canManageTask.value,
              canCompleteTask: canCompleteTask.value,
              isCompleted: task.value?.status === 'completed',
              votingEndTime: taskVotingEndTime.value,
              currentTime: currentTime.value
            })

            // 重置处理标志
            votingProcessing.value = false
          }, 500)
        } catch (error) {
          console.error('❌ Error processing voting results:', error)

          // 即使出错也要刷新任务状态，以防后端已经处理了
          try {
            await fetchTask()
            if (task.value?.status !== 'voting') {
              console.log('✅ Task status updated despite API error:', task.value?.status)
            }
          } catch (fetchError) {
            console.error('❌ Failed to refresh task after API error:', fetchError)
          }

          // 重置处理标志
          votingProcessing.value = false
        }
      }
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
  } catch (error: any) {
    console.error('Error deleting task:', error)

    // 处理特定错误消息
    let errorMessage = '删除任务失败，请重试'

    if (error.data?.error) {
      // 直接显示后端返回的具体错误信息
      errorMessage = error.data.error
    } else if (error.status === 404) {
      errorMessage = '任务不存在或已被删除'
    } else if (error.status === 403) {
      errorMessage = '您没有权限删除此任务'
    } else if (error.status === 500) {
      errorMessage = '服务器内部错误，请稍后重试'
    } else if (error.message) {
      errorMessage = `网络错误：${error.message}`
    }

    alert(`❌ ${errorMessage}`)
  }
}

const startTask = async () => {
  if (!task.value) return

  try {
    const updatedTask = await tasksApi.startTask(task.value.id)
    task.value = updatedTask
    console.log('任务已开始')
    startProgressUpdate()
    // 刷新用户数据以更新lock status
    authStore.refreshUser()
  } catch (error: any) {
    console.error('Error starting task:', error)

    // 处理特定错误消息
    let errorMessage = '开始任务失败，请重试'

    if (error.data?.error) {
      // 直接显示后端返回的具体错误信息
      errorMessage = error.data.error
    } else if (error.status === 404) {
      errorMessage = '任务不存在或已被删除'
    } else if (error.status === 403) {
      errorMessage = '您没有权限开始此任务'
    } else if (error.status === 500) {
      errorMessage = '服务器内部错误，请稍后重试'
    } else if (error.message) {
      errorMessage = `网络错误：${error.message}`
    }

    alert(`❌ ${errorMessage}`)
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

    // 刷新钥匙持有状态（钥匙应该已被销毁）
    if (updatedTask.task_type === 'lock') {
      await checkUserHasTaskKey()
    }

    // 刷新用户数据以更新lock status
    authStore.refreshUser()
    alert('✅ 任务已成功完成！钥匙已被销毁。')
  } catch (error: any) {
    console.error('Error completing task:', error)

    // 处理特定错误消息
    let errorMessage = '完成任务失败，请重试'

    if (error.data?.error) {
      // 直接显示后端返回的具体错误信息
      errorMessage = error.data.error
    } else if (error.status === 404) {
      errorMessage = '任务不存在或已被删除'
    } else if (error.status === 403) {
      errorMessage = '您没有权限完成此任务'
    } else if (error.status === 500) {
      errorMessage = '服务器内部错误，请稍后重试'
    } else if (error.message) {
      // 网络错误或其他客户端错误
      errorMessage = `网络错误：${error.message}`
    }

    alert(`❌ 完成失败：${errorMessage}`)
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
    // 刷新用户数据以更新lock status
    authStore.refreshUser()
    alert('⚠️ 任务已停止并标记为失败')
  } catch (error: any) {
    console.error('Error stopping task:', error)

    // 处理特定错误消息
    let errorMessage = '停止任务失败，请重试'

    if (error.data?.error) {
      // 直接显示后端返回的具体错误信息
      errorMessage = error.data.error
    } else if (error.status === 404) {
      errorMessage = '任务不存在或已被删除'
    } else if (error.status === 403) {
      errorMessage = '您没有权限停止此任务'
    } else if (error.status === 500) {
      errorMessage = '服务器内部错误，请稍后重试'
    } else if (error.message) {
      // 网络错误或其他客户端错误
      errorMessage = `网络错误：${error.message}`
    }

    alert(`❌ 停止失败：${errorMessage}`)
  }
}

const startVoting = async () => {
  if (!task.value || !canStartVoting.value) return

  if (!confirm('确定要发起投票吗？投票期将持续10分钟。')) {
    return
  }

  try {
    const updatedTask = await tasksApi.startVoting(task.value.id)
    task.value = updatedTask
    console.log('投票期已开始')

    // Refresh task data to get updated voting information
    await fetchTask()

    // Refresh user data to update lock status
    await authStore.refreshUser()
  } catch (error) {
    console.error('Error starting voting:', error)
    alert('发起投票失败，请重试')
  }
}

const submitVote = async (agree: boolean) => {
  if (!task.value || hasVoted.value) return

  try {
    await tasksApi.voteTask(task.value.id, agree)

    if (agree) {
      currentVotes.value += 1
    }

    hasVoted.value = true
    closeVoteModal()
    console.log(`投票成功: ${agree ? '同意' : '拒绝'}`)

    // 刷新任务数据以获取最新投票状态
    await fetchTask()

    // 检查是否达到解锁门槛
    if (agree && currentVotes.value >= taskVoteThresholdValue.value) {
      console.log('投票门槛已达到，任务可以解锁')
    }
  } catch (error) {
    console.error('Error voting:', error)
    alert('投票失败，请重试')
    closeVoteModal()
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

const openSubmissionModal = () => {
  showSubmissionModal.value = true
}

const closeSubmissionModal = () => {
  showSubmissionModal.value = false
}

const openUserProfile = (userId: number) => {
  selectedUserId.value = userId
  showProfileModal.value = true
}

const closeProfileModal = () => {
  showProfileModal.value = false
  selectedUserId.value = undefined
}

const openVoteModal = () => {
  showVoteModal.value = true
}

const closeVoteModal = () => {
  showVoteModal.value = false
}

const handleSubmissionSuccess = () => {
  // Refresh task data to get updated status
  fetchTask()
  // Close the modal
  showSubmissionModal.value = false
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
    if (result.new_end_time && task.value && task.value.task_type === 'lock') {
      (task.value as any).end_time = result.new_end_time
    }

    // 刷新用户数据以更新lock status
    authStore.refreshUser()

    // 显示加时信息
    alert(`成功为任务加时 ${result.overtime_minutes} 分钟！`)
    console.log('任务加时成功:', result)
  } catch (error: any) {
    console.error('Error adding overtime:', error)

    // 处理特定错误消息
    let errorMessage = '加时失败，请重试'

    if (error.data?.error) {
      // 直接显示后端返回的具体错误信息
      errorMessage = error.data.error
    } else if (error.status === 404) {
      errorMessage = '任务不存在或已被删除'
    } else if (error.status === 403) {
      errorMessage = '您没有权限为此任务加时'
    } else if (error.status === 500) {
      errorMessage = '服务器内部错误，请稍后重试'
    } else if (error.message) {
      errorMessage = `网络错误：${error.message}`
    }

    alert(`❌ ${errorMessage}`)
  }
}

const returnKeyToOriginalOwner = async () => {
  if (!taskKey.value || !taskKey.value.original_owner) {
    alert('无法归还：钥匙信息不完整')
    return
  }

  const originalOwnerName = taskKey.value.original_owner.username

  if (!confirm(`确定要将钥匙归还给 ${originalOwnerName} 吗？\n\n归还后您将失去对此任务的控制权。`)) {
    return
  }

  try {
    returningKey.value = true

    const result = await storeApi.returnItem(taskKey.value.id)

    // 重新检查钥匙状态
    await checkUserHasTaskKey()

    alert(`✅ 成功将钥匙归还给 ${originalOwnerName}`)
    console.log('钥匙归还成功:', result)

  } catch (error: any) {
    console.error('Error returning key:', error)

    // 处理特定错误消息
    let errorMessage = '归还钥匙失败，请重试'

    if (error.data?.error) {
      // 直接显示后端返回的具体错误信息
      errorMessage = error.data.error
    } else if (error.status === 404) {
      errorMessage = '钥匙不存在或您没有权限归还此钥匙'
    } else if (error.status === 403) {
      errorMessage = '您没有权限归还此钥匙'
    } else if (error.status === 500) {
      errorMessage = '服务器内部错误，请稍后重试'
    } else if (error.message) {
      // 网络错误或其他客户端错误
      errorMessage = `网络错误：${error.message}`
    }

    alert(`❌ ${errorMessage}`)
  } finally {
    returningKey.value = false
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
    voting: '投票期',
    completed: '已完成',
    failed: '已失败',
    open: '开放中',
    taken: '已接取',
    submitted: '已提交'
  }
  return texts[status as keyof typeof texts] || status
}

const formatDuration = (task: Task) => {
  if (task.task_type !== 'lock') return ''
  const lockTask = task as any
  const hours = Math.floor(lockTask.duration_value / 60)
  const minutes = lockTask.duration_value % 60

  if (lockTask.duration_type === 'random' && lockTask.duration_max) {
    const maxHours = Math.floor(lockTask.duration_max / 60)
    const maxMinutes = lockTask.duration_max % 60
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

const formatVotingTimeRemaining = () => {
  return formatTimeRemaining(votingTimeRemaining.value)
}

const getEventTypeClass = (eventType: string) => {
  const classMap: Record<string, string> = {
    'task_created': 'created',
    'task_started': 'start',
    'task_completed': 'completed',
    'task_stopped': 'failed',
    'time_wheel_increase': 'time-increase',
    'time_wheel_decrease': 'time-decrease',
    'overtime_added': 'overtime',
    'task_voted': 'vote',
    'task_failed': 'failed'
  }
  return classMap[eventType] || 'default'
}

// Watch for task changes to refresh timeline
watch(() => task.value?.updated_at, async (newUpdatedAt, oldUpdatedAt) => {
  if (newUpdatedAt && oldUpdatedAt && newUpdatedAt !== oldUpdatedAt) {
    console.log('Task updated, refreshing timeline...')
    await fetchTimeline()
  }
})

// Also watch for status changes
watch(() => task.value?.status, async (newStatus, oldStatus) => {
  if (newStatus && oldStatus && newStatus !== oldStatus) {
    console.log('📊 Task status changed from', oldStatus, 'to', newStatus)
    console.log('🔄 Refreshing timeline and checking button visibility...')
    await fetchTimeline()

    // Log button states after status change
    setTimeout(() => {
      console.log('🔘 Button visibility after status change:', {
        taskStatus: task.value?.status,
        canManageTask: canManageTask.value,
        canCompleteTask: canCompleteTask.value,
        stopButtonVisible: (task.value?.status === 'active' || task.value?.status === 'voting') && canManageTask.value,
        completeButtonVisible: task.value?.status === 'active' && canManageTask.value && canCompleteTask.value
      })
    }, 100)
  }
})

// Watch for end_time changes (from time wheel)
watch(() => taskEndTime.value, async (newEndTime, oldEndTime) => {
  if (newEndTime && oldEndTime && newEndTime !== oldEndTime) {
    console.log('Task end time changed, refreshing timeline...')
    await fetchTimeline()
  }
})

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

.task-status.voting {
  background-color: #ffc107;
  color: #212529;
  animation: pulse 2s infinite;
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

.username-btn {
  background: none;
  border: none;
  color: #007bff;
  font-weight: bold;
  font-size: 1.1rem;
  text-decoration: underline;
  cursor: pointer;
  padding: 0;
  transition: all 0.2s ease;
}

.username-btn:hover {
  color: #0056b3;
  text-decoration: none;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.1);
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

.countdown-display {
  font-size: 1.1rem;
  font-weight: 900;
  color: #007bff;
  animation: pulse-countdown 2s infinite;
}

.countdown-display.overtime {
  color: #dc3545;
  animation: pulse-danger 1s infinite;
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

.hint-vote {
  background-color: #e7f3ff;
  border: 1px solid #b3d9ff;
  color: #0066cc;
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

.hint-loading {
  background-color: #e2e3e5;
  border: 1px solid #ced4da;
  color: #495057;
}

.hint-no-key {
  background-color: #f8d7da;
  border: 1px solid #f5c6cb;
  color: #721c24;
  font-weight: 600;
}

.key-management {
  margin-top: 1rem;
  padding: 1rem;
  background-color: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 6px;
}

.key-return-info {
  margin-bottom: 0.75rem;
  font-size: 0.875rem;
  color: #495057;
  text-align: center;
}

.return-key-btn {
  display: block;
  width: 100%;
  padding: 0.75rem 1rem;
  background: linear-gradient(135deg, #17a2b8, #20c997);
  color: white;
  border: 2px solid #000;
  border-radius: 6px;
  font-weight: 600;
  font-size: 0.875rem;
  cursor: pointer;
  box-shadow: 2px 2px 0 #000;
  transition: all 0.2s ease;
}

.return-key-btn:hover:not(:disabled) {
  transform: translate(-1px, -1px);
  box-shadow: 3px 3px 0 #000;
  background: linear-gradient(135deg, #138496, #1e9b85);
}

.return-key-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
  box-shadow: 2px 2px 0 #000;
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

.vote-countdown-notice {
  padding: 1rem;
  background: linear-gradient(135deg, #fff3cd, #ffeaa7);
  border: 2px solid #ffc107;
  border-radius: 8px;
  color: #856404;
  font-weight: 500;
  text-align: center;
  margin-bottom: 1rem;
  animation: pulse-countdown-notice 2s infinite;
}

@keyframes pulse-countdown-notice {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.8; }
}

.vote-actions {
  margin-top: 1rem;
}

.vote-disabled-message {
  color: #6c757d;
  font-weight: 500;
  font-size: 1rem;
  text-align: center;
  padding: 0.75rem;
  background: #f8f9fa;
  border: 2px solid #dee2e6;
  border-radius: 8px;
}

/* Voting period specific styles */
.voting-waiting {
  margin-bottom: 1rem;
}

.vote-ready-notice {
  padding: 1rem;
  background: linear-gradient(135deg, #d4edda, #c3e6cb);
  border: 2px solid #28a745;
  border-radius: 8px;
  color: #155724;
  font-weight: 500;
  text-align: center;
  animation: pulse-ready 2s infinite;
}

.voting-active {
  margin-bottom: 1rem;
}

.voting-period-info {
  padding: 1.5rem;
  background: linear-gradient(135deg, #fff3cd, #ffeaa7);
  border: 2px solid #ffc107;
  border-radius: 8px;
  color: #856404;
}

.voting-period-info h4 {
  margin: 0 0 1rem 0;
  font-size: 1.2rem;
  font-weight: bold;
  text-align: center;
}

.voting-countdown {
  font-size: 1.1rem;
  font-weight: bold;
  text-align: center;
  margin-bottom: 0.5rem;
}

.voting-schedule {
  font-size: 0.875rem;
  text-align: center;
  opacity: 0.8;
}

.vote-breakdown {
  font-size: 0.875rem;
  color: #666;
  margin-top: 0.25rem;
  font-family: 'Courier New', monospace;
}

.voting-ended-message {
  padding: 1rem;
  background: linear-gradient(135deg, #f8d7da, #f5c6cb);
  border: 2px solid #dc3545;
  border-radius: 8px;
  color: #721c24;
  font-weight: 500;
  text-align: center;
  animation: pulse-warning 2s infinite;
}

@keyframes pulse-ready {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.8; transform: scale(1.02); }
}

.vote-waiting-notice {
  padding: 1rem;
  background: linear-gradient(135deg, #fff3cd, #ffeaa7);
  border: 2px solid #ffc107;
  border-radius: 8px;
  color: #856404;
  font-weight: 500;
  text-align: center;
  margin-bottom: 1rem;
}

.start-vote-btn {
  background: linear-gradient(135deg, #28a745, #20c997);
  color: white;
  border: 2px solid #000;
  border-radius: 8px;
  padding: 0.75rem 1.5rem;
  cursor: pointer;
  font-weight: 600;
  font-size: 1rem;
  box-shadow: 4px 4px 0 #000;
  transition: all 0.2s ease;
  animation: pulse-ready 2s infinite;
}

.start-vote-btn:hover {
  transform: translate(-2px, -2px);
  box-shadow: 6px 6px 0 #000;
}

@keyframes pulse-warning {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

/* Voting Results */
.voting-results {
  margin-top: 1.5rem;
  padding: 1.5rem;
  background: linear-gradient(135deg, #f8f9fa, #e9ecef);
  border: 2px solid #6c757d;
  border-radius: 8px;
}

.voting-results h4 {
  margin: 0 0 1rem 0;
  font-size: 1.2rem;
  font-weight: bold;
  text-align: center;
  color: #333;
}

.voting-result-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
  padding: 1rem;
  background: white;
  border: 1px solid #dee2e6;
  border-radius: 6px;
}

.result-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem;
  background: #f8f9fa;
  border-radius: 4px;
}

.result-label {
  font-weight: 500;
  color: #666;
  font-size: 0.875rem;
}

.result-value {
  font-weight: bold;
  color: #333;
  font-size: 0.875rem;
}

.voting-conclusion {
  padding: 1rem;
  border-radius: 6px;
  text-align: center;
  font-weight: 500;
}

.voting-passed {
  background: linear-gradient(135deg, #d4edda, #c3e6cb);
  border: 2px solid #28a745;
  color: #155724;
  animation: pulse-success 2s infinite;
}

.voting-failed {
  background: linear-gradient(135deg, #f8d7da, #f5c6cb);
  border: 2px solid #dc3545;
  color: #721c24;
}

.failure-reasons {
  margin-top: 0.75rem;
  font-size: 0.875rem;
  text-align: left;
  padding: 0.5rem;
  background: rgba(255, 255, 255, 0.5);
  border-radius: 4px;
}

.failure-reasons div {
  margin: 0.25rem 0;
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

/* Timeline styles */
.timeline-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.timeline-header h3 {
  margin: 0;
  font-size: 1.2rem;
  font-weight: bold;
}

.refresh-timeline-btn {
  background: #007bff;
  color: white;
  border: 2px solid #000;
  border-radius: 4px;
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  font-weight: bold;
  cursor: pointer;
  box-shadow: 2px 2px 0 #000;
  transition: all 0.2s ease;
}

.refresh-timeline-btn:hover:not(:disabled) {
  transform: translate(-1px, -1px);
  box-shadow: 3px 3px 0 #000;
}

.refresh-timeline-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  animation: spin 1s linear infinite;
}

.timeline-loading {
  text-align: center;
  color: #666;
  font-style: italic;
  padding: 1rem;
}

.timeline-container {
  max-height: 400px;
  overflow-y: auto;
  padding: 0.5rem;
  border: 1px solid #e9ecef;
  border-radius: 4px;
  background-color: #fafafa;
}

.timeline-description {
  font-size: 0.9rem;
  color: #555;
  margin-bottom: 0.25rem;
}

.timeline-user {
  font-size: 0.8rem;
  color: #666;
  font-style: italic;
}

.timeline-user-btn {
  background: none;
  border: none;
  color: #007bff;
  font-size: 0.8rem;
  font-style: italic;
  text-decoration: underline;
  cursor: pointer;
  padding: 0;
  margin-left: 0.25rem;
  transition: all 0.2s ease;
}

.timeline-user-btn:hover {
  color: #0056b3;
  text-decoration: none;
  font-weight: bold;
}

.timeline-time-change {
  font-size: 0.9rem;
  font-weight: bold;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  margin-top: 0.25rem;
}

.timeline-time-change:contains('+') {
  background-color: #d4edda;
  color: #155724;
}

.timeline-times {
  margin-top: 0.5rem;
  font-size: 0.8rem;
  background-color: #f8f9fa;
  padding: 0.5rem;
  border-radius: 4px;
  border-left: 3px solid #007bff;
}

.previous-time {
  color: #6c757d;
  text-decoration: line-through;
}

.new-time {
  color: #007bff;
  font-weight: bold;
  margin-top: 0.25rem;
}

/* Timeline dot styles for different event types */
.timeline-dot.created {
  background-color: #6c757d;
}

.timeline-dot.time-increase {
  background-color: #28a745;
  animation: pulse-success 2s infinite;
}

.timeline-dot.time-decrease {
  background-color: #dc3545;
  animation: pulse-danger 2s infinite;
}

.timeline-dot.overtime {
  background-color: #fd7e14;
  animation: pulse-warning 2s infinite;
}

.timeline-dot.vote {
  background-color: #ffc107;
}

.timeline-dot.completed {
  background-color: #28a745;
}

.timeline-dot.failed {
  background-color: #dc3545;
}

.timeline-dot.default {
  background-color: #6c757d;
}

@keyframes pulse-success {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.7; transform: scale(1.1); }
}

@keyframes pulse-warning {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.7; transform: scale(1.1); }
}
</style>