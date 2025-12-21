<template>
  <div v-if="isVisible" class="modal-overlay" @click="closeModal">
    <div class="modal-content" @click.stop>
      <div class="modal-header">
        <h2>{{ treasuryItem?.item_type?.display_name || '小金库' }}</h2>
        <button @click="closeModal" class="close-btn">×</button>
      </div>

      <div class="modal-body">
        <div class="treasury-info">
          <div class="treasury-icon">💰</div>
          <div class="treasury-status">
            <div class="stored-amount">
              存储积分: {{ storedCoins }} 枚
            </div>
            <div v-if="depositorInfo" class="deposit-info">
              存入者: {{ depositorInfo.username }}
              <br>
              存入时间: {{ formatTime(depositorInfo.time) }}
            </div>
          </div>
        </div>

        <!-- Deposit Section (only if empty) -->
        <div v-if="storedCoins === 0" class="action-section">
          <h3>存入积分</h3>
          <div class="input-group">
            <input
              v-model.number="depositAmount"
              type="number"
              min="1"
              :max="userCoins"
              placeholder="输入存入数量"
              class="amount-input"
            />
            <button
              @click="handleDeposit"
              :disabled="!canDeposit || submitting"
              class="action-btn deposit-btn"
            >
              {{ submitting ? '存入中...' : '存入' }}
            </button>
          </div>
          <div class="balance-info">
            可用积分: {{ userCoins }} 枚
          </div>
        </div>

        <!-- Withdraw Section (only if has coins) -->
        <div v-else class="action-section">
          <h3>提取积分</h3>
          <div class="withdraw-warning">
            ⚠️ 提取积分后，此道具将被销毁
          </div>
          <button
            @click="handleWithdraw"
            :disabled="submitting"
            class="action-btn withdraw-btn"
          >
            {{ submitting ? '提取中...' : `提取 ${storedCoins} 枚积分` }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { storeApi } from '../lib/api'
import { useAuthStore } from '../stores/auth'

interface Props {
  isVisible: boolean
  treasuryItem: any
}

interface Emits {
  (e: 'close'): void
  (e: 'success'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()
const authStore = useAuthStore()

const depositAmount = ref<number>(1)
const submitting = ref(false)

const storedCoins = computed(() => {
  return props.treasuryItem?.properties?.stored_coins || 0
})

const depositorInfo = computed(() => {
  const props_data = props.treasuryItem?.properties
  if (props_data?.depositor_username) {
    return {
      username: props_data.depositor_username,
      time: props_data.deposit_time
    }
  }
  return null
})

const userCoins = computed(() => authStore.user?.coins || 0)

const canDeposit = computed(() => {
  return depositAmount.value > 0 &&
         depositAmount.value <= userCoins.value &&
         storedCoins.value === 0
})

const handleDeposit = async () => {
  if (!canDeposit.value || submitting.value) return

  try {
    submitting.value = true
    await storeApi.depositTreasuryCoins(props.treasuryItem.id, depositAmount.value)

    // Refresh user data
    await authStore.refreshUser()

    // Update item properties locally
    props.treasuryItem.properties = {
      ...props.treasuryItem.properties,
      stored_coins: depositAmount.value,
      depositor_username: authStore.user?.username,
      deposit_time: new Date().toISOString()
    }

    emit('success')
    // Auto-close modal after successful deposit
    emit('close')
  } catch (error: any) {
    console.error('Deposit failed:', error)
    alert(error.message || '存入失败，请重试')
  } finally {
    submitting.value = false
  }
}

const handleWithdraw = async () => {
  if (submitting.value) return

  try {
    submitting.value = true
    await storeApi.withdrawTreasuryCoins(props.treasuryItem.id)

    // Refresh user data
    await authStore.refreshUser()

    emit('success')
    emit('close')
  } catch (error: any) {
    console.error('Withdraw failed:', error)
    alert(error.message || '提取失败，请重试')
  } finally {
    submitting.value = false
  }
}

const closeModal = () => {
  if (!submitting.value) {
    emit('close')
  }
}

const formatTime = (timeStr: string) => {
  return new Date(timeStr).toLocaleString()
}

// Reset deposit amount when modal opens
watch(() => props.isVisible, (newValue) => {
  if (newValue) {
    depositAmount.value = 1
  }
})
</script>

<style scoped>
/* Neo-Brutalism Treasury Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

.modal-content {
  background: white;
  border-radius: 8px;
  border: 3px solid #000;
  box-shadow: 8px 8px 0 #000;
  width: 100%;
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 2px solid #e9ecef;
}

.modal-header h2 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0.5rem;
  border-radius: 4px;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover {
  background-color: #f8f9fa;
}

.modal-body {
  padding: 1.5rem;
}

.treasury-info {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  background: linear-gradient(135deg, #fff3cd, #ffeaa7);
  border: 2px solid #000;
  border-radius: 8px;
  margin-bottom: 1.5rem;
}

.treasury-icon {
  font-size: 2rem;
  flex-shrink: 0;
}

.treasury-status {
  flex: 1;
}

.stored-amount {
  font-size: 1.25rem;
  font-weight: 700;
  color: #333;
  margin-bottom: 0.5rem;
}

.deposit-info {
  font-size: 0.875rem;
  color: #666;
  line-height: 1.4;
}

.action-section {
  background: white;
  border: 2px solid #000;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 4px 4px 0 #000;
}

.action-section h3 {
  margin: 0 0 1rem 0;
  font-size: 1.25rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.input-group {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
}

.amount-input {
  flex: 1;
  padding: 0.75rem;
  border: 2px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
  font-weight: 600;
}

.amount-input:focus {
  outline: none;
  border-color: #007bff;
}

.action-btn {
  padding: 0.75rem 1.5rem;
  border: 2px solid #000;
  border-radius: 4px;
  font-weight: 700;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.2s ease;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  box-shadow: 3px 3px 0 #000;
}

.deposit-btn {
  background: linear-gradient(135deg, #28a745, #20c997);
  color: white;
}

.withdraw-btn {
  background: linear-gradient(135deg, #fd7e14, #e76500);
  color: white;
  width: 100%;
}

.action-btn:hover:not(:disabled) {
  transform: translate(-2px, -2px);
  box-shadow: 5px 5px 0 #000;
}

.action-btn:disabled {
  background: #6c757d;
  cursor: not-allowed;
  opacity: 0.6;
}

.balance-info {
  font-size: 0.875rem;
  color: #666;
  font-weight: 500;
}

.withdraw-warning {
  background: #fff3cd;
  border: 2px solid #ffc107;
  padding: 1rem;
  border-radius: 4px;
  font-size: 0.875rem;
  font-weight: 600;
  color: #856404;
  margin-bottom: 1rem;
  text-align: center;
}

/* Mobile responsive */
@media (max-width: 768px) {
  .modal-overlay {
    padding: 0.5rem;
  }

  .modal-header {
    padding: 1rem;
  }

  .modal-body {
    padding: 1rem;
  }

  .input-group {
    flex-direction: column;
  }

  .treasury-info {
    flex-direction: column;
    text-align: center;
  }
}
</style>