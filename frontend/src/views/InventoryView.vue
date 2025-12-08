<template>
  <div class="inventory-view">
    <!-- Header -->
    <header class="inventory-header">
      <div class="header-content">
        <button @click="$router.back()" class="back-btn">
          ← 返回
        </button>
        <h1 class="inventory-title">🎒 物品背包</h1>
        <div class="header-stats">
          <div class="capacity-display">
            <span class="capacity-text">容量</span>
            <span class="capacity-amount">{{ inventory?.used_slots || 0 }}/{{ inventory?.max_slots || 6 }}</span>
          </div>
          <router-link to="/store" class="store-btn">
            🛍️ 返回商店
          </router-link>
        </div>
      </div>
    </header>

    <div class="container">

      <!-- Loading state -->
      <div v-if="loading" class="loading-state">
        <div class="loading-box">
          <div class="loading-spinner"></div>
          <p class="loading-text">加载背包中...</p>
        </div>
      </div>

      <!-- Error state -->
      <div v-else-if="error" class="error-state">
        <div class="error-box">
          <h3 class="error-title">❌ 加载失败</h3>
          <p class="error-message">{{ error }}</p>
          <button @click="loadInventory" class="retry-btn">🔄 重试</button>
        </div>
      </div>

      <!-- Inventory grid -->
      <div v-else class="inventory-content">
        <div class="inventory-section">
          <h2 class="section-title">物品栏位</h2>

          <!-- Items grid -->
          <div class="inventory-grid">
            <!-- Occupied slots -->
            <div
              v-for="item in inventory?.items || []"
              :key="item.id"
              class="inventory-slot occupied"
              @click="selectItem(item)"
              :class="{ 'selected': selectedItem?.id === item.id }"
            >
              <div class="slot-content">
                <span class="item-icon">{{ item.item_type.icon }}</span>
                <span class="item-name">{{ item.item_type.display_name }}</span>
                <span class="item-status">{{ getStatusText(item.status) }}</span>
              </div>
            </div>

            <!-- Empty slots -->
            <div
              v-for="n in (inventory?.available_slots || 0)"
              :key="`empty-${n}`"
              class="inventory-slot empty"
            >
              <div class="slot-content">
                <span class="empty-text">空槽</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Item details panel -->
        <div v-if="selectedItem" class="item-details-panel">
          <div class="panel-header">
            <div class="item-info">
              <h3 class="item-title">
                <span class="item-title-icon">{{ selectedItem.item_type.icon }}</span>
                <span class="item-title-text">{{ selectedItem.item_type.display_name }}</span>
              </h3>
              <p class="item-description">{{ selectedItem.item_type.description }}</p>
              <div class="item-meta">
                <p class="meta-item">
                  <span class="meta-label">状态:</span>
                  <span class="meta-value">{{ getStatusText(selectedItem.status) }}</span>
                </p>
                <p class="meta-item">
                  <span class="meta-label">创建时间:</span>
                  <span class="meta-value">{{ formatDate(selectedItem.created_at) }}</span>
                </p>
                <!-- 显示原始所有者（对于钥匙物品始终显示） -->
                <p v-if="selectedItem.original_creator || selectedItem.original_owner || selectedItem.item_type.name === 'key'" class="meta-item">
                  <span class="meta-label">原始所有者:</span>
                  <button @click="viewOwnerProfile(selectedItem.original_owner || selectedItem.original_creator)" class="owner-link" v-if="selectedItem.original_owner || selectedItem.original_creator">
                    {{ (selectedItem.original_owner || selectedItem.original_creator).username }}
                  </button>
                  <span v-else class="no-owner">未知</span>
                </p>

                <!-- 显示当前持有者（如果不同于原始所有者） -->
                <p v-if="selectedItem.owner && (selectedItem.original_owner || selectedItem.original_creator) && selectedItem.owner.id !== (selectedItem.original_owner || selectedItem.original_creator)?.id" class="meta-item">
                  <span class="meta-label">当前持有者:</span>
                  <button @click="viewOwnerProfile(selectedItem.owner)" class="owner-link">
                    {{ selectedItem.owner.username }}
                  </button>
                </p>
              </div>
            </div>
            <button @click="selectedItem = null" class="close-btn">
              ✕
            </button>
          </div>

          <!-- Item properties (only show for items other than keys and photos) -->
          <div v-if="Object.keys(selectedItem.properties).length > 0 && !['key', 'photo'].includes(selectedItem.item_type.name)" class="properties-section">
            <h4 class="properties-title">物品属性</h4>
            <div class="properties-content">
              <pre class="properties-json">{{ JSON.stringify(selectedItem.properties, null, 2) }}</pre>
            </div>
          </div>

          <!-- Item actions -->
          <div class="action-buttons">
            <!-- Photo paper upload -->
            <div v-if="selectedItem.item_type.name === 'photo_paper' && selectedItem.status === 'available'">
              <input
                type="file"
                ref="photoInput"
                accept="image/*"
                @change="handlePhotoUpload"
                class="hidden"
              >
              <button @click="triggerPhotoInput" class="action-btn primary">
                📸 上传照片
              </button>
            </div>

            <!-- Photo view -->
            <button
              v-if="selectedItem.item_type.name === 'photo' && selectedItem.status === 'available'"
              @click="viewPhoto(selectedItem)"
              class="action-btn primary"
            >
              👁️ 查看照片
            </button>

            <!-- Create drift bottle -->
            <button
              v-if="canAddToDriftBottle(selectedItem)"
              @click="showDriftBottleModal = true"
              class="action-btn secondary"
            >
              🍾 放入漂流瓶
            </button>

            <!-- Bury item -->
            <button
              v-if="canBuryItem(selectedItem)"
              @click="showBuryModal = true"
              class="action-btn secondary"
            >
              ⛏️ 掩埋物品
            </button>

            <!-- Discard item -->
            <button
              v-if="canDiscardItem(selectedItem)"
              @click="showDiscardModal = true"
              class="action-btn danger"
            >
              🗑️ 丢弃物品
            </button>
          </div>
        </div>

        <!-- Empty inventory message -->
        <div v-if="!inventory?.items || inventory.items.length === 0" class="empty-inventory">
          <div class="empty-box">
            <h3 class="empty-title">🎒 背包空空如也</h3>
            <p class="empty-message">快去商店购买一些物品吧！</p>
            <router-link to="/store" class="empty-action-btn">🛍️ 去商店看看</router-link>
          </div>
        </div>
      </div>

      <!-- Photo upload modal -->
      <div v-if="uploadingPhoto" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div class="bg-white rounded-lg p-6 max-w-md w-full mx-4">
          <h3 class="text-lg font-semibold mb-4">上传照片中...</h3>
          <div class="flex justify-center">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          </div>
        </div>
      </div>

      <!-- Photo viewer modal -->
      <div v-if="viewingPhoto" class="photo-viewer-overlay" @click="closePhotoViewer">
        <div class="photo-viewer-content" @click.stop>
          <div class="photo-container">
            <img :src="photoUrl" class="photo-image" />
            <div class="photo-timer">
              <div class="timer-display">
                <span class="timer-icon">⏱️</span>
                <span class="timer-text">{{ photoTimeRemaining }}s</span>
              </div>
              <div class="timer-bar">
                <div
                  class="timer-progress"
                  :style="{ width: `${(photoTimeRemaining / 5) * 100}%` }"
                ></div>
              </div>
            </div>
          </div>
          <div class="photo-hint">
            <p class="hint-text">🔥 阅后即焚 - {{ photoTimeRemaining }}秒后自动销毁</p>
            <p class="hint-action">点击任意位置立即关闭</p>
          </div>
        </div>
      </div>

      <!-- Drift bottle creation modal -->
      <div v-if="showDriftBottleModal" class="modal-overlay">
        <div class="action-modal">
          <div class="modal-header">
            <h3 class="modal-title">🍾 创建漂流瓶</h3>
            <button @click="closeDriftBottleModal" class="modal-close">×</button>
          </div>

          <div class="modal-body">
            <div class="form-group">
              <label class="form-label">留言内容</label>
              <textarea
                v-model="driftBottleMessage"
                placeholder="写下你想说的话..."
                class="form-textarea"
                maxlength="1000"
              ></textarea>
              <div class="char-counter">{{ driftBottleMessage.length }}/1000</div>
            </div>

            <div v-if="selectedItem" class="item-info-section">
              <h4 class="info-title">📦 附带物品</h4>
              <div class="item-info-card">
                <span class="item-icon">{{ selectedItem.item_type.icon }}</span>
                <div class="item-details">
                  <span class="item-name">{{ selectedItem.item_type.display_name }}</span>
                  <span class="item-description">{{ selectedItem.item_type.description }}</span>
                </div>
              </div>
            </div>
          </div>

          <div class="modal-footer">
            <button @click="closeDriftBottleModal" class="modal-btn secondary">取消</button>
            <button @click="createDriftBottle" class="modal-btn primary" :disabled="!driftBottleMessage.trim() || creatingDriftBottle">
              <span v-if="creatingDriftBottle">创建中...</span>
              <span v-else>创建漂流瓶</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Bury item modal -->
      <div v-if="showBuryModal" class="modal-overlay">
        <div class="action-modal">
          <div class="modal-header">
            <h3 class="modal-title">⛏️ 掩埋物品</h3>
            <button @click="closeBuryModal" class="modal-close">×</button>
          </div>

          <div class="modal-body">
            <div class="form-group">
              <label class="form-label">掩埋区域</label>
              <select v-model="buryData.location_zone" class="form-select">
                <option value="">选择区域</option>
                <option value="forest">🌲 神秘森林</option>
                <option value="mountain">🏔️ 雾山</option>
                <option value="beach">🏖️ 月光海滩</option>
                <option value="desert">🏜️ 沙漠绿洲</option>
                <option value="cave">🕳️ 深邃洞穴</option>
              </select>
            </div>

            <div class="form-group">
              <label class="form-label">寻找提示</label>
              <input
                v-model="buryData.location_hint"
                placeholder="留下寻找提示..."
                class="form-input"
                maxlength="200"
              >
              <div class="char-counter">{{ buryData.location_hint.length }}/200</div>
            </div>


            <div v-if="selectedItem" class="item-info-section">
              <h4 class="info-title">📦 掩埋物品</h4>
              <div class="item-info-card">
                <span class="item-icon">{{ selectedItem.item_type.icon }}</span>
                <div class="item-details">
                  <span class="item-name">{{ selectedItem.item_type.display_name }}</span>
                  <span class="item-description">{{ selectedItem.item_type.description }}</span>
                </div>
              </div>
            </div>
          </div>

          <div class="modal-footer">
            <button @click="closeBuryModal" class="modal-btn secondary">取消</button>
            <button
              @click="buryItem"
              class="modal-btn primary"
              :disabled="!buryData.location_zone || !buryData.location_hint.trim() || buryingItem"
            >
              <span v-if="buryingItem">掩埋中...</span>
              <span v-else>掩埋物品</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Discard item modal -->
      <div v-if="showDiscardModal" class="modal-overlay">
        <div class="action-modal">
          <div class="modal-header">
            <h3 class="modal-title">🗑️ 丢弃物品</h3>
            <button @click="closeDiscardModal" class="modal-close">×</button>
          </div>

          <div class="modal-body">
            <div class="warning-section">
              <div class="warning-icon">⚠️</div>
              <div class="warning-content">
                <h4 class="warning-title">确认丢弃</h4>
                <p class="warning-message">
                  你确定要丢弃 <strong>{{ selectedItem?.item_type.display_name }}</strong> 吗？
                </p>
                <p class="warning-note">
                  此操作不可撤销，物品将永久消失！
                </p>
              </div>
            </div>

            <div v-if="selectedItem?.properties && Object.keys(selectedItem.properties).length > 0" class="item-details">
              <h4 class="details-title">物品详情</h4>
              <div class="details-content">
                <pre class="details-json">{{ JSON.stringify(selectedItem.properties, null, 2) }}</pre>
              </div>
            </div>
          </div>

          <div class="modal-footer">
            <button @click="closeDiscardModal" class="modal-btn secondary">取消</button>
            <button @click="discardItem" class="modal-btn danger" :disabled="discardingItem">
              <span v-if="discardingItem">丢弃中...</span>
              <span v-else>确认丢弃</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { storeApi } from '../lib/api'
import type { UserInventory, Item } from '../types'

// Router
const router = useRouter()

// Reactive data
const inventory = ref<UserInventory | null>(null)
const selectedItem = ref<Item | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

// Photo related
const uploadingPhoto = ref(false)
const viewingPhoto = ref(false)
const photoUrl = ref('')
const photoAutoCloseTimer = ref<number | null>(null)
const photoTimeRemaining = ref(5)
const photoInput = ref<HTMLInputElement>()

// Drift bottle
const showDriftBottleModal = ref(false)
const driftBottleMessage = ref('')
const creatingDriftBottle = ref(false)

// Bury item
const showBuryModal = ref(false)
const buryingItem = ref(false)
const buryData = ref({
  location_zone: '',
  location_hint: ''
})

// Discard item
const showDiscardModal = ref(false)
const discardingItem = ref(false)

// Methods
const loadInventory = async () => {
  try {
    loading.value = true
    error.value = null
    inventory.value = await storeApi.getUserInventory()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载背包失败'
  } finally {
    loading.value = false
  }
}

const selectItem = (item: Item) => {
  selectedItem.value = selectedItem.value?.id === item.id ? null : item
}

const getStatusText = (status: string): string => {
  const statusMap = {
    'available': '可用',
    'used': '已使用',
    'expired': '已过期',
    'in_drift_bottle': '漂流中',
    'buried': '已掩埋'
  }
  return statusMap[status as keyof typeof statusMap] || status
}

const formatDate = (dateString: string): string => {
  return new Date(dateString).toLocaleString('zh-CN')
}

const triggerPhotoInput = () => {
  photoInput.value?.click()
}

const handlePhotoUpload = async (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file || !selectedItem.value) return

  try {
    uploadingPhoto.value = true
    await storeApi.uploadPhotoToPaper(selectedItem.value.id, file)
    await loadInventory()
    selectedItem.value = null
    input.value = ''
  } catch (err) {
    error.value = err instanceof Error ? err.message : '上传照片失败'
  } finally {
    uploadingPhoto.value = false
  }
}

const viewPhoto = async (item: Item) => {
  try {
    const blob = await storeApi.viewPhoto(item.id)
    photoUrl.value = URL.createObjectURL(blob)
    viewingPhoto.value = true

    // Start 5-second auto-close timer
    photoTimeRemaining.value = 5
    startPhotoAutoCloseTimer()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '查看照片失败'
  }
}

const startPhotoAutoCloseTimer = () => {
  if (photoAutoCloseTimer.value) {
    clearInterval(photoAutoCloseTimer.value)
  }

  photoAutoCloseTimer.value = window.setInterval(() => {
    photoTimeRemaining.value--

    if (photoTimeRemaining.value <= 0) {
      closePhotoViewer()
    }
  }, 1000)
}

const closePhotoViewer = () => {
  viewingPhoto.value = false

  // Clear timer
  if (photoAutoCloseTimer.value) {
    clearInterval(photoAutoCloseTimer.value)
    photoAutoCloseTimer.value = null
  }

  if (photoUrl.value) {
    URL.revokeObjectURL(photoUrl.value)
    photoUrl.value = ''
  }

  // Reset timer
  photoTimeRemaining.value = 5

  // Refresh inventory as photo might be burned after reading
  loadInventory()
}

const canAddToDriftBottle = (item: Item): boolean => {
  return item.status === 'available' && ['photo', 'note', 'key'].includes(item.item_type.name)
}

const canBuryItem = (item: Item): boolean => {
  return item.status === 'available' && ['photo', 'key', 'note'].includes(item.item_type.name)
}

const canDiscardItem = (item: Item): boolean => {
  return item.status === 'available'
}

const createDriftBottle = async () => {
  if (!selectedItem.value || !driftBottleMessage.value.trim()) return

  try {
    creatingDriftBottle.value = true
    await storeApi.createDriftBottle({
      message: driftBottleMessage.value,
      item_ids: [selectedItem.value.id]
    })
    await loadInventory()
    closeDriftBottleModal()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '创建漂流瓶失败'
  } finally {
    creatingDriftBottle.value = false
  }
}

const closeDriftBottleModal = () => {
  showDriftBottleModal.value = false
  driftBottleMessage.value = ''
  selectedItem.value = null
}

const buryItem = async () => {
  if (!selectedItem.value || !buryData.value.location_zone || !buryData.value.location_hint.trim()) return

  try {
    buryingItem.value = true
    await storeApi.buryItem({
      item_id: selectedItem.value.id,
      location_zone: buryData.value.location_zone,
      location_hint: buryData.value.location_hint
    })
    await loadInventory()
    closeBuryModal()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '掩埋物品失败'
  } finally {
    buryingItem.value = false
  }
}

const closeBuryModal = () => {
  showBuryModal.value = false
  buryData.value = {
    location_zone: '',
    location_hint: ''
  }
  selectedItem.value = null
}

const discardItem = async () => {
  if (!selectedItem.value) return

  try {
    discardingItem.value = true
    await storeApi.discardItem(selectedItem.value.id)
    await loadInventory()
    closeDiscardModal()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '丢弃物品失败'
  } finally {
    discardingItem.value = false
  }
}

const closeDiscardModal = () => {
  showDiscardModal.value = false
  selectedItem.value = null
}

const viewOwnerProfile = (owner: any) => {
  // Navigate to user profile page
  if (owner && owner.id) {
    router.push(`/profile/${owner.id}`)
  }
}

// Lifecycle
onMounted(() => {
  loadInventory()
})
</script>

<style scoped>
/* Neo-Brutalism Inventory Design */
.inventory-view {
  min-height: 100vh;
  background-color: #f5f5f5;
}

/* Header */
.inventory-header {
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

.inventory-title {
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

.capacity-display {
  background: #17a2b8;
  color: white;
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

.capacity-text {
  font-size: 0.875rem;
}

.capacity-amount {
  font-size: 1.25rem;
}

.store-btn {
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

.store-btn:hover {
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

/* Inventory Content */
.inventory-content {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.inventory-section {
  background: white;
  border: 4px solid #000;
  padding: 2rem;
  box-shadow: 8px 8px 0 #000;
}

.section-title {
  font-size: 1.5rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 1.5rem 0;
  color: #000;
}

/* Inventory Grid */
.inventory-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 1rem;
}

/* Inventory Slots */
.inventory-slot {
  aspect-ratio: 1;
  border: 4px solid #000;
  background: white;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.inventory-slot.occupied {
  background: white;
  box-shadow: 4px 4px 0 #000;
}

.inventory-slot.occupied:hover {
  transform: translate(-2px, -2px);
  box-shadow: 8px 8px 0 #000;
}

.inventory-slot.occupied.selected {
  background: #007bff;
  color: white;
  border-color: #000;
  box-shadow: 8px 8px 0 #000;
  transform: translate(-2px, -2px);
}

.inventory-slot.empty {
  background: #f8f9fa;
  border-style: dashed;
  border-color: #666;
  box-shadow: inset 2px 2px 0 #ddd;
}

.slot-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  text-align: center;
}

.item-icon {
  font-size: 2rem;
  display: block;
}

.item-name {
  font-size: 0.75rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  line-height: 1.2;
}

.item-status {
  font-size: 0.625rem;
  font-weight: 700;
  color: #666;
  text-transform: uppercase;
}

.inventory-slot.occupied.selected .item-status {
  color: #cce7ff;
}

.empty-text {
  font-size: 0.875rem;
  font-weight: 700;
  color: #999;
  text-transform: uppercase;
  letter-spacing: 1px;
}

/* Item Details Panel */
.item-details-panel {
  background: white;
  border: 4px solid #000;
  padding: 2rem;
  box-shadow: 8px 8px 0 #000;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.5rem;
}

.item-info {
  flex: 1;
}

.item-title {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin: 0 0 1rem 0;
}

.item-title-icon {
  font-size: 3rem;
}

.item-title-text {
  font-size: 1.5rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: #000;
}

.item-description {
  color: #333;
  line-height: 1.5;
  margin: 0 0 1rem 0;
  font-weight: 500;
}

.item-meta {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.meta-item {
  display: flex;
  gap: 0.5rem;
  margin: 0;
  font-size: 0.875rem;
}

.meta-label {
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #666;
}

.meta-value {
  font-weight: 700;
  color: #000;
}

.owner-link {
  background: #17a2b8;
  color: white;
  border: 2px solid #000;
  padding: 0.25rem 0.75rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  cursor: pointer;
  box-shadow: 2px 2px 0 #000;
  transition: all 0.2s ease;
  font-size: 0.75rem;
}

.owner-link:hover {
  transform: translate(1px, 1px);
  box-shadow: 1px 1px 0 #000;
  background: #138496;
}

.no-owner {
  color: #999;
  font-style: italic;
  font-weight: 600;
}

.close-btn {
  background: #dc3545;
  color: white;
  border: 3px solid #000;
  padding: 0.5rem 0.75rem;
  font-weight: 900;
  font-size: 1.25rem;
  cursor: pointer;
  box-shadow: 3px 3px 0 #000;
  transition: all 0.2s ease;
}

.close-btn:hover {
  transform: translate(1px, 1px);
  box-shadow: 2px 2px 0 #000;
}

/* Properties Section */
.properties-section {
  margin-bottom: 1.5rem;
}

.properties-title {
  font-size: 1rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 1rem 0;
  color: #000;
}

.properties-content {
  background: #f8f9fa;
  border: 3px solid #000;
  padding: 1rem;
}

.properties-json {
  font-family: 'Courier New', monospace;
  font-size: 0.75rem;
  margin: 0;
  white-space: pre-wrap;
  color: #333;
}

/* Action Buttons */
.action-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
}

.action-btn {
  padding: 0.75rem 1.5rem;
  border: 3px solid #000;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  cursor: pointer;
  box-shadow: 4px 4px 0 #000;
  transition: all 0.2s ease;
}

.action-btn.primary {
  background: #28a745;
  color: white;
}

.action-btn.secondary {
  background: #6c757d;
  color: white;
}

.action-btn.danger {
  background: #dc3545;
  color: white;
}

.action-btn:hover {
  transform: translate(2px, 2px);
  box-shadow: 2px 2px 0 #000;
}

/* Empty Inventory */
.empty-inventory {
  display: flex;
  justify-content: center;
  padding: 4rem 0;
}

.empty-box {
  background: white;
  border: 4px solid #000;
  padding: 3rem;
  text-align: center;
  box-shadow: 8px 8px 0 #000;
  max-width: 500px;
}

.empty-title {
  font-size: 1.5rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 1rem 0;
  color: #000;
}

.empty-message {
  margin: 0 0 2rem 0;
  color: #666;
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
  cursor: pointer;
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

/* Loading Modal */
.loading-modal {
  background: white;
  border: 4px solid #000;
  padding: 3rem;
  text-align: center;
  box-shadow: 12px 12px 0 #000;
  max-width: 400px;
  width: 100%;
}

/* Action Modal */
.action-modal {
  background: white;
  border: 4px solid #000;
  padding: 2rem;
  box-shadow: 12px 12px 0 #000;
  max-width: 500px;
  width: 100%;
}

.modal-title {
  font-size: 1.5rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 1.5rem 0;
  color: #000;
}

/* Modal Form */
.modal-form {
  margin-bottom: 2rem;
}

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

.form-input,
.form-select,
.form-textarea {
  width: 100%;
  border: 3px solid #000;
  padding: 0.75rem;
  font-weight: 700;
  background: white;
  color: #000;
}

.form-textarea {
  height: 100px;
  resize: none;
  font-family: inherit;
}

.form-input:focus,
.form-select:focus,
.form-textarea:focus {
  outline: none;
  box-shadow: 0 0 0 3px #007bff;
}

.char-counter {
  font-size: 0.75rem;
  font-weight: 700;
  color: #666;
  margin-top: 0.5rem;
  text-align: right;
}

/* Modal Actions */
.modal-actions {
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

.modal-btn:hover:not(:disabled) {
  transform: translate(2px, 2px);
  box-shadow: 2px 2px 0 #000;
}

.modal-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.modal-btn.danger {
  background: #dc3545;
  color: white;
}

/* Warning Section */
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

/* Item Details */
.item-details {
  background: #f8f9fa;
  border: 3px solid #000;
  padding: 1.5rem;
  box-shadow: 4px 4px 0 #000;
}

.details-title {
  font-size: 1rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 1rem 0;
  color: #000;
}

.details-content {
  background: white;
  border: 2px solid #000;
  padding: 1rem;
}

.details-json {
  font-family: 'Courier New', monospace;
  font-size: 0.75rem;
  margin: 0;
  white-space: pre-wrap;
  color: #333;
}

/* Form Elements */
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

.form-input,
.form-select,
.form-textarea {
  width: 100%;
  border: 3px solid #000;
  padding: 0.75rem;
  font-weight: 700;
  background: white;
  color: #000;
}

.form-input {
  height: auto;
}

.form-select {
  height: auto;
  background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%23000' stroke-linecap='round' stroke-linejoin='round' stroke-width='3' d='m6 8 4 4 4-4'/%3e%3c/svg%3e");
  background-position: right 0.75rem center;
  background-repeat: no-repeat;
  background-size: 1rem 1rem;
  padding-right: 2.5rem;
}

.form-textarea {
  height: 100px;
  resize: none;
  font-family: inherit;
}

.form-input:focus,
.form-select:focus,
.form-textarea:focus {
  outline: none;
  box-shadow: 0 0 0 3px #007bff;
}

.char-counter {
  font-size: 0.75rem;
  font-weight: 700;
  color: #666;
  margin-top: 0.5rem;
  text-align: right;
}

/* Item Info Section */
.item-info-section {
  background: #e8f4f8;
  border: 3px solid #17a2b8;
  padding: 1.5rem;
  margin-top: 1.5rem;
  box-shadow: 4px 4px 0 #17a2b8;
}

.info-title {
  font-size: 1rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 1rem 0;
  color: #000;
}

.item-info-card {
  background: white;
  border: 2px solid #000;
  padding: 1rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  box-shadow: 3px 3px 0 #000;
}

.item-info-card .item-icon {
  font-size: 2rem;
  flex-shrink: 0;
}

.item-info-card .item-details {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.item-info-card .item-name {
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #000;
  font-size: 0.875rem;
}

.item-info-card .item-description {
  font-size: 0.75rem;
  color: #666;
  font-weight: 600;
}

/* Photo Viewer */
.photo-viewer-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.95);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 2rem;
}

.photo-viewer-content {
  max-width: 90vw;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.photo-container {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.photo-image {
  max-width: 100%;
  max-height: 70vh;
  object-fit: contain;
  border: 4px solid white;
  box-shadow: 8px 8px 0 rgba(255, 255, 255, 0.3);
}

.photo-timer {
  position: absolute;
  top: 1rem;
  right: 1rem;
  background: #dc3545;
  border: 3px solid white;
  padding: 0.75rem 1rem;
  box-shadow: 4px 4px 0 rgba(255, 255, 255, 0.8);
  min-width: 120px;
}

.timer-display {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.timer-icon {
  font-size: 1.25rem;
}

.timer-text {
  color: white;
  font-weight: 900;
  font-size: 1.25rem;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.timer-bar {
  width: 100%;
  height: 6px;
  background: rgba(255, 255, 255, 0.3);
  border: 2px solid white;
  overflow: hidden;
}

.timer-progress {
  height: 100%;
  background: white;
  transition: width 1s linear;
}

.photo-hint {
  background: rgba(0, 0, 0, 0.8);
  border: 3px solid white;
  padding: 1.5rem 2rem;
  text-align: center;
  box-shadow: 8px 8px 0 rgba(255, 255, 255, 0.3);
  max-width: 500px;
}

.hint-text {
  color: white;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 0.5rem 0;
  font-size: 1.1rem;
}

.hint-action {
  color: rgba(255, 255, 255, 0.8);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 0;
  font-size: 0.875rem;
}

/* Hidden input */
.hidden {
  display: none;
}

/* Mobile Responsive */
@media (max-width: 768px) {
  .inventory-header {
    padding: 1rem 0;
  }

  .header-content {
    flex-direction: column;
    gap: 1rem;
  }

  .inventory-title {
    font-size: 1.5rem;
  }

  .inventory-grid {
    grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
    gap: 0.75rem;
  }

  .inventory-section {
    padding: 1.5rem;
  }

  .item-details-panel {
    padding: 1.5rem;
  }

  .panel-header {
    flex-direction: column;
    gap: 1rem;
  }

  .item-title {
    flex-direction: column;
    text-align: center;
    gap: 0.5rem;
  }

  .action-buttons {
    flex-direction: column;
  }

  .modal-actions {
    flex-direction: column;
    gap: 0.75rem;
  }
}
</style>