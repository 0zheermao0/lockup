<template>
  <div class="armory-view">

    <!-- Header -->
    <ZoneHeader title="🗄️ 储物柜" :player-badge="playerCount + ' 人在线'" />

    <!-- Body -->
    <div class="armory-body">

      <!-- Left: Chat -->
      <section class="main-panel neo-brutal-card">
        <h2 class="panel-title">储物柜通讯</h2>
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
            <p>储物柜里回响着金属碰撞声…</p>
          </div>
        </div>
        <div class="chat-input-row">
          <input
            v-model="chatInput"
            type="text"
            class="chat-input"
            placeholder="在储物柜发言…"
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
          <h2 class="panel-title">🗄️ 储物柜说明</h2>
          <p class="info-text">闺房的军备仓库，绕过安检口的暗道入口就在这里。</p>
          <p class="info-text">无小s检查，但暗道中常有意外遭遇。</p>
          <p class="info-text highlight">左路迂回：闺房 → 储物柜 → 更衣室 → 备皮间</p>
        </div>

        <!-- ② 信息框：遭遇战 -->
        <div class="zone-info neo-brutal-card">
          <h2 class="panel-title">⚔️ 暗道状态</h2>

          <!-- 无遭遇 -->
          <div v-if="!encounterState?.triggered" class="no-encounter">
            <p class="info-text">暗道目前平静，未发现其他人员。</p>
          </div>

          <!-- 遭遇战面板 -->
          <div v-else class="armory-encounter">
            <p class="encounter-desc">
              <strong>{{ encounterState.other_player?.username }}</strong> 挡住了去路
            </p>

            <!-- 小s视角：索取通行费 -->
            <template v-if="isPatrol && !activeTollTxId">
              <div class="demand-row">
                <label class="demand-label">索取备皮刀数量</label>
                <input
                  v-model.number="demandAmount"
                  type="number"
                  min="1"
                  max="200"
                  class="demand-input"
                />
                <button
                  class="neo-brutal-button demand-btn"
                  :disabled="demanding"
                  @click="handleTollDemand"
                >
                  {{ demanding ? '发起中…' : '索取通行费' }}
                </button>
              </div>
            </template>

            <!-- 小男娘视角：收到索取 -->
            <template v-if="isMimic && activeTollTxId">
              <p class="toll-amount">对方索取通行费，请选择应对方式：</p>
              <div class="encounter-actions">
                <button
                  class="neo-brutal-button pay-btn"
                  :disabled="encounterBusy"
                  @click="handlePayToll"
                >
                  💰 支付（光滑度+3，压制-5）
                </button>
                <button
                  class="neo-brutal-button resist-btn"
                  :disabled="encounterBusy"
                  @click="handleResistToll"
                >
                  ⚔️ 抵抗（control_resistance检定）
                </button>
                <button
                  class="neo-brutal-button flee-armory-btn"
                  :disabled="encounterBusy"
                  @click="handleFleeArmory"
                >
                  🏃 溜走（+15压制，-3纯净）
                </button>
              </div>
            </template>

            <!-- 小男娘等待（无toll）-->
            <template v-if="isMimic && !activeTollTxId">
              <p class="encounter-wait">对方正在考虑如何处置你…</p>
              <button
                class="neo-brutal-button flee-armory-btn"
                :disabled="encounterBusy"
                @click="handleFleeArmory"
              >
                🏃 溜走（+15压制，-3纯净）
              </button>
            </template>

            <p v-if="encounterResult" class="encounter-result" :class="encounterResultClass">
              {{ encounterResult }}
            </p>
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
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { usePhantomCityStore } from '../stores/phantomCity'
import * as api from '../lib/api-game'
import type { ArmoryEncounter } from '../lib/api-game'
import MiniMap from '../components/game/MiniMap.vue'
import ZoneHeader from '../components/game/ZoneHeader.vue'

const store = usePhantomCityStore()
const router = useRouter()

const chatInput = ref('')
const speaking = ref(false)
const chatContainer = ref<HTMLElement | null>(null)

const isPatrol = computed(() => store.currentFaction === 'patrol')
const isMimic = computed(() => store.currentFaction === 'mimic')

// Encounter state
const encounterState = ref<ArmoryEncounter | null>(null)
const activeTollTxId = ref<string | null>(null)
const demandAmount = ref(30)
const demanding = ref(false)
const encounterBusy = ref(false)
const encounterResult = ref<string | null>(null)
const encounterResultClass = ref<string>('result-neutral')
const encounterError = ref<string | null>(null)

let encounterPollTimer: ReturnType<typeof setInterval> | null = null

const playerCount = computed(() => {
  const zone = store.zones.find(z => z.name === 'armory')
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

async function checkEncounter() {
  try {
    const result = await api.checkArmoryEncounter()
    if (result.triggered) {
      encounterState.value = result
    }
  } catch {
    // 静默失败
  }
}

async function handleTollDemand() {
  if (!encounterState.value?.other_player) return
  demanding.value = true
  encounterError.value = null
  try {
    const result = await api.armoryTollDemand(encounterState.value.other_player.id, demandAmount.value)
    if (result.success) {
      encounterResult.value = `已向对方索取 ${demandAmount.value} 备皮刀，等待回应…`
      encounterResultClass.value = 'result-neutral'
    }
  } catch (e: unknown) {
    encounterError.value = e instanceof Error ? e.message : '操作失败'
  } finally {
    demanding.value = false
  }
}

async function handlePayToll() {
  if (!activeTollTxId.value) return
  encounterBusy.value = true
  encounterError.value = null
  try {
    const result = await api.armoryTollPay(activeTollTxId.value)
    if (result.success) {
      encounterResult.value = `已支付 ${result.crystals_paid} 备皮刀。光滑度+3，发毛值-5。`
      encounterResultClass.value = 'result-good'
      activeTollTxId.value = null
      encounterState.value = null
      await store.loadProfile()
    }
  } catch (e: unknown) {
    encounterError.value = e instanceof Error ? e.message : '支付失败'
  } finally {
    encounterBusy.value = false
  }
}

async function handleResistToll() {
  if (!activeTollTxId.value) return
  encounterBusy.value = true
  encounterError.value = null
  try {
    const result = await api.armoryTollResist(activeTollTxId.value)
    if (result.success) {
      if (result.escaped) {
        encounterResult.value = `成功抵抗！发毛值+5，光滑度+5，+2 coins。`
        encounterResultClass.value = 'result-good'
      } else {
        encounterResult.value = `抵抗失败！被强制收缴 ${result.crystals_seized ?? 0} 备皮刀。发毛值+15，光滑度-3。`
        encounterResultClass.value = 'result-bad'
      }
      activeTollTxId.value = null
      encounterState.value = null
      await store.loadProfile()
    }
  } catch (e: unknown) {
    encounterError.value = e instanceof Error ? e.message : '操作失败'
  } finally {
    encounterBusy.value = false
  }
}

async function handleFleeArmory() {
  encounterBusy.value = true
  encounterError.value = null
  try {
    const result = await api.armoryFlee()
    if (result.success) {
      router.push('/phantom-city/salon')
    }
  } catch (e: unknown) {
    encounterError.value = e instanceof Error ? e.message : '溜走失败'
  } finally {
    encounterBusy.value = false
  }
}

watch(() => store.chatMessages.length, async () => {
  await nextTick()
  scrollChatToBottom()
})

onMounted(async () => {
  await store.loadProfile()
  await Promise.all([
    store.loadChatMessages('armory'),
    store.loadZones(),
  ])
  await nextTick()
  scrollChatToBottom()
  // 进入时检查遭遇
  await checkEncounter()
  // 每15秒轮询
  encounterPollTimer = setInterval(checkEncounter, 15000)
})

onUnmounted(() => {
  if (encounterPollTimer) clearInterval(encounterPollTimer)
})
</script>

<style scoped>
.armory-view {
  min-height: 100vh;
  background: #1c1c1e;
  font-family: 'Courier New', Courier, monospace;
  color: #e5e7eb;
}


.armory-body {
  max-width: 1100px;
  margin: 0 auto;
  padding: 20px 16px;
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 20px;
}

.main-panel {
  background: #1f2937;
  border-color: #4b5563;
  box-shadow: 4px 4px 0 #374151;
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
  color: #f3f4f6;
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
  border-left: 3px solid #6b7280;
  background: #111827;
}

.system-message {
  border-left-color: #9ca3af;
  background: #1f2937;
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
  color: #d1d5db;
}

.message-time {
  font-size: 11px;
  color: #6b7280;
}

.message-content {
  margin: 0;
  font-size: 14px;
  line-height: 1.5;
  word-break: break-word;
  color: #e5e7eb;
}

.message-tells {
  margin-top: 4px;
  border-top: 1px dashed #4b5563;
  padding-top: 4px;
}

.tell-text {
  margin: 2px 0;
  font-style: italic;
  font-size: 12px;
  color: #9ca3af;
}

.empty-chat {
  text-align: center;
  padding: 40px 0;
  color: #6b7280;
  font-style: italic;
}

.chat-input-row {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  border-top: 2px solid #4b5563;
}

.chat-input {
  flex: 1;
  border: 2px solid #4b5563;
  padding: 8px 12px;
  font-family: inherit;
  font-size: 14px;
  outline: none;
  background: #111827;
  color: #e5e7eb;
}

.chat-input:focus {
  border-color: #6b7280;
}

.speak-btn {
  background: #374151;
  color: #e5e7eb;
  border-color: #6b7280;
  font-weight: 700;
}

.side-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
  overflow-y: auto;
  max-height: calc(100vh - 140px);
}

.zone-desc {
  background: #1f2937;
  border-color: #4b5563;
  box-shadow: 4px 4px 0 #374151;
  padding: 14px 16px;
}

.zone-info {
  background: #1f2937;
  border-color: #4b5563;
  box-shadow: 4px 4px 0 #374151;
  padding: 0 0 14px;
}

.no-encounter {
  padding: 0 14px;
}

/* Encounter Panel (inside zone-info) */
.armory-encounter {
  padding: 0 14px;
}

.encounter-desc {
  font-size: 13px;
  color: #d1d5db;
  margin: 0 0 12px;
}

.demand-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.demand-label {
  font-size: 12px;
  color: #9ca3af;
}

.demand-input {
  border: 2px solid #4b5563;
  background: #111827;
  color: #e5e7eb;
  padding: 6px 10px;
  font-family: inherit;
  font-size: 13px;
  width: 100%;
  outline: none;
}

.demand-btn {
  background: #f97316;
  color: #000;
  border-color: #f97316;
  font-weight: 700;
  font-size: 13px;
}

.toll-amount {
  font-size: 13px;
  color: #fbbf24;
  margin: 0 0 10px;
  font-weight: 700;
}

.encounter-actions {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.pay-btn {
  background: #065f46;
  color: #d1fae5;
  border-color: #059669;
  font-size: 12px;
  padding: 6px 10px;
}

.resist-btn {
  background: #7c2d12;
  color: #fed7aa;
  border-color: #ea580c;
  font-size: 12px;
  padding: 6px 10px;
}

.flee-armory-btn {
  background: #1f2937;
  color: #9ca3af;
  border-color: #4b5563;
  font-size: 12px;
  padding: 6px 10px;
}

.encounter-wait {
  font-size: 12px;
  color: #9ca3af;
  font-style: italic;
  margin: 0 0 8px;
}

.encounter-result {
  margin: 8px 0 0;
  font-size: 12px;
  font-weight: 700;
  padding: 6px 8px;
  border: 1px solid currentColor;
}

.result-good { color: #4ade80; }
.result-bad { color: #f87171; }
.result-neutral { color: #d1d5db; }


.info-text {
  font-size: 13px;
  color: #9ca3af;
  margin: 0 0 8px;
  line-height: 1.5;
}

.info-text.highlight {
  color: #d1d5db;
  font-weight: 700;
  border-left: 3px solid #6b7280;
  padding-left: 8px;
  margin-top: 8px;
}

.panel-error {
  color: #f87171;
  font-weight: 700;
  font-size: 13px;
  padding: 0 14px;
  margin: 8px 0 0;
}

.neo-brutal-card {
  border: 2px solid #4b5563;
  box-shadow: 4px 4px 0 #374151;
}

.neo-brutal-button {
  display: inline-block;
  border: 2px solid #4b5563;
  box-shadow: 3px 3px 0 #374151;
  background: #1f2937;
  color: #e5e7eb;
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
  box-shadow: 4px 4px 0 #374151;
}

.neo-brutal-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .armory-body {
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
