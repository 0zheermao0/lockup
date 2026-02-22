<template>
  <div class="explore-view">
    <!-- Header -->
    <header class="explore-header">
      <div class="header-content">
        <button @click="goBack" class="back-btn">
          ← 返回
        </button>
        <h1 class="explore-title">🗺️ 神秘探索</h1>
        <div class="header-actions">
          <router-link to="/inventory" class="action-btn inventory">
            🎒 背包 ({{ inventory?.used_slots || 0 }}/{{ inventory?.max_slots || 6 }})
          </router-link>
          <router-link to="/store" class="action-btn store">
            🛍️ 商店
          </router-link>
        </div>
      </div>
    </header>

    <div class="container">

      <!-- Exploration zones -->
      <div class="zones-section">
        <h2 class="section-title">🗺️ 探索区域</h2>

        <!-- Loading zones -->
        <div v-if="loadingZones" class="loading-center">
          <div class="loading-box">
            <div class="loading-spinner"></div>
            <p class="loading-text">加载探索区域中...</p>
          </div>
        </div>

        <!-- Zones grid -->
        <div v-else class="zones-grid">
          <div
            v-for="zone in zones"
            :key="zone.name"
            class="zone-card"
          >
            <div class="zone-header">
              <div class="zone-info">
                <h3>{{ zone.display_name }}</h3>
                <p class="zone-description">{{ zone.description }}</p>
              </div>
              <div :class="['difficulty-badge', getZoneDifficulty(zone.name)]">
                {{ getDifficultyText(getZoneDifficulty(zone.name)) }}
              </div>
            </div>

            <div class="zone-stats">
              <p>
                💎 宝物数量: {{ zone.treasure_count }}
              </p>
              <p>
                🃏 卡牌数量: {{ getZoneCardCount(zone.name) }}张
              </p>
              <p>
                💰 探索费用: {{ zone.next_cost || 1 }}积分
              </p>
            </div>

            <button
              @click="startCardExploration(zone.name)"
              :disabled="exploring || userCoins < (zone.next_cost || 1) || zone.is_cooldown"
              class="explore-btn"
              :class="{ disabled: exploring || userCoins < (zone.next_cost || 1) || zone.is_cooldown }"
            >
              <span v-if="exploring && exploringZone === zone.name">探索中...</span>
              <span v-else-if="zone.is_cooldown">冷却中 ({{ zoneCooldowns[zone.name] || zone.cooldown_seconds }}s)</span>
              <span v-else>🃏 开始探索 ({{ zone.next_cost || 1 }}积分)</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Card Exploration Modal -->
      <div v-if="cardExploration" class="modal-overlay" @click="closeCardExploration">
        <div class="card-exploration-modal" @click.stop>
          <div class="modal-header">
            <h3 class="modal-title">🃏 {{ getZoneDisplayName(cardExploration.zone) }} 探索</h3>
            <div class="exploration-info">
              <span class="difficulty-badge" :class="cardExploration.difficulty">
                {{ getDifficultyText(cardExploration.difficulty) }}
              </span>
              <span class="cost-info">💰 花费{{ explorationResult?.cost || explorationResult?.exploration_cost || cardExploration?.next_cost || 1 }}积分</span>
            </div>
            <button @click="closeCardExploration" class="modal-close">×</button>
          </div>

          <div class="modal-body">
            <div
              class="cards-grid"
              :data-count="cardExploration?.cards?.length || 6"
            >
              <div
                v-for="card in cardExploration.cards"
                :key="card.position"
                :class="['card-slot', {
                  'revealed': card.revealed,
                  'treasure': card.has_treasure && card.revealed,
                  'selected': card.revealed && explorationResult?.selected_position === card.position
                }]"
                @click="selectCard(card)"
              >
                <div v-if="card.revealed" class="card-content revealed">
                  <div v-if="card.has_treasure" class="treasure-content">
                    <div class="treasure-icon" :class="{ 'found': card.is_found }">
                      {{ card.is_found ? '✅' : '💎' }}
                    </div>
                    <div class="treasure-info">
                      <h4>{{ card.item_type }}</h4>
                      <p class="treasure-hint">💭 {{ card.location_hint }}</p>
                      <div class="treasure-meta">
                        <span class="difficulty-mini" :class="card.difficulty">
                          {{ getDifficultyText(card.difficulty) }}
                        </span>
                        <span>掩埋者: {{ card.burier }}</span>
                        <span v-if="card.is_found" class="found-status">已找到</span>
                      </div>
                    </div>
                  </div>
                  <div v-else class="empty-content">
                    <div class="empty-icon">{{ card.position === explorationResult?.selected_position ? '😞' : '😔' }}</div>
                    <p>{{ card.position === explorationResult?.selected_position ? '你选择的位置' : '这里什么都没有' }}</p>
                  </div>
                </div>
                <div v-else class="card-content hidden">
                  <div class="card-back">🃏</div>
                  <p class="card-hint">点击翻开</p>
                </div>
              </div>
            </div>
          </div>

          <div class="modal-footer">
            <button @click="resetExploration" class="modal-btn secondary">
              🔄 重新探索
            </button>
          </div>
        </div>
      </div>

      <!-- Exploration result modal -->
      <div v-if="explorationResult" class="modal-overlay" @click="closeExplorationResult">
        <div class="exploration-result-modal" @click.stop>
          <div class="modal-header">
            <h3 class="modal-title">
              {{ explorationResult.success ? '🎉 探索成功！' : '😔 探索结束' }}
            </h3>
            <button @click="closeExplorationResult" class="modal-close">×</button>
          </div>

          <div class="modal-body">
            <div class="result-summary">
              <p class="result-message">{{ explorationResult.message }}</p>
              <div class="result-stats">
                <div class="stat-item">
                  <span class="stat-label">探索区域:</span>
                  <span class="stat-value">{{ getZoneDisplayName(explorationResult.zone) }}</span>
                </div>
                <div class="stat-item">
                  <span class="stat-label">难度:</span>
                  <span class="stat-value">{{ getDifficultyText(explorationResult.difficulty) }}</span>
                </div>
                <div class="stat-item">
                  <span class="stat-label">花费:</span>
                  <span class="stat-value">💰 {{ explorationResult?.cost || explorationResult?.exploration_cost || 1 }}积分</span>
                </div>
                <div class="stat-item">
                  <span class="stat-label">宝物数量:</span>
                  <span class="stat-value">{{ explorationResult.treasure_count }}个</span>
                </div>
              </div>
            </div>

            <!-- Found item display -->
            <div v-if="explorationResult.found_item" class="found-item-display">
              <h4 class="found-title">📦 获得的物品</h4>
              <div class="item-info">
                <span class="item-icon">{{ getItemIcon(explorationResult.found_item.type) }}</span>
                <div class="item-details">
                  <h5>{{ explorationResult.found_item.type }}</h5>
                  <div v-if="Object.keys(explorationResult.found_item.properties).length > 0" class="item-properties">
                    <pre>{{ JSON.stringify(explorationResult.found_item.properties, null, 2) }}</pre>
                  </div>
                </div>
              </div>
            </div>

            <!-- All cards reveal -->
            <div class="cards-reveal-section">
              <h4 class="reveal-title">🃏 所有卡牌结果</h4>
              <div
                class="mini-cards-grid"
                :data-count="explorationResult.card_count"
              >
                <div
                  v-for="card in explorationResult.cards"
                  :key="card.position"
                  :class="['mini-card', {
                    'has-treasure': card.has_treasure,
                    'is-selected': card.position === explorationResult.selected_position,
                    'is-found': card.is_found
                  }]"
                >
                  <div class="mini-card-content">
                    <div v-if="card.has_treasure" class="mini-treasure-icon">
                      {{ card.is_found ? '✅' : '💎' }}
                    </div>
                    <div v-else class="mini-empty-icon">❌</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="modal-footer">
            <button @click="closeExplorationResult" class="modal-btn primary">
              确定
            </button>
          </div>
        </div>
      </div>

      <!-- My buried treasures -->
      <div class="my-treasures-section">
        <div class="treasures-header">
          <h2 class="section-title">🗝️ 我的掩埋物品</h2>
          <button @click="loadMyTreasures" class="refresh-btn">
            刷新
          </button>
        </div>

        <!-- Loading treasures -->
        <div v-if="loadingTreasures" class="loading-center">
          <div class="loading-box">
            <div class="loading-spinner"></div>
            <p class="loading-text">加载我的宝物中...</p>
          </div>
        </div>

        <!-- Treasures list -->
        <div v-else-if="myTreasures.length > 0" class="my-treasures-list">
          <div
            v-for="treasure in myTreasures"
            :key="treasure.id"
            class="my-treasure-card"
          >
            <div class="my-treasure-header">
              <div class="treasure-main-info">
                <div class="treasure-title">
                  <span class="my-treasure-icon">{{ getItemIcon(treasure.item.item_type.name) }}</span>
                  <span class="my-treasure-name">{{ treasure.item.item_type.display_name }}</span>
                </div>
                <div :class="['status-badge', treasure.status]">
                  {{ getStatusText(treasure.status) }}
                </div>
              </div>
            </div>
            <div class="my-treasure-details">
              <div class="detail-item">
                <span class="detail-label">区域:</span>
                <span class="detail-value">{{ getZoneDisplayName(treasure.location_zone) }}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">提示:</span>
                <span class="detail-value">{{ treasure.location_hint }}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">难度:</span>
                <span class="detail-value">{{ getDifficultyText(treasure.difficulty) }}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">掩埋时间:</span>
                <span class="detail-value">{{ formatDate(treasure.created_at) }}</span>
              </div>
              <div v-if="treasure.found_at" class="detail-item">
                <span class="detail-label">发现时间:</span>
                <span class="detail-value">{{ formatDate(treasure.found_at) }}</span>
              </div>
              <div v-if="treasure.finder" class="detail-item">
                <span class="detail-label">发现者:</span>
                <span class="detail-value">{{ treasure.finder.username }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- No treasures -->
        <div v-else class="empty-my-treasures">
          <div class="empty-title">🏜️ 暂无掩埋物品</div>
          <p class="empty-message">你还没有掩埋任何物品</p>
          <router-link to="/inventory" class="empty-action-btn">
            去背包掩埋物品
          </router-link>
        </div>
      </div>

      <!-- Inventory Full Modal -->
      <div v-if="showInventoryFullModal" class="modal-overlay" @click="closeInventoryFullModal">
        <div class="inventory-full-modal" @click.stop>
          <div class="modal-header">
            <h3 class="modal-title">🎒 背包已满！</h3>
            <button @click="closeInventoryFullModal" class="modal-close">×</button>
          </div>

          <div class="modal-body">
            <div class="warning-section">
              <div class="warning-icon">⚠️</div>
              <div class="warning-content">
                <h4 class="warning-title">无法获得宝物</h4>
                <p class="warning-message">
                  你的背包已满，无法放入新的宝物！
                </p>
                <p class="warning-note">
                  请先清理背包或丢弃一些物品来腾出空间。
                </p>
              </div>
            </div>

            <div class="inventory-status">
              <div class="status-info">
                <span class="status-label">当前容量:</span>
                <span class="status-value">
                  {{ inventory?.used_slots || 0 }}/{{ inventory?.max_slots || 6 }}
                </span>
              </div>
              <div class="status-info">
                <span class="status-label">剩余空间:</span>
                <span class="status-value critical">
                  {{ inventory?.available_slots || 0 }} 格
                </span>
              </div>
            </div>
          </div>

          <div class="modal-footer">
            <button @click="closeInventoryFullModal" class="modal-btn secondary">
              稍后再挖
            </button>
            <button @click="openInventoryToDiscard" class="modal-btn primary">
              🎒 打开背包整理
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { storeApi } from '../lib/api'
import { useAuthStore } from '../stores/auth'
import { smartGoBack } from '../utils/navigation'
import { useNotificationToast } from '../composables/NotificationToast'
import { ApiError } from '../lib/api-commons'
import type { ExplorationZone, BuriedTreasure, UserInventory } from '../types'

const { showNotification } = useNotificationToast()

const router = useRouter()

// Reactive data
const zones = ref<ExplorationZone[]>([])
const myTreasures = ref<BuriedTreasure[]>([])
const explorationResult = ref<any>(null)
const treasureResult = ref<any>(null)
const cardExploration = ref<any>(null)
const inventory = ref<UserInventory | null>(null)

// Loading states
const loadingZones = ref(false)
const loadingTreasures = ref(false)
const exploring = ref(false)
const exploringZone = ref('')

// User coins
const authStore = useAuthStore()
const userCoins = computed(() => authStore.user?.coins || 0)

// Inventory management states
const showInventoryFullModal = ref(false)
const pendingTreasureResult = ref<any>(null)
const digging = ref(false)
const diggingTreasureId = ref('')

// Cooldown timer states
const zoneCooldowns = ref<Record<string, number>>({})
const cooldownIntervals = ref<Record<string, number>>({})

// Methods
const goBack = () => {
  smartGoBack(router, { defaultRoute: 'home' })
}
const loadZones = async () => {
  try {
    loadingZones.value = true
    const result = await storeApi.getAvailableZones()
    zones.value = result.zones

    // Initialize cooldown timers for zones in cooldown
    result.zones.forEach((zone: ExplorationZone) => {
      if (zone.is_cooldown && zone.cooldown_seconds > 0) {
        startCooldownTimer(zone.name, zone.cooldown_seconds)
      }
    })
  } catch (err) {
    console.error('Load zones error:', err)
  } finally {
    loadingZones.value = false
  }
}

const startCooldownTimer = (zoneName: string, seconds: number) => {
  zoneCooldowns.value[zoneName] = seconds

  if (cooldownIntervals.value[zoneName]) {
    clearInterval(cooldownIntervals.value[zoneName])
  }

  cooldownIntervals.value[zoneName] = setInterval(() => {
    if ((zoneCooldowns.value[zoneName] ?? 0) > 0) {
      zoneCooldowns.value[zoneName]!--
    } else {
      clearInterval(cooldownIntervals.value[zoneName])
      // Update zone state when cooldown ends
      const zone = zones.value.find(z => z.name === zoneName)
      if (zone) {
        zone.is_cooldown = false
      }
    }
  }, 1000)
}

const getFibonacciCost = (n: number): number => {
  if (n <= 0) return 1
  if (n <= 2) return 1
  let a = 1, b = 1
  for (let i = 3; i <= n; i++) {
    [a, b] = [b, a + b]
  }
  return b
}

const loadMyTreasures = async () => {
  try {
    loadingTreasures.value = true
    myTreasures.value = await storeApi.getBuriedTreasures()
  } catch (err) {
    console.error('Load treasures error:', err)
  } finally {
    loadingTreasures.value = false
  }
}

const loadInventory = async () => {
  try {
    inventory.value = await storeApi.getUserInventory()
  } catch (err) {
    console.error('Load inventory error:', err)
  }
}

// New card exploration methods
const getZoneDifficulty = (zoneName: string): string => {
  const zoneDifficulties = {
    'beach': 'easy',
    'forest': 'normal',
    'mountain': 'hard',
    'desert': 'normal',
    'cave': 'hard'
  }
  return zoneDifficulties[zoneName as keyof typeof zoneDifficulties] || 'normal'
}

const getZoneCardCount = (zoneName: string): number => {
  const zoneCardCounts = {
    'beach': 3,
    'forest': 6,
    'mountain': 9,
    'desert': 6,
    'cave': 9
  }
  return zoneCardCounts[zoneName as keyof typeof zoneCardCounts] || 6
}

const startCardExploration = async (zoneName: string) => {
  if (exploring.value) return

  try {
    exploring.value = true
    exploringZone.value = zoneName
    cardExploration.value = null
    treasureResult.value = null
    explorationResult.value = null

    // Generate preview cards (all hidden)
    const cardCount = getZoneCardCount(zoneName)
    const previewCards = Array.from({ length: cardCount }, (_, i) => ({
      position: i,
      has_treasure: false,
      revealed: false
    }))

    cardExploration.value = {
      zone: zoneName,
      difficulty: getZoneDifficulty(zoneName),
      card_count: cardCount,
      cards: previewCards,
      treasure_count: 0,
      cost: 1
    }

  } catch (err) {
    console.error('Card exploration error:', err)
  } finally {
    exploring.value = false
    exploringZone.value = ''
  }
}

const selectCard = async (card: any) => {
  if (exploring.value || card.revealed) return

  try {
    exploring.value = true
    // DON'T reveal card here - wait for API response

    const result = await storeApi.exploreZone(cardExploration.value.zone, card.position)

    // NOW reveal the card after successful API call
    card.revealed = true

    // Update zone cooldown after exploration
    const zone = zones.value.find(z => z.name === cardExploration.value.zone)
    if (zone) {
      zone.is_cooldown = true
      zone.cooldown_seconds = result.cooldown_remaining || 30
      zone.today_count = result.today_count || zone.today_count
      zone.next_cost = result.next_cost || getFibonacciCost((result.today_count || 0) + 1)
      startCooldownTimer(zone.name, zone.cooldown_seconds)
    }

    // Update with actual results
    explorationResult.value = result
    treasureResult.value = result.found_item ? {
      message: result.success ? '🎉 恭喜！你找到了宝物！' : '很遗憾，这里什么都没有',
      item: result.found_item,
      reward_to_burier: result.success ? getRewardAmount(result.difficulty) : 0,
      remaining_slots: 0 // Will be updated after refresh
    } : {
      message: '很遗憾，这里什么都没有'
    }

    // Update cards with real data
    cardExploration.value.cards = result.cards.map(c => ({ ...c, revealed: true }))

    // Refresh user coins and inventory
    await authStore.refreshUser()
    await loadInventory()

  } catch (err) {
    // Handle ApiError with cooldown info
    if (err instanceof ApiError && err.status === 429) {
      const cooldownSeconds = err.data?.cooldown_seconds || 30
      showNotification(`探索冷却中，请等待 ${cooldownSeconds} 秒后再试`, 'warning')

      // Update zone cooldown state
      const zone = zones.value.find(z => z.name === cardExploration.value.zone)
      if (zone) {
        zone.is_cooldown = true
        zone.cooldown_seconds = cooldownSeconds
        startCooldownTimer(zone.name, cooldownSeconds)
      }
    } else {
      const errorMessage = err instanceof ApiError ? err.message : '探索失败，请重试'
      showNotification(errorMessage, 'error')
    }

    // Don't reveal card on error
    card.revealed = false
  } finally {
    exploring.value = false
  }
}

const resetExploration = () => {
  cardExploration.value = null
  treasureResult.value = null
  explorationResult.value = null
}

const closeExplorationResult = () => {
  explorationResult.value = null
  cardExploration.value = null
}

const closeCardExploration = () => {
  cardExploration.value = null
  treasureResult.value = null
  explorationResult.value = null
}

const getRewardAmount = (difficulty: string): number => {
  const rewards = {
    'easy': 5,
    'normal': 10,
    'hard': 20
  }
  return rewards[difficulty as keyof typeof rewards] || 10
}

const exploreZone = async (zoneName: string) => {
  if (exploring.value) return

  try {
    exploring.value = true
    exploringZone.value = zoneName
    explorationResult.value = null
    treasureResult.value = null

    const result = await storeApi.exploreZone(zoneName, 0) // Default card position
    explorationResult.value = result

  } catch (err) {
    console.error('Explore zone error:', err)
  } finally {
    exploring.value = false
    exploringZone.value = ''
  }
}


// Helper methods
const getDifficultyText = (difficulty: string): string => {
  const difficulties = {
    'easy': '简单',
    'normal': '普通',
    'hard': '困难'
  }
  return difficulties[difficulty as keyof typeof difficulties] || difficulty
}

const getDifficultyClass = (difficulty: string): string => {
  const classes = {
    'easy': 'bg-green-100 text-green-800',
    'normal': 'bg-yellow-100 text-yellow-800',
    'hard': 'bg-red-100 text-red-800'
  }
  return classes[difficulty as keyof typeof classes] || 'bg-gray-100 text-gray-800'
}

const getStatusText = (status: string): string => {
  const statuses = {
    'buried': '已掩埋',
    'found': '已发现',
    'expired': '已过期'
  }
  return statuses[status as keyof typeof statuses] || status
}

const getStatusClass = (status: string): string => {
  const classes = {
    'buried': 'bg-blue-100 text-blue-800',
    'found': 'bg-green-100 text-green-800',
    'expired': 'bg-gray-100 text-gray-800'
  }
  return classes[status as keyof typeof classes] || 'bg-gray-100 text-gray-800'
}

const getItemIcon = (itemType: string): string => {
  const icons = {
    'photo_paper': '📄',
    'photo': '📷',
    'drift_bottle': '🍾',
    'key': '🗝️',
    'note': '📝'
  }
  return icons[itemType as keyof typeof icons] || '📦'
}

const getZoneDisplayName = (zoneName: string): string => {
  const zoneNames = {
    'forest': '神秘森林',
    'mountain': '雾山',
    'beach': '月光海滩',
    'desert': '沙漠绿洲',
    'cave': '深邃洞穴'
  }
  return zoneNames[zoneName as keyof typeof zoneNames] || zoneName
}

const formatDate = (dateString: string): string => {
  return new Date(dateString).toLocaleString('zh-CN')
}

// Inventory management methods
const closeInventoryFullModal = () => {
  showInventoryFullModal.value = false
  pendingTreasureResult.value = null
  digging.value = false
  diggingTreasureId.value = ''
}

const openInventoryToDiscard = () => {
  closeInventoryFullModal()
  // Navigate to inventory view
  window.location.href = '/inventory'
}

const retryDigAfterSpace = async () => {
  if (!pendingTreasureResult.value) return

  // Check if there's space now
  await loadInventory()
  if (inventory.value && inventory.value.available_slots < 1) {
    // Still no space
    return
  }

  // There's space now, proceed with treasure digging
  try {
    const result = await storeApi.findTreasure(pendingTreasureResult.value.treasureId)
    treasureResult.value = result

    // Update inventory display
    await loadInventory()

    // Remove found treasure from exploration results
    if (explorationResult.value) {
      explorationResult.value.treasures_found = explorationResult.value.treasures_found.filter(
        (t: any) => t.treasure_id !== pendingTreasureResult.value.treasureId
      )
    }

    // Refresh zones to update treasure counts
    loadZones()

    closeInventoryFullModal()

  } catch (err) {
    console.error('Find treasure retry error:', err)
    closeInventoryFullModal()
  }
}

// Lifecycle
onMounted(() => {
  loadZones()
  loadMyTreasures()
  loadInventory()
})

onUnmounted(() => {
  Object.values(cooldownIntervals.value).forEach(interval => {
    clearInterval(interval)
  })
})
</script>

<style scoped>
/* Neo-Brutalism Explore Design */
.explore-view {
  min-height: 100vh;
  background-color: #f5f5f5;
}

/* Header */
.explore-header {
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

.explore-title {
  font-size: 2rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 2px;
  margin: 0;
  color: #000;
}

.header-actions {
  display: flex;
  gap: 1rem;
}

.action-btn {
  padding: 0.75rem 1.5rem;
  border: 3px solid #000;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  text-decoration: none;
  box-shadow: 4px 4px 0 #000;
  transition: all 0.2s ease;
}

.action-btn.inventory {
  background: #17a2b8;
  color: white;
}

.action-btn.store {
  background: #28a745;
  color: white;
}

.action-btn:hover {
  transform: translate(2px, 2px);
  box-shadow: 2px 2px 0 #000;
}

/* Container */
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem 1rem;
}

/* Section Titles */
.section-title {
  font-size: 1.5rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 1.5rem 0;
  color: #000;
  background: white;
  padding: 1rem 2rem;
  border: 4px solid #000;
  box-shadow: 8px 8px 0 #000;
  display: inline-block;
}

/* Loading States */
.loading-center {
  display: flex;
  justify-content: center;
  padding: 3rem 0;
}

.loading-box {
  background: white;
  border: 4px solid #000;
  padding: 3rem;
  text-align: center;
  box-shadow: 8px 8px 0 #000;
}

.loading-spinner {
  width: 3rem;
  height: 3rem;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #007bff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 1rem;
}

.loading-text {
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0;
  color: #000;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* Zone Grid */
.zones-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 2rem;
  margin-bottom: 3rem;
}

/* Zone Cards */
.zone-card {
  background: white;
  border: 4px solid #000;
  padding: 2rem;
  box-shadow: 8px 8px 0 #000;
  transition: all 0.2s ease;
}

.zone-card:hover {
  transform: translate(-2px, -2px);
  box-shadow: 12px 12px 0 #000;
}

.zone-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.5rem;
}

.zone-info h3 {
  font-size: 1.25rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 0.5rem 0;
  color: #000;
}

.zone-description {
  color: #666;
  font-size: 0.875rem;
  font-weight: 500;
}

.difficulty-badge {
  padding: 0.5rem 1rem;
  border: 2px solid #000;
  font-size: 0.75rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  box-shadow: 3px 3px 0 #000;
}

.difficulty-badge.easy {
  background: #28a745;
  color: white;
}

.difficulty-badge.normal {
  background: #ffc107;
  color: #000;
}

.difficulty-badge.hard {
  background: #dc3545;
  color: white;
}

.zone-stats {
  margin-bottom: 1.5rem;
}

.zone-stats p {
  color: #666;
  font-size: 0.875rem;
  font-weight: 600;
  margin: 0;
}

.explore-btn {
  width: 100%;
  background: #007bff;
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

.explore-btn:hover:not(:disabled) {
  transform: translate(2px, 2px);
  box-shadow: 2px 2px 0 #000;
}

.explore-btn:disabled {
  background: #6c757d;
  cursor: not-allowed;
  opacity: 0.6;
}

/* Results Section */
.results-section {
  background: white;
  border: 4px solid #000;
  padding: 2rem;
  box-shadow: 8px 8px 0 #000;
  margin-bottom: 3rem;
}

.results-title {
  font-size: 1.25rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 1.5rem 0;
  color: #000;
}

.results-message {
  color: #333;
  margin-bottom: 1.5rem;
  font-weight: 500;
}

/* Treasure Cards */
.treasures-grid {
  display: grid;
  gap: 1.5rem;
}

.treasure-card {
  background: #fffbf0;
  border: 3px solid #ffc107;
  padding: 1.5rem;
  box-shadow: 4px 4px 0 #ffc107;
  transition: all 0.2s ease;
}

.treasure-card:hover {
  transform: translate(-1px, -1px);
  box-shadow: 6px 6px 0 #ffc107;
}

.treasure-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.treasure-info h4 {
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 0 0 0.5rem 0;
  color: #000;
}

.treasure-meta {
  font-size: 0.875rem;
  color: #666;
  margin: 0.25rem 0;
  font-weight: 600;
}

.dig-btn {
  background: #fd7e14;
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

.dig-btn:hover:not(:disabled) {
  transform: translate(1px, 1px);
  box-shadow: 2px 2px 0 #000;
}

.dig-btn:disabled {
  background: #6c757d;
  cursor: not-allowed;
  opacity: 0.6;
}

.treasure-hint {
  color: #666;
  font-size: 0.875rem;
  font-style: italic;
  font-weight: 500;
}

/* Treasures Section */
.treasures-section {
  margin-top: 2rem;
}

.treasures-title {
  font-size: 1.125rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 1.5rem 0;
  color: #000;
}

.treasure-meta {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.treasure-meta p {
  margin: 0;
}

/* No Treasures */
.no-treasures {
  text-align: center;
  padding: 3rem;
  background: #f8f9fa;
  border: 3px solid #000;
  box-shadow: 4px 4px 0 #000;
}

.no-treasures-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.no-treasures-text {
  font-size: 1.125rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 0.5rem 0;
  color: #000;
}

.no-treasures-hint {
  color: #666;
  margin: 0;
  font-weight: 600;
}

/* Discovery Result */
.discovery-result {
  background: #d4edda;
  border: 4px solid #28a745;
  padding: 2rem;
  box-shadow: 8px 8px 0 #28a745;
  margin-bottom: 3rem;
}

.discovery-title {
  font-size: 1.25rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 1rem 0;
  color: #155724;
}

.discovery-message {
  color: #155724;
  margin-bottom: 1.5rem;
  font-weight: 600;
}

.item-display {
  background: white;
  border: 3px solid #000;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  box-shadow: 4px 4px 0 #000;
}

.item-display h4 {
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 0 0 1rem 0;
  color: #000;
}

.item-info {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
}

.item-icon {
  font-size: 2rem;
}

.item-details h5 {
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 0 0 0.25rem 0;
  color: #000;
}

.item-properties {
  background: #f8f9fa;
  border: 2px solid #000;
  padding: 0.75rem;
  font-family: 'Courier New', monospace;
  font-size: 0.75rem;
  white-space: pre-wrap;
  color: #333;
}

.reward-info {
  font-size: 0.875rem;
  color: #155724;
  font-weight: 700;
  margin: 0.25rem 0;
}

/* My Treasures Section */
.my-treasures-section {
  background: white;
  border: 4px solid #000;
  padding: 2rem;
  box-shadow: 8px 8px 0 #000;
}

.treasures-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.refresh-btn {
  background: #17a2b8;
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

.refresh-btn:hover {
  transform: translate(1px, 1px);
  box-shadow: 2px 2px 0 #000;
}

/* My Treasure Cards */
.my-treasures-list {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.my-treasure-card {
  background: white;
  border: 3px solid #000;
  padding: 1.5rem;
  box-shadow: 4px 4px 0 #000;
}

.my-treasure-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.my-treasure-icon {
  font-size: 1.5rem;
  margin-right: 0.75rem;
}

.my-treasure-name {
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 0 0 0.5rem 0;
  color: #000;
}

.status-badge {
  padding: 0.25rem 0.75rem;
  border: 2px solid #000;
  font-size: 0.75rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  box-shadow: 2px 2px 0 #000;
}

.status-badge.buried {
  background: #007bff;
  color: white;
}

.status-badge.found {
  background: #28a745;
  color: white;
}

.status-badge.expired {
  background: #6c757d;
  color: white;
}

.my-treasure-details {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  font-size: 0.875rem;
  color: #666;
  font-weight: 600;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.detail-label {
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #000;
}

.detail-value {
  color: #333;
}

/* Empty My Treasures */
.empty-my-treasures {
  text-align: center;
  padding: 3rem;
}

.empty-title {
  font-size: 1.25rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 1rem 0;
  color: #666;
}

.empty-message {
  color: #666;
  margin-bottom: 2rem;
  font-weight: 500;
}

.empty-action-btn {
  background: #007bff;
  color: white;
  border: 3px solid #000;
  padding: 0.75rem 2rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  text-decoration: none;
  box-shadow: 4px 4px 0 #000;
  transition: all 0.2s ease;
  display: inline-block;
}

.empty-action-btn:hover {
  transform: translate(2px, 2px);
  box-shadow: 2px 2px 0 #000;
}

/* Modal Overlay */
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

/* Inventory Full Modal */
.inventory-full-modal {
  background: white;
  border: 4px solid #000;
  max-width: 500px;
  width: 100%;
  box-shadow: 12px 12px 0 #000;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 2rem;
  border-bottom: 3px solid #000;
  background: #fff3cd;
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

.warning-section {
  display: flex;
  gap: 1rem;
  padding: 1.5rem;
  background: #f8d7da;
  border: 3px solid #dc3545;
  margin-bottom: 1.5rem;
  box-shadow: 4px 4px 0 #dc3545;
}

.warning-icon {
  font-size: 2rem;
  flex-shrink: 0;
}

.warning-content {
  flex: 1;
}

.warning-title {
  font-size: 1.1rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 0.5rem 0;
  color: #721c24;
}

.warning-message {
  font-weight: 700;
  color: #721c24;
  margin: 0 0 0.5rem 0;
}

.warning-note {
  font-size: 0.875rem;
  font-weight: 600;
  color: #856404;
  margin: 0;
}

.inventory-status {
  background: #f8f9fa;
  border: 3px solid #000;
  padding: 1.5rem;
  box-shadow: 4px 4px 0 #000;
}

.status-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 0;
  border-bottom: 2px solid #dee2e6;
}

.status-info:last-child {
  border-bottom: none;
}

.status-label {
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #000;
}

.status-value {
  font-weight: 700;
  font-size: 1.1rem;
  color: #000;
}

.status-value.critical {
  color: #dc3545;
}

.modal-footer {
  padding: 1.5rem 2rem;
  border-top: 3px solid #000;
  background: #f8f9fa;
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
}

.modal-btn {
  padding: 0.75rem 1.5rem;
  border: 3px solid #000;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  cursor: pointer;
  box-shadow: 4px 4px 0 #000;
  transition: all 0.2s ease;
}

.modal-btn.primary {
  background: #28a745;
  color: white;
}

.modal-btn.secondary {
  background: #6c757d;
  color: white;
}

.modal-btn:hover {
  transform: translate(2px, 2px);
  box-shadow: 2px 2px 0 #000;
}

/* Treasure Main Info */
.treasure-main-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.treasure-title {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

/* Card Exploration Modal */
.card-exploration-modal {
  background: white;
  border: 4px solid #000;
  max-width: 900px;
  width: 95vw;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 12px 12px 0 #000;
}

.card-exploration-modal .modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 2rem;
  border-bottom: 3px solid #000;
  background: #f8f9fa;
}

.card-exploration-modal .modal-title {
  font-size: 1.5rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0;
  color: #000;
}

.exploration-info {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.cost-info {
  background: #ffc107;
  color: #000;
  padding: 0.5rem 1rem;
  border: 3px solid #000;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  box-shadow: 3px 3px 0 #000;
}

.card-exploration-modal .modal-body {
  padding: 2rem;
}

.card-exploration-modal .modal-footer {
  padding: 1.5rem 2rem;
  border-top: 3px solid #000;
  background: #f8f9fa;
  display: flex;
  justify-content: center;
}

/* Cards Grid */
.cards-grid {
  display: grid;
  gap: 1rem;
  margin-bottom: 2rem;
}

/* Adjust grid size based on card count */
.cards-grid[data-count="3"] {
  grid-template-columns: repeat(3, 1fr);
  max-width: 400px;
  margin: 0 auto 2rem;
}

.cards-grid[data-count="6"] {
  grid-template-columns: repeat(3, 1fr);
  max-width: 600px;
  margin: 0 auto 2rem;
}

.cards-grid[data-count="9"] {
  grid-template-columns: repeat(3, 1fr);
  max-width: 600px;
  margin: 0 auto 2rem;
}

/* Card Slots */
.card-slot {
  aspect-ratio: 3/4;
  border: 4px solid #000;
  background: #f8f9fa;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 4px 4px 0 #000;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  position: relative;
  min-height: 120px;
}

.card-slot:hover:not(.revealed) {
  transform: translate(-2px, -2px);
  box-shadow: 6px 6px 0 #000;
  background: #e9ecef;
}

.card-slot.revealed {
  cursor: default;
  background: white;
  border-color: #007bff;
  box-shadow: 4px 4px 0 #007bff;
}

.card-slot.treasure {
  background: #fff3cd;
  border-color: #ffc107;
  box-shadow: 4px 4px 0 #ffc107;
}

/* Card Content */
.card-content {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  text-align: center;
}

.card-content.hidden {
  justify-content: center;
  gap: 0.5rem;
}

.card-back {
  font-size: 2.5rem;
  margin-bottom: 0.5rem;
}

.card-hint {
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #666;
  margin: 0;
}

/* Revealed Card Content */
.card-content.revealed {
  gap: 0.5rem;
}

.empty-content,
.treasure-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

.empty-icon {
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.treasure-icon {
  font-size: 2.5rem;
  margin-bottom: 0.5rem;
}

.treasure-info h4 {
  font-size: 0.875rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 0 0 0.25rem 0;
  color: #000;
}

.treasure-hint {
  font-size: 0.75rem;
  color: #666;
  font-style: italic;
  margin: 0 0 0.5rem 0;
  font-weight: 500;
}

.treasure-meta {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.625rem;
  color: #666;
  font-weight: 600;
}

.difficulty-mini {
  display: inline-block;
  padding: 0.125rem 0.375rem;
  border: 1px solid #000;
  font-size: 0.625rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 0.25rem;
}

.difficulty-mini.easy {
  background: #28a745;
  color: white;
}

.difficulty-mini.normal {
  background: #ffc107;
  color: #000;
}

.difficulty-mini.hard {
  background: #dc3545;
  color: white;
}

/* Dig Button */
.dig-btn.mini {
  background: #fd7e14;
  color: white;
  border: 2px solid #000;
  padding: 0.375rem 0.75rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  cursor: pointer;
  box-shadow: 2px 2px 0 #000;
  transition: all 0.2s ease;
  font-size: 0.75rem;
  margin-top: 0.5rem;
}

.dig-btn.mini:hover:not(:disabled) {
  transform: translate(1px, 1px);
  box-shadow: 1px 1px 0 #000;
}

.dig-btn.mini:disabled {
  background: #6c757d;
  cursor: not-allowed;
  opacity: 0.6;
}

/* Exploration Actions */
.exploration-actions {
  text-align: center;
  padding-top: 1rem;
  border-top: 2px solid #dee2e6;
}

/* Exploration Result Modal */
.exploration-result-modal {
  background: white;
  border: 4px solid #000;
  max-width: 600px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 12px 12px 0 #000;
}

.result-summary {
  text-align: center;
  margin-bottom: 2rem;
}

.result-message {
  font-size: 1.125rem;
  font-weight: 700;
  color: #333;
  margin-bottom: 1.5rem;
}

.result-stats {
  display: grid;
  gap: 1rem;
  margin-bottom: 2rem;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem;
  border: 2px solid #000;
  background: #f8f9fa;
  box-shadow: 3px 3px 0 #000;
}

.stat-label {
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #000;
}

.stat-value {
  font-weight: 700;
  color: #333;
}

/* Found Item Display */
.found-item-display {
  background: #d4edda;
  border: 3px solid #28a745;
  padding: 1.5rem;
  margin-bottom: 2rem;
  box-shadow: 4px 4px 0 #28a745;
}

.found-title {
  font-size: 1rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 1rem 0;
  color: #155724;
}

/* Cards Reveal Section */
.cards-reveal-section {
  margin-top: 2rem;
}

.reveal-title {
  font-size: 1rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 1rem 0;
  color: #000;
}

.mini-cards-grid {
  display: grid;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.mini-cards-grid[data-count="3"] {
  grid-template-columns: repeat(3, 1fr);
}

.mini-cards-grid[data-count="6"] {
  grid-template-columns: repeat(3, 1fr);
}

.mini-cards-grid[data-count="9"] {
  grid-template-columns: repeat(3, 1fr);
}

.mini-card {
  aspect-ratio: 1;
  border: 3px solid #000;
  background: white;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  box-shadow: 3px 3px 0 #000;
}

.mini-card.has-treasure {
  background: #fff3cd;
  border-color: #ffc107;
  box-shadow: 3px 3px 0 #ffc107;
}

.mini-card.is-selected {
  border-color: #007bff;
  border-width: 4px;
  box-shadow: 4px 4px 0 #007bff;
}

.mini-card.is-found {
  background: #d4edda;
  border-color: #28a745;
  box-shadow: 3px 3px 0 #28a745;
}

.mini-card-content {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
}

.mini-treasure-icon {
  color: #ffc107;
}

.mini-card.is-found .mini-treasure-icon {
  color: #28a745;
}

.mini-empty-icon {
  color: #dc3545;
}

/* Additional card styles for new gameplay */
.card-slot.selected {
  border-color: #007bff;
  border-width: 4px;
  box-shadow: 6px 6px 0 #007bff;
  transform: translate(-2px, -2px);
}

.treasure-icon.found {
  color: #28a745;
}

.found-status {
  background: #28a745;
  color: white;
  padding: 0.125rem 0.375rem;
  border: 1px solid #000;
  font-size: 0.625rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-top: 0.25rem;
  box-shadow: 2px 2px 0 rgba(0,0,0,0.3);
}

/* Mobile Responsive */
@media (max-width: 768px) {
  .explore-header {
    padding: 1rem 0;
  }

  .header-content {
    flex-direction: column;
    gap: 1rem;
  }

  .explore-title {
    font-size: 1.5rem;
  }

  .zones-grid {
    grid-template-columns: 1fr;
    gap: 1.5rem;
  }

  .zone-card {
    padding: 1.5rem;
  }

  .zone-header {
    flex-direction: column;
    gap: 1rem;
  }

  .results-section {
    padding: 1.5rem;
  }

  .treasure-header {
    flex-direction: column;
    gap: 1rem;
    align-items: stretch;
  }

  .my-treasure-header {
    flex-direction: column;
    gap: 1rem;
    align-items: stretch;
  }

  .my-treasure-details {
    grid-template-columns: 1fr;
  }

  /* Card exploration mobile */
  .card-exploration-modal {
    width: 98vw;
    max-width: none;
    margin: 1rem;
  }

  .card-exploration-modal .modal-header {
    flex-direction: column;
    gap: 1rem;
    align-items: stretch;
    padding: 1.5rem;
  }

  .card-exploration-modal .modal-body {
    padding: 1.5rem;
  }

  .cards-grid[data-count="3"],
  .cards-grid[data-count="6"],
  .cards-grid[data-count="9"] {
    grid-template-columns: repeat(2, 1fr);
    max-width: none;
    gap: 0.75rem;
  }

  .card-slot {
    min-height: 100px;
  }

  .card-back {
    font-size: 2rem;
  }

  .treasure-icon {
    font-size: 2rem;
  }

  .empty-icon {
    font-size: 1.5rem;
  }

  .treasure-info h4 {
    font-size: 0.75rem;
  }

  .treasure-hint {
    font-size: 0.625rem;
  }

  .dig-btn.mini {
    font-size: 0.625rem;
    padding: 0.25rem 0.5rem;
  }
}
</style>