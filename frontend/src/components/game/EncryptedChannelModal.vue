<template>
  <Teleport to="body">
    <div class="ecm-overlay" @click.self="emit('close')">
      <div class="ecm-container">

        <!-- Header -->
        <div class="ecm-header">
          <span class="ecm-header__title">
            🔒 [加密频道]
            {{ transaction.initiator.username }}
            ←→
            {{ transaction.recipient.username }}
          </span>
          <button class="ecm-header__close" @click="emit('close')">×</button>
        </div>

        <!-- Transaction info panel -->
        <div class="ecm-txn-panel">
          <div class="ecm-txn-panel__row">
            <span class="ecm-txn-panel__type">
              {{ txnTypeLabel }}
            </span>
            <span
              class="ecm-txn-panel__status"
              :class="`ecm-txn-panel__status--${transaction.status}`"
            >
              {{ transaction.status }}
            </span>
          </div>

          <div v-if="initiatorOffer" class="ecm-txn-panel__offer">
            <span class="ecm-txn-panel__offer-label">提案方:</span>
            <span v-if="initiatorOffer.crystals" class="ecm-txn-panel__offer-value">
              🔮 {{ initiatorOffer.crystals }} 刀具
            </span>
            <span v-if="initiatorOffer.lock_control_hours" class="ecm-txn-panel__offer-value ecm-txn-panel__offer-value--control">
              🗝️ 控制 {{ initiatorOffer.lock_control_hours }}h
            </span>
          </div>

          <div class="ecm-txn-panel__actions">
            <button
              v-if="canAccept"
              class="ecm-btn ecm-btn--accept"
              :disabled="isActing"
              @click="handleAccept"
            >
              接受
            </button>
            <button
              v-if="canCounter"
              class="ecm-btn ecm-btn--counter"
              :disabled="isActing"
              @click="showCounterInput = !showCounterInput"
            >
              反提案
            </button>
          </div>

          <div v-if="showCounterInput" class="ecm-counter">
            <input
              v-model.number="counterCrystals"
              type="number"
              class="ecm-counter__input"
              placeholder="刀具数量"
              min="0"
            />
            <button class="ecm-btn ecm-btn--accept" :disabled="isActing" @click="handleCounter">
              提交反提案
            </button>
          </div>
        </div>

        <!-- Messages area -->
        <div ref="messagesEl" class="ecm-messages">
          <div
            v-for="msg in store.channelMessages"
            :key="msg.id"
            class="ecm-messages__item"
            :class="{ 'ecm-messages__item--system': msg.is_system }"
          >
            <template v-if="msg.is_system">
              <span class="ecm-messages__system-text">— {{ msg.content }} —</span>
            </template>
            <template v-else>
              <span class="ecm-messages__line ecm-messages__line--typewriter">
                &gt; {{ msg.sender?.username ?? '???'}}: {{ msg.content }}
              </span>
            </template>
          </div>
          <div v-if="store.channelMessages.length === 0" class="ecm-messages__empty">
            — 频道已加密，等待通讯 —
          </div>
        </div>

        <!-- Input row -->
        <div class="ecm-input-row">
          <input
            v-model="inputText"
            class="ecm-input-row__field"
            placeholder="输入消息..."
            :disabled="isSending"
            @keydown.enter="handleSend"
          />
          <button
            class="ecm-input-row__send"
            :disabled="isSending || !inputText.trim()"
            @click="handleSend"
          >
            发送
          </button>
        </div>

      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import type { GrayMarketTransaction } from '../../lib/api-game'
import { acceptBribe, counterBribe } from '../../lib/api-game'
import { usePhantomCityStore } from '../../stores/phantomCity'

const props = defineProps<{
  channelId: string
  transaction: GrayMarketTransaction
}>()

const emit = defineEmits<{
  close: []
}>()

const store = usePhantomCityStore()

const inputText = ref('')
const isSending = ref(false)
const isActing = ref(false)
const showCounterInput = ref(false)
const counterCrystals = ref(0)
const messagesEl = ref<HTMLElement | null>(null)

let pollInterval: ReturnType<typeof setInterval> | null = null

const txnTypeLabel = computed(() => {
  const map: Record<string, string> = {
    bribe: '打点',
    extortion: '威胁',
    trade: '交易',
  }
  return map[props.transaction.transaction_type] ?? props.transaction.transaction_type
})

const initiatorOffer = computed(() => {
  const offer = props.transaction.offer_from_initiator as Record<string, unknown>
  return offer && Object.keys(offer).length > 0 ? offer : null
})

const canAccept = computed(() => {
  return ['pending', 'countered'].includes(props.transaction.status)
})

const canCounter = computed(() => {
  return props.transaction.status === 'pending' && props.transaction.transaction_type === 'bribe'
})

async function handleSend() {
  const text = inputText.value.trim()
  if (!text || isSending.value) return
  isSending.value = true
  try {
    await store.sendChannelMessage(text)
    inputText.value = ''
    await scrollToBottom()
  } finally {
    isSending.value = false
  }
}

async function handleAccept() {
  isActing.value = true
  try {
    await acceptBribe(props.transaction.id)
    await store.refreshChannelMessages()
  } finally {
    isActing.value = false
  }
}

async function handleCounter() {
  if (counterCrystals.value <= 0) return
  isActing.value = true
  try {
    await counterBribe(props.transaction.id, { crystals: counterCrystals.value })
    showCounterInput.value = false
    await store.refreshChannelMessages()
  } finally {
    isActing.value = false
  }
}

async function scrollToBottom() {
  await nextTick()
  if (messagesEl.value) {
    messagesEl.value.scrollTop = messagesEl.value.scrollHeight
  }
}

watch(() => store.channelMessages.length, () => scrollToBottom())

onMounted(async () => {
  await store.refreshChannelMessages()
  await scrollToBottom()
  pollInterval = setInterval(async () => {
    await store.refreshChannelMessages()
  }, 3000)
})

onUnmounted(() => {
  if (pollInterval !== null) {
    clearInterval(pollInterval)
    pollInterval = null
  }
})
</script>

<style scoped>
.ecm-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 16px;
}

.ecm-container {
  background: #1a1a1a;
  border: 2px solid #00ff41;
  color: #00ff41;
  font-family: 'JetBrains Mono', 'Courier New', monospace;
  max-width: 600px;
  width: 100%;
  display: flex;
  flex-direction: column;
  max-height: 90vh;
  box-shadow: 6px 6px 0 #00ff41;
}

/* Header */
.ecm-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  border-bottom: 2px solid #00ff41;
  background: #0d0d0d;
}

.ecm-header__title {
  font-size: 0.85em;
  font-weight: 700;
  letter-spacing: 0.04em;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ecm-header__close {
  background: transparent;
  border: 2px solid #00ff41;
  color: #00ff41;
  font-size: 1.1em;
  font-weight: 700;
  cursor: pointer;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 2px 2px 0 #00ff41;
  transition: background 0.15s;
}

.ecm-header__close:hover {
  background: #00ff41;
  color: #000;
}

/* Transaction panel */
.ecm-txn-panel {
  padding: 10px 14px;
  border-bottom: 2px solid #00ff41;
  background: #111;
  font-size: 0.8em;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.ecm-txn-panel__row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ecm-txn-panel__type {
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.ecm-txn-panel__status {
  padding: 1px 6px;
  border: 1px solid #00ff41;
  font-size: 0.9em;
  text-transform: uppercase;
}

.ecm-txn-panel__status--accepted,
.ecm-txn-panel__status--completed {
  border-color: #00cc44;
  color: #00cc44;
}

.ecm-txn-panel__status--pending,
.ecm-txn-panel__status--countered {
  border-color: #ffaa00;
  color: #ffaa00;
}

.ecm-txn-panel__status--rejected,
.ecm-txn-panel__status--expired {
  border-color: #ff3300;
  color: #ff3300;
}

.ecm-txn-panel__offer {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.ecm-txn-panel__offer-label {
  color: #888;
}

.ecm-txn-panel__offer-value {
  padding: 1px 6px;
  border: 1px solid #00ff41;
}

.ecm-txn-panel__offer-value--control {
  border-color: #cc88ff;
  color: #cc88ff;
}

.ecm-txn-panel__actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.ecm-counter {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.ecm-counter__input {
  background: #0d0d0d;
  border: 2px solid #00ff41;
  color: #00ff41;
  font-family: inherit;
  font-size: 0.9em;
  padding: 4px 8px;
  width: 120px;
  outline: none;
}

.ecm-counter__input::placeholder {
  color: #444;
}

/* Buttons */
.ecm-btn {
  background: transparent;
  border: 2px solid #000;
  font-family: inherit;
  font-size: 0.8em;
  font-weight: 700;
  padding: 4px 12px;
  cursor: pointer;
  box-shadow: 2px 2px 0 currentColor;
  transition: opacity 0.15s;
}

.ecm-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.ecm-btn--accept {
  border-color: #00ff41;
  color: #00ff41;
  box-shadow: 2px 2px 0 #00ff41;
}

.ecm-btn--accept:not(:disabled):hover {
  background: #00ff41;
  color: #000;
}

.ecm-btn--counter {
  border-color: #ffaa00;
  color: #ffaa00;
  box-shadow: 2px 2px 0 #ffaa00;
}

.ecm-btn--counter:not(:disabled):hover {
  background: #ffaa00;
  color: #000;
}

/* Messages */
.ecm-messages {
  flex: 1;
  overflow-y: auto;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  background: #0d0d0d;
  min-height: 200px;
}

.ecm-messages::-webkit-scrollbar {
  width: 6px;
}

.ecm-messages::-webkit-scrollbar-track {
  background: #0d0d0d;
}

.ecm-messages::-webkit-scrollbar-thumb {
  background: #00ff41;
}

.ecm-messages__empty {
  color: #444;
  font-style: italic;
  font-size: 0.85em;
  text-align: center;
  margin: auto;
}

.ecm-messages__item {
  font-size: 0.85em;
  line-height: 1.5;
}

.ecm-messages__system-text {
  color: #666;
  font-style: italic;
}

.ecm-messages__line {
  display: block;
  overflow: hidden;
  white-space: pre-wrap;
  word-break: break-all;
}

.ecm-messages__line--typewriter {
  animation: ecm-typewriter 0.6s steps(40, end) both;
}

/* Input row */
.ecm-input-row {
  display: flex;
  border-top: 2px solid #00ff41;
  background: #0d0d0d;
}

.ecm-input-row__field {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: #00ff41;
  font-family: inherit;
  font-size: 0.85em;
  padding: 10px 14px;
}

.ecm-input-row__field::placeholder {
  color: #2a5c35;
}

.ecm-input-row__field:disabled {
  opacity: 0.5;
}

.ecm-input-row__send {
  background: transparent;
  border: none;
  border-left: 2px solid #00ff41;
  color: #00ff41;
  font-family: inherit;
  font-size: 0.85em;
  font-weight: 700;
  padding: 10px 18px;
  cursor: pointer;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  transition: background 0.15s;
}

.ecm-input-row__send:not(:disabled):hover {
  background: #00ff41;
  color: #000;
}

.ecm-input-row__send:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

@keyframes ecm-typewriter {
  from { clip-path: inset(0 100% 0 0); }
  to { clip-path: inset(0 0% 0 0); }
}
</style>
