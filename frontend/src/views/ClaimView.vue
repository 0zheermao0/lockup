<template>
  <div class="claim-view">
    <!-- Header -->
    <header class="claim-header">
      <div class="header-content">
        <button @click="goHome" class="home-btn">
          🏠 返回首页
        </button>
        <h1 class="claim-title">🎁 领取物品</h1>
      </div>
    </header>

    <div class="container">
      <!-- Loading state -->
      <div v-if="loading" class="loading-state">
        <div class="loading-box">
          <div class="loading-spinner"></div>
          <p class="loading-text">正在处理...</p>
        </div>
      </div>

      <!-- Success state -->
      <div v-else-if="claimResult" class="success-state">
        <div class="success-box">
          <div class="success-icon">🎉</div>
          <h2 class="success-title">领取成功！</h2>
          <p class="success-message">{{ claimResult.message }}</p>

          <!-- Item details -->
          <div class="item-card">
            <div class="item-info">
              <h3 class="item-title">获得物品</h3>
              <div class="item-details">
                <span class="item-type">{{ claimResult.item.type }}</span>
                <span class="item-id">ID: {{ claimResult.item.id.substring(0, 8) }}...</span>
              </div>
            </div>
            <div class="item-meta">
              <p class="meta-item">
                <span class="meta-label">分享者:</span>
                <span class="meta-value">{{ claimResult.sharer }}</span>
              </p>
              <p class="meta-item">
                <span class="meta-label">剩余背包空间:</span>
                <span class="meta-value">{{ claimResult.remaining_slots }} 格</span>
              </p>
            </div>
          </div>

          <div class="action-buttons">
            <router-link to="/inventory" class="action-btn primary">
              🎒 查看背包
            </router-link>
            <router-link to="/" class="action-btn secondary">
              🏠 返回首页
            </router-link>
          </div>
        </div>
      </div>

      <!-- Error state -->
      <div v-else-if="error" class="error-state">
        <div class="error-box">
          <div class="error-icon">❌</div>
          <h2 class="error-title">领取失败</h2>
          <p class="error-message">{{ error }}</p>

          <div class="error-actions">
            <button @click="retryClaimItem" class="retry-btn">
              🔄 重试
            </button>
            <router-link to="/" class="action-btn secondary">
              🏠 返回首页
            </router-link>
          </div>
        </div>
      </div>

      <!-- Initial state (shouldn't happen if route is accessed correctly) -->
      <div v-else class="initial-state">
        <div class="initial-box">
          <div class="initial-icon">🔗</div>
          <h2 class="initial-title">分享链接</h2>
          <p class="initial-message">正在验证分享链接...</p>
        </div>
      </div>
    </div>

    <!-- Notification Toast for inventory full error -->
    <NotificationToast
      :is-visible="showInventoryFullToast"
      type="error"
      title="背包已满"
      :message="inventoryFullMessage"
      secondary-message="请先清理背包空间，然后重新尝试领取物品。"
      :details="inventoryFullDetails"
      :auto-close="false"
      @close="closeInventoryFullToast"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { storeApi } from '../lib/api'
import NotificationToast from '../components/NotificationToast.vue'

// Router
const router = useRouter()
const route = useRoute()

// Reactive data
const loading = ref(false)
const error = ref<string | null>(null)
const claimResult = ref<{
  message: string;
  item: {
    id: string;
    type: string;
    properties: Record<string, any>;
  };
  sharer: string;
  remaining_slots: number;
} | null>(null)

// Inventory full toast
const showInventoryFullToast = ref(false)
const inventoryFullMessage = ref('')
const inventoryFullDetails = ref<Record<string, any> | undefined>(undefined)

// Methods
const goHome = () => {
  router.push('/')
}

const claimItem = async () => {
  const shareToken = route.params.token as string

  if (!shareToken) {
    error.value = '无效的分享链接'
    return
  }

  try {
    loading.value = true
    error.value = null

    const result = await storeApi.claimSharedItem(shareToken)
    claimResult.value = result
  } catch (err: any) {
    console.log('领取物品错误:', err)

    // 优先使用后端返回的具体错误信息
    let errorMessage = '领取物品失败'

    if (err.message) {
      errorMessage = err.message
    } else if (err.data && err.data.error) {
      errorMessage = err.data.error
    } else if (err.error) {
      errorMessage = err.error
    }

    // Check if it's an inventory full error
    if (errorMessage.includes('背包空间不足')) {
      showInventoryFullToast.value = true
      inventoryFullMessage.value = errorMessage
      inventoryFullDetails.value = {
        '错误类型': '背包容量不足',
        '建议操作': '清理背包空间后重试',
        '或者': '丢弃不需要的物品'
      }
    } else {
      error.value = errorMessage
    }
  } finally {
    loading.value = false
  }
}

const retryClaimItem = () => {
  claimItem()
}

const closeInventoryFullToast = () => {
  showInventoryFullToast.value = false
  inventoryFullMessage.value = ''
  inventoryFullDetails.value = undefined
}

// Lifecycle
onMounted(() => {
  claimItem()
})
</script>

<style scoped>
/* Neo-Brutalism Claim Design */
.claim-view {
  min-height: 100vh;
  background-color: #f5f5f5;
}

/* Header */
.claim-header {
  background: white;
  border-bottom: 4px solid #000;
  padding: 1.5rem 0;
  box-shadow: 0 4px 0 #000;
}

.header-content {
  max-width: 800px;
  margin: 0 auto;
  padding: 0 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}

.home-btn {
  background: #007bff;
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

.home-btn:hover {
  transform: translate(2px, 2px);
  box-shadow: 2px 2px 0 #000;
}

.claim-title {
  font-size: 2rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 2px;
  margin: 0;
  color: #000;
  text-align: center;
  flex: 1;
}

/* Container */
.container {
  max-width: 800px;
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
  color: #000;
}

/* Success State */
.success-state {
  display: flex;
  justify-content: center;
  padding: 2rem 0;
}

.success-box {
  background: white;
  border: 4px solid #000;
  padding: 3rem;
  text-align: center;
  box-shadow: 8px 8px 0 #000;
  max-width: 600px;
  width: 100%;
}

.success-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
}

.success-title {
  font-size: 2rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 1rem 0;
  color: #28a745;
}

.success-message {
  font-size: 1.1rem;
  font-weight: 700;
  color: #000;
  margin: 0 0 2rem 0;
}

/* Item Card */
.item-card {
  background: #e8f4f8;
  border: 3px solid #17a2b8;
  padding: 2rem;
  margin: 2rem 0;
  box-shadow: 4px 4px 0 #17a2b8;
  text-align: left;
}

.item-info {
  margin-bottom: 1.5rem;
}

.item-title {
  font-size: 1.25rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 1rem 0;
  color: #000;
}

.item-details {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.item-type {
  font-size: 1.1rem;
  font-weight: 900;
  color: #17a2b8;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.item-id {
  font-size: 0.875rem;
  font-weight: 700;
  color: #666;
  font-family: 'Courier New', monospace;
}

.item-meta {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
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

/* Error State */
.error-state {
  display: flex;
  justify-content: center;
  padding: 2rem 0;
}

.error-box {
  background: #f8d7da;
  border: 4px solid #dc3545;
  padding: 3rem;
  text-align: center;
  box-shadow: 8px 8px 0 #dc3545;
  max-width: 600px;
  width: 100%;
}

.error-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
}

.error-title {
  font-size: 2rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 1rem 0;
  color: #dc3545;
}

.error-message {
  font-size: 1.1rem;
  font-weight: 700;
  color: #721c24;
  margin: 0 0 2rem 0;
}

.error-actions {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  align-items: center;
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

/* Initial State */
.initial-state {
  display: flex;
  justify-content: center;
  padding: 4rem 0;
}

.initial-box {
  background: white;
  border: 4px solid #000;
  padding: 3rem;
  text-align: center;
  box-shadow: 8px 8px 0 #000;
  max-width: 600px;
  width: 100%;
}

.initial-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
}

.initial-title {
  font-size: 2rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 1rem 0;
  color: #000;
}

.initial-message {
  font-size: 1.1rem;
  font-weight: 700;
  color: #666;
  margin: 0;
}

/* Action Buttons */
.action-buttons {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  align-items: center;
}

.action-btn {
  padding: 0.75rem 2rem;
  border: 3px solid #000;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  text-decoration: none;
  cursor: pointer;
  box-shadow: 4px 4px 0 #000;
  transition: all 0.2s ease;
  display: inline-block;
  text-align: center;
  min-width: 200px;
}

.action-btn.primary {
  background: #28a745;
  color: white;
}

.action-btn.secondary {
  background: #6c757d;
  color: white;
}

.action-btn:hover {
  transform: translate(2px, 2px);
  box-shadow: 2px 2px 0 #000;
}

/* Mobile Responsive */
@media (max-width: 768px) {
  .claim-header {
    padding: 1rem 0;
  }

  .header-content {
    flex-direction: column;
    gap: 1rem;
  }

  .claim-title {
    font-size: 1.5rem;
  }

  .success-box,
  .error-box,
  .initial-box,
  .loading-box {
    padding: 2rem;
  }

  .item-card {
    padding: 1.5rem;
  }

  .action-buttons {
    width: 100%;
  }

  .action-btn {
    width: 100%;
  }
}
</style>