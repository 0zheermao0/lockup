<template>
  <div class="dice-game">
    <!-- Game Creation Section -->
    <div class="game-section create-section">
      <div class="section-header">
        <h3 class="section-title">🎲 创建掷骰子游戏</h3>
      </div>

      <div class="create-form">
        <div class="form-group">
          <label class="form-label">参与费用 (积分)</label>
          <input
            v-model.number="createForm.bet_amount"
            type="number"
            min="1"
            class="form-input"
            placeholder="下注积分"
          />
        </div>

        <div class="form-group">
          <label class="form-label">奖励物品 (可选)</label>
          <select v-model="createForm.item_reward_id" class="form-select">
            <option value="">无奖励物品</option>
            <option
              v-for="item in availableItems"
              :key="item.id"
              :value="item.id"
            >
              {{ item.item_type.icon }} {{ item.item_type.display_name }}
            </option>
          </select>
        </div>

        <button
          @click="createGame"
          class="create-btn"
          :disabled="creating || !canCreate"
        >
          {{ creating ? '创建中...' : '🎲 创建游戏' }}
        </button>
      </div>
    </div>

    <!-- Available Games List -->
    <div class="game-section games-list-section">
      <div class="section-header">
        <h3 class="section-title">🎯 可参与的游戏</h3>
        <button @click="refreshGames" class="refresh-btn" :disabled="loading">
          {{ loading ? '刷新中...' : '🔄 刷新' }}
        </button>
      </div>

      <div v-if="loading && games.length === 0" class="loading-state">
        <div class="loading-spinner"></div>
        <p>加载游戏中...</p>
      </div>

      <div v-else-if="diceGames.length === 0" class="empty-state">
        <div class="empty-icon">🎲</div>
        <p class="empty-text">暂无可参与的掷骰子游戏</p>
        <p class="empty-hint">创建一个游戏开始玩吧！</p>
      </div>

      <div v-else class="games-grid">
        <div
          v-for="game in diceGames"
          :key="game.id"
          class="game-card"
          :class="{ 'joining': joiningGameId === game.id }"
        >
          <div class="game-header">
            <div class="creator-info">
              <UserAvatar :user="game.creator" size="small" />
              <span class="creator-name">{{ game.creator.username }}</span>
            </div>
            <div class="game-time">{{ formatDistanceToNow(game.created_at) }}</div>
          </div>

          <div class="game-details">
            <div class="bet-amount">
              <span class="bet-icon">🪙</span>
              <span class="bet-text">{{ game.bet_amount }} 积分</span>
            </div>

            <div v-if="getItemReward(game)" class="item-reward">
              <span class="reward-icon">{{ getItemReward(game).icon }}</span>
              <span class="reward-text">{{ getItemReward(game).display_name }}</span>
            </div>
            <div v-else class="no-reward">
              <span class="no-reward-text">无物品奖励</span>
            </div>
          </div>

          <div class="game-actions">
            <button
              v-if="canJoinGame(game)"
              @click="showJoinModal(game)"
              class="join-btn"
              :disabled="joiningGameId === game.id"
            >
              {{ joiningGameId === game.id ? '参与中...' : '🎯 参与游戏' }}
            </button>
            <div v-else-if="isCreator(game)" class="creator-actions">
              <span class="creator-badge">你的游戏</span>
              <button
                @click="cancelGame(game.id)"
                :disabled="cancelingGame"
                class="cancel-btn"
              >
                {{ cancelingGame ? '取消中...' : '❌ 取消游戏' }}
              </button>
            </div>
            <div v-else class="disabled-info">
              <span class="disabled-text">无法参与</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Join Game Modal -->
    <div v-if="showJoinGameModal" class="modal-overlay" @click="closeJoinModal">
      <div class="join-modal" @click.stop>
        <div class="modal-header">
          <h3 class="modal-title">🎲 参与掷骰子游戏</h3>
          <button @click="closeJoinModal" class="modal-close">×</button>
        </div>

        <div class="modal-body">
          <div class="game-info">
            <div class="info-row">
              <span class="info-label">创建者:</span>
              <span class="info-value">{{ selectedGame?.creator.username }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">参与费用:</span>
              <span class="info-value">{{ selectedGame?.bet_amount }} 积分</span>
            </div>
            <div class="info-row">
              <span class="info-label">物品奖励:</span>
              <span class="info-value">
                {{ getItemReward(selectedGame)?.display_name || '无' }}
              </span>
            </div>
          </div>

          <div class="guess-section">
            <h4 class="guess-title">选择您的猜测</h4>
            <div class="guess-options">
              <button
                @click="selectedGuess = 'small'"
                class="guess-btn"
                :class="{ 'selected': selectedGuess === 'small' }"
              >
                <span class="guess-icon">🔻</span>
                <span class="guess-text">小 (1,2,3)</span>
              </button>
              <button
                @click="selectedGuess = 'big'"
                class="guess-btn"
                :class="{ 'selected': selectedGuess === 'big' }"
              >
                <span class="guess-icon">🔺</span>
                <span class="guess-text">大 (4,5,6)</span>
              </button>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button @click="closeJoinModal" class="cancel-btn">取消</button>
          <button
            @click="joinGame"
            class="confirm-btn"
            :disabled="!selectedGuess || joining"
          >
            {{ joining ? '参与中...' : `确认参与 (-${selectedGame?.bet_amount} 积分)` }}
          </button>
        </div>
      </div>
    </div>

    <!-- Dice Result Modal -->
    <div v-if="showResultModal" class="modal-overlay" @click="closeResultModal">
      <div class="result-modal" @click.stop>
        <div class="modal-header">
          <h3 class="modal-title">🎲 掷骰子结果</h3>
          <button @click="closeResultModal" class="modal-close">×</button>
        </div>

        <div class="modal-body">
          <div class="dice-container">
            <div class="dice" :class="{ 'rolling': isRolling }">
              <div class="dice-face">{{ diceResult || '?' }}</div>
            </div>
          </div>

          <div class="result-info">
            <div class="result-summary">
              <div class="guess-result">
                您猜: <strong>{{ guessResult === 'big' ? '大' : '小' }}</strong>
              </div>
              <div class="dice-result">
                骰子: <strong>{{ diceResult }}</strong>
              </div>
              <div class="final-result" :class="{ 'win': isWin, 'lose': !isWin }">
                {{ isWin ? '🎉 猜中了！' : '😔 没猜中' }}
              </div>
            </div>

            <div v-if="gameResult" class="rewards-section">
              <div v-if="gameResult.item_received" class="item-received">
                <div class="reward-icon">🎁</div>
                <div class="reward-text">
                  获得奖励: {{ gameResult.item_received.display_name }}
                </div>
              </div>
              <div class="coins-info">
                <div class="coins-change">
                  剩余积分: {{ gameResult.remaining_coins }}
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button @click="closeResultModal" class="close-result-btn">确定</button>
        </div>
      </div>
    </div>

    <!-- Game Creation Result Modal -->
    <div v-if="showCreationModal" class="modal-overlay" @click="closeCreationModal">
      <div class="creation-modal" @click.stop>
        <div class="modal-header">
          <h3 class="modal-title">🎲 游戏创建成功</h3>
          <button @click="closeCreationModal" class="modal-close">×</button>
        </div>

        <div class="modal-body">
          <div class="creation-success">
            <div class="success-icon">✅</div>
            <p class="success-message">掷骰子游戏创建成功！</p>
          </div>

          <div class="dice-preview">
            <div class="dice-container">
              <div class="dice">
                <div class="dice-face">{{ createdGame?.game_data?.dice_result || '?' }}</div>
              </div>
            </div>
            <p class="dice-info">您的骰子点数：{{ createdGame?.game_data?.dice_result }}</p>
            <p class="dice-hint">
              {{ (createdGame?.game_data?.dice_result || 0) >= 4 ? '大 (4,5,6)' : '小 (1,2,3)' }}
            </p>
          </div>

          <div class="game-summary">
            <div class="summary-item">
              <span class="summary-label">参与费用:</span>
              <span class="summary-value">{{ createdGame?.bet_amount }} 积分</span>
            </div>
            <div v-if="getItemReward(createdGame)" class="summary-item">
              <span class="summary-label">奖励物品:</span>
              <span class="summary-value">
                {{ getItemReward(createdGame)?.icon }} {{ getItemReward(createdGame)?.display_name }}
              </span>
            </div>
            <div v-else class="summary-item">
              <span class="summary-label">奖励物品:</span>
              <span class="summary-value">无</span>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button @click="closeCreationModal" class="close-result-btn">确定</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import { storeApi } from '../lib/api'
import { formatDistanceToNow } from '../lib/utils'
import UserAvatar from './UserAvatar.vue'
import type { Game, Item, UserInventory } from '../types'

// Stores
const authStore = useAuthStore()

// Reactive data
const loading = ref(false)
const creating = ref(false)
const joining = ref(false)
const cancelingGame = ref(false)
const games = ref<Game[]>([])
const inventory = ref<UserInventory | null>(null)

// Game creation form
const createForm = ref({
  bet_amount: 1,
  item_reward_id: ''
})

// Join game modal
const showJoinGameModal = ref(false)
const selectedGame = ref<Game | null>(null)
const selectedGuess = ref<'big' | 'small' | ''>('')
const joiningGameId = ref<string | null>(null)

// Result modal
const showResultModal = ref(false)
const isRolling = ref(false)
const diceResult = ref<number | null>(null)
const guessResult = ref<'big' | 'small'>('big')
const isWin = ref(false)
const gameResult = ref<any>(null)

// Creation result modal
const showCreationModal = ref(false)
const createdGame = ref<any>(null)

// Computed properties
const diceGames = computed(() => {
  if (!Array.isArray(games.value)) {
    return []
  }
  return games.value.filter(game => game.game_type === 'dice' && game.status === 'waiting')
})

const availableItems = computed(() => {
  return inventory.value?.items?.filter(item => item.status === 'available') || []
})

const canCreate = computed(() => {
  return createForm.value.bet_amount >= 1
})

// Methods
const loadGames = async () => {
  try {
    loading.value = true
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
  } catch (error) {
    console.error('Failed to load games:', error)
    games.value = []
  } finally {
    loading.value = false
  }
}

const loadInventory = async () => {
  try {
    inventory.value = await storeApi.getUserInventory()
  } catch (error) {
    console.error('Failed to load inventory:', error)
  }
}

const refreshGames = () => {
  loadGames()
}

const createGame = async () => {
  if (!canCreate.value) return

  try {
    creating.value = true
    const game = await storeApi.createGame({
      game_type: 'dice',
      bet_amount: createForm.value.bet_amount,
      item_reward_id: createForm.value.item_reward_id || undefined
    })

    console.log('Created game:', game)
    console.log('Game data:', game.game_data)
    console.log('Dice result:', game.game_data?.dice_result)

    // Store the created game and show creation result
    createdGame.value = game
    showCreationModal.value = true

    // Reset form
    createForm.value = {
      bet_amount: 1,
      item_reward_id: ''
    }

    // Refresh games list
    await loadGames()

    // 注意：积分更新现在由API响应拦截器自动处理，无需手动刷新
  } catch (error: any) {
    console.error('Failed to create game:', error)
    alert(error.message || '创建游戏失败')
  } finally {
    creating.value = false
  }
}

const canJoinGame = (game: Game): boolean => {
  return game.creator.id !== authStore.user?.id &&
         (authStore.user?.coins || 0) >= game.bet_amount
}

const showJoinModal = (game: Game) => {
  selectedGame.value = game
  selectedGuess.value = ''
  showJoinGameModal.value = true
}

const closeJoinModal = () => {
  showJoinGameModal.value = false
  selectedGame.value = null
  selectedGuess.value = ''
}

const joinGame = async () => {
  if (!selectedGame.value || !selectedGuess.value) return

  try {
    joining.value = true
    joiningGameId.value = selectedGame.value.id

    const result = await storeApi.joinGame(selectedGame.value.id, {
      guess: selectedGuess.value
    })

    console.log('joinGame result:', result)

    // Close join modal
    closeJoinModal()

    // Show dice rolling animation
    showDiceResult(result)

    // Refresh games and user data
    await Promise.all([
      loadGames(),
      authStore.refreshUser()
    ])

  } catch (error: any) {
    console.error('Failed to join game:', error)
    alert(error.message || '参与游戏失败')
  } finally {
    joining.value = false
    joiningGameId.value = null
  }
}

const showDiceResult = (result: any) => {
  console.log('showDiceResult called with:', result)

  gameResult.value = result
  guessResult.value = result.guess
  isWin.value = result.is_correct

  showResultModal.value = true
  isRolling.value = true

  // Start dice rolling animation
  setTimeout(() => {
    isRolling.value = false
    diceResult.value = result.dice_result
    console.log('Dice animation finished, diceResult set to:', result.dice_result)
  }, 2000)
}

const closeResultModal = () => {
  showResultModal.value = false
  diceResult.value = null
  gameResult.value = null
  isRolling.value = false
}

const closeCreationModal = () => {
  showCreationModal.value = false
  createdGame.value = null
}

const getItemReward = (game?: Game | null) => {
  if (!game?.game_data?.item_reward_details) return null
  return game.game_data.item_reward_details
}

const isCreator = (game: Game): boolean => {
  return game.creator.id === authStore.user?.id
}

const cancelGame = async (gameId: string) => {
  if (cancelingGame.value) return

  try {
    cancelingGame.value = true

    const result = await storeApi.cancelGame(gameId)

    // 注意：积分更新现在由API响应拦截器自动处理，无需手动更新

    // Refresh games list and inventory
    await Promise.all([
      loadGames(),
      loadInventory()
    ])

    console.log(result.message)

  } catch (error: any) {
    console.error('Failed to cancel game:', error)
    alert(error.message || '取消游戏失败')
  } finally {
    cancelingGame.value = false
  }
}

// Lifecycle
onMounted(() => {
  Promise.all([
    loadGames(),
    loadInventory()
  ])
})
</script>

<style scoped>
.dice-game {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

/* Game Sections */
.game-section {
  background: white;
  border: 4px solid #000;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 6px 6px 0 #000;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.section-title {
  font-size: 1.25rem;
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
  padding: 0.5rem 1rem;
  border-radius: 4px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 3px 3px 0 #000;
}

.refresh-btn:hover:not(:disabled) {
  transform: translate(-1px, -1px);
  box-shadow: 4px 4px 0 #000;
}

.refresh-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Create Form */
.create-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-label {
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #333;
  font-size: 0.875rem;
}

.form-input,
.form-select {
  border: 3px solid #000;
  padding: 0.75rem;
  border-radius: 4px;
  font-weight: 600;
  background: white;
  color: #000;
}

.form-input:focus,
.form-select:focus {
  outline: none;
  box-shadow: 0 0 0 3px #007bff;
}

.create-btn {
  background: linear-gradient(135deg, #28a745, #20c997);
  color: white;
  border: 3px solid #000;
  padding: 1rem;
  border-radius: 6px;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  cursor: pointer;
  box-shadow: 4px 4px 0 #000;
  transition: all 0.2s ease;
}

.create-btn:hover:not(:disabled) {
  transform: translate(-2px, -2px);
  box-shadow: 6px 6px 0 #000;
}

.create-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Games Grid */
.games-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1rem;
}

.game-card {
  border: 3px solid #000;
  border-radius: 6px;
  padding: 1rem;
  background: white;
  transition: all 0.2s ease;
  box-shadow: 3px 3px 0 #000;
}

.game-card:hover {
  transform: translate(-1px, -1px);
  box-shadow: 4px 4px 0 #000;
}

.game-card.joining {
  opacity: 0.7;
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
  gap: 0.5rem;
}

.creator-name {
  font-weight: 700;
  color: #333;
}

.game-time {
  font-size: 0.75rem;
  color: #666;
}

.game-details {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.bet-amount,
.item-reward,
.no-reward {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  border: 2px solid #e9ecef;
  border-radius: 4px;
  background: #f8f9fa;
}

.bet-amount {
  border-color: #ffc107;
  background: #fff3cd;
}

.item-reward {
  border-color: #28a745;
  background: #d4edda;
}

.bet-icon,
.reward-icon {
  font-size: 1.25rem;
}

.bet-text,
.reward-text {
  font-weight: 700;
  color: #333;
}

.no-reward-text {
  color: #666;
  font-style: italic;
}

.join-btn {
  background: linear-gradient(135deg, #007bff, #0056b3);
  color: white;
  border: 3px solid #000;
  padding: 0.75rem;
  border-radius: 4px;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  cursor: pointer;
  box-shadow: 3px 3px 0 #000;
  transition: all 0.2s ease;
  width: 100%;
}

.join-btn:hover:not(:disabled) {
  transform: translate(-1px, -1px);
  box-shadow: 4px 4px 0 #000;
}

.join-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Loading and Empty States */
.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  text-align: center;
}

.loading-spinner {
  width: 3rem;
  height: 3rem;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #007bff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 1rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.empty-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
}

.empty-text {
  font-size: 1.25rem;
  font-weight: 700;
  color: #333;
  margin: 0 0 0.5rem 0;
}

.empty-hint {
  color: #666;
  margin: 0;
}

/* Modals */
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

.join-modal,
.result-modal {
  background: white;
  border: 4px solid #000;
  border-radius: 8px;
  box-shadow: 12px 12px 0 #000;
  max-width: 500px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
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
  letter-spacing: 1px;
  margin: 0;
  color: #000;
}

.modal-close {
  background: #dc3545;
  color: white;
  border: 3px solid #000;
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 50%;
  font-size: 1.25rem;
  font-weight: 900;
  cursor: pointer;
  box-shadow: 3px 3px 0 #000;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-close:hover {
  transform: translate(1px, 1px);
  box-shadow: 2px 2px 0 #000;
}

.modal-body {
  padding: 1.5rem;
}

.modal-footer {
  padding: 1.5rem;
  border-top: 3px solid #000;
  background: #f8f9fa;
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
}

/* Join Modal Specific */
.game-info {
  background: #e8f4f8;
  border: 3px solid #17a2b8;
  padding: 1rem;
  border-radius: 4px;
  margin-bottom: 1.5rem;
}

.info-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.info-row:last-child {
  margin-bottom: 0;
}

.info-label {
  font-weight: 700;
  color: #333;
}

.info-value {
  font-weight: 600;
  color: #000;
}

.guess-section {
  margin-bottom: 1rem;
}

.guess-title {
  font-size: 1rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 1rem 0;
  color: #000;
}

.guess-options {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.guess-btn {
  background: white;
  border: 3px solid #000;
  padding: 1rem;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  box-shadow: 3px 3px 0 #000;
}

.guess-btn:hover {
  transform: translate(-1px, -1px);
  box-shadow: 4px 4px 0 #000;
}

.guess-btn.selected {
  background: #007bff;
  color: white;
}

.guess-icon {
  font-size: 2rem;
}

.guess-text {
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.cancel-btn,
.confirm-btn,
.close-result-btn {
  padding: 0.75rem 1.5rem;
  border: 3px solid #000;
  border-radius: 4px;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  cursor: pointer;
  box-shadow: 3px 3px 0 #000;
  transition: all 0.2s ease;
}

.cancel-btn {
  background: #6c757d;
  color: white;
}

.confirm-btn,
.close-result-btn {
  background: #28a745;
  color: white;
}

.cancel-btn:hover,
.confirm-btn:hover:not(:disabled),
.close-result-btn:hover {
  transform: translate(-1px, -1px);
  box-shadow: 4px 4px 0 #000;
}

.confirm-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Dice Animation */
.dice-container {
  display: flex;
  justify-content: center;
  margin-bottom: 2rem;
}

.dice {
  width: 120px;
  height: 120px;
  border: 4px solid #000;
  border-radius: 12px;
  background: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 4rem;
  font-weight: 900;
  box-shadow: 6px 6px 0 #000;
  transition: all 0.3s ease;
}

.dice.rolling {
  animation: diceRoll 2s ease-in-out;
}

@keyframes diceRoll {
  0% { transform: rotate(0deg) scale(1); }
  25% { transform: rotate(90deg) scale(1.1); }
  50% { transform: rotate(180deg) scale(1.2); }
  75% { transform: rotate(270deg) scale(1.1); }
  100% { transform: rotate(360deg) scale(1); }
}

.dice-face {
  color: #000;
}

/* Result Info */
.result-info {
  text-align: center;
}

.result-summary {
  margin-bottom: 1.5rem;
}

.guess-result,
.dice-result {
  font-size: 1.1rem;
  margin-bottom: 0.5rem;
}

.final-result {
  font-size: 1.5rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  padding: 1rem;
  border-radius: 6px;
  margin-top: 1rem;
}

.final-result.win {
  background: #d4edda;
  color: #155724;
  border: 3px solid #28a745;
}

.final-result.lose {
  background: #f8d7da;
  color: #721c24;
  border: 3px solid #dc3545;
}

.rewards-section {
  background: #e8f4f8;
  border: 3px solid #17a2b8;
  padding: 1rem;
  border-radius: 4px;
}

.item-received {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  margin-bottom: 1rem;
  padding: 1rem;
  background: #d4edda;
  border: 2px solid #28a745;
  border-radius: 4px;
}

.reward-icon {
  font-size: 2rem;
}

.reward-text {
  font-weight: 700;
  color: #155724;
}

.coins-info {
  font-weight: 700;
  color: #0c5460;
}

/* Creation Modal */
.creation-modal {
  background: white;
  border: 4px solid #000;
  border-radius: 8px;
  box-shadow: 12px 12px 0 #000;
  max-width: 500px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
}

.creation-success {
  text-align: center;
  margin-bottom: 2rem;
}

.success-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
}

.success-message {
  font-size: 1.25rem;
  font-weight: 700;
  color: #28a745;
  margin: 0;
}

.dice-preview {
  text-align: center;
  margin-bottom: 2rem;
  background: #f8f9fa;
  border: 3px solid #000;
  padding: 1.5rem;
  border-radius: 6px;
}

.dice-preview .dice-container {
  display: flex;
  justify-content: center;
  margin-bottom: 1rem;
}

.dice-preview .dice {
  width: 80px;
  height: 80px;
  border: 4px solid #000;
  border-radius: 8px;
  background: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2.5rem;
  font-weight: 900;
  box-shadow: 4px 4px 0 #000;
}

.dice-info {
  font-size: 1.1rem;
  font-weight: 700;
  color: #333;
  margin: 0.5rem 0;
}

.dice-hint {
  font-size: 0.9rem;
  color: #666;
  font-weight: 600;
  margin: 0;
}

.game-summary {
  background: #e8f4f8;
  border: 3px solid #17a2b8;
  padding: 1rem;
  border-radius: 4px;
}

.summary-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.summary-item:last-child {
  margin-bottom: 0;
}

.summary-label {
  font-weight: 700;
  color: #333;
}

.summary-value {
  font-weight: 600;
  color: #000;
}

/* Creator Actions */
.creator-actions {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  align-items: flex-end;
}

.creator-badge {
  background: #17a2b8;
  color: white;
  padding: 0.25rem 0.75rem;
  border: 2px solid #000;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  box-shadow: 2px 2px 0 #000;
}

.cancel-btn {
  background: #dc3545;
  color: white;
  border: 3px solid #000;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  cursor: pointer;
  box-shadow: 3px 3px 0 #000;
  transition: all 0.2s ease;
  font-size: 0.875rem;
}

.cancel-btn:hover:not(:disabled) {
  transform: translate(-1px, -1px);
  box-shadow: 4px 4px 0 #000;
}

.cancel-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.disabled-info {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.75rem;
  background: #f8f9fa;
  border: 2px solid #dee2e6;
  border-radius: 4px;
}

.disabled-text {
  color: #6c757d;
  font-weight: 600;
  font-style: italic;
}

/* Mobile Responsive */
@media (max-width: 768px) {
  .games-grid {
    grid-template-columns: 1fr;
  }

  .guess-options {
    grid-template-columns: 1fr;
  }

  .modal-footer {
    flex-direction: column;
  }

  .dice {
    width: 100px;
    height: 100px;
    font-size: 3rem;
  }
}
</style>