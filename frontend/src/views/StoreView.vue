<template>
  <div class="store-view">
    <!-- Header -->
    <header class="store-header">
      <div class="header-content">
        <button @click="$router.back()" class="back-btn">
          ← 返回
        </button>
        <h1 class="store-title">🛍️ 积分商店</h1>
        <div class="user-stats">
          <div class="coins-display">
            <span class="coins-icon">🪙</span>
            <span class="coins-amount">{{ userCoins }}</span>
          </div>
          <router-link to="/inventory" class="inventory-btn">
            🎒 背包 ({{ inventoryUsed }}/{{ inventoryMax }})
          </router-link>
        </div>
      </div>
    </header>

    <div class="container">

      <!-- Loading state -->
      <div v-if="loading" class="loading-state">
        <div class="loading-box">
          <div class="loading-spinner"></div>
          <p class="loading-text">加载商店中...</p>
        </div>
      </div>

      <!-- Error state -->
      <div v-else-if="error" class="error-state">
        <div class="error-box">
          <h3 class="error-title">❌ 加载失败</h3>
          <p class="error-message">{{ error }}</p>
          <button @click="loadStoreItems" class="retry-btn">🔄 重试</button>
        </div>
      </div>

      <!-- Store items grid -->
      <div v-else class="store-grid">
        <div
          v-for="item in storeItems"
          :key="item.id"
          class="store-item"
        >
          <!-- Item header -->
          <div class="item-header">
            <div class="item-info">
              <span class="item-icon">{{ item.icon }}</span>
              <div class="item-details">
                <h3 class="item-name">{{ item.name }}</h3>
                <p class="item-type">{{ item.item_type.display_name }}</p>
              </div>
            </div>
            <div class="item-price">
              <div class="price-tag">{{ item.price }}🪙</div>
              <p v-if="item.stock !== null" class="stock-info">
                库存: {{ item.stock }}
              </p>
            </div>
          </div>

          <!-- Item description -->
          <p class="item-description">{{ item.description }}</p>

          <!-- Item restrictions -->
          <div class="item-restrictions">
            <div v-if="item.level_requirement > 1" class="restriction-badge level">
              等级 {{ item.level_requirement }}+
            </div>
            <div v-if="item.daily_limit" class="restriction-badge daily">
              每日限购 {{ item.daily_limit }}个
            </div>
          </div>

          <!-- Purchase controls -->
          <div class="purchase-controls">
            <div class="quantity-selector">
              <label class="quantity-label">数量</label>
              <select
                v-model="purchaseQuantities[item.id]"
                class="quantity-select"
                :disabled="!canPurchase(item)"
              >
                <option v-for="n in getMaxQuantity(item)" :key="n" :value="n">{{ n }}</option>
              </select>
            </div>
            <button
              @click="purchaseItem(item)"
              :disabled="!canPurchase(item) || purchasing"
              class="purchase-btn"
              :class="{ 'disabled': !canPurchase(item) || purchasing }"
            >
              <span v-if="purchasing && purchasingItemId === item.id">购买中...</span>
              <span v-else>💰 购买</span>
            </button>
          </div>

          <!-- Purchase restrictions warning -->
          <div v-if="!canPurchase(item)" class="purchase-warning">
            <p v-if="userLevel < item.level_requirement" class="warning-text">
              ⚠️ 等级不足 (需要等级{{ item.level_requirement }})
            </p>
            <p v-else-if="userCoins < item.price * purchaseQuantities[item.id]" class="warning-text">
              ⚠️ 积分不足
            </p>
            <p v-else-if="inventoryUsed + purchaseQuantities[item.id] > inventoryMax" class="warning-text">
              ⚠️ 背包空间不足
            </p>
            <p v-else-if="item.stock !== null && item.stock < purchaseQuantities[item.id]" class="warning-text">
              ⚠️ 库存不足
            </p>
          </div>
        </div>
      </div>

      <!-- Purchase success modal -->
      <div v-if="showPurchaseModal" class="modal-overlay">
        <div class="success-modal">
          <h3 class="modal-title">🎉 购买成功！</h3>
          <p class="modal-message">{{ purchaseMessage }}</p>
          <button @click="closePurchaseModal" class="modal-btn">确定</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { storeApi } from '../lib/api'
import { useAuthStore } from '../stores/auth'
import type { StoreItem, UserInventory } from '../types'

const authStore = useAuthStore()

// Reactive data
const storeItems = ref<StoreItem[]>([])
const inventory = ref<UserInventory | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const purchasing = ref(false)
const purchasingItemId = ref<string | null>(null)
const purchaseQuantities = ref<Record<string, number>>({})
const showPurchaseModal = ref(false)
const purchaseMessage = ref('')

// Computed properties
const userCoins = computed(() => authStore.user?.coins || 0)
const userLevel = computed(() => authStore.user?.level || 1)
const inventoryUsed = computed(() => inventory.value?.used_slots || 0)
const inventoryMax = computed(() => inventory.value?.max_slots || 6)

// Methods
const loadStoreItems = async () => {
  try {
    loading.value = true
    error.value = null

    const [items, userInventory] = await Promise.all([
      storeApi.getStoreItems(),
      storeApi.getUserInventory()
    ])

    storeItems.value = items
    inventory.value = userInventory

    // Initialize purchase quantities
    if (Array.isArray(items)) {
      items.forEach(item => {
        purchaseQuantities.value[item.id] = 1
      })
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载商店数据失败'
  } finally {
    loading.value = false
  }
}

const canPurchase = (item: StoreItem): boolean => {
  const quantity = purchaseQuantities.value[item.id] || 1

  return (
    userLevel.value >= item.level_requirement &&
    userCoins.value >= item.price * quantity &&
    inventoryUsed.value + quantity <= inventoryMax.value &&
    (item.stock === null || item.stock >= quantity)
  )
}

const getMaxQuantity = (item: StoreItem): number => {
  const maxByCoins = Math.floor(userCoins.value / item.price)
  const maxByInventory = inventoryMax.value - inventoryUsed.value
  const maxByStock = item.stock || 999
  const maxByDaily = item.daily_limit || 999

  return Math.min(maxByCoins, maxByInventory, maxByStock, maxByDaily, 10)
}

const purchaseItem = async (item: StoreItem) => {
  if (!canPurchase(item) || purchasing.value) return

  try {
    purchasing.value = true
    purchasingItemId.value = item.id

    const quantity = purchaseQuantities.value[item.id] || 1
    const result = await storeApi.purchaseItem(item.id, quantity)

    // Update user coins
    if (authStore.user) {
      authStore.user.coins = result.remaining_coins
    }

    // Update inventory
    inventory.value = await storeApi.getUserInventory()

    // Update store items (refresh stock)
    await loadStoreItems()

    // Show success message
    purchaseMessage.value = result.message
    showPurchaseModal.value = true

  } catch (err) {
    error.value = err instanceof Error ? err.message : '购买失败'
  } finally {
    purchasing.value = false
    purchasingItemId.value = null
  }
}

const closePurchaseModal = () => {
  showPurchaseModal.value = false
  purchaseMessage.value = ''
}

// Lifecycle
onMounted(() => {
  loadStoreItems()
})
</script>

<style scoped>
/* Neo-Brutalism Store Design */
.store-view {
  min-height: 100vh;
  background-color: #f5f5f5;
}

/* Header */
.store-header {
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

.store-title {
  font-size: 2rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 2px;
  margin: 0;
  color: #000;
}

.user-stats {
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
  background: #007bff;
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

/* Loading State */
.loading-state {
  display: flex;
  justify-content: center;
  padding: 4rem 0;
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

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loading-text {
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0;
}

/* Error State */
.error-state {
  display: flex;
  justify-content: center;
  padding: 4rem 0;
}

.error-box {
  background: #f8d7da;
  border: 4px solid #dc3545;
  padding: 3rem;
  text-align: center;
  box-shadow: 8px 8px 0 #dc3545;
  max-width: 500px;
}

.error-title {
  font-size: 1.5rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 1rem 0;
  color: #dc3545;
}

.error-message {
  margin: 0 0 2rem 0;
  color: #721c24;
}

.retry-btn {
  background: #dc3545;
  color: white;
  border: 3px solid #000;
  padding: 0.75rem 2rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  cursor: pointer;
  box-shadow: 4px 4px 0 #000;
  transition: all 0.2s ease;
}

.retry-btn:hover {
  transform: translate(2px, 2px);
  box-shadow: 2px 2px 0 #000;
}

/* Store Grid */
.store-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 2rem;
}

/* Store Item Card */
.store-item {
  background: white;
  border: 4px solid #000;
  padding: 2rem;
  box-shadow: 8px 8px 0 #000;
  transition: all 0.2s ease;
}

.store-item:hover {
  transform: translate(-2px, -2px);
  box-shadow: 12px 12px 0 #000;
}

/* Item Header */
.item-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.5rem;
}

.item-info {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.item-icon {
  font-size: 3rem;
  display: block;
}

.item-details {
  flex: 1;
}

.item-name {
  font-size: 1.25rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 0.5rem 0;
  color: #000;
}

.item-type {
  color: #666;
  margin: 0;
  font-weight: 600;
}

.item-price {
  text-align: right;
}

.price-tag {
  background: #28a745;
  color: white;
  padding: 0.5rem 1rem;
  border: 3px solid #000;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  font-size: 1.1rem;
  box-shadow: 3px 3px 0 #000;
  margin-bottom: 0.5rem;
}

.stock-info {
  color: #666;
  font-size: 0.875rem;
  margin: 0;
  font-weight: 600;
}

/* Item Description */
.item-description {
  color: #333;
  line-height: 1.5;
  margin: 0 0 1.5rem 0;
  font-weight: 500;
}

/* Item Restrictions */
.item-restrictions {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
}

.restriction-badge {
  padding: 0.25rem 0.75rem;
  border: 2px solid #000;
  font-size: 0.75rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.restriction-badge.level {
  background: #007bff;
  color: white;
}

.restriction-badge.daily {
  background: #fd7e14;
  color: white;
}

/* Purchase Controls */
.purchase-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
}

.quantity-selector {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.quantity-label {
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  font-size: 0.875rem;
}

.quantity-select {
  border: 3px solid #000;
  padding: 0.5rem;
  font-weight: 700;
  background: white;
  min-width: 60px;
}

.quantity-select:disabled {
  background: #f5f5f5;
  color: #999;
}

.purchase-btn {
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

.purchase-btn:hover:not(.disabled) {
  transform: translate(2px, 2px);
  box-shadow: 2px 2px 0 #000;
}

.purchase-btn.disabled {
  background: #6c757d;
  cursor: not-allowed;
  opacity: 0.6;
}

/* Purchase Warning */
.purchase-warning {
  background: #fff3cd;
  border: 2px solid #ffc107;
  padding: 0.75rem;
  margin-top: 1rem;
}

.warning-text {
  color: #856404;
  font-size: 0.875rem;
  font-weight: 600;
  margin: 0;
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

.success-modal {
  background: white;
  border: 4px solid #000;
  padding: 3rem;
  text-align: center;
  box-shadow: 12px 12px 0 #000;
  max-width: 500px;
  width: 100%;
}

.modal-title {
  font-size: 1.5rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 1rem 0;
  color: #28a745;
}

.modal-message {
  margin: 0 0 2rem 0;
  color: #333;
  font-weight: 500;
}

.modal-btn {
  background: #28a745;
  color: white;
  border: 3px solid #000;
  padding: 0.75rem 2rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  cursor: pointer;
  box-shadow: 4px 4px 0 #000;
  transition: all 0.2s ease;
}

.modal-btn:hover {
  transform: translate(2px, 2px);
  box-shadow: 2px 2px 0 #000;
}

/* Mobile Responsive */
@media (max-width: 768px) {
  .store-header {
    padding: 1rem 0;
  }

  .header-content {
    flex-direction: column;
    gap: 1rem;
  }

  .store-title {
    font-size: 1.5rem;
  }

  .store-grid {
    grid-template-columns: 1fr;
    gap: 1.5rem;
  }

  .store-item {
    padding: 1.5rem;
  }

  .item-header {
    flex-direction: column;
    gap: 1rem;
  }

  .item-price {
    text-align: left;
  }

  .purchase-controls {
    flex-direction: column;
    gap: 1rem;
    align-items: stretch;
  }
}
</style>