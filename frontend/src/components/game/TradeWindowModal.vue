<template>
  <Teleport to="body">
    <div class="twm-overlay" @click.self="emit('close')">
      <div class="twm-container">

        <!-- Header -->
        <div class="twm-header">
          <span class="twm-header__title">⚖️ 交易窗口</span>
          <button class="twm-header__close" @click="emit('close')">×</button>
        </div>

        <!-- Two-panel trade area -->
        <div class="twm-panels">

          <!-- Left: Initiator -->
          <div class="twm-panel twm-panel--left">
            <div class="twm-panel__player">
              <div class="twm-panel__avatar">
                <img
                  v-if="transaction.initiator.avatar"
                  :src="transaction.initiator.avatar"
                  :alt="transaction.initiator.username"
                  class="twm-panel__avatar-img"
                />
                <span v-else class="twm-panel__avatar-fallback">
                  {{ transaction.initiator.username.charAt(0).toUpperCase() }}
                </span>
              </div>
              <span class="twm-panel__username">{{ transaction.initiator.username }}</span>
              <span class="twm-panel__role-badge twm-panel__role-badge--initiator">发起方</span>
            </div>

            <div class="twm-panel__offer">
              <div v-if="initiatorCrystals > 0" class="twm-panel__offer-row">
                <span class="twm-panel__offer-icon">🔮</span>
                <span class="twm-panel__offer-value">{{ initiatorCrystals }} 刀具</span>
              </div>
              <div v-if="initiatorControlHours > 0" class="twm-panel__offer-row">
                <span class="twm-panel__offer-icon">🗝️</span>
                <span class="twm-panel__control-badge">
                  钥匙控制: {{ initiatorControlHours }}h
                </span>
              </div>
              <div v-if="initiatorCrystals === 0 && initiatorControlHours === 0" class="twm-panel__offer-empty">
                （无提案内容）
              </div>
            </div>
          </div>

          <!-- Divider -->
          <div class="twm-divider">
            <span class="twm-divider__icon">⇄</span>
          </div>

          <!-- Right: Recipient -->
          <div class="twm-panel twm-panel--right">
            <div class="twm-panel__player">
              <div class="twm-panel__avatar">
                <img
                  v-if="transaction.recipient.avatar"
                  :src="transaction.recipient.avatar"
                  :alt="transaction.recipient.username"
                  class="twm-panel__avatar-img"
                />
                <span v-else class="twm-panel__avatar-fallback">
                  {{ transaction.recipient.username.charAt(0).toUpperCase() }}
                </span>
              </div>
              <span class="twm-panel__username">{{ transaction.recipient.username }}</span>
              <span class="twm-panel__role-badge twm-panel__role-badge--recipient">接收方</span>
            </div>

            <div class="twm-panel__offer">
              <div v-if="recipientCrystals > 0" class="twm-panel__offer-row">
                <span class="twm-panel__offer-icon">🔮</span>
                <span class="twm-panel__offer-value">{{ recipientCrystals }} 刀具</span>
              </div>
              <div v-if="recipientControlHours > 0" class="twm-panel__offer-row">
                <span class="twm-panel__offer-icon">🗝️</span>
                <span class="twm-panel__control-badge">
                  钥匙控制: {{ recipientControlHours }}h
                </span>
              </div>
              <div v-if="recipientCrystals === 0 && recipientControlHours === 0" class="twm-panel__offer-empty">
                （无回报内容）
              </div>
            </div>
          </div>

        </div>

        <!-- Transaction status -->
        <div class="twm-status">
          <span class="twm-status__label">交易状态:</span>
          <span class="twm-status__value twm-status__value--{{ transaction.status }}">
            {{ transaction.status }}
          </span>
          <span v-if="transaction.escrowed_crystals > 0" class="twm-status__escrow">
            🔮 托管: {{ transaction.escrowed_crystals }}
          </span>
        </div>

        <!-- Actions -->
        <div class="twm-actions">
          <button
            class="twm-btn twm-btn--confirm"
            :disabled="isConfirming"
            @click="handleConfirm"
          >
            {{ isConfirming ? '处理中...' : '确认交易' }}
          </button>
          <button
            class="twm-btn twm-btn--cancel"
            :disabled="isConfirming"
            @click="emit('close')"
          >
            取消
          </button>
        </div>

        <p v-if="errorMsg" class="twm-error">{{ errorMsg }}</p>

      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { GrayMarketTransaction } from '../../lib/api-game'
import { acceptTrade } from '../../lib/api-game'

const props = defineProps<{
  transaction: GrayMarketTransaction
}>()

const emit = defineEmits<{
  close: []
  accepted: []
}>()

const isConfirming = ref(false)
const errorMsg = ref('')

const initiatorOffer = computed(
  () => props.transaction.offer_from_initiator as Record<string, number>
)
const recipientOffer = computed(
  () => props.transaction.offer_from_recipient as Record<string, number>
)

const initiatorCrystals = computed(() => Number(initiatorOffer.value?.crystals ?? 0))
const initiatorControlHours = computed(() => Number(initiatorOffer.value?.lock_control_hours ?? 0))
const recipientCrystals = computed(() => Number(recipientOffer.value?.crystals ?? 0))
const recipientControlHours = computed(() => Number(recipientOffer.value?.lock_control_hours ?? 0))

async function handleConfirm() {
  isConfirming.value = true
  errorMsg.value = ''
  try {
    await acceptTrade(props.transaction.id, props.transaction.offer_from_recipient)
    emit('accepted')
    emit('close')
  } catch (e: unknown) {
    errorMsg.value = e instanceof Error ? e.message : '交易失败，请重试'
  } finally {
    isConfirming.value = false
  }
}
</script>

<style scoped>
.twm-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 16px;
}

.twm-container {
  background: #ffffff;
  border: 2px solid #000;
  box-shadow: 6px 6px 0 #000;
  max-width: 640px;
  width: 100%;
  font-family: 'Inter', sans-serif;
}

/* Header */
.twm-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 2px solid #000;
  background: #f5f5f5;
}

.twm-header__title {
  font-size: 1em;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.twm-header__close {
  background: transparent;
  border: 2px solid #000;
  color: #000;
  font-size: 1.1em;
  font-weight: 700;
  cursor: pointer;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 2px 2px 0 #000;
  transition: background 0.15s;
}

.twm-header__close:hover {
  background: #000;
  color: #fff;
}

/* Panels */
.twm-panels {
  display: flex;
  align-items: stretch;
  border-bottom: 2px solid #000;
}

.twm-panel {
  flex: 1;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.twm-panel--left {
  border-right: 1px solid #ccc;
}

.twm-panel__player {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.twm-panel__avatar {
  width: 48px;
  height: 48px;
  border: 2px solid #000;
  box-shadow: 3px 3px 0 #000;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #e8e8e8;
  flex-shrink: 0;
}

.twm-panel__avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.twm-panel__avatar-fallback {
  font-size: 1.2em;
  font-weight: 800;
}

.twm-panel__username {
  font-weight: 700;
  font-size: 0.9em;
  text-align: center;
  word-break: break-all;
}

.twm-panel__role-badge {
  font-size: 0.7em;
  font-weight: 700;
  padding: 1px 8px;
  border: 2px solid #000;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.twm-panel__role-badge--initiator {
  background: #000;
  color: #fff;
}

.twm-panel__role-badge--recipient {
  background: #fff;
  color: #000;
}

.twm-panel__offer {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-height: 60px;
}

.twm-panel__offer-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.twm-panel__offer-icon {
  font-size: 1em;
  flex-shrink: 0;
}

.twm-panel__offer-value {
  font-weight: 700;
  font-size: 0.9em;
}

.twm-panel__control-badge {
  font-size: 0.8em;
  font-weight: 700;
  padding: 2px 8px;
  border: 2px solid #8800cc;
  color: #8800cc;
  box-shadow: 2px 2px 0 #8800cc;
}

.twm-panel__offer-empty {
  font-size: 0.8em;
  color: #999;
  font-style: italic;
  text-align: center;
  padding-top: 8px;
}

/* Divider */
.twm-divider {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 8px;
  background: #f5f5f5;
  border-left: 1px solid #ccc;
  border-right: 1px solid #ccc;
}

.twm-divider__icon {
  font-size: 1.4em;
  font-weight: 900;
  color: #555;
}

/* Status */
.twm-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border-bottom: 2px solid #000;
  background: #fafafa;
  font-size: 0.85em;
}

.twm-status__label {
  font-weight: 700;
  color: #555;
}

.twm-status__value {
  font-weight: 700;
  padding: 1px 6px;
  border: 1px solid #000;
  text-transform: uppercase;
  font-size: 0.9em;
}

.twm-status__escrow {
  margin-left: auto;
  font-weight: 700;
  color: #555;
}

/* Actions */
.twm-actions {
  display: flex;
  gap: 10px;
  padding: 14px 16px;
}

.twm-btn {
  font-family: inherit;
  font-size: 0.9em;
  font-weight: 800;
  padding: 8px 20px;
  border: 2px solid #000;
  cursor: pointer;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  box-shadow: 4px 4px 0 #000;
  transition: transform 0.1s, box-shadow 0.1s;
}

.twm-btn:not(:disabled):active {
  transform: translate(2px, 2px);
  box-shadow: 2px 2px 0 #000;
}

.twm-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.twm-btn--confirm {
  background: #00cc44;
  color: #000;
}

.twm-btn--confirm:not(:disabled):hover {
  background: #00aa38;
}

.twm-btn--cancel {
  background: #e0e0e0;
  color: #000;
}

.twm-btn--cancel:not(:disabled):hover {
  background: #c8c8c8;
}

.twm-error {
  margin: 0;
  padding: 8px 16px;
  background: #fff0ee;
  border-top: 2px solid #ff3300;
  color: #ff3300;
  font-size: 0.85em;
  font-weight: 700;
}
</style>
