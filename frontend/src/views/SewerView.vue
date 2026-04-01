<template>
  <div class="sewer-view">

    <!-- Header -->
    <ZoneHeader title="☠️ 下水道" danger-badge="污染区域" />

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

    <!-- Sewer Entry Warning -->
    <div class="sewer-warning-banner">
      <span class="warning-icon">⚠️</span>
      <span class="warning-text">进入下水道时发毛值 <strong>+10</strong> — 腐蚀性环境，快速通过！</span>
    </div>

    <!-- Body -->
    <div class="sewer-body">

      <!-- Left: Chat -->
      <section class="main-panel neo-brutal-card">
        <h2 class="panel-title">管道通讯</h2>
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
            <p>管道内只有腐蚀液体的流动声…</p>
          </div>
        </div>
        <div class="chat-input-row">
          <input
            v-model="chatInput"
            type="text"
            class="chat-input"
            placeholder="在管道中低声通讯…"
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
          <h2 class="panel-title">☠️ 管道说明</h2>
          <p class="info-text">贯通城市地下的腐蚀性排水网络，最快的绕行路线。</p>
          <p class="info-text">进入时发毛值 <strong class="cost">+10</strong>，污染环境，快速通过！</p>
          <p class="info-text highlight">右路地下：闺房 → 下水道 → 外围备皮间 → 备皮间</p>
        </div>

        <!-- ② 信息框：发毛值 + 遭遇战 -->
        <div class="zone-info neo-brutal-card">
          <h2 class="panel-title">⚡ 管道状态</h2>

          <!-- 发毛值显示 -->
          <div v-if="store.mimicProfile" class="supp-display">
            <span class="supp-label">当前发毛值</span>
            <span class="supp-value" :class="suppressionTextClass">
              {{ store.mimicProfile.suppression_value }}%
            </span>
          </div>

          <!-- 无遭遇 -->
          <div v-if="!encounterState?.triggered" class="no-encounter">
            <p class="info-text">管道内暂无其他人员。</p>
          </div>

          <!-- 遭遇战 -->
          <div v-else class="sewer-encounter">
            <!-- 小男娘互认（立即结算） -->
            <template v-if="encounterState.type === 'mimic_mimic'">
              <p class="encounter-desc">对方的锁在黑暗中发出熟悉的声响。</p>
              <p class="result-good">发毛值 -5 | 光滑度 +2 | +1 coin</p>
              <button class="neo-brutal-button dismiss-btn" @click="encounterState = null">知道了</button>
            </template>

            <!-- 小s视角 -->
            <template v-if="isPatrol && encounterState.type === 'patrol_mimic'">
              <p class="encounter-desc">快速检查 <strong>{{ encounterState.other_player?.username }}</strong>：</p>
              <div v-if="encounterState.tells?.length" class="tells-list">
                <p v-for="(tell, i) in encounterState.tells" :key="i" class="tell-item">{{ tell }}</p>
              </div>
              <p v-else class="no-tells">未发现明显破绽</p>
              <div class="demand-row">
                <label class="demand-label">收缴备皮刀数量</label>
                <input v-model.number="demandAmount" type="number" min="1" max="100" class="demand-input" />
                <div class="demand-btns">
                  <button
                    class="neo-brutal-button demand-btn"
                    :disabled="demandBusy"
                    @click="handleSewerDemand"
                  >
                    {{ demandBusy ? '收缴中…' : '收缴备皮刀' }}
                  </button>
                  <button class="neo-brutal-button dismiss-btn" @click="encounterState = null">放行</button>
                </div>
              </div>
            </template>

            <!-- 小男娘视角：等待 -->
            <template v-if="isMimic && encounterState.type === 'patrol_mimic'">
              <p class="encounter-desc"><strong>{{ encounterState.other_player?.username }}</strong> 拦住了你…</p>
              <p class="encounter-wait">等待对方处置</p>
            </template>

            <p v-if="encounterResult" class="encounter-result" :class="encounterResultClass">{{ encounterResult }}</p>
          </div>

          <p v-if="encounterError" class="panel-error">{{ encounterError }}</p>
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
import type { SewerEncounter } from '../lib/api-game'
import MiniMap from '../components/game/MiniMap.vue'
import ZoneHeader from '../components/game/ZoneHeader.vue'

const store = usePhantomCityStore()

const chatInput = ref('')
const speaking = ref(false)
const chatContainer = ref<HTMLElement | null>(null)

const isPatrol = computed(() => store.currentFaction === 'patrol')
const isMimic = computed(() => store.currentFaction === 'mimic')

// Encounter state
const encounterState = ref<SewerEncounter | null>(null)
const demandAmount = ref(20)
const demandBusy = ref(false)
const encounterResult = ref<string | null>(null)
const encounterResultClass = ref<string>('result-neutral')
const encounterError = ref<string | null>(null)

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

async function checkEncounter() {
  try {
    const result = await api.checkSewerEncounter()
    if (result.triggered) {
      encounterState.value = result
      if (result.type === 'mimic_mimic') {
        await store.loadProfile()
      }
    }
  } catch {
    // 静默失败
  }
}

async function handleSewerDemand() {
  if (!encounterState.value?.other_player) return
  demandBusy.value = true
  encounterError.value = null
  try {
    const result = await api.sewerDemand(encounterState.value.other_player.id, demandAmount.value)
    if (result.success) {
      encounterResult.value = `已收缴 ${result.crystals_seized} 备皮刀。+2 coins。`
      encounterResultClass.value = 'result-good'
      encounterState.value = null
    }
  } catch (e: unknown) {
    encounterError.value = e instanceof Error ? e.message : '操作失败'
  } finally {
    demandBusy.value = false
  }
}

watch(() => store.chatMessages.length, async () => {
  await nextTick()
  scrollChatToBottom()
})

onMounted(async () => {
  await store.loadProfile()
  await Promise.all([
    store.loadChatMessages('sewer'),
    store.loadZones(),
  ])
  await nextTick()
  scrollChatToBottom()
  await checkEncounter()
})
</script>

<style scoped>
.sewer-view {
  min-height: 100vh;
  background: #0a1a0a;
  font-family: 'Courier New', Courier, monospace;
  color: #a3e635;
}


/* Suppression Meter */
.suppression-meter-bar {
  background: #052e16;
  border-bottom: 2px solid #166534;
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
  color: #86efac;
  font-weight: 700;
  font-size: 13px;
  white-space: nowrap;
}

.meter-track {
  flex: 1;
  height: 14px;
  background: #14532d;
  border: 2px solid #166534;
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
  animation: sewer-pulse 0.8s infinite;
}

/* Warning Banner */
.sewer-warning-banner {
  background: #14532d;
  border-bottom: 2px solid #166534;
  padding: 8px 16px;
  display: flex;
  align-items: center;
  gap: 10px;
  max-width: 100%;
}

.warning-icon {
  font-size: 18px;
  flex-shrink: 0;
}

.warning-text {
  font-size: 13px;
  color: #86efac;
}

.warning-text strong {
  color: #f87171;
}

/* Body */
.sewer-body {
  max-width: 1100px;
  margin: 0 auto;
  padding: 20px 16px;
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 20px;
}

.main-panel {
  background: #052e16;
  border-color: #166534;
  box-shadow: 4px 4px 0 #14532d;
  display: flex;
  flex-direction: column;
  height: calc(100vh - 180px);
  min-height: 400px;
}

.panel-title {
  font-size: 15px;
  font-weight: 900;
  margin: 0 0 12px;
  padding: 14px 16px 0;
  color: #86efac;
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
  border-left: 3px solid #166534;
  background: #0a1a0a;
}

.system-message {
  border-left-color: #4ade80;
  background: #052e16;
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
  color: #86efac;
}

.message-time {
  font-size: 11px;
  color: #4ade80;
}

.message-content {
  margin: 0;
  font-size: 14px;
  line-height: 1.5;
  word-break: break-word;
  color: #a3e635;
}

.message-tells {
  margin-top: 4px;
  border-top: 1px dashed #166534;
  padding-top: 4px;
}

.tell-text {
  margin: 2px 0;
  font-style: italic;
  font-size: 12px;
  color: #4ade80;
}

.empty-chat {
  text-align: center;
  padding: 40px 0;
  color: #4ade80;
  font-style: italic;
}

.chat-input-row {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  border-top: 2px solid #166534;
}

.chat-input {
  flex: 1;
  border: 2px solid #166534;
  padding: 8px 12px;
  font-family: inherit;
  font-size: 14px;
  outline: none;
  background: #0a1a0a;
  color: #a3e635;
}

.chat-input:focus {
  border-color: #4ade80;
}

.speak-btn {
  background: #14532d;
  color: #86efac;
  border-color: #166534;
  font-weight: 700;
}

.side-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
  overflow-y: auto;
  max-height: calc(100vh - 180px);
}

.zone-desc {
  background: #052e16;
  border-color: #166534;
  box-shadow: 4px 4px 0 #14532d;
  padding: 14px 16px;
}

.zone-info {
  background: #052e16;
  border-color: #166534;
  box-shadow: 4px 4px 0 #14532d;
  padding: 0 0 14px;
}

.zone-info .panel-title {
  padding: 14px 16px 0;
}

.no-encounter {
  padding: 0 14px;
}

.sewer-encounter {
  padding: 0 14px;
}

.encounter-desc {
  font-size: 13px;
  color: #86efac;
  margin: 0 0 8px;
}

.tells-list {
  margin: 0 0 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.tell-item {
  font-size: 12px;
  color: #fbbf24;
  font-style: italic;
  margin: 0;
  border-left: 2px solid #fbbf24;
  padding-left: 6px;
}

.no-tells {
  font-size: 12px;
  color: #4ade80;
  font-style: italic;
  margin: 0 0 10px;
}

.demand-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.demand-label {
  font-size: 12px;
  color: #86efac;
}

.demand-input {
  border: 2px solid #166534;
  background: #0a1a0a;
  color: #a3e635;
  padding: 6px 10px;
  font-family: inherit;
  font-size: 13px;
  width: 100%;
  outline: none;
}

.demand-btns {
  display: flex;
  gap: 6px;
}

.demand-btn {
  background: #14532d;
  color: #86efac;
  border-color: #166534;
  font-size: 12px;
  padding: 5px 10px;
}

.dismiss-btn {
  background: #0a1a0a;
  color: #4ade80;
  border-color: #166534;
  font-size: 12px;
  padding: 5px 10px;
}

.encounter-wait {
  font-size: 12px;
  color: #4ade80;
  font-style: italic;
  margin: 0;
}

.encounter-result {
  margin: 8px 0 0;
  font-size: 12px;
  font-weight: 700;
  padding: 4px 6px;
  border: 1px solid currentColor;
}

.result-good { color: #4ade80; }
.result-bad { color: #f87171; }
.result-neutral { color: #86efac; }


.info-text {
  font-size: 13px;
  color: #4ade80;
  margin: 0 0 8px;
  line-height: 1.5;
}

.info-text .cost {
  color: #f87171;
}

.info-text.highlight {
  color: #86efac;
  font-weight: 700;
  border-left: 3px solid #166534;
  padding-left: 8px;
  margin-top: 8px;
}

.supp-display {
  padding: 0 14px;
  margin: 8px 0;
  display: flex;
  align-items: center;
  gap: 10px;
}

.supp-label {
  font-size: 12px;
  color: #4ade80;
}

.supp-value {
  font-weight: 900;
  font-size: 18px;
}

.panel-error {
  color: #f87171;
  font-weight: 700;
  font-size: 13px;
  padding: 0 14px;
  margin: 8px 0 0;
}

.neo-brutal-card {
  border: 2px solid #166534;
  box-shadow: 4px 4px 0 #14532d;
}

.neo-brutal-button {
  display: inline-block;
  border: 2px solid #166534;
  box-shadow: 3px 3px 0 #14532d;
  background: #052e16;
  color: #86efac;
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
  box-shadow: 4px 4px 0 #14532d;
}

.neo-brutal-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .sewer-body {
    grid-template-columns: 1fr;
  }
  .main-panel {
    height: 400px;
  }
  .side-panel {
    max-height: none;
  }
}
</style>
