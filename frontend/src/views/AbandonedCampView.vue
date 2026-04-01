<template>
  <div class="camp-view">
    <ZoneHeader title="⛺ 更衣室" :player-badge="playerCount + ' 人在线'" />

    <div class="zone-body">
      <!-- Left: Chat -->
      <section class="main-panel neo-brutal-card">
        <h2 class="panel-title">营地通讯</h2>
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
            <p>营地里只有风声…</p>
          </div>
        </div>
        <div class="chat-input-row">
          <input
            v-model="chatInput"
            type="text"
            class="chat-input"
            placeholder="在营地发言…"
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
          <h2 class="panel-title">⛺ 营地说明</h2>
          <p class="desc-text">安检口与备皮间之间的废弃驻扎点，进入时自动轻度补觉。</p>
          <p class="desc-text">进入营地自动降低 <strong>5</strong> 点发毛值，不如闺房安全，但胜在无人问津。</p>
          <div v-if="store.mimicProfile" class="suppression-display">
            <span class="supp-label">当前发毛值</span>
            <span class="supp-value" :class="suppressionClass">
              {{ store.mimicProfile.suppression_value }}%
            </span>
          </div>
        </div>

        <!-- ② 信息框：营地互助 -->
        <div class="camp-aid neo-brutal-card">
          <h2 class="panel-title">🤝 营地互助</h2>

          <!-- 分享食物 -->
          <div class="aid-section">
            <h4 class="aid-subtitle">分享食物</h4>
            <p v-if="!hasConsumables" class="aid-hint">（需要背包中有消耗品）</p>
            <select v-model="shareTarget" class="aid-select" :disabled="!hasConsumables">
              <option :value="null">选择目标玩家</option>
              <option v-for="p in campPlayers" :key="p.id" :value="p.id">
                {{ p.username }}
              </option>
            </select>
            <button
              class="neo-brutal-button share-btn"
              :disabled="!hasConsumables || !shareTarget || sharingFood"
              @click="handleShareFood"
            >
              {{ sharingFood ? '分享中…' : '分享食物（目标-10压制）' }}
            </button>
          </div>

          <!-- 哨岗警戒 -->
          <div class="aid-section">
            <h4 class="aid-subtitle">哨岗警戒</h4>
            <p v-if="activeWatchers.length" class="watchers-list">
              值班中：{{ activeWatchers.map(w => w.username).join('、') }}
            </p>
            <button
              class="neo-brutal-button watch-btn"
              :disabled="isOnWatch || startingWatch"
              @click="handleStartWatch"
            >
              {{ isOnWatch ? `值班中（${watchCountdown}）` : '开始站岗（10分钟）' }}
            </button>
          </div>

          <p v-if="aidResult" class="panel-success">{{ aidResult }}</p>
          <p v-if="aidError" class="panel-error">{{ aidError }}</p>
        </div>

        <!-- ③ 地图 -->
        <MiniMap />

      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { usePhantomCityStore } from '../stores/phantomCity'
import * as api from '../lib/api-game'
import MiniMap from '../components/game/MiniMap.vue'
import ZoneHeader from '../components/game/ZoneHeader.vue'

const store = usePhantomCityStore()

const chatInput = ref('')
const speaking = ref(false)
const chatContainer = ref<HTMLElement | null>(null)

const campPlayers = ref<Array<{id: number; username: string}>>([])
const activeWatchers = ref<Array<{id: number; username: string}>>([])
const shareTarget = ref<number | null>(null)
const sharingFood = ref(false)
const startingWatch = ref(false)
const isOnWatch = ref(false)
const watchUntil = ref<string | null>(null)
const watchCountdown = ref('')
const aidResult = ref<string | null>(null)
const aidError = ref<string | null>(null)

let watchTimer: ReturnType<typeof setInterval> | null = null

const hasConsumables = computed(() =>
  store.inventory.some(inv => inv.item.slot === 'consumable' && inv.quantity > 0)
)

const playerCount = computed(() => {
  const zone = store.zones.find(z => z.name === 'abandoned_camp')
  return zone?.player_count ?? 0
})

const suppressionClass = computed(() => {
  const v = store.mimicProfile?.suppression_value ?? 0
  if (v >= 80) return 'supp-red'
  if (v >= 40) return 'supp-orange'
  return 'supp-green'
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

async function loadCampPlayers() {
  try {
    const players = await api.getZonePlayers('abandoned_camp')
    campPlayers.value = (players as Array<{id: number; username: string}>)
      .filter(p => p.username !== store.mimicProfile?.username)
  } catch {
    // 静默失败
  }
}

async function loadActiveWatches() {
  try {
    const watches = await api.campActiveWatches()
    activeWatchers.value = watches
  } catch {
    // 静默失败
  }
}

function updateWatchCountdown() {
  if (!watchUntil.value) return
  const remaining = Math.max(0, Math.floor((new Date(watchUntil.value).getTime() - Date.now()) / 1000))
  if (remaining === 0) {
    isOnWatch.value = false
    watchUntil.value = null
    watchCountdown.value = ''
    if (watchTimer) clearInterval(watchTimer)
  } else {
    const m = Math.floor(remaining / 60)
    const s = remaining % 60
    watchCountdown.value = `${m}:${s.toString().padStart(2, '0')}`
  }
}

async function handleShareFood() {
  if (!shareTarget.value) return
  sharingFood.value = true
  aidError.value = null
  aidResult.value = null
  try {
    const result = await api.campShareFood(shareTarget.value)
    if (result.success) {
      aidResult.value = `已分享 ${result.item_used}，对方发毛值降至 ${result.recipient_suppression}%。+1 coin，光滑度+2。`
      shareTarget.value = null
      await store.loadProfile()
      await store.loadInventory()
      setTimeout(() => { aidResult.value = null }, 4000)
    }
  } catch (e: unknown) {
    aidError.value = e instanceof Error ? e.message : '分享失败'
  } finally {
    sharingFood.value = false
  }
}

async function handleStartWatch() {
  startingWatch.value = true
  aidError.value = null
  try {
    const result = await api.campStartWatch()
    if (result.success) {
      isOnWatch.value = true
      watchUntil.value = result.watch_until
      updateWatchCountdown()
      watchTimer = setInterval(updateWatchCountdown, 1000)
      aidResult.value = '已开始站岗警戒（10分钟）。'
      setTimeout(() => { aidResult.value = null }, 3000)
    }
  } catch (e: unknown) {
    aidError.value = e instanceof Error ? e.message : '站岗失败'
  } finally {
    startingWatch.value = false
  }
}

watch(() => store.chatMessages.length, async () => {
  await nextTick()
  scrollChatToBottom()
})

onMounted(async () => {
  await store.loadProfile()
  await Promise.all([
    store.loadChatMessages('abandoned_camp'),
    store.loadZones(),
    store.loadInventory(),
  ])
  await Promise.all([
    loadCampPlayers(),
    loadActiveWatches(),
  ])
  await nextTick()
  scrollChatToBottom()
})

onUnmounted(() => {
  if (watchTimer) clearInterval(watchTimer)
})
</script>

<style scoped>
.camp-view {
  min-height: 100vh;
  background: #f5f0e8;
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
  border-left: 3px solid #d4a017;
  background: #f9f9f9;
}

.system-message {
  border-left-color: #888;
  background: #f3f4f6;
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
  background: #d4a017;
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

.desc-text {
  font-size: 12px;
  color: #555;
  line-height: 1.6;
  margin: 0;
  padding: 0 14px;
}

.desc-text + .desc-text { margin-top: 4px; }

.suppression-display {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px 0;
}

.supp-label { font-size: 13px; color: #666; }

.supp-value {
  font-weight: 900;
  font-size: 18px;
}

.supp-green { color: #16a34a; }
.supp-orange { color: #d97706; }
.supp-red { color: #dc2626; }

/* Camp Aid */
.camp-aid {
  background: #fff;
  padding: 0 0 14px;
}

.aid-section {
  padding: 10px 14px 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.aid-subtitle {
  font-size: 13px;
  font-weight: 900;
  margin: 0;
  color: #555;
}

.aid-hint {
  font-size: 12px;
  color: #888;
  font-style: italic;
  margin: 0;
}

.aid-select {
  border: 2px solid #000;
  padding: 6px 8px;
  font-family: inherit;
  font-size: 13px;
  background: #fff;
  outline: none;
}

.share-btn {
  background: #fef3c7;
  font-size: 12px;
  padding: 5px 10px;
}

.watchers-list {
  font-size: 12px;
  color: #555;
  margin: 0;
  font-style: italic;
}

.watch-btn {
  background: #f0fdf4;
  font-size: 12px;
  padding: 5px 10px;
}

.panel-success {
  color: #16a34a;
  font-weight: 700;
  font-size: 13px;
  padding: 0 14px;
  margin: 8px 0 0;
}

.panel-error {
  color: #dc2626;
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
