<template>
  <div class="ruins-deep-view">

    <!-- Header -->
    <ZoneHeader title="🔥 深处备皮间" danger-badge="极危区域" />

    <!-- Suppression Meter -->
    <div v-if="store.mimicProfile" class="suppression-meter-bar">
      <div class="suppression-meter-inner">
        <span class="meter-label">⚡ 发毛值</span>
        <div class="meter-track">
          <div
            class="meter-fill"
            :style="{ width: suppressionPercent + '%' }"
            :class="suppressionFillClass"
          ></div>
        </div>
        <span class="meter-value" :class="suppressionTextClass">
          {{ store.mimicProfile.suppression_value }}%
        </span>
        <span v-if="store.mimicProfile.suppression_value >= 80" class="suppression-warning">
          高压警告！
        </span>
      </div>
    </div>

    <!-- Body -->
    <div class="ruins-body">

      <!-- Left: Mining + Chat -->
      <div class="ruins-left">

        <!-- Depilation Warning -->
        <div
          v-if="store.mimicProfile && store.mimicProfile.depilation_charge < 30"
          class="depilation-warning neo-brutal-card"
        >
          <span class="warn-icon">⚠️</span>
          <div>
            <strong>电量不足！</strong>
            <p>电量仅剩 {{ store.mimicProfile.depilation_charge }}%，收集效率大幅下降</p>
          </div>
        </div>

        <!-- Raw Crystals Status -->
        <div class="crystal-status neo-brutal-card">
          <h2 class="panel-title">💎 晶矿状态</h2>
          <div class="crystal-stats">
            <div class="crystal-stat-item">
              <span class="crystal-stat-label">备皮刀储量</span>
              <span class="crystal-stat-value raw">{{ store.crystals?.raw_crystals ?? 0 }}</span>
            </div>
            <div class="crystal-stat-item">
              <span class="crystal-stat-label">脱毛仪储量</span>
              <span class="crystal-stat-value purified">{{ store.crystals?.purified_crystals ?? 0 }}</span>
            </div>
          </div>
        </div>

        <!-- Crystal Deposits -->
        <div class="deposits-section neo-brutal-card">
          <h2 class="panel-title">深层矿脉收集点</h2>
          <div v-if="store.ruinsDeepDeposits.length === 0" class="empty-panel">
            <p>暂无可收集矿脉</p>
          </div>
          <div v-else class="deposits-grid">
            <div
              v-for="deposit in store.ruinsDeepDeposits"
              :key="deposit.id"
              class="deposit-card"
              :class="{ depleted: deposit.quantity === 0 }"
            >
              <div class="deposit-header">
                <span class="deposit-icon">💎</span>
                <span class="deposit-quantity">{{ deposit.quantity }} / {{ deposit.max_quantity }}</span>
              </div>
              <div class="deposit-bar-wrap">
                <div
                  class="deposit-bar-fill"
                  :style="{ width: depositPercent(deposit) + '%' }"
                  :class="depositBarClass(deposit)"
                ></div>
              </div>
              <div class="deposit-info">
                <span class="deposit-respawn">↺ {{ deposit.respawn_rate_per_hour }}/h</span>
              </div>
              <button
                class="neo-brutal-button harvest-btn"
                :disabled="harvestingId === deposit.id || deposit.quantity === 0"
                @click="handleHarvest(deposit.id)"
              >
                <span v-if="harvestingId === deposit.id">收集中…</span>
                <span v-else-if="deposit.quantity === 0">已耗尽</span>
                <span v-else>收集</span>
              </button>
              <p v-if="harvestResults[deposit.id]" class="harvest-result">
                +{{ harvestResults[deposit.id] }} 💎
              </p>
            </div>
          </div>
          <p v-if="harvestError" class="panel-error">{{ harvestError }}</p>
        </div>

        <!-- Zone Chat -->
        <section class="chat-panel neo-brutal-card">
          <h2 class="panel-title">深处通讯</h2>
          <div class="chat-messages" ref="chatContainer">
            <div
              v-for="msg in store.chatMessages"
              :key="msg.id"
              class="chat-message"
              :class="{ 'system-message': msg.is_system }"
            >
              <div class="message-header">
                <span class="message-sender">
                  {{ msg.is_system ? '【系统】' : (msg.sender?.username ?? '匿名') }}
                </span>
                <span class="message-time">{{ formatTime(msg.created_at) }}</span>
              </div>
              <p class="message-content">{{ msg.content }}</p>
              <div v-if="msg.tells && msg.tells.length" class="message-tells">
                <p
                  v-for="tell in msg.tells"
                  :key="tell.id"
                  class="tell-text"
                >{{ tell.tell_text }}</p>
              </div>
            </div>
            <div v-if="store.chatMessages.length === 0" class="empty-chat">
              <p>深处只有诡异的嗡鸣声…</p>
            </div>
          </div>
          <div class="chat-input-row">
            <input
              v-model="chatInput"
              type="text"
              class="chat-input"
              placeholder="发送无线电信号…"
              maxlength="200"
              @keydown.enter="handleSpeak"
            />
            <button
              class="neo-brutal-button speak-btn"
              :disabled="speaking || !chatInput.trim()"
              @click="handleSpeak"
            >
              {{ speaking ? '…' : '发言' }}
            </button>
          </div>
        </section>

      </div>

      <!-- Right: Side Panel -->
      <section class="side-panel">

        <!-- ① 场景说明 -->
        <div class="zone-desc neo-brutal-card">
          <h2 class="panel-title">🔥 深处说明</h2>
          <p class="desc-text">男娘幻城最危险的核心地带，污染最严重。</p>
          <p class="desc-text">原初刀具密度极高，但发毛值积累速度翻倍，务必快速撤离。</p>
        </div>

        <!-- ② 信息框：发毛值 + 危险警告 -->
        <div class="zone-info neo-brutal-card">
          <h2 class="panel-title">⚡ 深处状态</h2>
          <div v-if="store.mimicProfile" class="supp-display">
            <span class="supp-label">当前发毛值</span>
            <span class="supp-value" :class="suppressionTextClass">
              {{ store.mimicProfile.suppression_value }}%
            </span>
          </div>
          <div class="danger-alert">
            <span>🔥 极危区域：发毛值积累速度 ×2</span>
          </div>
          <div
            v-if="store.mimicProfile && store.mimicProfile.depilation_charge < 30"
            class="depilation-alert"
          >
            <span>⚠️ 电量不足：{{ store.mimicProfile.depilation_charge }}%</span>
          </div>
        </div>

        <!-- ③ 地图 -->
        <MiniMap />

      </section>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { usePhantomCityStore } from '../stores/phantomCity'
import * as api from '../lib/api-game'
import type { CrystalDeposit } from '../lib/api-game'
import MiniMap from '../components/game/MiniMap.vue'
import ZoneHeader from '../components/game/ZoneHeader.vue'

const store = usePhantomCityStore()

const chatInput = ref('')
const speaking = ref(false)
const chatContainer = ref<HTMLElement | null>(null)

const harvestingId = ref<string | null>(null)
const harvestError = ref<string | null>(null)
const harvestResults = ref<Record<string, number>>({})

const suppressionPercent = computed(() => {
  return Math.min(100, store.mimicProfile?.suppression_value ?? 0)
})

const suppressionFillClass = computed(() => {
  const v = suppressionPercent.value
  if (v >= 80) return 'fill-red'
  if (v >= 40) return 'fill-orange'
  return 'fill-green'
})

const suppressionTextClass = computed(() => {
  const v = suppressionPercent.value
  if (v >= 80) return 'text-red'
  if (v >= 40) return 'text-orange'
  return 'text-green'
})

function depositPercent(deposit: CrystalDeposit): number {
  if (deposit.max_quantity === 0) return 0
  return Math.round((deposit.quantity / deposit.max_quantity) * 100)
}

function depositBarClass(deposit: CrystalDeposit): string {
  const pct = depositPercent(deposit)
  if (pct >= 60) return 'dep-full'
  if (pct >= 25) return 'dep-mid'
  return 'dep-low'
}

function formatTime(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

async function handleHarvest(depositId: string) {
  harvestingId.value = depositId
  harvestError.value = null
  try {
    const result = await api.harvestCrystals(depositId)
    if (result.success) {
      harvestResults.value[depositId] = result.harvested
      await store.loadDeepDeposits()
      await store.loadProfile()
      setTimeout(() => {
        delete harvestResults.value[depositId]
      }, 3000)
    }
  } catch (e: unknown) {
    harvestError.value = e instanceof Error ? e.message : '收集失败'
  } finally {
    harvestingId.value = null
  }
}

async function handleSpeak() {
  if (!chatInput.value.trim() || speaking.value) return
  speaking.value = true
  try {
    await store.speak(chatInput.value.trim())
    chatInput.value = ''
    await nextTick()
    scrollChatToBottom()
  } finally {
    speaking.value = false
  }
}

function scrollChatToBottom() {
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

watch(() => store.chatMessages.length, async () => {
  await nextTick()
  scrollChatToBottom()
})

onMounted(async () => {
  await store.loadProfile()
  await Promise.all([
    store.loadDeepDeposits(),
    store.loadChatMessages('ruins_deep'),
    store.loadZones(),
  ])
  await nextTick()
  scrollChatToBottom()
})
</script>

<style scoped>
.ruins-deep-view {
  min-height: 100vh;
  background: #1a0a0a;
  font-family: 'Courier New', Courier, monospace;
  color: #e0c0c0;
}


/* Suppression Meter */
.suppression-meter-bar {
  background: #0a0a0a;
  border-bottom: 2px solid #600;
  padding: 8px 16px;
}

.suppression-meter-inner {
  max-width: 1100px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  gap: 12px;
}

.meter-label {
  color: #ffaaaa;
  font-weight: 700;
  font-size: 13px;
  white-space: nowrap;
}

.meter-track {
  flex: 1;
  height: 14px;
  background: #333;
  border: 2px solid #600;
  max-width: 300px;
}

.meter-fill {
  height: 100%;
  transition: width 0.4s ease;
}

.fill-green { background: #22c55e; }
.fill-orange { background: #f97316; }
.fill-red { background: #ef4444; }

.meter-value {
  font-weight: 900;
  font-size: 14px;
}

.text-green { color: #4ade80; }
.text-orange { color: #fb923c; }
.text-red { color: #f87171; }

.suppression-warning {
  color: #f87171;
  font-weight: 700;
  font-size: 12px;
  animation: danger-pulse 0.8s infinite;
}

/* Body Layout */
.ruins-body {
  max-width: 1100px;
  margin: 0 auto;
  padding: 20px 16px;
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 20px;
}

.ruins-left {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* Side Panel */
.side-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
  overflow-y: auto;
  max-height: calc(100vh - 160px);
}

.zone-desc {
  background: #1a0a0a;
  border-color: #600;
  box-shadow: 4px 4px 0 #600;
  padding: 0 0 14px;
}

.zone-info {
  background: #1a0a0a;
  border-color: #600;
  box-shadow: 4px 4px 0 #600;
  padding: 0 0 14px;
}

.zone-desc .panel-title,
.zone-info .panel-title {
  padding: 14px 16px 0;
  margin: 0 0 8px;
}

.desc-text {
  font-size: 12px;
  color: #aa8888;
  line-height: 1.6;
  margin: 0;
  padding: 0 14px;
}

.desc-text + .desc-text { margin-top: 4px; }

.supp-display {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 14px;
  margin-bottom: 8px;
}

.supp-label {
  font-size: 12px;
  color: #886666;
}

.supp-value {
  font-weight: 900;
  font-size: 18px;
}

.danger-alert {
  padding: 6px 14px;
  font-size: 12px;
  font-weight: 700;
  color: #ff8080;
  background: #2a0a0a;
  border-top: 1px solid #600;
}

.depilation-alert {
  padding: 6px 14px;
  font-size: 12px;
  font-weight: 700;
  color: #ff8c00;
  background: #1a0a00;
  border-top: 1px solid #440;
}

/* Warnings */
.depilation-warning,
.danger-notice {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 16px;
  background: #2a0a0a;
  border: 2px solid #600;
  box-shadow: 4px 4px 0 #600;
  color: #e0c0c0;
}

.danger-notice {
  background: #1a0505;
}

.warn-icon {
  font-size: 24px;
  flex-shrink: 0;
}

.depilation-warning strong,
.danger-notice strong {
  font-size: 15px;
  color: #ff8080;
}

.depilation-warning p,
.danger-notice p {
  margin: 4px 0 0;
  font-size: 13px;
  color: #aa8888;
}

/* Crystal Status */
.crystal-status {
  background: #1a0a0a;
  padding: 14px 16px;
  border: 2px solid #600;
  box-shadow: 4px 4px 0 #600;
}

.crystal-stats {
  display: flex;
  gap: 24px;
}

.crystal-stat-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.crystal-stat-label {
  font-size: 12px;
  color: #888;
  font-weight: 600;
}

.crystal-stat-value {
  font-size: 24px;
  font-weight: 900;
}

.raw { color: #ff8c00; }
.purified { color: #cc88ff; }

/* Deposits */
.deposits-section {
  background: #1a0a0a;
  padding: 14px 16px;
  border: 2px solid #600;
  box-shadow: 4px 4px 0 #600;
}

.deposits-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 12px;
}

.deposit-card {
  border: 2px solid #600;
  padding: 12px;
  background: #220a0a;
  display: flex;
  flex-direction: column;
  gap: 8px;
  position: relative;
}

.deposit-card.depleted {
  opacity: 0.5;
  background: #111;
}

.deposit-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.deposit-icon {
  font-size: 20px;
}

.deposit-quantity {
  font-size: 13px;
  font-weight: 700;
  color: #ffaaaa;
}

.deposit-bar-wrap {
  height: 8px;
  background: #333;
  border: 1px solid #600;
}

.deposit-bar-fill {
  height: 100%;
  transition: width 0.4s ease;
}

.dep-full { background: #ff6b35; }
.dep-mid { background: #cc4400; }
.dep-low { background: #880000; }

.deposit-info {
  display: flex;
  justify-content: flex-end;
}

.deposit-respawn {
  font-size: 11px;
  color: #888;
}

.harvest-btn {
  width: 100%;
  text-align: center;
  background: #440000;
  color: #ffaaaa;
  border-color: #800;
  box-shadow: 3px 3px 0 #800;
  padding: 6px;
  font-size: 13px;
}

.harvest-btn:hover:not(:disabled) {
  background: #660000;
}

.harvest-result {
  text-align: center;
  color: #ff8c00;
  font-weight: 900;
  font-size: 14px;
  margin: 0;
  animation: fadeup 0.4s ease;
}

@keyframes fadeup {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Chat Panel */
.chat-panel {
  background: #0f0505;
  border: 2px solid #600;
  box-shadow: 4px 4px 0 #600;
  display: flex;
  flex-direction: column;
  height: 360px;
  min-height: 300px;
}

.panel-title {
  font-size: 15px;
  font-weight: 900;
  margin: 0 0 12px;
  padding: 14px 16px 0;
  color: #ff8080;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 0 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.chat-message {
  padding: 8px 10px;
  border-left: 3px solid #ff6b35;
  background: #1a0a0a;
}

.system-message {
  border-left-color: #666;
  background: #111;
  font-style: italic;
}

.message-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
}

.message-sender {
  font-weight: 700;
  font-size: 13px;
  color: #ff8080;
}

.message-time {
  font-size: 11px;
  color: #666;
}

.message-content {
  margin: 0;
  font-size: 14px;
  line-height: 1.5;
  word-break: break-word;
  color: #ccaaaa;
}

.message-tells {
  margin-top: 4px;
  border-top: 1px dashed #600;
  padding-top: 4px;
}

.tell-text {
  margin: 2px 0;
  font-style: italic;
  font-size: 12px;
  color: #886666;
}

.empty-chat {
  text-align: center;
  padding: 40px 0;
  color: #664444;
  font-style: italic;
}

.chat-input-row {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  border-top: 2px solid #600;
}

.chat-input {
  flex: 1;
  border: 2px solid #600;
  padding: 8px 12px;
  font-family: inherit;
  font-size: 14px;
  outline: none;
  background: #1a0a0a;
  color: #e0c0c0;
}

.chat-input:focus {
  border-color: #ff6b35;
}

.speak-btn {
  background: #660000;
  color: #ffaaaa;
  font-weight: 700;
  border-color: #800;
}

.panel-error {
  color: #ff8080;
  font-weight: 700;
  font-size: 13px;
  margin: 8px 0 0;
}

.empty-panel {
  text-align: center;
  padding: 20px;
  color: #664444;
  font-style: italic;
  font-size: 13px;
}

/* Neo-brutal base overrides for dark theme */
.neo-brutal-card {
  border: 2px solid #600;
  box-shadow: 4px 4px 0 #600;
}

.neo-brutal-button {
  display: inline-block;
  border: 2px solid #600;
  box-shadow: 3px 3px 0 #600;
  background: #220a0a;
  color: #e0c0c0;
  font-weight: 700;
  padding: 6px 14px;
  cursor: pointer;
  font-family: inherit;
  font-size: 14px;
  text-decoration: none;
  transition: transform 0.1s, box-shadow 0.1s;
}

.neo-brutal-button:hover:not(:disabled) {
  transform: translate(-1px, -1px);
  box-shadow: 4px 4px 0 #800;
}

.neo-brutal-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .ruins-body {
    grid-template-columns: 1fr;
  }
  .side-panel {
    max-height: none;
  }
}
</style>
