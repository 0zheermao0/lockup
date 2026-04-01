<template>
  <div class="checkpoint-view">

    <!-- Header -->
    <ZoneHeader
      title="🚧 安检口"
      :extra-badge="store.checkpointSession ? (store.checkpointSession.status === 'active' ? '会话进行中' : '会话已关闭') : undefined"
      :extra-badge-class="store.checkpointSession?.status === 'active' ? 'badge-active-extra' : 'badge-closed-extra'"
    />

    <!-- Pending Interrogation Banner (targeting me) -->
    <div v-if="pendingInterrogation" class="interrogation-banner neo-brutal-card">
      <div class="interrogation-banner-header">
        <span class="interro-icon">💬</span>
        <strong>盘问中！</strong>
        <span class="interro-from">来自 {{ pendingInterrogation.interrogator.username }}</span>
        <span class="interro-countdown" :class="{ urgent: interroCountdown <= 10 }">
          {{ interroCountdown }}s
        </span>
      </div>
      <p class="interro-question">{{ pendingInterrogation.question }}</p>
      <div class="interro-input-row">
        <input
          v-model="interroResponse"
          type="text"
          class="interro-input"
          placeholder="输入回答…"
          maxlength="300"
          @keydown.enter="handleRespond"
        />
        <button
          class="neo-brutal-button respond-btn"
          :disabled="responding || !interroResponse.trim()"
          @click="handleRespond"
        >
          {{ responding ? '回答中…' : '回答' }}
        </button>
      </div>
      <p v-if="respondError" class="panel-error">{{ respondError }}</p>
    </div>

    <!-- Main Layout -->
    <div class="checkpoint-body">

      <!-- LEFT: Queue Panel -->
      <div class="queue-panel">
        <h2 class="panel-title">
          混合队列
          <span class="queue-count" v-if="store.checkpointSession">
            ({{ totalQueueSize }} 人)
          </span>
        </h2>

        <div v-if="!store.checkpointSession" class="empty-panel">
          <p>暂无安检口会话</p>
          <button class="neo-brutal-button" @click="loadAll">刷新</button>
        </div>

        <div v-else class="queue-list">

          <!-- Real Players -->
          <div
            v-for="participant in store.checkpointSession.participants"
            :key="participant.id"
            class="queue-item real-player"
            :class="outcomeClass(participant.outcome)"
          >
            <div class="queue-item-header">
              <div class="queue-avatar">
                <img
                  v-if="participant.user.avatar"
                  :src="participant.user.avatar"
                  :alt="participant.user.username"
                  class="avatar-img"
                />
                <span v-else class="avatar-placeholder">
                  {{ participant.user.username[0].toUpperCase() }}
                </span>
              </div>
              <div class="queue-item-info">
                <span class="queue-item-name">{{ participant.user.username }}</span>
                <span class="queue-outcome-badge" :class="outcomeClass(participant.outcome)">
                  {{ outcomeLabel(participant.outcome) }}
                </span>
              </div>
              <span v-if="participant.queue_position !== null" class="queue-position">
                #{{ participant.queue_position }}
              </span>
            </div>

            <!-- Tells (shown for all visible players) -->
            <div v-if="participantTells(participant.id).length" class="player-tells">
              <p
                v-for="(tell, i) in participantTells(participant.id)"
                :key="i"
                class="tell-line"
              >{{ tell }}</p>
            </div>

            <!-- Waiting status for smuggler -->
            <div v-if="isMimic && participant.outcome === 'pending' && participant.user.username === store.mimicProfile?.username" class="smuggler-status">
              <span class="waiting-label">等待通过</span>
              <div class="flee-section">
                <p class="flee-cost">溜走代价：发毛值 +20，光滑度 -5</p>
                <button
                  class="neo-brutal-button flee-btn"
                  :disabled="actionBusy || fleeing"
                  @click="handleFlee"
                >
                  {{ fleeing ? '溜走中…' : '🏃 溜走队列' }}
                </button>
              </div>
            </div>

            <!-- Patrol Action Buttons -->
            <div v-if="isPatrol && participant.outcome === 'pending'" class="patrol-actions">
              <button
                class="neo-brutal-button action-inspect"
                :disabled="actionBusy"
                @click="handleInspect(participant.user.id)"
              >
                🔍 检查
              </button>
              <button
                class="neo-brutal-button action-interrogate"
                :disabled="actionBusy"
                @click="openInterrogateModal(participant.user.id, participant.user.username)"
              >
                💬 盘问
              </button>
              <button
                class="neo-brutal-button action-patdown"
                :disabled="actionBusy || getSuspicion(participant.user.id) < 30"
                :title="getSuspicion(participant.user.id) < 30 ? '需要可疑度≥30' : '体检'"
                @click="handlePatDown(participant.user.id)"
              >
                🔒 体检
              </button>
              <button
                class="neo-brutal-button action-extort"
                :disabled="actionBusy"
                @click="handleExtort(participant.user.id)"
              >
                💰 威胁
              </button>
            </div>

            <!-- Mimic bribe button -->
            <div v-if="isMimic && participant.role === 'patrol' && participant.outcome === 'pending'" class="mimic-actions">
              <button
                class="neo-brutal-button bribe-btn"
                :disabled="actionBusy"
                @click="handleBribe(participant.user.id)"
              >
                🤝 打点
              </button>
            </div>
          </div>

          <!-- NPC Entries -->
          <div
            v-for="npc in store.checkpointSession.npc_queue"
            :key="npc.id"
            class="queue-item npc-item"
          >
            <div class="queue-item-header">
              <div class="queue-avatar npc-avatar">
                <span class="npc-icon">🤖</span>
              </div>
              <div class="queue-item-info">
                <span class="queue-item-name">{{ npc.name }}</span>
                <span class="npc-badge">NPC</span>
              </div>
            </div>
            <p class="npc-description">{{ npc.description }}</p>
            <div v-if="npc.tells.length" class="player-tells">
              <p v-for="(tell, i) in npc.tells" :key="i" class="tell-line">{{ tell }}</p>
            </div>

            <!-- Patrol can also inspect NPCs -->
            <div v-if="isPatrol" class="patrol-actions">
              <button
                class="neo-brutal-button action-inspect"
                :disabled="actionBusy"
                @click="handleInspectNPC(npc.id)"
              >
                🔍 检查
              </button>
            </div>
          </div>

        </div>

        <!-- Action Feedback -->
        <div v-if="actionFeedback" class="action-feedback neo-brutal-card" :class="feedbackClass">
          <p>{{ actionFeedback }}</p>
          <div v-if="inspectResult" class="inspect-result-details">
            <p><strong>可疑度：</strong>{{ inspectResult.suspicion_score }}</p>
            <div v-if="inspectResult.tells.length" class="tells-list">
              <span
                v-for="(t, i) in inspectResult.tells"
                :key="i"
                class="tell-badge"
              >{{ t.text }}</span>
            </div>
          </div>
          <button class="neo-brutal-button close-feedback-btn" @click="clearFeedback">✕</button>
        </div>

        <!-- Token Feedback -->
        <p v-if="tokenFeedback" class="token-feedback-line">{{ tokenFeedback }}</p>

        <!-- Action Error -->
        <p v-if="actionError" class="panel-error">{{ actionError }}</p>
      </div>

      <!-- RIGHT: Side Panel -->
      <section class="side-panel">

        <!-- ① 场景说明 -->
        <div class="zone-desc neo-brutal-card">
          <h2 class="panel-title">🚧 防线说明</h2>
          <p class="desc-text">安检口是走私路线的必经安检口，小s在此审查过境者。</p>
          <p class="desc-text">小s可检查、盘问、体检或威胁过境者；小男娘需保持冷静通过审查。</p>
        </div>

        <!-- ② 信息框：巡逻→疑犯仪表盘 / 拟态→通关状态 -->
        <div v-if="isPatrol" class="zone-info neo-brutal-card suspicion-panel">
          <h2 class="panel-title">疑犯仪表盘</h2>

          <div class="token-display">
            <span class="token-icon">🎟️</span>
            <span class="token-val">{{ store.inspectionTokens }}</span>
            <span class="token-label">配额（每日补充10张）</span>
          </div>

          <div v-if="Object.keys(store.suspicionData).length === 0" class="empty-panel">
            <p>暂无可疑数据</p>
          </div>

          <div v-else class="suspicion-list">
            <div
              v-for="(score, username) in store.suspicionData"
              :key="username"
              class="suspicion-item"
              :class="suspicionClass(score)"
            >
              <div class="suspicion-item-header">
                <span class="sus-username">{{ username }}</span>
                <span class="sus-score-badge" :class="suspicionClass(score)">
                  {{ score }}
                </span>
              </div>
              <div class="sus-bar-wrap">
                <div
                  class="sus-bar-fill"
                  :style="{ width: Math.min(100, score) + '%' }"
                  :class="suspicionFillClass(score)"
                ></div>
              </div>
              <div class="sus-item-footer">
                <span class="sus-level-label">{{ suspicionLevelLabel(score) }}</span>
                <button
                  v-if="(score as number) >= 30 && store.inspectionTokens >= 2"
                  class="neo-brutal-button sus-patdown-btn"
                  :disabled="actionBusy"
                  @click="handlePatDownByUsername(username as string)"
                >体检</button>
              </div>
            </div>
          </div>

          <button
            class="neo-brutal-button refresh-sus-btn"
            :disabled="loadingSuspicion"
            @click="loadSuspicionData"
          >
            {{ loadingSuspicion ? '刷新中…' : '↺ 刷新数据' }}
          </button>
        </div>

        <div v-if="isMimic" class="zone-info neo-brutal-card smuggler-panel">
          <h2 class="panel-title">通关状态</h2>
          <div class="smuggler-status-card">
            <p class="smuggler-hint">保持冷静，避免触发破绽</p>
            <div v-if="store.mimicProfile" class="suppression-display">
              <span class="sup-label">⚡ 发毛值</span>
              <div class="sup-bar-wrap">
                <div
                  class="sup-bar-fill"
                  :style="{ width: Math.min(100, store.mimicProfile.suppression_value) + '%' }"
                  :class="mimicSuppressionClass"
                ></div>
              </div>
              <span class="sup-value">{{ store.mimicProfile.suppression_value }}%</span>
            </div>
          </div>
        </div>

        <!-- ③ 地图 -->
        <MiniMap />

      </section>

    </div>

    <!-- Interrogate Modal -->
    <div v-if="showInterrogateModal" class="modal-overlay" @click.self="closeInterrogateModal">
      <div class="interro-modal neo-brutal-card">
        <h3 class="modal-title">💬 盘问 {{ interrogateTarget?.name }}</h3>
        <textarea
          v-model="interrogateQuestion"
          class="interro-textarea"
          placeholder="输入盘问问题…"
          maxlength="500"
          rows="4"
        ></textarea>
        <div class="modal-actions">
          <button
            class="neo-brutal-button confirm-interro-btn"
            :disabled="sendingInterrogation || !interrogateQuestion.trim()"
            @click="confirmInterrogate"
          >
            {{ sendingInterrogation ? '发送中…' : '发出盘问' }}
          </button>
          <button
            class="neo-brutal-button cancel-btn"
            @click="closeInterrogateModal"
          >
            取消
          </button>
        </div>
        <p v-if="interroSendError" class="panel-error">{{ interroSendError }}</p>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { usePhantomCityStore } from '../stores/phantomCity'
import * as api from '../lib/api-game'
import type { InterrogationRequest } from '../lib/api-game'
import MiniMap from '../components/game/MiniMap.vue'
import ZoneHeader from '../components/game/ZoneHeader.vue'

const store = usePhantomCityStore()

// Faction helpers
const isPatrol = computed(() => store.currentFaction === 'patrol')
const isMimic = computed(() => store.currentFaction === 'mimic')

// Queue totals
const totalQueueSize = computed(() => {
  if (!store.checkpointSession) return 0
  return store.checkpointSession.participants.length + store.checkpointSession.npc_queue.length
})

// Action state
const actionBusy = ref(false)
const actionError = ref<string | null>(null)
const actionFeedback = ref<string | null>(null)
const feedbackClass = ref<string>('feedback-neutral')
const inspectResult = ref<{ tells: Array<{ type: string; text: string }>; suspicion_score: number; can_pat_down: boolean } | null>(null)

// Flee state
const fleeing = ref(false)

// Interrogation state (sending)
const showInterrogateModal = ref(false)
const interrogateTarget = ref<{ id: number; name: string } | null>(null)
const interrogateQuestion = ref('')
const sendingInterrogation = ref(false)
const interroSendError = ref<string | null>(null)

// Interrogation state (responding)
const pendingInterrogation = ref<InterrogationRequest | null>(null)
const interroResponse = ref('')
const responding = ref(false)
const respondError = ref<string | null>(null)
const interroCountdown = ref(30)
let interroTimer: ReturnType<typeof setInterval> | null = null

// Token feedback
const tokenFeedback = ref<string | null>(null)

// Suspicion loading
const loadingSuspicion = ref(false)

// Tells index: keyed by participant user ID
const tellsIndex = ref<Record<number, string[]>>({})

// Per-participant tells from inspect results
function participantTells(participantId: number): string[] {
  return tellsIndex.value[participantId] ?? []
}

function getSuspicion(userId: number): number {
  const username = store.checkpointSession?.participants
    .find(p => p.user.id === userId)?.user.username
  if (!username) return 0
  return store.suspicionData[username] ?? 0
}

function outcomeClass(outcome: string): string {
  if (outcome === 'passed' || outcome === 'bribed_through') return 'outcome-passed'
  if (outcome === 'arrested') return 'outcome-arrested'
  if (outcome === 'fled') return 'outcome-fled'
  return 'outcome-pending'
}

function outcomeLabel(outcome: string): string {
  const map: Record<string, string> = {
    pending: '待审',
    passed: '已通过',
    arrested: '已收押',
    fled: '已溜走',
    bribed_through: '打点通过',
  }
  return map[outcome] ?? outcome
}

function suspicionClass(score: number): string {
  if (score >= 80) return 'sus-red'
  if (score >= 30) return 'sus-orange'
  return 'sus-green'
}

function suspicionFillClass(score: number): string {
  if (score >= 80) return 'sus-fill-red'
  if (score >= 30) return 'sus-fill-orange'
  return 'sus-fill-green'
}

function suspicionLevelLabel(score: number): string {
  if (score >= 80) return '高度可疑'
  if (score >= 30) return '有所怀疑'
  return '正常'
}

const mimicSuppressionClass = computed(() => {
  const v = store.mimicProfile?.suppression_value ?? 0
  if (v >= 80) return 'sup-fill-red'
  if (v >= 40) return 'sup-fill-orange'
  return 'sup-fill-green'
})

function clearFeedback() {
  actionFeedback.value = null
  inspectResult.value = null
  actionError.value = null
  tokenFeedback.value = null
}

async function handleInspect(userId: number) {
  if (!store.checkpointSession) return
  actionBusy.value = true
  clearFeedback()
  try {
    const result = await api.inspectPlayer(userId, store.checkpointSession.id)
    inspectResult.value = result
    actionFeedback.value = `检查完成 — 可疑度：${result.suspicion_score}`
    feedbackClass.value = result.suspicion_score >= 80 ? 'feedback-danger' : result.suspicion_score >= 30 ? 'feedback-warn' : 'feedback-neutral'

    // Store tells for this participant
    tellsIndex.value[userId] = result.tells.map(t => t.text)

    // Update suspicion data
    await loadSuspicionData()
  } catch (e: unknown) {
    actionError.value = e instanceof Error ? e.message : '检查失败'
  } finally {
    actionBusy.value = false
  }
}

async function handleInspectNPC(_npcId: string) {
  // NPCs are identified by string IDs; the inspect endpoint requires a numeric user ID.
  // NPCs don't have real user IDs so we show a message.
  actionFeedback.value = 'NPC 检查：此为系统生成角色，记录在案'
  feedbackClass.value = 'feedback-neutral'
}

function openInterrogateModal(userId: number, username: string) {
  interrogateTarget.value = { id: userId, name: username }
  interrogateQuestion.value = ''
  interroSendError.value = null
  showInterrogateModal.value = true
}

function closeInterrogateModal() {
  showInterrogateModal.value = false
  interrogateTarget.value = null
}

async function confirmInterrogate() {
  if (!store.checkpointSession || !interrogateTarget.value) return
  sendingInterrogation.value = true
  interroSendError.value = null
  try {
    await api.interrogatePlayer(
      interrogateTarget.value.id,
      store.checkpointSession.id,
      interrogateQuestion.value.trim()
    )
    actionFeedback.value = `已向 ${interrogateTarget.value.name} 发出盘问`
    feedbackClass.value = 'feedback-neutral'
    closeInterrogateModal()
  } catch (e: unknown) {
    interroSendError.value = e instanceof Error ? e.message : '盘问失败'
  } finally {
    sendingInterrogation.value = false
  }
}

async function handlePatDown(userId: number) {
  if (!store.checkpointSession) return
  actionBusy.value = true
  clearFeedback()
  try {
    const result = await api.patDownPlayer(userId, store.checkpointSession.id)
    if (result.arrested && result.detention) {
      const gains = result.authority_gained ? ` 管控力+${result.authority_gained} 信誉+${result.reputation_gained}` : ''
      actionFeedback.value = `体检成功！玩家已被收押，没收刀具：${result.detention.seized_crystals}。${gains}`
      feedbackClass.value = 'feedback-success'
    } else if (result.false_accusation) {
      actionFeedback.value = `体检完毕，未发现走私物品。信誉-${result.reputation_lost ?? 5}`
      feedbackClass.value = 'feedback-warn'
    } else {
      actionFeedback.value = '体检完毕，未发现走私物品'
      feedbackClass.value = 'feedback-neutral'
    }
    if (result.inspection_tokens_remaining !== undefined) {
      tokenFeedback.value = `剩余配额：${result.inspection_tokens_remaining}`
    }
    await store.loadProfile()
    await store.loadCheckpointSession()
    await loadSuspicionData()
  } catch (e: unknown) {
    actionError.value = e instanceof Error ? e.message : '体检失败'
  } finally {
    actionBusy.value = false
  }
}

async function handleExtort(userId: number) {
  actionBusy.value = true
  clearFeedback()
  try {
    const result = await api.demandExtortion(
      userId,
      { crystals: 50 },
      store.checkpointSession?.id
    )
    if (result.success) {
      actionFeedback.value = '威胁请求已发出，等待对方响应'
      feedbackClass.value = 'feedback-neutral'
      if (result.channel?.id) {
        await store.openEncryptedChannel(result.channel.id, result.transaction)
      }
    }
  } catch (e: unknown) {
    actionError.value = e instanceof Error ? e.message : '威胁失败'
  } finally {
    actionBusy.value = false
  }
}

async function handleBribe(patrolUserId: number) {
  actionBusy.value = true
  clearFeedback()
  try {
    const result = await api.proposeBribe(
      patrolUserId,
      { crystals: 100 },
      store.checkpointSession?.id
    )
    if (result.success) {
      actionFeedback.value = '打点提案已发出，等待巡逻员响应'
      feedbackClass.value = 'feedback-neutral'
      if (result.channel?.id) {
        await store.openEncryptedChannel(result.channel.id, result.transaction)
      }
    }
  } catch (e: unknown) {
    actionError.value = e instanceof Error ? e.message : '打点失败'
  } finally {
    actionBusy.value = false
  }
}

async function handleFlee() {
  if (!store.checkpointSession) return
  fleeing.value = true
  actionError.value = null
  try {
    const result = await api.checkpointFlee(store.checkpointSession.id)
    if (result.success) {
      actionFeedback.value = `已溜走队列。发毛值 +${result.suppression_added}，光滑度 -${result.purity_lost}。`
      feedbackClass.value = 'feedback-neutral'
      await store.loadProfile()
      await store.loadCheckpointSession()
    }
  } catch (e: unknown) {
    actionError.value = e instanceof Error ? e.message : '溜走失败'
  } finally {
    fleeing.value = false
  }
}

async function handleRespond() {
  if (!pendingInterrogation.value || !interroResponse.value.trim()) return
  responding.value = true
  respondError.value = null
  try {
    const result = await api.respondToInterrogation(
      pendingInterrogation.value.id,
      interroResponse.value.trim()
    )
    if (result.success) {
      pendingInterrogation.value = null
      interroResponse.value = ''
      stopInterroCountdown()
    }
  } catch (e: unknown) {
    respondError.value = e instanceof Error ? e.message : '回答失败'
  } finally {
    responding.value = false
  }
}

function startInterroCountdown(seconds: number) {
  interroCountdown.value = seconds
  stopInterroCountdown()
  interroTimer = setInterval(() => {
    if (interroCountdown.value > 0) {
      interroCountdown.value--
    } else {
      stopInterroCountdown()
      pendingInterrogation.value = null
    }
  }, 1000)
}

function stopInterroCountdown() {
  if (interroTimer) {
    clearInterval(interroTimer)
    interroTimer = null
  }
}

async function handlePatDownByUsername(username: string) {
  const participant = store.checkpointSession?.participants.find(
    p => p.user.username === username
  )
  if (!participant) return
  await handlePatDown(participant.user.id)
}

async function loadSuspicionData() {
  if (!isPatrol.value) return
  loadingSuspicion.value = true
  try {
    await store.loadSuspicion()
  } finally {
    loadingSuspicion.value = false
  }
}

async function loadAll() {
  await store.loadCheckpointSession()
  if (isPatrol.value) {
    await loadSuspicionData()
  }
  // Check for pending interrogation targeting me
  checkPendingInterrogation()
}

function checkPendingInterrogation() {
  // In a real implementation, this would be fetched from the server.
  // Here we trigger a polling mechanism or websocket listener.
  // For now we leave it as a hook that can be extended.
}

onMounted(async () => {
  await store.loadProfile()
  await loadAll()
})

onUnmounted(() => {
  stopInterroCountdown()
})
</script>

<style scoped>
.checkpoint-view {
  min-height: 100vh;
  background: #fef2f2;
  font-family: 'Courier New', Courier, monospace;
  position: relative;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

/* Extra badge variants for checkpoint */
:deep(.badge-active-extra) {
  color: #065f46 !important;
  background: #d1fae5 !important;
  border-color: #065f46 !important;
  animation: pulse 1.5s infinite;
}

:deep(.badge-closed-extra) {
  color: #6b7280 !important;
  background: #e5e7eb !important;
  border-color: #6b7280 !important;
}

/* Interrogation Banner */
.interrogation-banner {
  max-width: 1200px;
  margin: 16px auto;
  padding: 16px 20px;
  background: #fef3c7;
  border: 2px solid #000;
  box-shadow: 4px 4px 0 #f59e0b;
}

.interrogation-banner-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.interro-icon {
  font-size: 22px;
}

.interro-from {
  font-size: 13px;
  color: #555;
  flex: 1;
}

.interro-countdown {
  font-size: 18px;
  font-weight: 900;
  color: #d97706;
  min-width: 40px;
  text-align: right;
}

.interro-countdown.urgent {
  color: #dc2626;
  animation: urgentBlink 0.5s infinite;
}

@keyframes urgentBlink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.interro-question {
  font-size: 15px;
  font-weight: 700;
  margin: 0 0 12px;
  padding: 8px 10px;
  background: #fff;
  border: 2px solid #000;
}

.interro-input-row {
  display: flex;
  gap: 8px;
}

.interro-input {
  flex: 1;
  border: 2px solid #000;
  padding: 8px 12px;
  font-family: inherit;
  font-size: 14px;
  outline: none;
}

.respond-btn {
  background: #f59e0b;
  color: #000;
  white-space: nowrap;
}

/* Body */
.checkpoint-body {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px 16px;
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 20px;
}

/* Queue Panel */
.queue-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.panel-title {
  font-size: 17px;
  font-weight: 900;
  margin: 0 0 12px;
}

.zone-desc .panel-title,
.zone-info .panel-title {
  font-size: 15px;
  padding: 14px 16px 0;
  margin: 0 0 12px;
}

.queue-count {
  font-size: 14px;
  font-weight: 600;
  color: #666;
}

.queue-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.queue-item {
  border: 2px solid #000;
  padding: 12px;
  background: #fff;
  box-shadow: 3px 3px 0 #000;
}

.real-player {
  background: #fff;
}

.npc-item {
  background: #f3f4f6;
}

.outcome-passed { border-left: 4px solid #22c55e; }
.outcome-arrested { border-left: 4px solid #ef4444; opacity: 0.7; }
.outcome-fled { border-left: 4px solid #6b7280; opacity: 0.7; }
.outcome-pending { border-left: 4px solid #f59e0b; }

.queue-item-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.queue-avatar {
  width: 36px;
  height: 36px;
  flex-shrink: 0;
  border: 2px solid #000;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-placeholder {
  font-size: 16px;
  font-weight: 900;
  background: #e5e7eb;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.npc-avatar {
  background: #e5e7eb;
}

.npc-icon {
  font-size: 18px;
}

.queue-item-info {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
}

.queue-item-name {
  font-weight: 700;
  font-size: 14px;
}

.queue-outcome-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 1px 6px;
  border: 1px solid #000;
}

.outcome-passed .queue-outcome-badge { background: #d1fae5; }
.outcome-arrested .queue-outcome-badge { background: #fee2e2; }
.outcome-fled .queue-outcome-badge { background: #e5e7eb; }
.outcome-pending .queue-outcome-badge { background: #fef3c7; }

.npc-badge {
  font-size: 10px;
  font-weight: 700;
  background: #e5e7eb;
  border: 1px solid #000;
  padding: 1px 5px;
}

.queue-position {
  font-size: 14px;
  font-weight: 900;
  color: #666;
}

.npc-description {
  font-size: 13px;
  color: #555;
  margin: 0 0 8px;
  font-style: italic;
}

/* Tells */
.player-tells {
  padding: 6px 8px;
  background: #f9f9f9;
  border-left: 3px dashed #9ca3af;
  margin-bottom: 8px;
}

.tell-line {
  margin: 2px 0;
  font-size: 12px;
  font-style: italic;
  color: #6b7280;
}

/* Smuggler status */
.smuggler-status {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 6px;
}

.waiting-label {
  font-size: 12px;
  font-weight: 700;
  background: #fef3c7;
  border: 1px solid #000;
  padding: 2px 8px;
  animation: pulse 2s infinite;
  align-self: flex-start;
}

.flee-section {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.flee-cost {
  font-size: 11px;
  color: #888;
  margin: 0;
}

.flee-btn {
  background: #fee2e2;
  font-size: 12px;
  padding: 4px 10px;
  align-self: flex-start;
}

/* Patrol Actions */
.patrol-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.action-inspect { background: #e0f2fe; font-size: 12px; padding: 4px 10px; }
.action-interrogate { background: #fef3c7; font-size: 12px; padding: 4px 10px; }
.action-patdown { background: #fee2e2; font-size: 12px; padding: 4px 10px; }
.action-extort { background: #f5f3ff; font-size: 12px; padding: 4px 10px; }

/* Mimic Actions */
.mimic-actions {
  margin-top: 6px;
}

.bribe-btn { background: #d1fae5; font-size: 12px; padding: 4px 10px; }

/* Action Feedback */
.action-feedback {
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  position: relative;
}

.feedback-neutral { background: #f9fafb; }
.feedback-warn { background: #fef3c7; border-color: #f59e0b !important; box-shadow: 3px 3px 0 #f59e0b !important; }
.feedback-danger { background: #fee2e2; border-color: #ef4444 !important; box-shadow: 3px 3px 0 #ef4444 !important; }
.feedback-success { background: #d1fae5; border-color: #22c55e !important; box-shadow: 3px 3px 0 #22c55e !important; }

.action-feedback p {
  margin: 0;
  font-weight: 700;
  font-size: 14px;
}

.inspect-result-details {
  font-size: 13px;
}

.inspect-result-details p { margin: 0 0 6px; }

.tells-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tell-badge {
  background: #fef3c7;
  border: 1px solid #000;
  padding: 2px 6px;
  font-size: 11px;
  font-weight: 600;
}

.close-feedback-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  padding: 2px 8px;
  font-size: 12px;
  background: #e5e7eb;
  box-shadow: 2px 2px 0 #000;
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

/* Suspicion Panel */
.suspicion-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.suspicion-panel .suspicion-list,
.suspicion-panel .empty-panel,
.suspicion-panel .refresh-sus-btn {
  margin: 0 14px;
}

.suspicion-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.suspicion-item {
  border: 2px solid #000;
  padding: 10px 12px;
  background: #fff;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.sus-red { border-left: 4px solid #ef4444 !important; background: #fef2f2 !important; }
.sus-orange { border-left: 4px solid #f59e0b !important; background: #fffbeb !important; }
.sus-green { border-left: 4px solid #22c55e !important; background: #f0fdf4 !important; }

.suspicion-item-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.sus-username {
  font-weight: 700;
  font-size: 14px;
}

.sus-score-badge {
  font-size: 16px;
  font-weight: 900;
  padding: 1px 8px;
  border: 2px solid #000;
}

.sus-red .sus-score-badge { background: #fca5a5; }
.sus-orange .sus-score-badge { background: #fcd34d; }
.sus-green .sus-score-badge { background: #86efac; }

.sus-bar-wrap {
  height: 8px;
  background: #e5e7eb;
  border: 1px solid #000;
}

.sus-bar-fill {
  height: 100%;
  transition: width 0.4s;
}

.sus-fill-red { background: #ef4444; }
.sus-fill-orange { background: #f59e0b; }
.sus-fill-green { background: #22c55e; }

.sus-item-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.sus-level-label {
  font-size: 11px;
  font-weight: 700;
  color: #666;
}

.sus-patdown-btn {
  font-size: 11px;
  padding: 2px 8px;
  background: #fee2e2;
}

/* Token display in suspicion panel */
.token-display {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  font-size: 13px;
  font-weight: 700;
  background: #f0fdf4;
  border-bottom: 1px solid #d1fae5;
  margin-bottom: 4px;
}

.token-val {
  font-size: 16px;
  font-weight: 900;
  color: #065f46;
}

.token-label {
  font-size: 11px;
  color: #6b7280;
}

/* Token feedback line */
.token-feedback-line {
  font-size: 12px;
  color: #6b7280;
  font-weight: 600;
  margin: 4px 0 0;
  padding: 4px 8px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
}

.refresh-sus-btn {
  background: #e0e7ff;
  font-size: 13px;
  align-self: flex-start;
}

/* Smuggler Panel */
.smuggler-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.smuggler-status-card {
  padding: 0 14px 4px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.smuggler-hint {
  margin: 0;
  font-style: italic;
  color: #555;
  font-size: 13px;
}

.suppression-display {
  display: flex;
  align-items: center;
  gap: 10px;
}

.sup-label {
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
}

.sup-bar-wrap {
  flex: 1;
  height: 10px;
  background: #e5e7eb;
  border: 1px solid #000;
}

.sup-bar-fill {
  height: 100%;
  transition: width 0.3s;
}

.sup-fill-green { background: #22c55e; }
.sup-fill-orange { background: #f97316; }
.sup-fill-red { background: #ef4444; }

.sup-value {
  font-size: 13px;
  font-weight: 900;
  min-width: 36px;
}

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.interro-modal {
  background: #fff;
  padding: 24px;
  max-width: 480px;
  width: 90%;
}

.modal-title {
  font-size: 18px;
  font-weight: 900;
  margin: 0 0 16px;
}

.interro-textarea {
  width: 100%;
  border: 2px solid #000;
  padding: 10px;
  font-family: inherit;
  font-size: 14px;
  resize: vertical;
  outline: none;
  box-sizing: border-box;
}

.modal-actions {
  display: flex;
  gap: 10px;
  margin-top: 14px;
}

.confirm-interro-btn {
  background: #fef08a;
  font-size: 14px;
  padding: 8px 16px;
}

.cancel-btn {
  background: #e5e7eb;
  font-size: 14px;
  padding: 8px 16px;
}

/* Shared */
.empty-panel {
  text-align: center;
  padding: 30px;
  color: #888;
  font-style: italic;
  font-size: 14px;
  border: 2px dashed #ccc;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.panel-error {
  color: #dc2626;
  font-weight: 700;
  font-size: 13px;
  margin: 6px 0 0;
}

/* Neo-brutal base */
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
  transform: none;
  box-shadow: 3px 3px 0 #000;
}

@media (max-width: 768px) {
  .checkpoint-body {
    grid-template-columns: 1fr;
  }
}
</style>
