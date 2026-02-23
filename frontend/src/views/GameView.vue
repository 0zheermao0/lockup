<template>
  <div class="game-view">
    <!-- Header -->
    <header class="game-header">
      <div class="header-content">
        <button @click="goBack" class="back-btn">
          ← 返回
        </button>
        <h1 class="game-title">🎮 游戏中心</h1>
        <div class="header-stats">
          <NotificationBell />
          <div class="coins-display">
            <span class="coins-icon">🪙</span>
            <span class="coins-amount">{{ userCoins }}</span>
          </div>
          <router-link to="/inventory" class="inventory-btn">
            🎒 背包
          </router-link>
        </div>
      </div>
    </header>

    <div class="container">

      <!-- Game tabs -->
      <div class="game-tabs">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          @click="activeTab = tab.id"
          :class="[
            'game-tab',
            activeTab === tab.id ? 'active' : ''
          ]"
        >
          {{ tab.name }}
        </button>
      </div>

      <!-- Rock Paper Scissors Game -->
      <div v-if="activeTab === 'rockPaperScissors'" class="space-y-6">
        <div class="game-section">
          <h2 class="section-title">✂️ 石头剪刀布</h2>
          <p class="section-description">
            发起异步猜拳挑战！任何人都可以发起并选择出拳，其他人可以参与对战。输家将增加30分钟锁时间。
          </p>

          <!-- Lock task requirement -->
          <div v-if="!hasActiveLockTask" class="warning-box">
            <p class="warning-text">
              ⚠️ 只有正在进行锁任务时才能参与游戏
            </p>
          </div>

          <div v-else>
            <!-- Create game with choice -->
            <div class="form-group">
              <h3 class="form-label">发起新挑战</h3>
              <div class="game-creation">
                <div>
                  <label class="form-label">下注积分</label>
                  <input
                    v-model.number="newGameBet"
                    type="number"
                    min="1"
                    class="form-input"
                    :disabled="creatingGame"
                  >
                </div>
                <div>
                  <label class="form-label">你的出拳</label>
                  <div class="choice-buttons">
                    <button
                      v-for="choice in choices"
                      :key="choice.value"
                      @click="selectedChoice = choice.value"
                      :class="[
                        'choice-btn',
                        selectedChoice === choice.value ? 'selected' : ''
                      ]"
                      :disabled="creatingGame"
                    >
                      <span class="choice-icon">{{ choice.icon }}</span>
                      <span class="choice-name">{{ choice.name }}</span>
                    </button>
                  </div>
                </div>
                <button
                  @click="createRockPaperScissorsGameWithChoice"
                  :disabled="!canCreateGameWithChoice || creatingGame"
                  class="btn-primary"
                  :class="{ 'opacity-50 cursor-not-allowed': !canCreateGameWithChoice || creatingGame }"
                >
                  <span v-if="creatingGame">发起中...</span>
                  <span v-else>发起挑战</span>
                </button>
              </div>
              <div v-if="!canCreateGameWithChoice" class="restrictions">
                <p v-if="userCoins < newGameBet">积分不足</p>
                <p v-else-if="newGameBet < 1">至少下注1积分</p>
                <p v-else-if="!selectedChoice">请选择你的出拳</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Available games -->
        <div v-if="hasActiveLockTask" class="game-section">
          <div class="section-header">
            <h3 class="section-title">待接受的挑战</h3>
            <button
              @click="refreshGames"
              :disabled="loadingGames"
              class="refresh-btn"
              title="刷新挑战列表"
            >
              <span class="refresh-icon" :class="{ spinning: loadingGames }">🔄</span>
              刷新
            </button>
          </div>

          <!-- Loading -->
          <div v-if="loadingGames" class="loading-center">
            <div class="loading-spinner"></div>
          </div>

          <!-- No games -->
          <div v-else-if="filteredRPSGames.length === 0" class="empty-state">
            暂无可参与的挑战
          </div>

          <!-- Games list -->
          <div v-else class="games-list">
            <div
              v-for="game in filteredRPSGames"
              :key="game.id"
              class="game-card"
            >
              <div class="game-info">
                <h4>{{ game.creator?.username || '未知用户' }} 的挑战</h4>
                <p class="game-meta">下注: {{ game.bet_amount }}积分 | 创建时间: {{ formatTime(game.created_at) }}</p>
                <p class="game-meta">状态: 等待对手</p>
              </div>

              <!-- Join with choice selection -->
              <div v-if="game.creator?.id !== authStore.user?.id" class="join-game-section">
                <div v-if="!showJoinChoice[game.id]">
                  <button
                    @click="showJoinChoice[game.id] = true"
                    :disabled="joiningGame"
                    class="btn-secondary"
                    :class="{ 'opacity-50': joiningGame }"
                  >
                    接受挑战
                  </button>
                </div>
                <div v-else class="join-choice-section">
                  <p class="form-label">选择你的出拳:</p>
                  <div class="choice-buttons small">
                    <button
                      v-for="choice in choices"
                      :key="choice.value"
                      @click="joinChoices[game.id] = choice.value"
                      :class="[
                        'choice-btn',
                        'small',
                        joinChoices[game.id] === choice.value ? 'selected' : ''
                      ]"
                      :disabled="joiningGame"
                    >
                      <span class="choice-icon">{{ choice.icon }}</span>
                      <span class="choice-name">{{ choice.name }}</span>
                    </button>
                  </div>
                  <div class="join-actions">
                    <button
                      @click="joinGameWithChoice(game.id)"
                      :disabled="!joinChoices[game.id] || joiningGame"
                      class="btn-primary small"
                      :class="{ 'opacity-50': !joinChoices[game.id] || joiningGame }"
                    >
                      <span v-if="joiningGame">参与中...</span>
                      <span v-else>确认参与</span>
                    </button>
                    <button
                      @click="showJoinChoice[game.id] = false"
                      class="btn-secondary small"
                      :disabled="joiningGame"
                    >
                      取消
                    </button>
                  </div>
                </div>
              </div>
              <div v-else class="creator-info">
                <span class="creator-badge">你的挑战</span>
                <p class="game-meta">等待其他玩家接受</p>
                <button
                  @click="cancelGame(game.id)"
                  :disabled="cancelingGame"
                  class="btn-cancel"
                  :class="{ 'opacity-50': cancelingGame }"
                >
                  <span v-if="cancelingGame">取消中...</span>
                  <span v-else>❌ 取消挑战</span>
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Game Result Modal -->
        <div v-if="showResultModal" class="modal-overlay" @click="closeResultModal">
          <div class="modal-content" @click.stop>
            <div class="modal-header">
              <h3 class="modal-title">🎮 对战结果</h3>
              <button @click="closeResultModal" class="modal-close">×</button>
            </div>

            <div class="modal-body">
              <div class="result-display">
                <div class="result-icon-large">{{ getGameResultIcon(gameResult) }}</div>
                <p class="result-message-large">{{ gameResult?.message }}</p>
              </div>

              <div v-if="gameResult?.results" class="battle-details">
                <h4 class="battle-title">⚔️ 出拳详情</h4>
                <div class="battle-grid">
                  <div v-for="result in gameResult.results" :key="result.player || result.user || Math.random()" class="battle-item">
                    <div class="player-name">{{ result.player || result.user || '玩家' }}</div>
                    <div class="player-choice">{{ getChoiceText(result.choice) }}</div>
                  </div>
                </div>
              </div>

              <div class="result-stats">
                <div v-if="gameResult?.winner" class="stat-item winner">
                  <span class="stat-label">🏆 获胜者</span>
                  <span class="stat-value">{{ gameResult.winner }}</span>
                </div>
                <div v-if="gameResult?.coins_change" class="stat-item coins">
                  <span class="stat-label">💰 积分变化</span>
                  <span class="stat-value" :class="gameResult.coins_change > 0 ? 'positive' : 'negative'">
                    {{ gameResult.coins_change > 0 ? '+' : '' }}{{ gameResult.coins_change }}
                  </span>
                </div>
              </div>
            </div>

            <div class="modal-footer">
              <button @click="closeResultModal" class="btn-primary modal-btn">确定</button>
            </div>
          </div>
        </div>
      </div>

      <!-- Time Wheel Game -->
      <div v-if="activeTab === 'timeWheel'" class="space-y-6">
        <div class="game-section">
          <h2 class="section-title">🎰 时间转盘</h2>
          <p class="section-description">
            投入积分来改变带锁任务的时间！52%概率增加时间，48%概率减少时间。基础时间档位：5、15、30、60分钟。
          </p>

          <!-- Lock task requirement -->
          <div v-if="!hasActiveLockTask" class="warning-box">
            <p class="warning-text">
              ⚠️ 只有正在进行锁任务时才能参与时间转盘
            </p>
          </div>

          <!-- Time Wheel Component -->
          <div v-else-if="getActiveLockTaskId()">
            <TimeWheel
              :task-id="getActiveLockTaskId()"
              :user-coins="userCoins"
              @time-changed="handleTimeChanged"
              @coins-changed="handleCoinsChanged"
              @error="handleTimeWheelError"
              @close="handleTimeWheelClose"
            />
          </div>
          <div v-else class="warning-box">
            <p class="warning-text">
              ⚠️ 正在加载锁任务信息...
            </p>
          </div>
        </div>
      </div>

      <!-- Dice Game -->
      <div v-if="activeTab === 'dice'" class="space-y-6">
        <div class="game-section">
          <h2 class="section-title">🎲 掷骰子</h2>
          <p class="section-description">
            创建掷骰子游戏！设置参与费用和可选奖励物品，参与者猜大小，猜中可获得奖励物品。
          </p>

          <!-- Dice Game Component -->
          <div>
            <DiceGame />
          </div>
        </div>
      </div>

      <!-- Arena Game -->
      <div v-if="activeTab === 'arena'" class="space-y-6">
        <div class="game-section">
          <h2 class="section-title">🏟️ 角斗场</h2>
          <p class="section-description">
            发起照片挑战，观众付费入场投票决胜负！胜者获得投注积分和门票奖励。
          </p>
          <ArenaGame />
        </div>
      </div>

      <!-- Degrees of Lewdity Game -->
      <div v-if="activeTab === 'dol'" class="space-y-6">
        <div class="game-section">
          <div class="game-header-with-actions">
            <h2 class="section-title">📖 欲都孤儿</h2>
            <button
              @click="toggleFullscreen"
              class="fullscreen-btn"
              :title="isFullscreen ? '退出全屏' : '全屏游戏'"
            >
              <span v-if="isFullscreen">⛶ 退出全屏</span>
              <span v-else>⛶ 全屏游戏</span>
            </button>
          </div>
          <p class="section-description">
            Degrees of Lewdity 中文版 - 一款文字冒险游戏，在这个陌生的城市中探索、生存并寻找属于自己的道路。
          </p>

          <!-- Game iframe container -->
          <div
            ref="gameContainer"
            class="game-iframe-container"
            :class="{ 'fullscreen': isFullscreen }"
          >
            <iframe
              src="https://eltirosto.github.io/Degrees-of-Lewdity-Chinese-Localization/Degrees%20of%20Lewdity%20VERSION.html.mod.html"
              class="game-iframe"
              :class="{ 'fullscreen': isFullscreen }"
              title="欲都孤儿"
              sandbox="allow-scripts allow-same-origin allow-popups allow-forms"
              loading="lazy"
            ></iframe>
            <button
              v-if="isFullscreen"
              @click="toggleFullscreen"
              class="fullscreen-exit-overlay"
              title="退出全屏"
            >
              ⛶ 退出全屏
            </button>
          </div>
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeApi, tasksApi } from '../lib/api'
import { useAuthStore } from '../stores/auth'
import { smartGoBack } from '../utils/navigation'
import TimeWheel from '../components/TimeWheel.vue'
import DiceGame from '../components/DiceGame.vue'
import ArenaGame from '../components/ArenaGame.vue'
import NotificationBell from '../components/NotificationBell.vue'
import NotificationToast from '../components/NotificationToast.vue'
import { toastState, closeToast } from '../composables/useGameToast'
import type { Game } from '../types'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

// Valid tab IDs
const validTabs = ['dice', 'rockPaperScissors', 'timeWheel', 'arena', 'dol']

// Methods
const goBack = () => {
  smartGoBack(router, { defaultRoute: 'home' })
}

// Reactive data
const activeTab = ref('dice')
const activeLockTask = ref<any>(null) // Active lock task for time wheel
const games = ref<Game[]>([])
const loadingGames = ref(false)
const gamePollingInterval = ref<number | null>(null)

// Fullscreen state for Oliver Twist game
const isFullscreen = ref(false)
const gameContainer = ref<HTMLDivElement | null>(null)

// Fullscreen toggle function
const toggleFullscreen = async () => {
  if (!gameContainer.value) return

  try {
    if (!document.fullscreenElement) {
      // Enter fullscreen
      await gameContainer.value.requestFullscreen()
      isFullscreen.value = true
    } else {
      // Exit fullscreen
      await document.exitFullscreen()
      isFullscreen.value = false
    }
  } catch (err) {
    console.error('Fullscreen error:', err)
    // Fallback: toggle class-based fullscreen
    isFullscreen.value = !isFullscreen.value
  }
}

// Handle fullscreen change events
const handleFullscreenChange = () => {
  isFullscreen.value = !!document.fullscreenElement
}

// Time wheel (removed - now handled by TimeWheel component)

// Rock paper scissors
const newGameBet = ref(1)
const selectedChoice = ref('')
const creatingGame = ref(false)
const joiningGame = ref(false)
const gameResult = ref<any>(null)
const showJoinChoice = ref<Record<string, boolean>>({})
const joinChoices = ref<Record<string, string>>({})
const showResultModal = ref(false)
const cancelingGame = ref(false)

// Computed
const userCoins = computed(() => authStore.user?.coins || 0)
const hasActiveLockTask = computed(() => {
  // Check both local activeLockTask and auth store data for more reliable detection
  const localTask = activeLockTask.value !== null
  const authStoreTask = authStore.user?.active_lock_task !== null && authStore.user?.active_lock_task !== undefined

  console.log('hasActiveLockTask check:', {
    localTask: localTask,
    authStoreTask: authStoreTask,
    localTaskData: activeLockTask.value,
    authStoreTaskData: authStore.user?.active_lock_task
  })

  // Return true if either source indicates there's an active lock task
  return localTask || authStoreTask
})

// TimeWheel computed removed - handled by component

const canCreateGame = computed(() => {
  return hasActiveLockTask.value &&
         userCoins.value >= newGameBet.value &&
         newGameBet.value >= 1
})

const canCreateGameWithChoice = computed(() => {
  return canCreateGame.value && selectedChoice.value !== ''
})

const filteredRPSGames = computed(() => {
  const filtered = games.value.filter(game => {
    const isRPS = game.game_type === 'rock_paper_scissors'
    const isWaiting = game.status === 'waiting'
    const hasSpace = (game.participants?.length || 0) < (game.max_players || 2)

    console.log(`Game ${game.id}: isRPS=${isRPS}, isWaiting=${isWaiting}, hasSpace=${hasSpace}, creator=${game.creator?.username}, currentUser=${authStore.user?.username}`)

    return isRPS && isWaiting && hasSpace
  })

  console.log('Filtered RPS games:', filtered.length)
  return filtered
})

// Data
const tabs = [
  { id: 'dice', name: '掷骰子' },
  { id: 'rockPaperScissors', name: '石头剪刀布' },
  { id: 'timeWheel', name: '时间转盘' },
  { id: 'arena', name: '角斗场' },
  { id: 'dol', name: '欲都孤儿' }
]

const choices = [
  { value: 'rock', name: '石头', icon: '🪨' },
  { value: 'paper', name: '布', icon: '📄' },
  { value: 'scissors', name: '剪刀', icon: '✂️' }
]

// Helper methods
const getActiveLockTaskId = () => {
  // Try to get ID from local state first, then from auth store
  if (activeLockTask.value?.id) {
    return activeLockTask.value.id
  }
  if (authStore.user?.active_lock_task?.id) {
    return authStore.user.active_lock_task.id
  }
  return null
}

// TimeWheel event handlers
const handleTimeChanged = async (change: { isIncrease: boolean, minutes: number, taskId: string, newEndTime?: string }) => {
  console.log('Time changed:', change)
  // Reload the active lock task to reflect time changes
  await loadActiveLockTask()

  // Also refresh the global auth store user data so other components (HomeView, ProfileView, etc.)
  // get the updated lock task information
  try {
    await authStore.refreshUser()
    console.log('Auth store user data refreshed after time wheel change')
  } catch (error) {
    console.error('Failed to refresh user data after time wheel change:', error)
  }
}

const handleCoinsChanged = (newCoins: number) => {
  console.log('Coins changed:', newCoins)
  // Update user coins
  if (authStore.user) {
    authStore.user.coins = newCoins
  }
}

const handleTimeWheelError = (message: string) => {
  console.error('Time wheel error:', message)
  toastState.value = {
    isVisible: true,
    type: 'error',
    title: '时间转盘错误',
    message
  }
}

const handleTimeWheelClose = () => {
  console.log('Time wheel closed')
  // Could show a different UI state here if needed
}

const createRockPaperScissorsGame = async () => {
  if (!canCreateGame.value || creatingGame.value) return

  try {
    creatingGame.value = true

    await storeApi.createGame({
      game_type: 'rock_paper_scissors',
      bet_amount: newGameBet.value,
      max_players: 2
    })

    // Refresh games list
    loadGames()

  } catch (err) {
    console.error('Create game error:', err)
  } finally {
    creatingGame.value = false
  }
}

const createRockPaperScissorsGameWithChoice = async () => {
  if (!canCreateGameWithChoice.value || creatingGame.value) return

  try {
    creatingGame.value = true
    gameResult.value = null

    // First create the game
    const game = await storeApi.createGame({
      game_type: 'rock_paper_scissors',
      bet_amount: newGameBet.value,
      max_players: 2
    })

    // Then immediately join it with our choice
    const result = await storeApi.joinGame(game.id, { choice: selectedChoice.value })

    // Check if the game completed immediately
    if (result.winner || result.message.includes('平局')) {
      gameResult.value = result
      showResultModal.value = true
    }

    // Update user coins - refresh from API to get accurate count
    await authStore.refreshUser()

    // Reset form
    selectedChoice.value = ''
    newGameBet.value = 1

    // Refresh games list
    loadGames()

  } catch (err) {
    console.error('Create game with choice error:', err)
  } finally {
    creatingGame.value = false
  }
}

const joinGame = async (gameId: string) => {
  if (joiningGame.value) return

  try {
    joiningGame.value = true
    gameResult.value = null

    const result = await storeApi.joinGame(gameId)
    gameResult.value = result

    // Update user coins if bet was deducted
    // TODO: Get updated user info from API

    // Refresh games list
    loadGames()

  } catch (err) {
    console.error('Join game error:', err)
  } finally {
    joiningGame.value = false
  }
}

const joinGameWithChoice = async (gameId: string) => {
  const choice = joinChoices.value[gameId]
  if (!choice || joiningGame.value) return

  try {
    joiningGame.value = true
    gameResult.value = null

    const result = await storeApi.joinGame(gameId, { choice })
    gameResult.value = result
    showResultModal.value = true

    // 注意：积分更新现在由API响应拦截器自动处理，无需手动更新

    // Clear choice selection
    delete joinChoices.value[gameId]
    showJoinChoice.value[gameId] = false

    // Refresh games list
    loadGames()

  } catch (err) {
    console.error('Join game with choice error:', err)
  } finally {
    joiningGame.value = false
  }
}

const loadActiveLockTask = async () => {
  try {
    console.log('=== LOADING ACTIVE LOCK TASK ===')
    console.log('Auth token from localStorage:', localStorage.getItem('token') ? localStorage.getItem('token')!.substring(0, 10) + '...' : 'null')

    // First check and complete any expired tasks
    console.log('Checking for expired tasks...')
    await tasksApi.checkAndCompleteExpiredTasks()

    console.log('Getting active lock task...')
    activeLockTask.value = await tasksApi.getActiveLockTask()
    console.log('Active lock task loaded:', activeLockTask.value)
    console.log('Task ID:', activeLockTask.value?.id)
    console.log('Task status:', activeLockTask.value?.status)
    console.log('Task type:', activeLockTask.value?.task_type)
  } catch (err: any) {
    console.error('=== LOAD ACTIVE LOCK TASK ERROR ===')
    console.error('Full error:', err)
    console.error('Error message:', err?.message)
    console.error('Error status:', err?.status)
    console.error('Error data:', err?.data)
    activeLockTask.value = null
  }
}

const loadGames = async () => {
  console.log('loadGames called, hasActiveLockTask:', hasActiveLockTask.value)
  if (!hasActiveLockTask.value) {
    console.log('No active lock task, skipping loadGames')
    return
  }

  try {
    loadingGames.value = true
    console.log('Making API call to storeApi.getGames()')
    const result = await storeApi.getGames() as any
    console.log('API response:', result)

    if (result && (result as any).results) {
      // Handle paginated response
      games.value = Array.isArray((result as any).results) ? (result as any).results : []
      console.log('Games loaded from paginated response:', games.value.length, 'games')
    } else if (Array.isArray(result)) {
      // Handle direct array response
      games.value = result
      console.log('Games loaded from direct array:', games.value.length, 'games')
    } else {
      console.warn('Unexpected API response format:', result)
      games.value = []
    }

    console.log('Final games array:', games.value)
  } catch (err: any) {
    console.error('Load games error:', err)
    console.error('Error details:', {
      message: err?.message,
      status: err?.status,
      data: err?.data
    })
    games.value = []
  } finally {
    loadingGames.value = false
  }
}

const refreshGames = async () => {
  console.log('Manual refresh triggered')
  await loadGames()
}

const getGameTypeText = (gameType: string): string => {
  const types = {
    'rock_paper_scissors': '石头剪刀布',
    'time_wheel': '时间转盘',
    'exploration': '探索'
  }
  return types[gameType as keyof typeof types] || gameType
}

const getChoiceText = (choice: string): string => {
  const choices = {
    'rock': '石头 🪨',
    'paper': '布 📄',
    'scissors': '剪刀 ✂️'
  }
  return choices[choice as keyof typeof choices] || choice
}

const formatTime = (dateString: string): string => {
  return new Date(dateString).toLocaleString('zh-CN')
}

const getGameResultIcon = (result: any): string => {
  if (result.winner) {
    return result.winner === authStore.user?.username ? '🎉' : '😢'
  }
  return '🤝' // Tie
}

const closeResultModal = () => {
  showResultModal.value = false
  gameResult.value = null
}

const cancelGame = async (gameId: string) => {
  if (cancelingGame.value) return

  try {
    cancelingGame.value = true

    const result = await storeApi.cancelGame(gameId)

    // 注意：积分更新现在由API响应拦截器自动处理，无需手动更新

    // Refresh games list
    loadGames()

    console.log(result.message)

  } catch (err) {
    console.error('Cancel game error:', err)
  } finally {
    cancelingGame.value = false
  }
}

const startGamePolling = () => {
  // DISABLED: Auto-polling has been disabled. Users should use the refresh button instead.
  console.log('Game polling is disabled - users can use the refresh button to manually update challenges')
  return

  /* COMMENTED OUT - keeping code for reference
  if (gamePollingInterval.value) return

  gamePollingInterval.value = window.setInterval(async () => {
    // Only check and process hourly rewards for active lock tasks
    try {
      if (hasActiveLockTask.value) {
        await tasksApi.processHourlyRewards()
      }

      // Reload active lock task to get updated status
      const previousTask = activeLockTask.value
      await loadActiveLockTask()

      // If the active task changed from active to completed, refresh the page state
      if (previousTask && previousTask.status === 'active' && !hasActiveLockTask.value) {
        console.log('Lock task expired and was auto-completed')
      }
    } catch (err) {
      console.error('Error in game polling:', err)
    }
  }, 5000) // Poll every 5 seconds
  */
}

const stopGamePolling = () => {
  if (gamePollingInterval.value) {
    clearInterval(gamePollingInterval.value)
    gamePollingInterval.value = null
  }
}

// Lifecycle
onMounted(async () => {
  console.log('=== GAMEVIEW MOUNTED ===')
  console.log('Auth token from localStorage:', localStorage.getItem('token') ? localStorage.getItem('token')!.substring(0, 10) + '...' : 'null')
  console.log('Auth token from store:', authStore.token ? authStore.token.substring(0, 10) + '...' : 'null')
  console.log('Auth store user:', authStore.user)
  console.log('Is authenticated:', authStore.isAuthenticated)

  // Check for tab query parameter on mount
  const tabFromQuery = route.query.tab as string
  if (tabFromQuery && validTabs.includes(tabFromQuery)) {
    activeTab.value = tabFromQuery
  }

  // Refresh user data to get current coins
  try {
    console.log('Refreshing user data...')
    await authStore.refreshUser()
    console.log('User data refreshed:', authStore.user)
  } catch (err) {
    console.error('Failed to refresh user data:', err)
  }

  await loadActiveLockTask()

  if (hasActiveLockTask.value) {
    // Load games once on initial page load
    loadGames()
    // startGamePolling() // Removed auto-polling - users can use refresh button for updates
  }

  // Add fullscreen change event listener
  document.addEventListener('fullscreenchange', handleFullscreenChange)
})

// Watch activeTab changes
const handleTabChange = () => {
  if (activeTab.value === 'rockPaperScissors' && hasActiveLockTask.value) {
    // Auto-loading removed - users should use the refresh button to manually update challenges
    // loadGames() // Removed automatic loading - users can use refresh button instead
    // startGamePolling() // Removed auto-polling - users can use refresh button instead
  } else {
    stopGamePolling()
  }
}

// Setup watcher for activeTab
const stopTabWatcher = watch(activeTab, handleTabChange)

// Watch auth store user changes to sync local activeLockTask
const stopAuthWatcher = watch(
  () => authStore.user?.active_lock_task,
  (newTask) => {
    console.log('Auth store active_lock_task changed:', newTask)
    // If local task is null but auth store has a task, update local task
    if (!activeLockTask.value && newTask) {
      console.log('Syncing local activeLockTask with auth store data')
      activeLockTask.value = newTask
    }
  },
  { deep: true }
)

// Watch for query changes (browser back/forward)
const stopRouteWatcher = watch(() => route.query.tab, (newTab) => {
  if (newTab && validTabs.includes(newTab as string)) {
    activeTab.value = newTab as string
  }
})

// Sync tab changes to URL
const stopTabSyncWatcher = watch(activeTab, (newTab) => {
  if (route.query.tab !== newTab) {
    router.replace({ query: { ...route.query, tab: newTab } })
  }
})

onUnmounted(() => {
  stopGamePolling()
  stopTabWatcher()
  stopAuthWatcher()
  stopRouteWatcher()
  stopTabSyncWatcher()
  // Remove fullscreen change event listener
  document.removeEventListener('fullscreenchange', handleFullscreenChange)
})
</script>

<style scoped>
/* Neo-Brutalism Game Design */
.game-view {
  min-height: 100vh;
  background-color: #f5f5f5;
}

/* Header */
.game-header {
  background: white;
  border-bottom: 4px solid #000;
  padding: 1.5rem 0;
  box-shadow: 0 4px 0 #000;
}

.header-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}

.back-btn {
  background: #dc3545;
  color: white;
  padding: 0.75rem 1.5rem;
  border: 3px solid #000;
  border-radius: 0;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  cursor: pointer;
  box-shadow: 4px 4px 0 #000;
  transition: all 0.2s ease;
}

.back-btn:hover {
  transform: translate(2px, 2px);
  box-shadow: 2px 2px 0 #000;
}

.game-title {
  font-size: 2rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 2px;
  margin: 0;
  color: #000;
}

.header-stats {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.coins-display {
  background: #ffc107;
  color: #000;
  padding: 0.75rem 1.5rem;
  border: 3px solid #000;
  border-radius: 0;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  box-shadow: 4px 4px 0 #000;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.coins-icon {
  font-size: 1.25rem;
}

.coins-amount {
  font-size: 1.25rem;
}

.inventory-btn {
  background: #17a2b8;
  color: white;
  padding: 0.75rem 1.5rem;
  border: 3px solid #000;
  border-radius: 0;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  text-decoration: none;
  box-shadow: 4px 4px 0 #000;
  transition: all 0.2s ease;
}

.inventory-btn:hover {
  transform: translate(2px, 2px);
  box-shadow: 2px 2px 0 #000;
}

/* Container */
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem 1rem;
}

/* Game Tabs */
.game-tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 2rem;
  background: white;
  border: 4px solid #000;
  padding: 1rem;
  box-shadow: 8px 8px 0 #000;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.game-tabs::-webkit-scrollbar {
  display: none;
}

.game-tab {
  flex: 0 0 auto;
  min-width: 120px;
  padding: 1rem 1.5rem;
  border: 3px solid #000;
  background: #f8f9fa;
  color: #000;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 4px 4px 0 #000;
  white-space: nowrap;
  text-align: center;
}

.game-tab:hover {
  transform: translate(-1px, -1px);
  box-shadow: 6px 6px 0 #000;
}

.game-tab.active {
  background: #007bff;
  color: white;
  transform: translate(-2px, -2px);
  box-shadow: 8px 8px 0 #000;
}

/* Game Sections */
.game-section {
  background: white;
  border: 4px solid #000;
  padding: 2rem;
  box-shadow: 8px 8px 0 #000;
  margin-bottom: 2rem;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.section-title {
  font-size: 1.5rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0;
  color: #000;
}

.refresh-btn {
  background: #17a2b8;
  color: white;
  border: 3px solid #000;
  border-radius: 6px;
  padding: 0.5rem 1rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  cursor: pointer;
  box-shadow: 3px 3px 0 #000;
  transition: all 0.2s ease;
  font-size: 0.875rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.refresh-btn:hover:not(:disabled) {
  transform: translate(-1px, -1px);
  box-shadow: 4px 4px 0 #000;
  background: #138496;
}

.refresh-btn:disabled {
  background: #6c757d;
  cursor: not-allowed;
  opacity: 0.6;
}

.refresh-icon {
  display: inline-block;
  transition: transform 0.3s ease;
}

.refresh-icon.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.section-description {
  color: #333;
  line-height: 1.5;
  margin-bottom: 1.5rem;
  font-weight: 500;
}

/* Warning Boxes */
.warning-box {
  background: #fff3cd;
  border: 3px solid #ffc107;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  box-shadow: 4px 4px 0 #ffc107;
}

.warning-text {
  color: #856404;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 0;
}

/* Form Controls */
.form-group {
  margin-bottom: 1.5rem;
}

.form-label {
  display: block;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 0.5rem;
  color: #000;
  font-size: 0.875rem;
}

.form-input {
  border: 3px solid #000;
  padding: 0.75rem;
  font-weight: 700;
  background: white;
  color: #000;
  width: 100px;
}

.form-hint {
  font-size: 0.75rem;
  color: #666;
  margin-top: 0.5rem;
  font-weight: 600;
}

/* Buttons */
.btn-primary {
  background: #28a745;
  color: white;
  border: 3px solid #000;
  padding: 0.75rem 1.5rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  cursor: pointer;
  box-shadow: 4px 4px 0 #000;
  transition: all 0.2s ease;
}

.btn-primary:hover:not(:disabled) {
  transform: translate(2px, 2px);
  box-shadow: 2px 2px 0 #000;
}

.btn-primary:disabled {
  background: #6c757d;
  cursor: not-allowed;
  opacity: 0.6;
}

.btn-secondary {
  background: #6c757d;
  color: white;
  border: 3px solid #000;
  padding: 0.5rem 1rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  cursor: pointer;
  box-shadow: 3px 3px 0 #000;
  transition: all 0.2s ease;
  font-size: 0.875rem;
}

.btn-secondary:hover {
  transform: translate(1px, 1px);
  box-shadow: 2px 2px 0 #000;
}

/* Game Creation */
.game-creation {
  display: flex;
  align-items: end;
  gap: 1rem;
  flex-wrap: wrap;
}

/* Game List */
.games-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.game-card {
  background: white;
  border: 3px solid #000;
  padding: 1.5rem;
  box-shadow: 4px 4px 0 #000;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: all 0.2s ease;
}

.game-card:hover {
  transform: translate(-1px, -1px);
  box-shadow: 6px 6px 0 #000;
}

.game-info h4 {
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 0 0 0.5rem 0;
}

.game-meta {
  font-size: 0.875rem;
  color: #666;
  margin: 0.25rem 0;
}

/* Result Boxes */
.result-box {
  background: white;
  border: 4px solid #000;
  padding: 2rem;
  box-shadow: 8px 8px 0 #000;
  margin-bottom: 2rem;
}

.result-title {
  font-size: 1.25rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 1rem 0;
  color: #000;
}

.result-content {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
}

.result-icon {
  font-size: 2rem;
}

.result-message {
  font-weight: 700;
  font-size: 1.1rem;
}

.result-message.increase {
  color: #dc3545;
}

.result-message.decrease {
  color: #28a745;
}

.result-meta {
  font-size: 0.875rem;
  color: #666;
  font-weight: 600;
}

/* Battle Results */
.battle-results {
  margin-top: 1rem;
}

.battle-results h4 {
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 0 0 0.75rem 0;
}

.battle-results .result-item {
  font-size: 0.875rem;
  margin: 0.25rem 0;
  font-weight: 600;
}

/* Loading States */
.loading-center {
  display: flex;
  justify-content: center;
  padding: 2rem 0;
}

.loading-spinner {
  width: 2rem;
  height: 2rem;
  border: 3px solid #f3f3f3;
  border-top: 3px solid #007bff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* Empty State */
.empty-state {
  text-align: center;
  padding: 3rem;
  color: #666;
  font-weight: 600;
}

/* Restrictions */
.restrictions {
  font-size: 0.75rem;
  color: #dc3545;
  margin-top: 0.5rem;
  font-weight: 700;
}

/* Neo-Brutalist Time Wheel */
.neo-wheel-container {
  display: flex;
  justify-content: center;
  margin: 2rem 0;
}

.neo-wheel-machine {
  background: #000;
  border: 6px solid #000;
  padding: 2rem;
  box-shadow: 12px 12px 0 #ff0066;
  transform: rotate(-2deg);
}

.neo-wheel-display {
  background: white;
  border: 4px solid #000;
  padding: 1.5rem;
  box-shadow: 8px 8px 0 #000;
  transform: rotate(2deg);
}

.neo-wheel-frame {
  position: relative;
  width: 280px;
  height: 280px;
  background: #ffc107;
  border: 4px solid #000;
  box-shadow: inset 4px 4px 0 #000;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Time Selector (Inner) */
.neo-time-selector {
  position: relative;
  width: 160px;
  height: 160px;
  background: white;
  border: 4px solid #000;
  box-shadow: 4px 4px 0 #000;
  z-index: 3;
}

.neo-time-selector.spinning {
  animation: neoSpinInner 2s ease-out forwards;
}

.neo-time-slot {
  position: absolute;
  width: 76px;
  height: 76px;
  background: #28a745;
  border: 3px solid #000;
  color: white;
  font-weight: 900;
  font-size: 0.875rem;
  text-transform: uppercase;
  letter-spacing: 1px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 2px 2px 0 #000;
}

.neo-time-slot-1 {
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  background: #007bff;
}

.neo-time-slot-2 {
  top: 50%;
  right: 0;
  transform: translateY(-50%);
  background: #28a745;
}

.neo-time-slot-3 {
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  background: #ffc107;
  color: #000;
}

.neo-time-slot-4 {
  top: 50%;
  left: 0;
  transform: translateY(-50%);
  background: #dc3545;
}

.neo-time-center {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: #000;
  color: white;
  padding: 0.5rem;
  border: 2px solid #000;
  font-weight: 900;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 1px;
  box-shadow: 2px 2px 0 rgba(0,0,0,0.3);
  z-index: 4;
}

/* Direction Selector (Outer) */
.neo-direction-selector {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 240px;
  height: 240px;
  z-index: 2;
}

.neo-direction-selector.spinning {
  animation: neoSpinOuter 3s ease-out forwards;
}

.neo-direction-slot {
  position: absolute;
  width: 60px;
  height: 60px;
  border: 4px solid #000;
  font-size: 2rem;
  font-weight: 900;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 4px 4px 0 #000;
  color: white;
}

.neo-direction-slot:nth-child(1) {
  top: 10px;
  left: 50%;
  transform: translateX(-50%);
}

.neo-direction-slot:nth-child(2) {
  top: 50%;
  right: 10px;
  transform: translateY(-50%);
}

.neo-direction-slot:nth-child(3) {
  bottom: 10px;
  left: 50%;
  transform: translateX(-50%);
}

.neo-direction-slot:nth-child(4) {
  top: 50%;
  left: 10px;
  transform: translateY(-50%);
}

.neo-direction-increase {
  background: #28a745;
}

.neo-direction-decrease {
  background: #dc3545;
}

/* Pointer */
.neo-wheel-pointer {
  position: absolute;
  top: -30px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 5;
}

.neo-pointer-arrow {
  background: #ff0066;
  color: white;
  padding: 0.5rem 1rem;
  border: 4px solid #000;
  font-size: 1.5rem;
  font-weight: 900;
  box-shadow: 4px 4px 0 #000;
  transform: rotate(45deg);
}

/* Status Display */
.neo-wheel-status {
  margin-top: 2rem;
  background: #000;
  border: 4px solid #000;
  padding: 1rem 2rem;
  box-shadow: 8px 8px 0 #ffc107;
  transform: rotate(1deg);
}

.neo-status-text {
  color: white;
  font-weight: 900;
  font-size: 1.25rem;
  text-transform: uppercase;
  letter-spacing: 2px;
  text-align: center;
  margin: 0;
}

/* Neo-Brutalist Animations */
@keyframes neoSpinInner {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(720deg);
  }
}

@keyframes neoSpinOuter {
  0% {
    transform: translate(-50%, -50%) rotate(0deg);
  }
  100% {
    transform: translate(-50%, -50%) rotate(-1080deg);
  }
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* Choice Buttons */
.choice-buttons {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.choice-buttons.small {
  grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.choice-btn {
  background: white;
  border: 3px solid #000;
  padding: 1rem;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 4px 4px 0 #000;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

.choice-btn:hover:not(:disabled) {
  transform: translate(-2px, -2px);
  box-shadow: 6px 6px 0 #000;
}

.choice-btn.selected {
  background: #007bff;
  color: white;
  transform: translate(-2px, -2px);
  box-shadow: 6px 6px 0 #000;
}

.choice-btn:disabled {
  background: #f5f5f5;
  color: #999;
  cursor: not-allowed;
  opacity: 0.6;
}

.choice-btn.small {
  padding: 0.75rem;
  font-size: 0.875rem;
}

.choice-icon {
  font-size: 2rem;
  display: block;
}

.choice-btn.small .choice-icon {
  font-size: 1.5rem;
}

.choice-name {
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  font-size: 0.875rem;
}

.choice-btn.small .choice-name {
  font-size: 0.75rem;
}

/* Join Game Section */
.join-game-section {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.join-choice-section {
  background: #f8f9fa;
  border: 3px solid #000;
  padding: 1.5rem;
  margin-top: 1rem;
}

.join-actions {
  display: flex;
  gap: 1rem;
  margin-top: 1rem;
}

.btn-primary.small,
.btn-secondary.small {
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  box-shadow: 3px 3px 0 #000;
}

.btn-primary.small:hover,
.btn-secondary.small:hover {
  transform: translate(1px, 1px);
  box-shadow: 2px 2px 0 #000;
}

/* Creator Info */
.creator-info {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  align-items: flex-end;
}

.creator-badge {
  background: #17a2b8;
  color: white;
  padding: 0.25rem 0.75rem;
  border: 2px solid #000;
  font-size: 0.75rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  box-shadow: 2px 2px 0 #000;
}

/* Battle Results */
.battle-results {
  background: #f8f9fa;
  border: 3px solid #000;
  padding: 1.5rem;
  margin-top: 1rem;
}

.battle-results h4 {
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 0 0 1rem 0;
  color: #000;
}

.result-item {
  background: white;
  border: 2px solid #000;
  padding: 0.75rem;
  margin: 0.5rem 0;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Cancel Button */
.btn-cancel {
  background: #dc3545;
  color: white;
  border: 3px solid #000;
  padding: 0.5rem 1rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  cursor: pointer;
  box-shadow: 3px 3px 0 #000;
  transition: all 0.2s ease;
  font-size: 0.875rem;
}

.btn-cancel:hover:not(:disabled) {
  transform: translate(1px, 1px);
  box-shadow: 2px 2px 0 #000;
}

.btn-cancel:disabled {
  background: #6c757d;
  cursor: not-allowed;
  opacity: 0.6;
}

/* Modal Styles */
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
  max-width: 600px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 12px 12px 0 #000;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 2rem;
  border-bottom: 3px solid #000;
  background: #f8f9fa;
}

.modal-title {
  font-size: 1.5rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0;
  color: #000;
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
  transition: all 0.2s ease;
}

.modal-close:hover {
  transform: translate(1px, 1px);
  box-shadow: 2px 2px 0 #000;
}

.modal-body {
  padding: 2rem;
}

.modal-footer {
  padding: 1.5rem 2rem;
  border-top: 3px solid #000;
  background: #f8f9fa;
  text-align: center;
}

.modal-btn {
  min-width: 120px;
}

/* Result Display */
.result-display {
  text-align: center;
  margin-bottom: 2rem;
}

.result-icon-large {
  font-size: 4rem;
  margin-bottom: 1rem;
}

.result-message-large {
  font-size: 1.25rem;
  font-weight: 700;
  color: #333;
  margin: 0;
}

/* Battle Details */
.battle-details {
  background: #f8f9fa;
  border: 3px solid #000;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
}

.battle-title {
  font-size: 1.1rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 1rem 0;
  color: #000;
}

.battle-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.battle-item {
  background: white;
  border: 2px solid #000;
  padding: 1rem;
  text-align: center;
  box-shadow: 3px 3px 0 #000;
}

.player-name {
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 0.5rem;
  color: #000;
}

.player-choice {
  font-size: 1.1rem;
  color: #333;
}

/* Result Stats */
.result-stats {
  display: grid;
  gap: 1rem;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border: 2px solid #000;
  background: white;
  box-shadow: 3px 3px 0 #000;
}

.stat-item.winner {
  background: #d4edda;
  border-color: #28a745;
  box-shadow: 3px 3px 0 #28a745;
}

.stat-item.coins {
  background: #fff3cd;
  border-color: #ffc107;
  box-shadow: 3px 3px 0 #ffc107;
}

.stat-label {
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #000;
}

.stat-value {
  font-weight: 700;
  font-size: 1.1rem;
}

.stat-value.positive {
  color: #28a745;
}

.stat-value.negative {
  color: #dc3545;
}

/* Mobile Responsive */
@media (max-width: 768px) {
  .game-header {
    padding: 1rem 0;
  }

  .header-content {
    flex-direction: column;
    gap: 1rem;
  }

  .game-title {
    font-size: 1.5rem;
  }

  .header-stats {
    flex-wrap: wrap;
    justify-content: center;
    gap: 0.5rem;
  }

  .game-tabs {
    gap: 0.5rem;
    padding: 0.75rem;
  }

  .game-tab {
    min-width: 100px;
    padding: 0.75rem 1rem;
    font-size: 0.875rem;
  }

  .game-section {
    padding: 1.25rem;
  }

  .section-title {
    font-size: 1.25rem;
  }

  .game-creation {
    flex-direction: column;
    align-items: stretch;
  }

  .game-card {
    flex-direction: column;
    align-items: stretch;
    gap: 1rem;
    padding: 1.25rem;
  }

  .result-content {
    flex-direction: column;
    text-align: center;
  }

  .modal-content {
    margin: 1rem;
    max-height: calc(100vh - 2rem);
  }

  .modal-header,
  .modal-body,
  .modal-footer {
    padding: 1.25rem;
  }

  .wheel-animation {
    width: 180px;
    height: 180px;
  }

  .inner-wheel {
    width: 100px;
    height: 100px;
  }

  .outer-wheel {
    width: 160px;
    height: 160px;
  }

  .inner-section {
    font-size: 0.75rem;
  }

  .outer-section {
    font-size: 1.5rem;
  }

  .neo-wheel-machine {
    padding: 1rem;
    transform: rotate(-1deg);
  }

  .neo-wheel-display {
    padding: 1rem;
    transform: rotate(1deg);
  }

  .neo-wheel-frame {
    width: 220px;
    height: 220px;
  }

  .neo-time-selector {
    width: 120px;
    height: 120px;
  }

  .neo-time-slot {
    width: 56px;
    height: 56px;
    font-size: 0.75rem;
  }

  .neo-time-center {
    padding: 0.25rem;
    font-size: 0.625rem;
  }

  .neo-direction-selector {
    width: 180px;
    height: 180px;
  }

  .neo-direction-slot {
    width: 45px;
    height: 45px;
    font-size: 1.5rem;
  }

  .neo-status-text {
    font-size: 1rem;
    letter-spacing: 1px;
  }

  .choice-buttons {
    grid-template-columns: 1fr;
    gap: 0.75rem;
  }

  .choice-btn {
    min-height: 48px;
  }

  .join-actions {
    flex-direction: column;
    gap: 0.75rem;
  }

  .btn-primary,
  .btn-secondary,
  .btn-cancel {
    min-height: 48px;
  }
}

/* Game iframe container */
.game-iframe-container {
  width: 100%;
  border: 4px solid #000;
  box-shadow: 8px 8px 0 #000;
  background: white;
  overflow: hidden;
  position: relative;
}

.game-iframe-container.fullscreen {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: 9999;
  border: none;
  box-shadow: none;
}

.game-iframe {
  width: 100%;
  height: 80vh;
  min-height: 600px;
  border: none;
  display: block;
}

.game-iframe.fullscreen {
  height: 100vh;
  min-height: 100vh;
}

/* Game header with actions */
.game-header-with-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
  margin-bottom: 0.5rem;
}

/* Fullscreen button */
.fullscreen-btn {
  background: #6c757d;
  color: white;
  border: 3px solid #000;
  padding: 0.5rem 1rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  cursor: pointer;
  box-shadow: 4px 4px 0 #000;
  transition: all 0.2s ease;
  font-size: 0.875rem;
}

.fullscreen-btn:hover {
  background: #495057;
  transform: translate(2px, 2px);
  box-shadow: 2px 2px 0 #000;
}

/* Fullscreen exit overlay button */
.fullscreen-exit-overlay {
  position: absolute;
  top: 1rem;
  right: 1rem;
  background: rgba(220, 53, 69, 0.9);
  color: white;
  border: 3px solid #000;
  padding: 0.75rem 1.25rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  cursor: pointer;
  box-shadow: 4px 4px 0 rgba(0, 0, 0, 0.5);
  transition: all 0.2s ease;
  font-size: 0.875rem;
  z-index: 10000;
}

.fullscreen-exit-overlay:hover {
  background: #c82333;
  transform: translate(2px, 2px);
  box-shadow: 2px 2px 0 rgba(0, 0, 0, 0.5);
}

/* Mobile responsive */
@media (max-width: 768px) {
  .game-iframe {
    height: 70vh;
    min-height: 400px;
  }

  .game-header-with-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .fullscreen-btn {
    width: 100%;
  }
}
</style>