<template>
  <div class="salon-view">

    <!-- Header -->
    <ZoneHeader
      title="🥂 闺房"
      :player-badge="salonPlayerCount + ' 人在线'"
      :extra-badge="store.activeChannelId ? '📡 频道活跃' : undefined"
    />

    <!-- Main Layout -->
    <div class="zone-body">

      <!-- Left: Chat Panel -->
      <section class="main-panel neo-brutal-card">
        <h2 class="panel-title">区域聊天</h2>
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
              <p v-for="tell in msg.tells" :key="tell.id" class="tell-text">{{ tell.tell_text }}</p>
            </div>
          </div>
          <div v-if="store.chatMessages.length === 0" class="empty-chat">
            <p>闺房内一片寂静…</p>
          </div>
        </div>
        <div class="chat-input-row">
          <input
            v-model="chatInput"
            type="text"
            class="chat-input"
            placeholder="在闺房内发言…"
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

      <!-- Right: Side Panel -->
      <section class="side-panel">

        <!-- ① 场景说明 -->
        <div class="zone-desc neo-brutal-card">
          <h2 class="panel-title">🥂 闺房说明</h2>
          <p class="desc-text">男娘幻城中最安全的中立区域，小男娘可在此补觉降低发毛值，同时交易市场物品。</p>
          <p class="desc-text">补觉可降低 <strong>15</strong> 点发毛值。</p>
        </div>

        <!-- ② 信息框：操作 + 市场/背包 -->
        <div class="zone-info neo-brutal-card">
          <h2 class="panel-title">快速操作</h2>
          <div class="actions-grid">
            <button
              class="action-btn neo-brutal-button rest-btn"
              :disabled="resting"
              @click="handleRest"
            >
              <span class="action-icon">💤</span>
              <span class="action-label">补觉</span>
              <span v-if="lastRestResult" class="action-result">-{{ lastRestResult }}⚡</span>
            </button>
            <button
              class="action-btn neo-brutal-button market-btn"
              :class="{ active: showMarket }"
              @click="toggleMarket"
            >
              <span class="action-icon">💰</span>
              <span class="action-label">市场</span>
            </button>
            <button
              class="action-btn neo-brutal-button inventory-btn"
              :class="{ active: showInventory }"
              @click="toggleInventory"
            >
              <span class="action-icon">🎒</span>
              <span class="action-label">背包</span>
            </button>
          </div>
          <p v-if="restError" class="panel-error">{{ restError }}</p>
        </div>

        <!-- 市场面板（折叠） -->
        <div v-if="showMarket" class="market-panel neo-brutal-card">
          <h2 class="panel-title">💰 黑市行情</h2>
          <div v-if="store.marketRates.length === 0" class="empty-panel">
            <p>市场暂无报价</p>
          </div>
          <div v-else class="market-list">
            <div v-for="rate in store.marketRates" :key="rate.item_slug" class="market-item">
              <div class="market-item-info">
                <span class="market-item-name">{{ rate.item_display_name }}</span>
                <span class="market-item-price">
                  💎 {{ rate.current_price_crystals }}
                  <span class="demand-badge" :class="demandClass(rate.demand_pressure)">
                    {{ demandLabel(rate.demand_pressure) }}
                  </span>
                </span>
              </div>
              <button
                class="neo-brutal-button buy-btn"
                :disabled="buyingSlug === rate.item_slug"
                @click="handleBuy(rate.item_slug)"
              >
                {{ buyingSlug === rate.item_slug ? '购买中…' : '购买' }}
              </button>
            </div>
          </div>
          <p v-if="buyError" class="panel-error">{{ buyError }}</p>
          <p v-if="buySuccess" class="panel-success">{{ buySuccess }}</p>
        </div>

        <!-- 背包面板（折叠） -->
        <div v-if="showInventory" class="inventory-panel neo-brutal-card">
          <h2 class="panel-title">🎒 背包物品</h2>
          <div v-if="store.inventory.length === 0" class="empty-panel">
            <p>背包空空如也</p>
          </div>
          <div v-else class="inventory-list">
            <div v-for="entry in store.inventory" :key="entry.id" class="inventory-item">
              <span class="item-icon">{{ entry.item.icon }}</span>
              <div class="item-info">
                <span class="item-name">{{ entry.item.name }}</span>
                <span class="item-tier">T{{ entry.item.tier }}</span>
              </div>
              <span class="item-qty">x{{ entry.quantity }}</span>
            </div>
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
import MiniMap from '../components/game/MiniMap.vue'
import ZoneHeader from '../components/game/ZoneHeader.vue'

const store = usePhantomCityStore()

const chatInput = ref('')
const speaking = ref(false)
const chatContainer = ref<HTMLElement | null>(null)

const resting = ref(false)
const restError = ref<string | null>(null)
const lastRestResult = ref<number | null>(null)

const showMarket = ref(false)
const showInventory = ref(false)
const buyingSlug = ref<string | null>(null)
const buyError = ref<string | null>(null)
const buySuccess = ref<string | null>(null)

const salonPlayerCount = computed(() => {
  const zone = store.zones.find(z => z.name === 'salon')
  return zone?.player_count ?? store.chatMessages.length
})

function formatTime(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function demandClass(pressure: number): string {
  if (pressure > 1.2) return 'demand-high'
  if (pressure < 0.8) return 'demand-low'
  return 'demand-normal'
}

function demandLabel(pressure: number): string {
  if (pressure > 1.2) return '热销'
  if (pressure < 0.8) return '滞销'
  return '正常'
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

async function handleRest() {
  resting.value = true
  restError.value = null
  lastRestResult.value = null
  try {
    const result = await store.salonRest()
    if (result.success) {
      lastRestResult.value = result.suppression_before - result.suppression_after
    }
  } catch (e: unknown) {
    restError.value = e instanceof Error ? e.message : '补觉失败'
  } finally {
    resting.value = false
    setTimeout(() => { lastRestResult.value = null }, 3000)
  }
}

function toggleMarket() {
  showMarket.value = !showMarket.value
  if (showMarket.value) showInventory.value = false
}

function toggleInventory() {
  showInventory.value = !showInventory.value
  if (showInventory.value) showMarket.value = false
}

async function handleBuy(slug: string) {
  buyingSlug.value = slug
  buyError.value = null
  buySuccess.value = null
  try {
    const result = await api.buyItem(slug, 1)
    if (result.success) {
      buySuccess.value = `购买成功：${result.item.name}，消耗 ${result.cost} 💎`
      await store.loadInventory()
      await store.loadProfile()
    }
  } catch (e: unknown) {
    buyError.value = e instanceof Error ? e.message : '购买失败'
  } finally {
    buyingSlug.value = null
    setTimeout(() => { buySuccess.value = null }, 3000)
  }
}

watch(() => store.chatMessages.length, async () => {
  await nextTick()
  scrollChatToBottom()
})

onMounted(async () => {
  await store.loadProfile()
  await Promise.all([
    store.loadChatMessages('salon'),
    store.loadMarketRates(),
    store.loadInventory(),
    store.loadZones(),
  ])
  await nextTick()
  scrollChatToBottom()
})
</script>

<style scoped>
.salon-view {
  min-height: 100vh;
  background: #f0fdf4;
  font-family: 'Courier New', Courier, monospace;
}


.zone-body {
  max-width: 1100px;
  margin: 0 auto;
  padding: 20px 16px;
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 20px;
}

.main-panel {
  background: #fff;
  display: flex;
  flex-direction: column;
  height: calc(100vh - 140px);
  min-height: 400px;
}

.panel-title {
  font-size: 15px;
  font-weight: 900;
  margin: 0 0 12px;
  padding: 14px 16px 0;
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
  border-left: 3px solid #000;
  background: #f9f9f9;
}

.system-message {
  border-left-color: #f59e0b;
  background: #fffbeb;
  font-style: italic;
}

.message-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
}

.message-sender { font-weight: 700; font-size: 13px; }
.message-time { font-size: 11px; color: #888; }

.message-content {
  margin: 0;
  font-size: 14px;
  line-height: 1.5;
  word-break: break-word;
}

.message-tells {
  margin-top: 4px;
  border-top: 1px dashed #ccc;
  padding-top: 4px;
}

.tell-text {
  margin: 2px 0;
  font-style: italic;
  font-size: 12px;
  color: #888;
}

.empty-chat {
  text-align: center;
  padding: 40px 0;
  color: #888;
  font-style: italic;
}

.chat-input-row {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  border-top: 2px solid #000;
}

.chat-input {
  flex: 1;
  border: 2px solid #000;
  padding: 8px 12px;
  font-family: inherit;
  font-size: 14px;
  outline: none;
  background: #fff;
}

.chat-input:focus { background: #fffdf0; }

.speak-btn {
  background: #22c55e;
  color: #000;
  font-weight: 700;
}

/* Side Panel */
.side-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
  overflow-y: auto;
  max-height: calc(100vh - 140px);
}

.zone-desc {
  background: #fff;
  padding: 0 0 14px;
}

.zone-info {
  background: #fff;
  padding: 0 0 14px;
}

.desc-text {
  font-size: 12px;
  color: #555;
  line-height: 1.6;
  margin: 0;
  padding: 0 14px;
}

.desc-text + .desc-text { margin-top: 4px; }

.actions-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  padding: 0 14px;
}

.action-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 14px 8px;
  font-size: 13px;
  cursor: pointer;
  color: #000;
  background: #fff;
  transition: transform 0.1s;
}

.action-btn:hover:not(:disabled) {
  transform: translate(-2px, -2px);
  box-shadow: 5px 5px 0 #000;
}

.action-btn.active { background: #fef08a; }

.action-icon { font-size: 22px; }
.action-label { font-weight: 700; font-size: 13px; }
.action-result { font-size: 11px; color: #22c55e; font-weight: 700; }

.rest-btn { background: #fffbeb; }
.market-btn { background: #fff7ed; }
.inventory-btn { background: #f0f4ff; }

.market-panel { background: #fff; padding: 0 0 14px; }

.market-list {
  padding: 0 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.market-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  border: 1px solid #ddd;
  background: #fafafa;
  gap: 10px;
}

.market-item-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.market-item-name { font-weight: 700; font-size: 13px; }

.market-item-price {
  font-size: 12px;
  color: #555;
  display: flex;
  align-items: center;
  gap: 6px;
}

.demand-badge {
  font-size: 10px;
  font-weight: 700;
  padding: 1px 5px;
  border: 1px solid #000;
}

.demand-high { background: #fca5a5; }
.demand-normal { background: #d1fae5; }
.demand-low { background: #e5e7eb; }

.buy-btn {
  background: #fef08a;
  font-size: 12px;
  padding: 4px 10px;
  white-space: nowrap;
}

.inventory-panel { background: #fff; padding: 0 0 14px; }

.inventory-list {
  padding: 0 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.inventory-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 10px;
  border: 1px solid #ddd;
  background: #fafafa;
}

.item-icon { font-size: 20px; }

.item-info {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
}

.item-name { font-weight: 700; font-size: 13px; }

.item-tier {
  font-size: 11px;
  background: #e0e0e0;
  padding: 1px 5px;
  border: 1px solid #000;
  font-weight: 700;
}

.item-qty { font-weight: 700; font-size: 13px; color: #555; }

.empty-panel {
  text-align: center;
  padding: 20px;
  color: #888;
  font-style: italic;
  font-size: 13px;
}

.panel-error {
  color: #dc2626;
  font-weight: 700;
  font-size: 13px;
  padding: 0 14px;
  margin: 8px 0 0;
}

.panel-success {
  color: #16a34a;
  font-weight: 700;
  font-size: 13px;
  padding: 0 14px;
  margin: 8px 0 0;
}

.neo-brutal-card {
  border: 2px solid #000;
  box-shadow: 4px 4px 0 #000;
}

.neo-brutal-button {
  display: inline-block;
  border: 2px solid #000;
  box-shadow: 3px 3px 0 #000;
  background: #fff;
  color: #000;
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
  box-shadow: 4px 4px 0 #000;
}

.neo-brutal-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.back-btn {
  font-size: 14px;
  padding: 6px 12px;
  white-space: nowrap;
}

@media (max-width: 768px) {
  .zone-body { grid-template-columns: 1fr; }
  .main-panel { height: 400px; }
  .side-panel { max-height: none; }
}
</style>
