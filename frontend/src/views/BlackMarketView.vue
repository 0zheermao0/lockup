<template>
  <div class="blackmarket-view">
    <ZoneHeader title="💹 黑市" :player-badge="playerCount + ' 人在线'" />

    <div class="zone-body">
      <!-- Left: Chat -->
      <section class="main-panel neo-brutal-card">
        <h2 class="panel-title">街道通讯</h2>
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
          </div>
          <div v-if="store.chatMessages.length === 0" class="empty-chat">
            <p>街道一片死寂…</p>
          </div>
        </div>
        <div class="chat-input-row">
          <input
            v-model="chatInput"
            type="text"
            class="chat-input"
            placeholder="在街道上发言…"
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
          <h2 class="panel-title">💹 黑市说明</h2>
          <p class="desc-text">走私者的集散地，隐藏在男娘幻城的阴暗角落。</p>
          <p class="desc-text">备皮刀可在此以 <strong>70%</strong> 汇率洗白为脱毛仪，悄然完成交易。</p>
        </div>

        <!-- ② 信息框：洗白操作 -->
        <div class="bm-launder neo-brutal-card">
          <h2 class="panel-title">🧪 备皮刀洗白</h2>
          <div class="launder-info">
            <p class="launder-rate">转换率：<strong>70%</strong></p>
            <p class="launder-stock">当前备皮刀：<strong>{{ store.crystals?.raw_crystals ?? 0 }}</strong></p>
          </div>
          <div class="launder-form">
            <label class="launder-label">洗白数量</label>
            <input
              v-model.number="launderAmount"
              type="number"
              min="1"
              :max="store.crystals?.raw_crystals ?? 0"
              class="launder-input"
            />
            <p class="launder-preview">
              预计获得：<strong>{{ Math.floor((launderAmount || 0) * 0.7) }}</strong> 脱毛仪
            </p>
            <button
              class="neo-brutal-button launder-btn"
              :disabled="laundering || !launderAmount || launderAmount < 1"
              @click="handleLaunder"
            >
              {{ laundering ? '洗白中…' : '确认洗白' }}
            </button>
          </div>
          <p v-if="launderResult" class="launder-result">{{ launderResult }}</p>
          <p v-if="launderError" class="panel-error">{{ launderError }}</p>
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

const launderAmount = ref(1)
const laundering = ref(false)
const launderResult = ref<string | null>(null)
const launderError = ref<string | null>(null)

const playerCount = computed(() => {
  const zone = store.zones.find(z => z.name === 'black_market')
  return zone?.player_count ?? 0
})

function formatTime(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
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

async function handleLaunder() {
  if (!launderAmount.value || launderAmount.value < 1) return
  laundering.value = true
  launderError.value = null
  launderResult.value = null
  try {
    const result = await api.bmLaunder(launderAmount.value)
    if (result.success) {
      launderResult.value = `洗白成功：消耗 ${result.raw_consumed} 备皮刀，获得 ${result.purified_gained} 脱毛仪。`
      launderAmount.value = 1
      await store.loadProfile()
      setTimeout(() => { launderResult.value = null }, 4000)
    }
  } catch (e: unknown) {
    launderError.value = e instanceof Error ? e.message : '洗白失败'
  } finally {
    laundering.value = false
  }
}

watch(() => store.chatMessages.length, async () => {
  await nextTick()
  scrollChatToBottom()
})

onMounted(async () => {
  await store.loadProfile()
  await Promise.all([
    store.loadChatMessages('black_market'),
    store.loadZones(),
  ])
  await nextTick()
  scrollChatToBottom()
})
</script>

<style scoped>
.blackmarket-view {
  min-height: 100vh;
  background: #1a1a2e;
  font-family: 'Courier New', Courier, monospace;
  color: #e0e0e0;
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
  background: #111;
  border-color: #444;
  box-shadow: 4px 4px 0 #444;
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
  color: #f0c040;
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
  border-left: 3px solid #f0c040;
  background: #1a1a1a;
}

.system-message {
  border-left-color: #666;
  background: #222;
  font-style: italic;
}

.message-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
}

.message-sender { font-weight: 700; font-size: 13px; color: #f0c040; }
.message-time { font-size: 11px; color: #666; }

.message-content {
  margin: 0;
  font-size: 14px;
  line-height: 1.5;
  word-break: break-word;
  color: #ccc;
}

.empty-chat {
  text-align: center;
  padding: 40px 0;
  color: #555;
  font-style: italic;
}

.chat-input-row {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  border-top: 2px solid #444;
}

.chat-input {
  flex: 1;
  border: 2px solid #444;
  padding: 8px 12px;
  font-family: inherit;
  font-size: 14px;
  outline: none;
  background: #222;
  color: #e0e0e0;
}

.chat-input:focus { border-color: #f0c040; }

.speak-btn {
  background: #f0c040;
  color: #000;
  font-weight: 700;
  border-color: #f0c040;
}

.side-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
  overflow-y: auto;
  max-height: calc(100vh - 140px);
}

.zone-desc {
  background: #111;
  border-color: #444;
  box-shadow: 4px 4px 0 #444;
  padding: 0 0 14px;
}

.zone-desc .panel-title { color: #f0c040; }

.desc-text {
  font-size: 12px;
  color: #aaa;
  line-height: 1.6;
  margin: 0;
  padding: 0 14px;
}

.desc-text + .desc-text { margin-top: 4px; }
.desc-text strong { color: #f0c040; }

.bm-launder {
  background: #111;
  border-color: #f0c040;
  box-shadow: 4px 4px 0 #f0c040;
  padding: 0 0 14px;
}

.bm-launder .panel-title { color: #f0c040; }

.launder-info { padding: 0 14px; margin-bottom: 10px; }
.launder-rate { font-size: 13px; color: #aaa; margin: 0 0 4px; }
.launder-rate strong { color: #f0c040; }
.launder-stock { font-size: 13px; color: #aaa; margin: 0; }
.launder-stock strong { color: #e0e0e0; }

.launder-form {
  padding: 0 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.launder-label { font-size: 12px; color: #888; }

.launder-input {
  border: 2px solid #444;
  background: #222;
  color: #e0e0e0;
  padding: 6px 10px;
  font-family: inherit;
  font-size: 13px;
  outline: none;
}

.launder-input:focus { border-color: #f0c040; }

.launder-preview { font-size: 12px; color: #888; margin: 0; }
.launder-preview strong { color: #f0c040; }

.launder-btn {
  background: #f0c040;
  color: #000;
  border-color: #f0c040;
  font-weight: 700;
  font-size: 13px;
}

.launder-result {
  margin: 8px 14px 0;
  font-size: 12px;
  font-weight: 700;
  color: #4ade80;
}

.panel-error {
  color: #f87171;
  font-weight: 700;
  font-size: 13px;
  padding: 0 14px;
  margin: 8px 0 0;
}

.neo-brutal-card {
  border: 2px solid #444;
  box-shadow: 4px 4px 0 #444;
}

.neo-brutal-button {
  display: inline-block;
  border: 2px solid #555;
  box-shadow: 3px 3px 0 #555;
  background: #222;
  color: #e0e0e0;
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
  box-shadow: 4px 4px 0 #555;
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
