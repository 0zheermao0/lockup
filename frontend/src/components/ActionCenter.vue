<template>
  <div class="action-center">
    <!-- Desktop: 4-Grid Layout -->
    <div class="action-grid desktop-grid">
      <!-- Task Management -->
      <button
        v-if="showTaskManagement"
        class="action-card"
        :class="{ 'has-actions': hasTaskManagementActions }"
        @click="openTaskManagementMenu"
      >
        <div class="card-icon">🚀</div>
        <div class="card-label">任务</div>
      </button>

      <!-- Random Overtime - 独立显示 -->
      <button
        v-if="canAddOvertime"
        class="action-card overtime"
        @click="handleAction(addOvertime)"
      >
        <div class="card-icon">🎲</div>
        <div class="card-label">随机加时</div>
      </button>

      <!-- Bounty Operations -->
      <button
        v-if="showBounty"
        class="action-card"
        :class="{ 'has-actions': hasBountyActions }"
        @click="openBountyMenu"
      >
        <div class="card-icon">📋</div>
        <div class="card-label">悬赏</div>
      </button>

      <!-- Key Center -->
      <button
        v-if="showKeyCenter"
        class="action-card key-center"
        @click="openKeyCenterMenu"
      >
        <div class="card-icon">🔑</div>
        <div class="card-label">钥匙</div>
      </button>
    </div>

    <!-- Mobile: Horizontal Scroll -->
    <div class="action-scroll mobile-scroll">
      <button
        v-if="showTaskManagement"
        class="action-chip"
        @click="openTaskManagementMenu"
      >
        <span class="chip-icon">🚀</span>
        <span class="chip-label">任务</span>
      </button>

      <button
        v-if="canAddOvertime"
        class="action-chip overtime"
        @click="handleAction(addOvertime)"
      >
        <span class="chip-icon">🎲</span>
        <span class="chip-label">随机加时</span>
      </button>

      <button
        v-if="showBounty"
        class="action-chip"
        @click="openBountyMenu"
      >
        <span class="chip-icon">📋</span>
        <span class="chip-label">悬赏</span>
      </button>

      <button
        v-if="showKeyCenter"
        class="action-chip key-chip"
        @click="openKeyCenterMenu"
      >
        <span class="chip-icon">🔑</span>
        <span class="chip-label">钥匙</span>
      </button>
    </div>
  </div>

  <!-- Task Management Menu -->
  <NotificationToast
    :is-visible="showTaskMenu"
    type="menu"
    title="🚀 任务管理"
    :variant="isMobile ? 'drawer' : 'menu'"
    :show-actions="false"
    @close="showTaskMenu = false"
  >
    <div class="menu-item-list">
      <button
        v-if="canStartTask"
        class="menu-item primary"
        @click="handleAction(startTask)"
      >
        <span class="menu-item-icon">🟢</span>
        <div class="menu-item-content">
          <span class="menu-item-title">开始任务</span>
          <span class="menu-item-desc">启动任务计时</span>
        </div>
      </button>

      <button
        v-if="canCompleteTask"
        class="menu-item success"
        @click="handleAction(completeTask)"
      >
        <span class="menu-item-icon">✅</span>
        <div class="menu-item-content">
          <span class="menu-item-title">完成任务</span>
          <span class="menu-item-desc">标记任务为已完成</span>
        </div>
      </button>

      <button
        v-if="canStopTask"
        class="menu-item danger"
        @click="handleAction(stopTask)"
      >
        <span class="menu-item-icon">🛑</span>
        <div class="menu-item-content">
          <span class="menu-item-title">停止任务</span>
          <span class="menu-item-desc">任务将标记为失败</span>
        </div>
      </button>

      <button
        v-if="canStartVoting"
        class="menu-item warning pulse"
        @click="handleAction(startVoting)"
      >
        <span class="menu-item-icon">🗳️</span>
        <div class="menu-item-content">
          <span class="menu-item-title">发起投票</span>
          <span class="menu-item-desc">开始10分钟投票期</span>
        </div>
      </button>

      <button
        v-if="canVote"
        class="menu-item primary"
        @click="handleAction(openVoteModal)"
      >
        <span class="menu-item-icon">🗳️</span>
        <div class="menu-item-content">
          <span class="menu-item-title">参与投票</span>
          <span class="menu-item-desc">为此任务投票</span>
        </div>
      </button>
    </div>
  </NotificationToast>

  <!-- Bounty Menu -->
  <NotificationToast
    :is-visible="showBountyMenu"
    type="menu"
    title="📋 悬赏操作"
    :variant="isMobile ? 'drawer' : 'menu'"
    :show-actions="false"
    @close="showBountyMenu = false"
  >
    <div class="menu-item-list">
      <button
        v-if="canClaimTask"
        class="menu-item warning"
        @click="handleAction(claimTask)"
      >
        <span class="menu-item-icon">📋</span>
        <div class="menu-item-content">
          <span class="menu-item-title">揭榜任务</span>
          <span class="menu-item-desc">接取此悬赏任务</span>
        </div>
      </button>

      <button
        v-if="canSubmitProof"
        class="menu-item primary"
        @click="handleAction(openSubmissionModal)"
      >
        <span class="menu-item-icon">📤</span>
        <div class="menu-item-content">
          <span class="menu-item-title">提交完成证明</span>
          <span class="menu-item-desc">上传任务完成证据</span>
        </div>
      </button>

      <button
        v-if="canReviewTask"
        class="menu-item success"
        @click="handleAction(approveTask)"
      >
        <span class="menu-item-icon">✅</span>
        <div class="menu-item-content">
          <span class="menu-item-title">审核通过</span>
          <span class="menu-item-desc">批准任务完成</span>
        </div>
      </button>

      <button
        v-if="canReviewTask"
        class="menu-item danger"
        @click="handleAction(rejectTask)"
      >
        <span class="menu-item-icon">❌</span>
        <div class="menu-item-content">
          <span class="menu-item-title">审核拒绝</span>
          <span class="menu-item-desc">拒绝任务完成</span>
        </div>
      </button>

      <button
        v-if="canEndTask"
        class="menu-item danger"
        @click="handleAction(endTask)"
      >
        <span class="menu-item-icon">🏁</span>
        <div class="menu-item-content">
          <span class="menu-item-title">结束任务</span>
          <span class="menu-item-desc">提前结束悬赏任务</span>
        </div>
      </button>
    </div>
  </NotificationToast>

  <!-- Key Center Menu -->
  <NotificationToast
    :is-visible="showKeyMenu"
    type="menu"
    title="🔑 钥匙中心"
    :variant="isMobile ? 'drawer' : 'menu'"
    :show-actions="false"
    @close="showKeyMenu = false"
  >
    <div class="key-center-header">
      <div class="coins-display">
        <span class="coins-icon">💰</span>
        <span class="coins-value">{{ userCoins }} 积分</span>
      </div>
    </div>

    <div class="menu-item-list">
      <!-- Manual Time Adjustment -->
      <button
        v-if="canManualTimeAdjust"
        class="menu-item"
        :class="{ 'disabled': !canAffordTimeAdjustment }"
        :disabled="!canAffordTimeAdjustment"
        @click="handleAction(() => manualTimeAdjustment('increase'))"
      >
        <span class="menu-item-icon">➕</span>
        <div class="menu-item-content">
          <span class="menu-item-title">手动加时 (+20分)</span>
          <span class="menu-item-desc">消耗 10 积分</span>
        </div>
        <span v-if="!canAffordTimeAdjustment" class="menu-item-cost">积分不足</span>
      </button>

      <button
        v-if="canManualTimeAdjust"
        class="menu-item"
        :class="{ 'disabled': !canAffordTimeAdjustment }"
        :disabled="!canAffordTimeAdjustment"
        @click="handleAction(() => manualTimeAdjustment('decrease'))"
      >
        <span class="menu-item-icon">➖</span>
        <div class="menu-item-content">
          <span class="menu-item-title">手动减时 (-20分)</span>
          <span class="menu-item-desc">消耗 10 积分</span>
        </div>
        <span v-if="!canAffordTimeAdjustment" class="menu-item-cost">积分不足</span>
      </button>

      <!-- Time Display Control -->
      <button
        class="menu-item"
        :class="{ 'disabled': !canAffordTimeToggle }"
        :disabled="!canAffordTimeToggle"
        @click="handleAction(toggleTimeDisplay)"
      >
        <span class="menu-item-icon">👁️</span>
        <div class="menu-item-content">
          <span class="menu-item-title">{{ timeDisplayHidden ? '显示时间' : '隐藏时间' }}</span>
          <span class="menu-item-desc">消耗 50 积分</span>
        </div>
      </button>

      <!-- Freeze Control -->
      <button
        class="menu-item"
        :class="{ 'disabled': !canAffordFreeze }"
        :disabled="!canAffordFreeze"
        @click="handleAction(taskFrozen ? unfreezeTask : freezeTask)"
      >
        <span class="menu-item-icon">{{ taskFrozen ? '🔥' : '❄️' }}</span>
        <div class="menu-item-content">
          <span class="menu-item-title">{{ taskFrozen ? '解冻任务' : '冻结任务' }}</span>
          <span class="menu-item-desc">消耗 25 积分</span>
        </div>
      </button>

      <!-- Pin Task Owner -->
      <button
        class="menu-item"
        :class="{ 'disabled': !canAffordPinning }"
        :disabled="!canAffordPinning"
        @click="handleAction(pinTaskOwner)"
      >
        <span class="menu-item-icon">📌</span>
        <div class="menu-item-content">
          <span class="menu-item-title">置顶惩罚</span>
          <span class="menu-item-desc">消耗 60 积分 · 30分钟</span>
        </div>
      </button>

      <!-- Exclusive Task -->
      <button
        class="menu-item"
        :class="{ 'disabled': !canAffordExclusiveTask }"
        :disabled="!canAffordExclusiveTask"
        @click="handleAction(openExclusiveTaskModal)"
      >
        <span class="menu-item-icon">🎯</span>
        <div class="menu-item-content">
          <span class="menu-item-title">专属任务</span>
          <span class="menu-item-desc">消耗 15 积分</span>
        </div>
      </button>

      <!-- Shield Control -->
      <button
        class="menu-item"
        :class="{ 'disabled': !canAffordShield }"
        :disabled="!canAffordShield"
        @click="handleAction(toggleShield)"
      >
        <span class="menu-item-icon">{{ shieldActive ? '🔓' : '🛡️' }}</span>
        <div class="menu-item-content">
          <span class="menu-item-title">{{ shieldActive ? '关闭防护罩' : '开启防护罩' }}</span>
          <span class="menu-item-desc">消耗 15 积分</span>
        </div>
      </button>

      <!-- Return Key -->
      <button
        v-if="canReturnKey"
        class="menu-item gold"
        @click="handleAction(returnKey)"
      >
        <span class="menu-item-icon">🗝️</span>
        <div class="menu-item-content">
          <span class="menu-item-title">归还钥匙</span>
          <span class="menu-item-desc">免费 · 归还给 {{ originalOwnerName }}</span>
        </div>
      </button>
    </div>
  </NotificationToast>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import NotificationToast from './NotificationToast.vue'

interface Props {
  // Task info
  taskType: 'lock' | 'board'
  taskStatus: string
  isOwnTask: boolean
  isKeyHolder: boolean
  userCoins: number

  // Permissions - Task Management
  canStartTask: boolean
  canCompleteTask: boolean
  canStopTask: boolean
  canStartVoting: boolean
  canVote: boolean

  // Permissions - Overtime (Random only)
  canAddOvertime: boolean

  // Permissions - Bounty
  canClaimTask: boolean
  canSubmitProof: boolean
  canReviewTask: boolean
  canEndTask: boolean

  // Key holder info
  timeDisplayHidden: boolean
  taskFrozen: boolean
  shieldActive: boolean
  canReturnKey: boolean
  originalOwnerName?: string

  // Key holder permissions
  canManualTimeAdjust: boolean

  // Cost checks
  canAffordTimeAdjustment: boolean
  canAffordTimeToggle: boolean
  canAffordFreeze: boolean
  canAffordPinning: boolean
  canAffordExclusiveTask: boolean
  canAffordShield: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'startTask'): void
  (e: 'completeTask'): void
  (e: 'stopTask'): void
  (e: 'startVoting'): void
  (e: 'openVoteModal'): void
  (e: 'addOvertime'): void
  (e: 'manualTimeAdjustment', type: 'increase' | 'decrease'): void
  (e: 'claimTask'): void
  (e: 'openSubmissionModal'): void
  (e: 'approveTask'): void
  (e: 'rejectTask'): void
  (e: 'endTask'): void
  (e: 'toggleTimeDisplay'): void
  (e: 'freezeTask'): void
  (e: 'unfreezeTask'): void
  (e: 'pinTaskOwner'): void
  (e: 'openExclusiveTaskModal'): void
  (e: 'toggleShield'): void
  (e: 'returnKey'): void
  (e: 'scrollPassed'): void
  (e: 'scrollTop'): void
}>()

// Mobile detection
const isMobile = computed(() => window.innerWidth <= 768)

// Menu visibility states
const showTaskMenu = ref(false)
const showBountyMenu = ref(false)
const showKeyMenu = ref(false)

// Visibility computed properties
const showTaskManagement = computed(() =>
  props.canStartTask ||
  props.canCompleteTask ||
  props.canStopTask ||
  props.canStartVoting ||
  props.canVote
)

const showBounty = computed(() =>
  props.canClaimTask ||
  props.canSubmitProof ||
  props.canReviewTask ||
  props.canEndTask
)

const showKeyCenter = computed(() => props.isKeyHolder)

const hasTaskManagementActions = computed(() =>
  props.canStartTask ||
  props.canCompleteTask ||
  props.canStopTask ||
  props.canStartVoting ||
  props.canVote
)

const hasBountyActions = computed(() =>
  props.canClaimTask ||
  props.canSubmitProof ||
  props.canReviewTask
)

// Menu open handlers
const openTaskManagementMenu = () => {
  showTaskMenu.value = true
}

const openBountyMenu = () => {
  showBountyMenu.value = true
}

const openKeyCenterMenu = () => {
  showKeyMenu.value = true
}

// Action handlers
const handleAction = (handler: Function) => {
  handler()
  // Close all menus
  showTaskMenu.value = false
  showBountyMenu.value = false
  showKeyMenu.value = false
}

// Emit wrappers
const startTask = () => emit('startTask')
const completeTask = () => emit('completeTask')
const stopTask = () => emit('stopTask')
const startVoting = () => emit('startVoting')
const openVoteModal = () => emit('openVoteModal')
const addOvertime = () => emit('addOvertime')
const manualTimeAdjustment = (type: 'increase' | 'decrease') => emit('manualTimeAdjustment', type)
const claimTask = () => emit('claimTask')
const openSubmissionModal = () => emit('openSubmissionModal')
const approveTask = () => emit('approveTask')
const rejectTask = () => emit('rejectTask')
const endTask = () => emit('endTask')
const toggleTimeDisplay = () => emit('toggleTimeDisplay')
const freezeTask = () => emit('freezeTask')
const unfreezeTask = () => emit('unfreezeTask')
const pinTaskOwner = () => emit('pinTaskOwner')
const openExclusiveTaskModal = () => emit('openExclusiveTaskModal')
const toggleShield = () => emit('toggleShield')
const returnKey = () => emit('returnKey')

// Scroll detection for sticky effect
let lastScrollY = 0
let isSticky = false

const handleScroll = () => {
  const currentScrollY = window.scrollY
  const scrollThreshold = 80

  if (currentScrollY > scrollThreshold && !isSticky) {
    isSticky = true
    emit('scrollPassed')
  } else if (currentScrollY <= scrollThreshold && isSticky) {
    isSticky = false
    emit('scrollTop')
  }

  lastScrollY = currentScrollY
}

onMounted(() => {
  window.addEventListener('scroll', handleScroll, { passive: true })
})

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll)
})
</script>

<style scoped>
.action-center {
  background: white;
  border: 2px solid #000;
  border-radius: 8px;
  box-shadow: 3px 3px 0 #000;
  padding: 0.375rem;
  margin-bottom: 0.5rem;
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

/* Desktop Grid */
.action-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(72px, 1fr));
  gap: 0.375rem;
}

.action-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.125rem;
  padding: 0.375rem 0.25rem;
  background: linear-gradient(135deg, #f8fafc, #f1f5f9);
  border: 2px solid #000;
  border-radius: 6px;
  box-shadow: 2px 2px 0 #000;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
  min-height: 48px;
}

.action-card:hover {
  transform: translate(-2px, -2px);
  box-shadow: 4px 4px 0 #000;
}

.action-card:hover .card-icon {
  transform: scale(1.1);
}

.action-card:active {
  transform: translate(0, 0);
  box-shadow: 1px 1px 0 #000;
}

.card-icon {
  font-size: 1rem;
  transition: transform 0.2s ease;
}

.card-label {
  font-weight: 700;
  font-size: 0.6rem;
  color: #000;
  text-transform: uppercase;
  letter-spacing: 0.2px;
}

/* Random Overtime Special Styling */
.action-card.overtime {
  background: linear-gradient(135deg, #fef3c7, #fde68a);
}

.action-card.overtime:hover {
  background: linear-gradient(135deg, #fde68a, #fcd34d);
}

.action-card.overtime:hover .card-icon {
  animation: dice-roll 0.6s ease infinite;
}

@keyframes dice-roll {
  0%, 100% { transform: rotate(0deg); }
  25% { transform: rotate(-15deg) scale(1.1); }
  75% { transform: rotate(15deg) scale(1.1); }
}

/* Key Center Special Styling */
.action-card.key-center {
  background: linear-gradient(135deg, #fef3c7, #fde68a);
}

.action-card.key-center:hover {
  background: linear-gradient(135deg, #fde68a, #fcd34d);
}

/* Mobile Scroll */
.action-scroll {
  display: none;
  gap: 0.375rem;
  overflow-x: auto;
  padding-bottom: 0.125rem;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
}

.action-scroll::-webkit-scrollbar {
  display: none;
}

.action-chip {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.375rem 0.625rem;
  background: linear-gradient(135deg, #f8fafc, #f1f5f9);
  border: 2px solid #000;
  border-radius: 6px;
  box-shadow: 2px 2px 0 #000;
  cursor: pointer;
  transition: all 0.15s ease;
  flex-shrink: 0;
  white-space: nowrap;
}

.action-chip:hover {
  transform: translate(-1px, -1px);
  box-shadow: 3px 3px 0 #000;
}

.action-chip:active {
  transform: translate(0, 0);
  box-shadow: 1px 1px 0 #000;
}

.chip-icon {
  font-size: 0.9rem;
}

.chip-label {
  font-weight: 700;
  font-size: 0.7rem;
  color: #000;
}

.action-chip.overtime {
  background: linear-gradient(135deg, #fef3c7, #fde68a);
}

.action-chip.key-chip {
  background: linear-gradient(135deg, #fef3c7, #fde68a);
}

/* Key Center Header */
.key-center-header {
  display: flex;
  justify-content: center;
  margin-bottom: 0.75rem;
  padding-bottom: 0.75rem;
  border-bottom: 2px solid #e2e8f0;
}

.coins-display {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  background: linear-gradient(135deg, #fbbf24, #f59e0b);
  color: #000;
  padding: 0.375rem 0.75rem;
  border: 2px solid #000;
  border-radius: 6px;
  font-weight: 800;
  font-size: 0.8rem;
  box-shadow: 2px 2px 0 #000;
}

.coins-icon {
  font-size: 1rem;
}

/* Menu Styles */
.menu-item-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  background: white;
  border: 2px solid #000;
  border-radius: 8px;
  box-shadow: 2px 2px 0 #000;
  cursor: pointer;
  transition: all 0.15s ease;
  text-align: left;
  width: 100%;
}

.menu-item:hover:not(:disabled) {
  transform: translate(-2px, -2px);
  box-shadow: 4px 4px 0 #000;
}

.menu-item:active:not(:disabled) {
  transform: translate(0, 0);
  box-shadow: 1px 1px 0 #000;
}

.menu-item-icon {
  font-size: 1.25rem;
  flex-shrink: 0;
}

.menu-item-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.menu-item-title {
  font-weight: 700;
  font-size: 0.9rem;
  color: #000;
}

.menu-item-desc {
  font-size: 0.75rem;
  color: #666;
}

.menu-item-cost {
  font-size: 0.7rem;
  font-weight: 700;
  color: #dc3545;
  background: rgba(220, 53, 69, 0.1);
  padding: 0.125rem 0.375rem;
  border-radius: 4px;
  white-space: nowrap;
}

/* Menu item variants */
.menu-item.primary {
  background: linear-gradient(135deg, #eff6ff, #dbeafe);
}

.menu-item.success {
  background: linear-gradient(135deg, #f0fdf4, #dcfce7);
}

.menu-item.danger {
  background: linear-gradient(135deg, #fef2f2, #fee2e2);
}

.menu-item.warning {
  background: linear-gradient(135deg, #fffbeb, #fef3c7);
}

.menu-item.gold {
  background: linear-gradient(135deg, #fef3c7, #fde68a);
}

.menu-item:disabled,
.menu-item.disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
  box-shadow: 2px 2px 0 #000;
}

/* Responsive */
@media (max-width: 768px) {
  .action-center {
    padding: 0.375rem;
    border-width: 2px;
    box-shadow: 2px 2px 0 #000;
    margin-bottom: 0.375rem;
  }

  .action-card {
    min-height: 44px;
    padding: 0.25rem 0.125rem;
  }

  .card-icon {
    font-size: 0.9rem;
  }

  .card-label {
    font-size: 0.55rem;
  }

  .desktop-grid {
    display: none;
  }

  .mobile-scroll {
    display: flex;
  }
}

/* Pulse animation for voting */
@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.9;
    transform: scale(1.02);
  }
}

.menu-item.pulse {
  animation: pulse 2s ease-in-out infinite;
}
</style>
