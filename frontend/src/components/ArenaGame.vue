<template>
  <div class="arena-game">
    <!-- Game Rules Intro -->
    <div class="game-section intro-section">
      <div class="intro-header">
        <h3 class="section-title">🏟️ 角斗场</h3>
        <button @click="showRules = !showRules" class="rules-toggle">
          {{ showRules ? '收起规则' : '查看规则' }}
        </button>
      </div>

      <div v-if="showRules" class="rules-content">
        <div class="rules-flow">
          <div class="flow-step">
            <span class="step-icon">📸</span>
            <span class="step-text">发起者上传照片</span>
          </div>
          <div class="flow-arrow">→</div>
          <div class="flow-step">
            <span class="step-icon">⚔️</span>
            <span class="step-text">挑战者加入</span>
          </div>
          <div class="flow-arrow">→</div>
          <div class="flow-step">
            <span class="step-icon">🎫</span>
            <span class="step-text">观众付费入场</span>
          </div>
          <div class="flow-arrow">→</div>
          <div class="flow-step">
            <span class="step-icon">🗳️</span>
            <span class="step-text">投票决胜负</span>
          </div>
        </div>
        <div class="rules-details">
          <p>• 观众需支付门票后才能查看双方照片</p>
          <p>• 胜者获得 (投注积分 + 所有门票) × {{ defaultWinnerPercentage }}%</p>
          <p>• 败者获得剩余积分奖励</p>
          <p>• 所有观众投票完成或截止时间到达时结算</p>
        </div>
      </div>
    </div>

    <!-- Create Game Section -->
    <div class="game-section create-section">
      <div class="section-header">
        <h3 class="section-title">⚔️ 发起挑战</h3>
      </div>

      <div class="create-form">
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">投注积分</label>
            <input
              v-model.number="createForm.bet_amount"
              type="number"
              min="1"
              class="form-input"
              placeholder="下注积分"
            />
          </div>

          <div class="form-group">
            <label class="form-label">门票价格</label>
            <input
              v-model.number="createForm.audience_ticket_price"
              type="number"
              min="1"
              class="form-input"
              placeholder="观众门票"
            />
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label class="form-label">观众上限 ({{ createForm.max_audience }}人)</label>
            <input
              v-model.number="createForm.max_audience"
              type="range"
              min="5"
              max="50"
              class="form-slider"
            />
          </div>

          <div class="form-group">
            <label class="form-label">截止时间 ({{ createForm.deadline_hours }}小时)</label>
            <input
              v-model.number="createForm.deadline_hours"
              type="range"
              min="1"
              max="72"
              class="form-slider"
            />
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">胜者奖励比例 ({{ createForm.winner_reward_percentage }}%)</label>
          <input
            v-model.number="createForm.winner_reward_percentage"
            type="range"
            min="50"
            max="95"
            class="form-slider"
          />
          <p class="form-hint">胜者获得 {{ calculateWinnerReward }} 积分，败者获得 {{ calculateLoserReward }} 积分（假设满员）</p>
        </div>

        <div class="form-group">
          <label class="form-label">上传照片</label>
          <div
            class="photo-upload-area"
            :class="{ 'has-photo': createForm.photoPreview }"
            @click="photoInput?.click()"
            @drop.prevent="handlePhotoDrop"
            @dragover.prevent
          >
            <input
              ref="photoInput"
              type="file"
              accept="image/*"
              class="hidden-input"
              @change="handlePhotoSelect"
            />
            <div v-if="createForm.photoPreview" class="photo-preview">
              <img :src="createForm.photoPreview" alt="Preview" />
            </div>
            <div v-else class="upload-placeholder">
              <span class="upload-icon">📸</span>
              <span class="upload-text">点击或拖拽上传照片</span>
            </div>
          </div>
        </div>

        <button
          @click="createGame"
          class="create-btn"
          :disabled="creating || !canCreate"
        >
          {{ creating ? '创建中...' : '⚔️ 发起挑战' }}
        </button>
      </div>
    </div>

    <!-- Active Games List -->
    <div class="game-section games-list-section">
      <div class="section-header">
        <h3 class="section-title">🎯 进行中的对决</h3>
        <button @click="refreshGames" class="refresh-btn" :disabled="loading">
          {{ loading ? '刷新中...' : '🔄 刷新' }}
        </button>
      </div>

      <div v-if="loading && games.length === 0" class="loading-state">
        <div class="loading-spinner"></div>
        <p>加载游戏中...</p>
      </div>

      <div v-else-if="filteredGames.length === 0" class="empty-state">
        <div class="empty-icon">🏟️</div>
        <p class="empty-text">暂无进行中的角斗场对决</p>
        <p class="empty-hint">发起一个挑战开始吧！</p>
      </div>

      <div v-else class="games-grid">
        <div
          v-for="game in filteredGames"
          :key="game.id"
          class="game-card"
          :class="{ 'can-join': canJoinAsChallenger(game), 'is-creator': isCreator(game) }"
        >
          <div class="game-header">
            <div class="creator-info">
              <UserAvatar
                :user="game.creator"
                size="small"
                :clickable="true"
                :show-lock-indicator="true"
                :title="`查看 ${game.creator.username} 的资料`"
                @click.stop="openProfileModal(game.creator)"
              />
              <div class="creator-details">
                <span
                  class="creator-name clickable"
                  @click.stop="openProfileModal(game.creator)"
                  :title="`查看 ${game.creator.username} 的资料`"
                >
                  {{ game.creator.username }}
                </span>
                <span class="game-time">{{ formatDistanceToNow(game.created_at) }}</span>
              </div>
            </div>
            <div class="game-status" :class="game.status">
              {{ getStatusText(game.status) }}
            </div>
          </div>

          <div class="battle-preview">
            <div class="fighter creator-side">
              <div class="fighter-avatar">
                <UserAvatar
                  :user="game.creator"
                  size="large"
                  :clickable="true"
                  :show-lock-indicator="true"
                  :title="`查看 ${game.creator.username} 的资料`"
                  @click.stop="openProfileModal(game.creator)"
                />
              </div>
              <span
                class="fighter-name clickable"
                @click.stop="openProfileModal(game.creator)"
                :title="`查看 ${game.creator.username} 的资料`"
              >
                {{ game.creator.username }}
              </span>
              <div v-if="game.votes" class="vote-count">
                🗳️ {{ game.votes.creator || 0 }}
              </div>
            </div>

            <div class="vs-divider">
              <span class="vs-text">VS</span>
              <span class="bet-amount">🪙 {{ game.bet_amount }}</span>
            </div>

            <div class="fighter challenger-side">
              <div v-if="game.challenger" class="fighter-avatar">
                <UserAvatar
                  :user="game.challenger"
                  size="large"
                  :clickable="true"
                  :show-lock-indicator="true"
                  :title="`查看 ${game.challenger.username} 的资料`"
                  @click.stop="openProfileModal(game.challenger)"
                />
              </div>
              <div v-else class="fighter-avatar empty">
                <span class="empty-icon">?</span>
              </div>
              <span
                v-if="game.challenger"
                class="fighter-name clickable"
                @click.stop="openProfileModal(game.challenger)"
                :title="`查看 ${game.challenger.username} 的资料`"
              >
                {{ game.challenger.username }}
              </span>
              <span v-else class="fighter-name">
                等待挑战者
              </span>
              <div v-if="game.votes && game.challenger" class="vote-count">
                🗳️ {{ game.votes.challenger || 0 }}
              </div>
            </div>
          </div>

          <div class="game-meta">
            <div class="meta-item">
              <span class="meta-icon">🎫</span>
              <span class="meta-text">门票: {{ game.config?.audience_ticket_price || 5 }} 积分</span>
            </div>
            <div class="meta-item">
              <span class="meta-icon">👥</span>
              <span class="meta-text">观众: {{ game.audience_count || 0 }}/{{ game.config?.max_audience || 20 }}</span>
            </div>
          </div>

          <div class="game-actions">
            <!-- Creator View -->
            <div v-if="isCreator(game)" class="creator-actions">
              <span class="role-badge creator">你的挑战</span>
              <button
                v-if="game.status === 'waiting'"
                @click="cancelGame(game.id)"
                :disabled="cancelingGame"
                class="cancel-btn"
              >
                {{ cancelingGame ? '取消中...' : '❌ 取消' }}
              </button>
              <button
                v-else-if="game.status === 'active'"
                @click="viewGameDetails(game)"
                class="view-btn"
              >
                👁️ 查看详情
              </button>
            </div>

            <!-- Challenger Join -->
            <button
              v-else-if="canJoinAsChallenger(game)"
              @click="openJoinModal(game)"
              class="join-btn challenger"
              :disabled="joiningGameId === game.id"
            >
              {{ joiningGameId === game.id ? '加入中...' : '⚔️ 接受挑战' }}
            </button>

            <!-- Vote (for audience who entered but not voted) -->
            <button
              v-else-if="canVote(game)"
              @click="openVoteModal(game)"
              class="vote-btn"
            >
              🗳️ 投票
            </button>

            <!-- View Battle (for audience who entered and voted, or creator/challenger) -->
            <button
              v-else-if="canViewBattle(game) && game.status === 'active'"
              @click="openVoteModal(game)"
              class="view-btn"
            >
              {{ hasVoted(game) ? '👁️ 查看对决' : '🎫 已入场' }}
            </button>

            <!-- Audience Enter -->
            <button
              v-else-if="canEnterAsAudience(game)"
              @click="openEnterModal(game)"
              class="enter-btn"
              :disabled="enteringGameId === game.id"
            >
              {{ enteringGameId === game.id ? '入场中...' : `🎫 入场 (${game.config?.audience_ticket_price || 5} 积分)` }}
            </button>

            <!-- View Result -->
            <button
              v-else-if="game.status === 'completed'"
              @click="openResultModal(game)"
              class="result-btn"
            >
              🏆 查看结果
            </button>

            <span v-else class="disabled-text">
              {{ getDisabledReason(game) }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Join as Challenger Modal -->
    <div v-if="showJoinModal" class="modal-overlay" @click="closeJoinModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3 class="modal-title">⚔️ 接受挑战</h3>
          <button @click="closeJoinModal" class="modal-close">×</button>
        </div>

        <div class="modal-body">
          <div class="challenge-info">
            <p>发起者: <strong>{{ selectedGame?.creator.username }}</strong></p>
            <p>需要投注: <strong>{{ selectedGame?.bet_amount }} 积分</strong></p>
          </div>

          <div class="photo-upload-section">
            <label class="form-label">上传你的照片</label>
            <div
              class="photo-upload-area large"
              :class="{ 'has-photo': joinForm.photoPreview }"
              @click="joinPhotoInput?.click()"
            >
              <input
                ref="joinPhotoInput"
                type="file"
                accept="image/*"
                class="hidden-input"
                @change="handleJoinPhotoSelect"
              />
              <div v-if="joinForm.photoPreview" class="photo-preview">
                <img :src="joinForm.photoPreview" alt="Preview" />
              </div>
              <div v-else class="upload-placeholder">
                <span class="upload-icon">📸</span>
                <span class="upload-text">点击上传照片</span>
              </div>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button @click="closeJoinModal" class="cancel-btn">取消</button>
          <button
            @click="joinAsChallenger"
            class="confirm-btn"
            :disabled="!joinForm.photo || joining"
          >
            {{ joining ? '加入中...' : `确认加入 (-${selectedGame?.bet_amount} 积分)` }}
          </button>
        </div>
      </div>
    </div>

    <!-- Enter as Audience Modal -->
    <div v-if="showEnterModal" class="modal-overlay" @click="closeEnterModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3 class="modal-title">🎫 观众入场</h3>
          <button @click="closeEnterModal" class="modal-close">×</button>
        </div>

        <div class="modal-body">
          <div class="enter-info">
            <p>入场后可以查看双方照片并投票</p>
            <p class="ticket-price">
              门票价格: <strong>{{ selectedGame?.config?.audience_ticket_price || 5 }} 积分</strong>
            </p>
          </div>

          <div class="preview-hint">
            <div class="mosaic-preview">
              <div class="mosaic-box"></div>
              <div class="mosaic-box"></div>
            </div>
            <p class="hint-text">入场前照片将被马赛克遮挡</p>
          </div>
        </div>

        <div class="modal-footer">
          <button @click="closeEnterModal" class="cancel-btn">取消</button>
          <button
            @click="enterAsAudience"
            class="confirm-btn"
            :disabled="entering"
          >
            {{ entering ? '入场中...' : '确认入场' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Vote Modal -->
    <div v-if="showVoteModal" class="modal-overlay" @click="closeVoteModal">
      <div class="modal-content vote-modal" @click.stop>
        <div class="modal-header">
          <h3 class="modal-title">🗳️ 投票决胜负</h3>
          <button @click="closeVoteModal" class="modal-close">×</button>
        </div>

        <div class="modal-body">
          <p class="vote-instruction">请选择你认为更精彩的照片：</p>

          <div class="vote-options">
            <div
              class="vote-option"
              :class="{ 'selected': selectedVote === 'creator' }"
              @click="selectedVote = 'creator'"
            >
              <div class="vote-photo">
                <img
                  v-if="selectedGameDetails?.creator_photo"
                  :src="getPhotoUrl(selectedGameDetails.creator_photo)"
                  alt="Creator"
                />
              </div>
              <div class="vote-info">
                <span class="voter-name">{{ selectedGame?.creator.username }}</span>
                <span class="vote-label">发起者</span>
              </div>
            </div>

            <div
              class="vote-option"
              :class="{ 'selected': selectedVote === 'challenger' }"
              @click="selectedVote = 'challenger'"
            >
              <div class="vote-photo">
                <img
                  v-if="selectedGameDetails?.challenger_photo"
                  :src="getPhotoUrl(selectedGameDetails.challenger_photo)"
                  alt="Challenger"
                />
              </div>
              <div class="vote-info">
                <span class="voter-name">{{ selectedGame?.challenger?.username }}</span>
                <span class="vote-label">挑战者</span>
              </div>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button @click="closeVoteModal" class="cancel-btn">取消</button>
          <button
            @click="submitVote"
            class="confirm-btn"
            :disabled="!selectedVote || voting"
          >
            {{ voting ? '投票中...' : '确认投票' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Result Modal -->
    <div v-if="showResultModal" class="modal-overlay" @click="closeResultModal">
      <div class="modal-content result-modal" @click.stop>
        <div class="modal-header">
          <h3 class="modal-title">🏆 对决结果</h3>
          <button @click="closeResultModal" class="modal-close">×</button>
        </div>

        <div class="modal-body">
          <div v-if="selectedGameResult" class="result-display">
            <div class="winner-section" :class="selectedGameResult.winner">
              <div class="winner-crown">👑</div>
              <div class="winner-text">
                <span v-if="selectedGameResult.winner === 'creator'">发起者获胜！</span>
                <span v-else-if="selectedGameResult.winner === 'challenger'">挑战者获胜！</span>
                <span v-else>平局！</span>
              </div>
            </div>

            <div class="vote-stats">
              <div class="stat-bar">
                <div class="stat-label">发起者</div>
                <div class="stat-progress">
                  <div
                    class="stat-fill creator"
                    :style="{ width: getVotePercentage('creator') + '%' }"
                  ></div>
                </div>
                <div class="stat-value">{{ selectedGameResult.final_votes?.creator || 0 }}</div>
              </div>
              <div class="stat-bar">
                <div class="stat-label">挑战者</div>
                <div class="stat-progress">
                  <div
                    class="stat-fill challenger"
                    :style="{ width: getVotePercentage('challenger') + '%' }"
                  ></div>
                </div>
                <div class="stat-value">{{ selectedGameResult.final_votes?.challenger || 0 }}</div>
              </div>
            </div>

            <div class="reward-section">
              <div class="reward-item">
                <span class="reward-label">总奖池</span>
                <span class="reward-value">🪙 {{ selectedGameResult.total_pot }}</span>
              </div>
              <div class="reward-item">
                <span class="reward-label">发起者获得</span>
                <span class="reward-value">🪙 {{ selectedGameResult.creator_reward }}</span>
              </div>
              <div class="reward-item">
                <span class="reward-label">挑战者获得</span>
                <span class="reward-value">🪙 {{ selectedGameResult.challenger_reward }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button @click="closeResultModal" class="confirm-btn">确定</button>
        </div>
      </div>
    </div>

    <!-- Toast Notification -->
    <NotificationToast
      :is-visible="toastState.isVisible"
      :type="toastState.type"
      :title="toastState.title"
      :message="toastState.message"
      @close="closeToast"
    />

    <!-- Profile Modal -->
    <ProfileModal
      :is-visible="showProfileModal"
      :user="selectedUser"
      @close="closeProfileModal"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { storeApi } from '../lib/api'
import { useAuthStore } from '../stores/auth'
import UserAvatar from './UserAvatar.vue'
import NotificationToast from './NotificationToast.vue'
import ProfileModal from './ProfileModal.vue'
import { toastState, closeToast } from '../composables/useGameToast'
import type { User } from '../types'

interface ArenaAudience {
  user_id: number
  username: string
  joined_at: string
  has_voted: boolean
  vote_for?: 'creator' | 'challenger'
}

interface ArenaGame {
  id: string
  creator: User
  challenger?: User
  bet_amount: number
  status: 'waiting' | 'active' | 'completed' | 'cancelled'
  config: {
    audience_ticket_price: number
    max_audience: number
    deadline: string
    winner_reward_percentage: number
  }
  audience_count: number
  audience?: ArenaAudience[]
  votes: {
    creator: number
    challenger: number
  }
  result?: Record<string, any>
  created_at: string
}

const authStore = useAuthStore()

// Template refs
const photoInput = ref<HTMLInputElement | null>(null)
const joinPhotoInput = ref<HTMLInputElement | null>(null)

// State
const showRules = ref(false)
const loading = ref(false)
const games = ref<ArenaGame[]>([])
const creating = ref(false)
const joiningGameId = ref<string | null>(null)
const enteringGameId = ref<string | null>(null)
const cancelingGame = ref(false)

// Modals
const showJoinModal = ref(false)
const showEnterModal = ref(false)
const showVoteModal = ref(false)
const showResultModal = ref(false)
const showProfileModal = ref(false)
const selectedGame = ref<ArenaGame | null>(null)
const selectedGameDetails = ref<any>(null)
const selectedGameResult = ref<any>(null)
const selectedUser = ref<User | undefined>(undefined)

// Forms
const createForm = ref({
  bet_amount: 10,
  audience_ticket_price: 5,
  max_audience: 20,
  deadline_hours: 12,
  winner_reward_percentage: 80,
  photo: null as File | null,
  photoPreview: ''
})

const joinForm = ref({
  photo: null as File | null,
  photoPreview: ''
})

const selectedVote = ref('')
const joining = ref(false)
const entering = ref(false)
const voting = ref(false)

const defaultWinnerPercentage = 80

// Computed
const canCreate = computed(() => {
  return createForm.value.bet_amount >= 1 &&
         createForm.value.photo !== null &&
         authStore.user!.coins >= createForm.value.bet_amount
})

const calculateWinnerReward = computed(() => {
  const totalBet = createForm.value.bet_amount * 2
  const totalTickets = createForm.value.audience_ticket_price * createForm.value.max_audience
  const totalPot = totalBet + totalTickets
  return Math.floor(totalPot * createForm.value.winner_reward_percentage / 100)
})

const calculateLoserReward = computed(() => {
  const totalBet = createForm.value.bet_amount * 2
  const totalTickets = createForm.value.audience_ticket_price * createForm.value.max_audience
  const totalPot = totalBet + totalTickets
  const winnerReward = Math.floor(totalPot * createForm.value.winner_reward_percentage / 100)
  return totalPot - winnerReward
})

const filteredGames = computed(() => {
  return games.value.filter(g => g.status !== 'cancelled')
})

// Methods
const formatDistanceToNow = (dateString: string) => {
  const date = new Date(dateString)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)

  if (days > 0) return `${days}天前`
  if (hours > 0) return `${hours}小时前`
  if (minutes > 0) return `${minutes}分钟前`
  return '刚刚'
}

const getStatusText = (status: string) => {
  const statusMap: Record<string, string> = {
    waiting: '等待挑战者',
    active: '进行中',
    completed: '已结束',
    cancelled: '已取消'
  }
  return statusMap[status] || status
}

const isCreator = (game: ArenaGame) => {
  return game.creator.id === authStore.user?.id
}

const canJoinAsChallenger = (game: ArenaGame) => {
  return game.status === 'waiting' &&
         game.creator.id !== authStore.user?.id &&
         !game.challenger &&
         authStore.user!.coins >= game.bet_amount
}

const isInAudience = (game: ArenaGame) => {
  // Check if current user is in the audience list
  const audience = (game as any).audience || []
  return audience.some((a: any) => a.user_id === authStore.user?.id)
}

const hasVoted = (game: ArenaGame) => {
  // Check if current user has already voted
  const audience = (game as any).audience || []
  const me = audience.find((a: any) => a.user_id === authStore.user?.id)
  return me?.has_voted === true
}

const canEnterAsAudience = (game: ArenaGame) => {
  if (game.status !== 'active') return false
  // Creator and challenger don't need to "enter" - they already have access
  if (isCreator(game)) return false
  if (game.challenger?.id === authStore.user?.id) return false

  // If already in audience, don't show enter button
  if (isInAudience(game)) return false

  return true
}

const canVote = (game: ArenaGame) => {
  if (game.status !== 'active') return false

  // Creator and challenger can't vote
  if (isCreator(game)) return false
  if (game.challenger?.id === authStore.user?.id) return false

  // Must be in audience and not voted yet
  if (!isInAudience(game)) return false
  if (hasVoted(game)) return false

  return true
}

const canViewBattle = (game: ArenaGame) => {
  // Creator and challenger can always view
  if (isCreator(game)) return true
  if (game.challenger?.id === authStore.user?.id) return true

  // Audience members who have entered can view
  if (isInAudience(game)) return true

  return false
}

const getDisabledReason = (game: ArenaGame) => {
  if (game.status === 'completed') return '已结束'
  if (game.status === 'cancelled') return '已取消'
  if (game.challenger?.id === authStore.user?.id) return '你是挑战者'
  if (hasVoted(game)) return '已投票'
  return '无法参与'
}

const handlePhotoSelect = (event: Event) => {
  const input = event.target as HTMLInputElement
  if (input.files && input.files[0]) {
    const file = input.files[0]
    createForm.value.photo = file
    createForm.value.photoPreview = URL.createObjectURL(file)
  }
}

const handlePhotoDrop = (event: DragEvent) => {
  const files = event.dataTransfer?.files
  if (files && files[0]) {
    const file = files[0]
    if (file.type.startsWith('image/')) {
      createForm.value.photo = file
      createForm.value.photoPreview = URL.createObjectURL(file)
    }
  }
}

const handleJoinPhotoSelect = (event: Event) => {
  const input = event.target as HTMLInputElement
  if (input.files && input.files[0]) {
    const file = input.files[0]
    joinForm.value.photo = file
    joinForm.value.photoPreview = URL.createObjectURL(file)
  }
}

const createGame = async () => {
  if (!canCreate.value || creating.value) return

  try {
    creating.value = true
    const result = await storeApi.createArenaGame({
      bet_amount: createForm.value.bet_amount,
      audience_ticket_price: createForm.value.audience_ticket_price,
      max_audience: createForm.value.max_audience,
      deadline_hours: createForm.value.deadline_hours,
      winner_reward_percentage: createForm.value.winner_reward_percentage,
      photo: createForm.value.photo!
    })

    // Reset form
    createForm.value = {
      bet_amount: 10,
      audience_ticket_price: 5,
      max_audience: 20,
      deadline_hours: 12,
      winner_reward_percentage: 80,
      photo: null,
      photoPreview: ''
    }

    await authStore.refreshUser()
    await refreshGames()

    toastState.value = {
      isVisible: true,
      type: 'success',
      title: '创建成功',
      message: '角斗场游戏创建成功！'
    }
  } catch (err: any) {
    toastState.value = {
      isVisible: true,
      type: 'error',
      title: '创建失败',
      message: err.message || '创建游戏失败'
    }
  } finally {
    creating.value = false
  }
}

const refreshGames = async () => {
  try {
    loading.value = true
    const result = await storeApi.listArenaGames()
    games.value = result.games as ArenaGame[]
  } catch (err) {
    console.error('Failed to load games:', err)
  } finally {
    loading.value = false
  }
}

const openJoinModal = (game: ArenaGame) => {
  selectedGame.value = game
  showJoinModal.value = true
}

const closeJoinModal = () => {
  showJoinModal.value = false
  selectedGame.value = null
  joinForm.value = { photo: null, photoPreview: '' }
}

const joinAsChallenger = async () => {
  if (!selectedGame.value || !joinForm.value.photo) return

  try {
    joining.value = true
    joiningGameId.value = selectedGame.value.id

    await storeApi.joinArenaGame(selectedGame.value.id, joinForm.value.photo)

    await authStore.refreshUser()
    await refreshGames()

    closeJoinModal()
    toastState.value = {
      isVisible: true,
      type: 'success',
      title: '加入成功',
      message: '成功加入角斗场！'
    }
  } catch (err: any) {
    toastState.value = {
      isVisible: true,
      type: 'error',
      title: '加入失败',
      message: err.message || '加入失败'
    }
  } finally {
    joining.value = false
    joiningGameId.value = null
  }
}

const openEnterModal = (game: ArenaGame) => {
  selectedGame.value = game
  showEnterModal.value = true
}

const closeEnterModal = () => {
  showEnterModal.value = false
  selectedGame.value = null
}

const enterAsAudience = async () => {
  if (!selectedGame.value) return

  try {
    entering.value = true
    enteringGameId.value = selectedGame.value.id

    await storeApi.enterArenaAsAudience(selectedGame.value.id)

    await authStore.refreshUser()
    await refreshGames()

    closeEnterModal()
    toastState.value = {
      isVisible: true,
      type: 'success',
      title: '入场成功',
      message: '现在可以查看照片并投票了'
    }
  } catch (err: any) {
    toastState.value = {
      isVisible: true,
      type: 'error',
      title: '入场失败',
      message: err.message || '入场失败'
    }
  } finally {
    entering.value = false
    enteringGameId.value = null
  }
}

const openVoteModal = async (game: ArenaGame) => {
  selectedGame.value = game
  selectedVote.value = ''

  // Load game details to get photos
  try {
    const details = await storeApi.getArenaGameStatus(game.id)
    selectedGameDetails.value = details
    showVoteModal.value = true
  } catch (err) {
    toastState.value = {
      isVisible: true,
      type: 'error',
      title: '获取失败',
      message: '获取游戏详情失败'
    }
  }
}

const closeVoteModal = () => {
  showVoteModal.value = false
  selectedGame.value = null
  selectedGameDetails.value = null
  selectedVote.value = ''
}

const getPhotoUrl = (photoData: any) => {
  if (!photoData) return ''
  // Construct URL from photo path
  // Media files are served at /media/ not /api/media/
  return `/media/${photoData.path}`
}

const submitVote = async () => {
  if (!selectedGame.value || !selectedVote.value) return

  try {
    voting.value = true

    await storeApi.voteArenaGame(selectedGame.value.id, selectedVote.value as 'creator' | 'challenger')

    await refreshGames()

    closeVoteModal()
    toastState.value = {
      isVisible: true,
      type: 'success',
      title: '投票成功',
      message: '您的投票已提交'
    }
  } catch (err: any) {
    toastState.value = {
      isVisible: true,
      type: 'error',
      title: '投票失败',
      message: err.message || '投票失败'
    }
  } finally {
    voting.value = false
  }
}

const viewGameDetails = async (game: ArenaGame) => {
  try {
    const details = await storeApi.getArenaGameStatus(game.id)
    selectedGame.value = game
    selectedGameDetails.value = details
    // Could show a details modal here
  } catch (err) {
    toastState.value = {
      isVisible: true,
      type: 'error',
      title: '获取失败',
      message: '获取详情失败'
    }
  }
}

const openResultModal = async (game: ArenaGame) => {
  selectedGame.value = game
  selectedGameResult.value = game.result || null
  showResultModal.value = true
}

const closeResultModal = () => {
  showResultModal.value = false
  selectedGame.value = null
  selectedGameResult.value = null
}

const getVotePercentage = (side: 'creator' | 'challenger') => {
  if (!selectedGameResult.value?.final_votes) return 0
  const creator = selectedGameResult.value.final_votes.creator || 0
  const challenger = selectedGameResult.value.final_votes.challenger || 0
  const total = creator + challenger
  if (total === 0) return 0
  return Math.round((selectedGameResult.value.final_votes[side] / total) * 100)
}

const cancelGame = async (gameId: string) => {
  if (!confirm('确定要取消这个游戏吗？')) return

  try {
    cancelingGame.value = true
    await storeApi.cancelGame(gameId)
    await refreshGames()
    toastState.value = {
      isVisible: true,
      type: 'success',
      title: '取消成功',
      message: '游戏已取消'
    }
  } catch (err: any) {
    toastState.value = {
      isVisible: true,
      type: 'error',
      title: '取消失败',
      message: err.message || '取消失败'
    }
  } finally {
    cancelingGame.value = false
  }
}

// Profile Modal
const openProfileModal = (user: User) => {
  selectedUser.value = user
  showProfileModal.value = true
}

const closeProfileModal = () => {
  showProfileModal.value = false
  selectedUser.value = undefined
}

onMounted(() => {
  refreshGames()
})
</script>

<style scoped>
.arena-game {
  padding: 1rem 0;
}

.game-section {
  background: white;
  border: 4px solid #000;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  box-shadow: 8px 8px 0 #000;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.section-title {
  font-size: 1.25rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0;
}

/* Rules */
.intro-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.rules-toggle {
  background: #f8f9fa;
  border: 2px solid #000;
  padding: 0.5rem 1rem;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 2px 2px 0 #000;
  transition: all 0.2s;
}

.rules-toggle:hover {
  transform: translate(-1px, -1px);
  box-shadow: 3px 3px 0 #000;
}

.rules-content {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 2px dashed #ccc;
}

.rules-flow {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.flow-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
  padding: 0.75rem;
  background: #f8f9fa;
  border: 2px solid #000;
}

.step-icon {
  font-size: 1.5rem;
}

.step-text {
  font-size: 0.75rem;
  font-weight: 700;
  text-align: center;
}

.flow-arrow {
  font-size: 1.25rem;
  font-weight: 900;
}

.rules-details {
  background: #fff3cd;
  border: 2px solid #ffc107;
  padding: 1rem;
  font-size: 0.875rem;
}

.rules-details p {
  margin: 0.25rem 0;
}

/* Create Form */
.create-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-label {
  font-weight: 700;
  font-size: 0.875rem;
  text-transform: uppercase;
}

.form-input {
  border: 3px solid #000;
  padding: 0.75rem;
  font-size: 1rem;
  background: white;
}

.form-slider {
  width: 100%;
  height: 8px;
  -webkit-appearance: none;
  appearance: none;
  background: #ddd;
  border: 2px solid #000;
  outline: none;
}

.form-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 24px;
  height: 24px;
  background: #007bff;
  border: 2px solid #000;
  cursor: pointer;
}

.form-hint {
  font-size: 0.75rem;
  color: #666;
}

/* Photo Upload */
.photo-upload-area {
  border: 3px dashed #000;
  padding: 2rem;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  min-height: 150px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.photo-upload-area:hover {
  background: #f8f9fa;
}

.photo-upload-area.has-photo {
  border-style: solid;
  border-color: #28a745;
  padding: 0;
}

.photo-upload-area.large {
  min-height: 200px;
}

.hidden-input {
  display: none;
}

.upload-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

.upload-icon {
  font-size: 2rem;
}

.upload-text {
  font-weight: 700;
  color: #666;
}

.photo-preview {
  width: 100%;
  height: 100%;
}

.photo-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* Buttons */
.create-btn {
  background: #28a745;
  color: white;
  border: 3px solid #000;
  padding: 1rem;
  font-size: 1.1rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  cursor: pointer;
  box-shadow: 4px 4px 0 #000;
  transition: all 0.2s ease;
  min-height: 48px;
}

.create-btn:hover:not(:disabled) {
  transform: translate(2px, 2px);
  box-shadow: 2px 2px 0 #000;
}

.create-btn:disabled {
  background: #6c757d;
  cursor: not-allowed;
  opacity: 0.6;
}

.refresh-btn {
  background: #17a2b8;
  color: white;
  border: 3px solid #000;
  padding: 0.5rem 1rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  cursor: pointer;
  box-shadow: 3px 3px 0 #000;
  transition: all 0.2s ease;
  min-height: 40px;
}

.refresh-btn:hover:not(:disabled) {
  transform: translate(1px, 1px);
  box-shadow: 2px 2px 0 #000;
}

.refresh-btn:disabled {
  background: #6c757d;
  cursor: not-allowed;
  opacity: 0.6;
}

/* Games Grid */
.games-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1rem;
}

.game-card {
  background: white;
  border: 3px solid #000;
  padding: 1rem;
  box-shadow: 4px 4px 0 #000;
  transition: all 0.2s;
}

.game-card:hover {
  transform: translate(-2px, -2px);
  box-shadow: 6px 6px 0 #000;
}

.game-card.can-join {
  border-color: #28a745;
}

.game-card.is-creator {
  border-color: #007bff;
}

.game-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.creator-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.creator-info :deep(.user-avatar) {
  flex-shrink: 0;
}

.creator-details {
  display: flex;
  flex-direction: column;
}

.creator-name {
  font-weight: 700;
}

.creator-name.clickable {
  cursor: pointer;
  transition: opacity 0.2s ease;
}

.creator-name.clickable:hover {
  opacity: 0.8;
  text-decoration: underline;
}

.game-time {
  font-size: 0.75rem;
  color: #666;
}

.game-status {
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  border: 2px solid #000;
}

.game-status.waiting {
  background: #ffc107;
}

.game-status.active {
  background: #28a745;
  color: white;
}

.game-status.completed {
  background: #6c757d;
  color: white;
}

/* Battle Preview */
.battle-preview {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem;
  background: #f8f9fa;
  border: 2px solid #000;
  margin-bottom: 1rem;
}

.fighter {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

.fighter-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
}

.fighter-avatar.empty {
  width: 80px;
  height: 80px;
  background: #ddd;
  border-radius: 50%;
  border: 3px solid #000;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 2px 2px 0 #000;
}

.empty-icon {
  font-size: 1.5rem;
  font-weight: 900;
  color: #666;
}

.fighter-name {
  font-size: 0.75rem;
  font-weight: 700;
  text-align: center;
  max-width: 90px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fighter-name.clickable {
  cursor: pointer;
  color: #007bff;
  transition: all 0.2s ease;
}

.fighter-name.clickable:hover {
  text-decoration: underline;
  color: #0056b3;
}

.vote-count {
  font-size: 0.875rem;
  font-weight: 700;
  background: white;
  padding: 0.25rem 0.5rem;
  border: 2px solid #000;
}

.vs-divider {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
}

.vs-text {
  font-size: 1.25rem;
  font-weight: 900;
}

.bet-amount {
  font-weight: 700;
  background: #ffc107;
  padding: 0.25rem 0.5rem;
  border: 2px solid #000;
}

/* Game Meta */
.game-meta {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.875rem;
}

/* Game Actions */
.game-actions {
  display: flex;
  gap: 0.5rem;
}

.join-btn, .enter-btn, .vote-btn, .result-btn, .view-btn {
  flex: 1;
  padding: 0.75rem;
  border: 3px solid #000;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  cursor: pointer;
  box-shadow: 3px 3px 0 #000;
  transition: all 0.2s ease;
  min-height: 48px;
}

.join-btn:hover:not(:disabled), .enter-btn:hover:not(:disabled), .vote-btn:hover:not(:disabled), .result-btn:hover:not(:disabled), .view-btn:hover:not(:disabled) {
  transform: translate(1px, 1px);
  box-shadow: 2px 2px 0 #000;
}

.join-btn:disabled, .enter-btn:disabled, .vote-btn:disabled, .result-btn:disabled, .view-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.join-btn {
  background: #28a745;
  color: white;
}

.join-btn.challenger {
  background: #dc3545;
}

.enter-btn {
  background: #ffc107;
}

.vote-btn {
  background: #007bff;
  color: white;
}

.result-btn {
  background: #6f42c1;
  color: white;
}

.view-btn {
  background: #17a2b8;
  color: white;
}

.creator-actions {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.role-badge {
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  font-weight: 700;
  border: 2px solid #000;
}

.role-badge.creator {
  background: #007bff;
  color: white;
}

.cancel-btn {
  background: #dc3545;
  color: white;
  border: 3px solid #000;
  padding: 0.5rem 1rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  cursor: pointer;
  box-shadow: 3px 3px 0 #000;
  transition: all 0.2s ease;
  min-height: 40px;
}

.cancel-btn:hover:not(:disabled) {
  transform: translate(1px, 1px);
  box-shadow: 2px 2px 0 #000;
}

.cancel-btn:disabled {
  background: #6c757d;
  cursor: not-allowed;
  opacity: 0.6;
}

.disabled-text {
  color: #666;
  font-size: 0.875rem;
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

.modal-content {
  background: white;
  border: 4px solid #000;
  border-radius: 0;
  max-width: 500px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 12px 12px 0 #000;
}

.modal-content.vote-modal {
  max-width: 700px;
}

.modal-content.result-modal {
  max-width: 500px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 3px solid #000;
  background: #f8f9fa;
}

.modal-title {
  font-size: 1.25rem;
  font-weight: 900;
  text-transform: uppercase;
  margin: 0;
}

.modal-close {
  background: #dc3545;
  color: white;
  border: 3px solid #000;
  padding: 0.5rem 1rem;
  font-weight: 900;
  font-size: 1.25rem;
  cursor: pointer;
  box-shadow: 3px 3px 0 #000;
}

.modal-body {
  padding: 1.5rem;
}

.modal-footer {
  display: flex;
  gap: 1rem;
  padding: 1rem 1.5rem;
  border-top: 3px solid #000;
  background: #f8f9fa;
}

.modal-footer .cancel-btn {
  flex: 1;
  padding: 0.75rem;
  background: #6c757d;
  color: white;
  border: 3px solid #000;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  cursor: pointer;
  box-shadow: 3px 3px 0 #000;
  transition: all 0.2s ease;
  min-height: 48px;
}

.modal-footer .confirm-btn {
  flex: 1;
  padding: 0.75rem;
  background: #28a745;
  color: white;
  border: 3px solid #000;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  cursor: pointer;
  box-shadow: 3px 3px 0 #000;
  transition: all 0.2s ease;
  min-height: 48px;
}

.modal-footer .cancel-btn:hover:not(:disabled),
.modal-footer .confirm-btn:hover:not(:disabled) {
  transform: translate(1px, 1px);
  box-shadow: 2px 2px 0 #000;
}

.modal-footer .confirm-btn:disabled {
  background: #6c757d;
  cursor: not-allowed;
  opacity: 0.6;
}

/* Vote Modal */
.vote-instruction {
  text-align: center;
  font-weight: 700;
  margin-bottom: 1rem;
}

.vote-options {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.vote-option {
  border: 3px solid #000;
  padding: 1rem;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 4px 4px 0 #000;
}

.vote-option:hover {
  transform: translate(-2px, -2px);
  box-shadow: 6px 6px 0 #000;
}

.vote-option.selected {
  background: #007bff;
  color: white;
}

.vote-photo {
  aspect-ratio: 1;
  background: #f8f9fa;
  border: 2px solid #000;
  margin-bottom: 0.5rem;
  overflow: hidden;
}

.vote-photo img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.vote-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
}

.voter-name {
  font-weight: 700;
}

.vote-label {
  font-size: 0.75rem;
  opacity: 0.8;
}

/* Result Modal */
.winner-section {
  text-align: center;
  padding: 2rem;
  margin-bottom: 1.5rem;
  border: 4px solid #000;
}

.winner-section.creator {
  background: #d4edda;
}

.winner-section.challenger {
  background: #f8d7da;
}

.winner-section.tie {
  background: #fff3cd;
}

.winner-crown {
  font-size: 3rem;
  margin-bottom: 0.5rem;
}

.winner-text {
  font-size: 1.5rem;
  font-weight: 900;
  text-transform: uppercase;
}

.vote-stats {
  margin-bottom: 1.5rem;
}

.stat-bar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.stat-label {
  width: 80px;
  font-weight: 700;
  font-size: 0.875rem;
}

.stat-progress {
  flex: 1;
  height: 24px;
  background: #f8f9fa;
  border: 2px solid #000;
  overflow: hidden;
}

.stat-fill {
  height: 100%;
  transition: width 0.5s ease;
}

.stat-fill.creator {
  background: #28a745;
}

.stat-fill.challenger {
  background: #dc3545;
}

.stat-value {
  width: 40px;
  text-align: right;
  font-weight: 700;
}

.reward-section {
  background: #f8f9fa;
  border: 3px solid #000;
  padding: 1rem;
}

.reward-item {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  border-bottom: 1px dashed #ccc;
}

.reward-item:last-child {
  border-bottom: none;
}

.reward-label {
  font-weight: 700;
}

.reward-value {
  font-weight: 900;
}

/* Enter Modal */
.enter-info {
  text-align: center;
  margin-bottom: 1.5rem;
}

.ticket-price {
  font-size: 1.25rem;
  margin-top: 0.5rem;
}

.preview-hint {
  text-align: center;
}

.mosaic-preview {
  display: flex;
  justify-content: center;
  gap: 1rem;
  margin-bottom: 0.5rem;
}

.mosaic-box {
  width: 80px;
  height: 80px;
  background: #ddd;
  border: 2px solid #000;
  filter: blur(8px);
}

.hint-text {
  color: #666;
  font-size: 0.875rem;
}

/* Loading & Empty States */
.loading-state, .empty-state {
  text-align: center;
  padding: 3rem;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #007bff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 1rem;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: 0.5rem;
}

.empty-text {
  font-weight: 700;
  font-size: 1.1rem;
}

.empty-hint {
  color: #666;
}

/* Mobile Responsive */
@media (max-width: 768px) {
  .arena-game {
    padding: 0.5rem 0;
  }

  .game-section {
    padding: 1rem;
    margin-bottom: 1rem;
  }

  .form-row {
    grid-template-columns: 1fr;
  }

  .games-grid {
    grid-template-columns: 1fr;
  }

  .game-card {
    padding: 1rem;
  }

  .battle-preview {
    flex-direction: column;
    gap: 1rem;
  }

  .vs-divider {
    order: -1;
  }

  .vote-options {
    grid-template-columns: 1fr;
  }

  .rules-flow {
    flex-direction: column;
  }

  .flow-arrow {
    transform: rotate(90deg);
  }

  .modal-content {
    margin: 0.5rem;
    max-height: calc(100vh - 1rem);
  }

  .modal-header,
  .modal-body,
  .modal-footer {
    padding: 1rem;
  }

  .modal-footer {
    flex-direction: column;
    gap: 0.75rem;
  }

  .modal-footer .cancel-btn,
  .modal-footer .confirm-btn {
    width: 100%;
  }

  .game-actions {
    flex-direction: column;
  }

  .join-btn, .enter-btn, .vote-btn, .result-btn, .view-btn {
    width: 100%;
  }

  .creator-actions {
    flex-direction: column;
    width: 100%;
  }

  .photo-upload-area {
    min-height: 120px;
  }

  .photo-upload-area.large {
    min-height: 160px;
  }
}
</style>
