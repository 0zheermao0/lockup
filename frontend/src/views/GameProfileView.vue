<template>
  <div class="game-profile-view">

    <!-- Header -->
    <ZoneHeader
      title="📋 游戏档案"
      :extra-badge="store.currentFaction ? factionLabel : undefined"
      :extra-badge-class="factionBadgeClass"
    />

    <!-- Loading -->
    <div v-if="store.isLoading" class="profile-loading">
      <p>加载档案中…</p>
    </div>

    <div v-else-if="!store.profile" class="profile-empty">
      <p>未找到游戏档案。请先选择阵营。</p>
      <RouterLink to="/phantom-city" class="neo-brutal-button">前往男娘幻城</RouterLink>
    </div>

    <div v-else class="profile-body">

      <!-- Active Detention Card -->
      <div v-if="store.profile.active_detention" class="detention-card neo-brutal-card">
        <div class="detention-card-header">
          <h2 class="detention-title">🔒 收押中</h2>
          <span class="detention-status-badge">{{ store.profile.active_detention.status }}</span>
        </div>
        <div class="detention-details">
          <div class="detention-detail-row">
            <span class="detail-label">执行者</span>
            <span class="detail-value">{{ store.profile.active_detention.captor.username }}</span>
          </div>
          <div class="detention-detail-row">
            <span class="detail-label">没收刀具</span>
            <span class="detail-value">💎 {{ store.profile.active_detention.seized_crystals }}</span>
          </div>
          <div class="detention-detail-row">
            <span class="detail-label">剩余时间</span>
            <span class="detail-value countdown">{{ formatSeconds(detentionCountdown) }}</span>
          </div>
          <div class="detention-detail-row">
            <span class="detail-label">哄骗次数</span>
            <span class="detail-value">{{ store.profile.active_detention.charm_attempts_used }} 次</span>
          </div>
        </div>
        <button
          class="neo-brutal-button charm-btn"
          :disabled="charming"
          @click="handleCharm"
        >
          {{ charming ? '哄骗中…' : '哄骗看守' }}
        </button>
        <p v-if="charmResult" class="charm-result">{{ charmResult }}</p>
        <p v-if="charmError" class="panel-error">{{ charmError }}</p>
      </div>

      <!-- Crystals -->
      <div class="crystals-card neo-brutal-card">
        <h2 class="section-title">💎 刀具储量</h2>
        <div class="crystals-grid">
          <div class="crystal-item raw-crystal">
            <span class="crystal-amount">{{ store.crystals?.raw_crystals ?? 0 }}</span>
            <span class="crystal-label">备皮刀</span>
          </div>
          <div class="crystal-item purified-crystal">
            <span class="crystal-amount">{{ store.crystals?.purified_crystals ?? 0 }}</span>
            <span class="crystal-label">脱毛仪</span>
          </div>
        </div>
      </div>

      <!-- Mimic Stats -->
      <div v-if="store.mimicProfile" class="stats-section neo-brutal-card">
        <h2 class="section-title">🎭 小男娘数据</h2>
        <div class="stats-grid">

          <div class="stat-card">
            <span class="stat-icon">🔋</span>
            <span class="stat-name">电量</span>
            <div class="stat-bar-wrap">
              <div
                class="stat-bar-fill"
                :style="{ width: store.mimicProfile.depilation_charge + '%' }"
                :class="chargeBarClass"
              ></div>
            </div>
            <span class="stat-num">{{ store.mimicProfile.depilation_charge }}%</span>
          </div>

          <div class="stat-card">
            <span class="stat-icon">⚡</span>
            <span class="stat-name">发毛值</span>
            <div class="stat-bar-wrap">
              <div
                class="stat-bar-fill"
                :style="{ width: Math.min(100, store.mimicProfile.suppression_value) + '%' }"
                :class="suppressionBarClass"
              ></div>
            </div>
            <span class="stat-num" :class="suppressionNumClass">
              {{ store.mimicProfile.suppression_value }}%
            </span>
          </div>

          <div class="stat-card simple">
            <span class="stat-icon">✨</span>
            <span class="stat-name">光滑度</span>
            <span class="stat-big">{{ store.mimicProfile.purity_score }}</span>
          </div>

          <div class="stat-card simple">
            <span class="stat-icon">🌸</span>
            <span class="stat-name">柔化度</span>
            <span class="stat-big">{{ store.mimicProfile.femboy_score }}</span>
          </div>

          <div class="stat-card simple">
            <span class="stat-icon">🏃</span>
            <span class="stat-name">成功出逃</span>
            <span class="stat-big success">{{ store.mimicProfile.total_successful_runs }}</span>
          </div>

          <div class="stat-card simple">
            <span class="stat-icon">❌</span>
            <span class="stat-name">失败次数</span>
            <span class="stat-big fail">{{ store.mimicProfile.total_failed_runs }}</span>
          </div>

          <div class="stat-card simple">
            <span class="stat-icon">🔍</span>
            <span class="stat-name">基础可探测</span>
            <span class="stat-big">{{ store.mimicProfile.base_detectability }}</span>
          </div>

          <div class="stat-card simple">
            <span class="stat-icon">🛡️</span>
            <span class="stat-name">控制抗性</span>
            <span class="stat-big">{{ store.mimicProfile.control_resistance }}</span>
          </div>

        </div>

        <!-- Permanent Tells -->
        <div v-if="store.mimicProfile.permanent_tells.length" class="tells-section">
          <h3 class="tells-title">永久破绽</h3>
          <div class="tells-list">
            <span
              v-for="(tell, i) in store.mimicProfile.permanent_tells"
              :key="i"
              class="tell-badge"
            >{{ tell }}</span>
          </div>
        </div>
      </div>

      <!-- Patrol Stats -->
      <div v-if="store.patrolProfile" class="stats-section neo-brutal-card patrol-stats">
        <h2 class="section-title">🛡️ 小s数据</h2>
        <div class="stats-grid">

          <div class="stat-card simple">
            <span class="stat-icon">⚖️</span>
            <span class="stat-name">管控力</span>
            <span class="stat-big">{{ store.patrolProfile.authority_value }}</span>
          </div>

          <div class="stat-card simple">
            <span class="stat-icon">⭐</span>
            <span class="stat-name">信誉</span>
            <span class="stat-big">{{ store.patrolProfile.reputation_score }}</span>
          </div>

          <div class="stat-card simple">
            <span class="stat-icon">🎟️</span>
            <span class="stat-name">配额</span>
            <span class="stat-big">{{ store.patrolProfile.inspection_tokens }}</span>
          </div>

          <div class="stat-card simple">
            <span class="stat-icon">🔒</span>
            <span class="stat-name">总收押数</span>
            <span class="stat-big success">{{ store.patrolProfile.total_arrests }}</span>
          </div>

          <div class="stat-card simple">
            <span class="stat-icon">✅</span>
            <span class="stat-name">正确识别</span>
            <span class="stat-big success">{{ store.patrolProfile.total_correct_identifications }}</span>
          </div>

          <div class="stat-card simple">
            <span class="stat-icon">⚠️</span>
            <span class="stat-name">误判次数</span>
            <span class="stat-big fail">{{ store.patrolProfile.false_accusations }}</span>
          </div>

        </div>
      </div>

      <!-- Active Disguise -->
      <div v-if="store.activeDisguise" class="disguise-section neo-brutal-card">
        <h2 class="section-title">🎭 当前伪装</h2>
        <div class="disguise-info">
          <div class="disguise-detectability">
            <span class="detect-label">可探测度</span>
            <div class="detect-bar-wrap">
              <div
                class="detect-bar-fill"
                :style="{ width: Math.min(100, store.activeDisguise.computed_detectability) + '%' }"
                :class="detectBarClass"
              ></div>
            </div>
            <span class="detect-value">{{ store.activeDisguise.computed_detectability }}</span>
          </div>
          <div class="disguise-mode">
            <span class="mode-label">行为模式：</span>
            <span class="mode-value mode-badge">{{ behaviorModeLabel }}</span>
          </div>
        </div>

        <div v-if="store.activeDisguise.outer_layer_item" class="equip-row">
          <span class="equip-slot">外层</span>
          <span class="equip-icon">{{ store.activeDisguise.outer_layer_item.icon }}</span>
          <span class="equip-name">{{ store.activeDisguise.outer_layer_item.name }}</span>
          <span class="equip-tier">T{{ store.activeDisguise.outer_layer_item.tier }}</span>
        </div>

        <div v-if="store.activeDisguise.inner_items.length" class="inner-items">
          <h3 class="inner-title">内层物品</h3>
          <div
            v-for="item in store.activeDisguise.inner_items"
            :key="item.id"
            class="equip-row"
          >
            <span class="equip-slot">内层</span>
            <span class="equip-icon">{{ item.icon }}</span>
            <span class="equip-name">{{ item.name }}</span>
            <span class="equip-tier">T{{ item.tier }}</span>
          </div>
        </div>

        <div v-if="store.activeDisguise.computed_active_tells.length" class="active-tells">
          <h3 class="tells-title">当前破绽</h3>
          <div class="tells-list">
            <span
              v-for="(tell, i) in store.activeDisguise.computed_active_tells"
              :key="i"
              class="tell-badge active-tell"
            >{{ tell }}</span>
          </div>
        </div>
      </div>

      <!-- Control Transfers -->
      <div v-if="store.controlTransfers.length" class="transfers-section neo-brutal-card">
        <h2 class="section-title">🎮 控制权</h2>
        <div
          v-for="transfer in store.controlTransfers"
          :key="transfer.id"
          class="transfer-card"
          :class="{ 'transfer-expired': !transfer.is_active }"
        >
          <div class="transfer-header">
            <span class="transfer-task">{{ transfer.lock_task_title }}</span>
            <span class="transfer-source-badge source-badge">{{ sourceLabel(transfer.source) }}</span>
          </div>
          <div class="transfer-parties">
            <span class="party-label">授权方：{{ transfer.grantor.username }}</span>
            <span class="party-sep">→</span>
            <span class="party-label">受让方：{{ transfer.grantee.username }}</span>
          </div>
          <div class="transfer-meta">
            <span>{{ transfer.duration_hours }}h</span>
            <span class="transfer-expires">到期：{{ formatDate(transfer.expires_at) }}</span>
          </div>
          <div v-if="transfer.is_active" class="transfer-actions">
            <button
              v-if="transfer.can_add_time"
              class="neo-brutal-button add-time-btn"
              :disabled="processingTransferId === transfer.id"
              @click="handleAddTime(transfer.id)"
            >
              ⏰ 加时
            </button>
            <button
              v-if="transfer.can_freeze"
              class="neo-brutal-button freeze-btn"
              :disabled="processingTransferId === transfer.id"
              @click="handleFreeze(transfer.id)"
            >
              🧊 冻结
            </button>
          </div>
          <span v-else class="transfer-inactive">已失效</span>
        </div>
        <p v-if="transferError" class="panel-error">{{ transferError }}</p>
        <p v-if="transferSuccess" class="panel-success">{{ transferSuccess }}</p>
      </div>

      <!-- Rest Button (in salon) -->
      <div v-if="store.currentZone?.name === 'salon'" class="rest-section">
        <button
          class="neo-brutal-button rest-btn"
          :disabled="resting"
          @click="handleRest"
        >
          {{ resting ? '补觉中…' : '💤 补觉（降低发毛值）' }}
        </button>
        <p v-if="restResult" class="panel-success">{{ restResult }}</p>
        <p v-if="restError" class="panel-error">{{ restError }}</p>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { usePhantomCityStore } from '../stores/phantomCity'
import * as api from '../lib/api-game'
import ZoneHeader from '../components/game/ZoneHeader.vue'

const store = usePhantomCityStore()

const charming = ref(false)
const charmResult = ref<string | null>(null)
const charmError = ref<string | null>(null)

const resting = ref(false)
const restResult = ref<string | null>(null)
const restError = ref<string | null>(null)

const processingTransferId = ref<string | null>(null)
const transferError = ref<string | null>(null)
const transferSuccess = ref<string | null>(null)

let countdownTimer: ReturnType<typeof setInterval> | null = null
const detentionCountdown = ref(0)

const factionLabel = computed(() => {
  if (store.currentFaction === 'mimic') return '🎭 小男娘'
  if (store.currentFaction === 'patrol') return '🛡️ 小s'
  return ''
})

const factionClass = computed(() => ({
  'faction-mimic': store.currentFaction === 'mimic',
  'faction-patrol': store.currentFaction === 'patrol',
}))

const factionBadgeClass = computed(() =>
  store.currentFaction === 'mimic' ? 'faction-mimic-extra' : 'faction-patrol-extra'
)

const chargeBarClass = computed(() => {
  const v = store.mimicProfile?.depilation_charge ?? 100
  if (v < 20) return 'bar-red'
  if (v < 50) return 'bar-orange'
  return 'bar-green'
})

const suppressionBarClass = computed(() => {
  const v = store.mimicProfile?.suppression_value ?? 0
  if (v >= 80) return 'bar-red'
  if (v >= 40) return 'bar-orange'
  return 'bar-green'
})

const suppressionNumClass = computed(() => {
  const v = store.mimicProfile?.suppression_value ?? 0
  if (v >= 80) return 'text-red'
  if (v >= 40) return 'text-orange'
  return ''
})

const detectBarClass = computed(() => {
  const v = store.activeDisguise?.computed_detectability ?? 0
  if (v >= 70) return 'bar-red'
  if (v >= 40) return 'bar-orange'
  return 'bar-green'
})

const behaviorModeLabel = computed(() => {
  const mode = store.activeDisguise?.behavioral_mode
  if (mode === 'passive') return '被动'
  if (mode === 'confident') return '自信'
  if (mode === 'evasive') return '逃避'
  return mode ?? '—'
})

function sourceLabel(source: string): string {
  if (source === 'arrest') return '收押'
  if (source === 'bribe_deal') return '打点'
  if (source === 'extortion_deal') return '威胁'
  return source
}

function formatSeconds(secs: number): string {
  const h = Math.floor(secs / 3600)
  const m = Math.floor((secs % 3600) / 60)
  const s = secs % 60
  if (h > 0) return `${h}h ${m}m ${s}s`
  if (m > 0) return `${m}m ${s}s`
  return `${s}s`
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString('zh-CN', {
    month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function startCountdown() {
  if (!store.profile?.active_detention) return
  detentionCountdown.value = store.profile.active_detention.time_remaining_seconds
  countdownTimer = setInterval(() => {
    if (detentionCountdown.value > 0) {
      detentionCountdown.value--
    } else {
      if (countdownTimer) clearInterval(countdownTimer)
    }
  }, 1000)
}

async function handleCharm() {
  if (!store.profile?.active_detention) return
  charming.value = true
  charmResult.value = null
  charmError.value = null
  try {
    const result = await api.charmWarden(store.profile.active_detention.id)
    if (result.success) {
      if (result.conversion_triggered) {
        charmResult.value = '哄骗成功！狱卒被转化！'
      } else {
        charmResult.value = `哄骗成功！消耗对方管控力 ${result.authority_drained ?? 0}`
      }
      await store.loadProfile()
    }
  } catch (e: unknown) {
    charmError.value = e instanceof Error ? e.message : '哄骗失败'
  } finally {
    charming.value = false
    setTimeout(() => { charmResult.value = null }, 4000)
  }
}

async function handleRest() {
  resting.value = true
  restResult.value = null
  restError.value = null
  try {
    const result = await store.salonRest()
    if (result.success) {
      const reduction = result.suppression_before - result.suppression_after
      restResult.value = `补觉完毕，发毛值降低 ${reduction}`
    }
  } catch (e: unknown) {
    restError.value = e instanceof Error ? e.message : '补觉失败'
  } finally {
    resting.value = false
    setTimeout(() => { restResult.value = null }, 3000)
  }
}

async function handleAddTime(transferId: string) {
  processingTransferId.value = transferId
  transferError.value = null
  transferSuccess.value = null
  try {
    const result = await api.addTimeToLock(transferId, 30)
    if (result.success) {
      transferSuccess.value = `已加时 30 分钟，新结束时间：${formatDate(result.new_end_time)}`
      await store.loadControlTransfers()
    }
  } catch (e: unknown) {
    transferError.value = e instanceof Error ? e.message : '加时失败'
  } finally {
    processingTransferId.value = null
    setTimeout(() => { transferSuccess.value = null }, 4000)
  }
}

async function handleFreeze(transferId: string) {
  processingTransferId.value = transferId
  transferError.value = null
  transferSuccess.value = null
  try {
    const result = await api.freezeLock(transferId)
    if (result.success) {
      transferSuccess.value = '已冻结锁时间'
      await store.loadControlTransfers()
    }
  } catch (e: unknown) {
    transferError.value = e instanceof Error ? e.message : '冻结失败'
  } finally {
    processingTransferId.value = null
    setTimeout(() => { transferSuccess.value = null }, 4000)
  }
}

onMounted(async () => {
  await store.loadProfile()
  await store.loadControlTransfers()
  startCountdown()
})

onUnmounted(() => {
  if (countdownTimer) clearInterval(countdownTimer)
})
</script>

<style scoped>
.game-profile-view {
  min-height: 100vh;
  background: #faf5ff;
  font-family: 'Courier New', Courier, monospace;
}

/* Header */
/* Faction badge variants for ZoneHeader extra-badge */
:deep(.faction-mimic-extra) {
  color: #9d174d !important;
  background: #fce7f3 !important;
  border-color: #9d174d !important;
}

:deep(.faction-patrol-extra) {
  color: #1e40af !important;
  background: #dbeafe !important;
  border-color: #1e40af !important;
}

/* Loading / Empty */
.profile-loading, .profile-empty {
  text-align: center;
  padding: 60px 16px;
  font-size: 16px;
  color: #666;
}

/* Body */
.profile-body {
  max-width: 900px;
  margin: 0 auto;
  padding: 20px 16px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* Detention Card */
.detention-card {
  background: #fee2e2;
  padding: 18px;
}

.detention-card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}

.detention-title {
  font-size: 18px;
  font-weight: 900;
  margin: 0;
}

.detention-status-badge {
  background: #ef4444;
  color: #fff;
  border: 2px solid #000;
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
}

.detention-details {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 14px;
}

.detention-detail-row {
  display: flex;
  gap: 12px;
  font-size: 14px;
}

.detail-label {
  font-weight: 600;
  color: #555;
  min-width: 80px;
}

.detail-value {
  font-weight: 700;
}

.countdown {
  font-size: 16px;
  color: #dc2626;
  font-weight: 900;
}

.charm-btn {
  background: #f9a8d4;
  font-size: 14px;
  padding: 8px 18px;
}

.charm-result {
  margin: 8px 0 0;
  color: #7c3aed;
  font-weight: 700;
  font-size: 13px;
}

/* Crystals Card */
.crystals-card {
  background: #fff;
  padding: 16px 18px;
}

.crystals-grid {
  display: flex;
  gap: 24px;
}

.crystal-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 16px 24px;
  border: 2px solid #000;
  min-width: 100px;
}

.raw-crystal { background: #fffbeb; }
.purified-crystal { background: #f5f3ff; }

.crystal-amount {
  font-size: 32px;
  font-weight: 900;
}

.crystal-label {
  font-size: 13px;
  color: #666;
  font-weight: 600;
}

/* Stats Section */
.stats-section {
  background: #fff;
  padding: 16px 18px;
}

.patrol-stats {
  background: #eff6ff;
}

.section-title {
  font-size: 17px;
  font-weight: 900;
  margin: 0 0 16px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 12px;
}

.stat-card {
  border: 2px solid #000;
  padding: 12px;
  background: #f9f9f9;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.stat-icon {
  font-size: 18px;
}

.stat-name {
  font-size: 12px;
  color: #666;
  font-weight: 600;
}

.stat-bar-wrap {
  height: 8px;
  background: #e5e7eb;
  border: 1px solid #000;
}

.stat-bar-fill {
  height: 100%;
  transition: width 0.3s ease;
}

.bar-green { background: #22c55e; }
.bar-orange { background: #f97316; }
.bar-red { background: #ef4444; }

.stat-num {
  font-size: 13px;
  font-weight: 900;
}

.text-red { color: #dc2626; }
.text-orange { color: #d97706; }

.stat-big {
  font-size: 26px;
  font-weight: 900;
}

.success { color: #16a34a; }
.fail { color: #dc2626; }

/* Tells */
.tells-section {
  margin-top: 16px;
  padding-top: 14px;
  border-top: 2px dashed #ccc;
}

.tells-title {
  font-size: 14px;
  font-weight: 700;
  margin: 0 0 8px;
  color: #555;
}

.tells-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tell-badge {
  background: #fef3c7;
  border: 2px solid #000;
  padding: 3px 8px;
  font-size: 12px;
  font-weight: 600;
}

.active-tell {
  background: #fca5a5;
}

/* Disguise */
.disguise-section {
  background: #fff;
  padding: 16px 18px;
}

.disguise-info {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 14px;
}

.disguise-detectability {
  display: flex;
  align-items: center;
  gap: 10px;
}

.detect-label {
  font-size: 13px;
  font-weight: 600;
  color: #555;
  min-width: 70px;
}

.detect-bar-wrap {
  flex: 1;
  height: 10px;
  background: #e5e7eb;
  border: 1px solid #000;
  max-width: 200px;
}

.detect-bar-fill {
  height: 100%;
  transition: width 0.3s;
}

.detect-value {
  font-weight: 900;
  font-size: 14px;
}

.disguise-mode {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.mode-label {
  color: #666;
  font-weight: 600;
}

.mode-badge {
  border: 2px solid #000;
  padding: 2px 8px;
  font-weight: 700;
  font-size: 12px;
  background: #e0f2fe;
}

.equip-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border: 1px solid #ddd;
  background: #f9f9f9;
  margin-bottom: 6px;
}

.equip-slot {
  font-size: 11px;
  background: #e5e7eb;
  border: 1px solid #000;
  padding: 1px 5px;
  font-weight: 700;
  min-width: 32px;
  text-align: center;
}

.equip-icon {
  font-size: 18px;
}

.equip-name {
  flex: 1;
  font-weight: 700;
  font-size: 14px;
}

.equip-tier {
  font-size: 11px;
  background: #fef08a;
  border: 1px solid #000;
  padding: 1px 5px;
  font-weight: 700;
}

.inner-title {
  font-size: 13px;
  font-weight: 700;
  color: #555;
  margin: 12px 0 6px;
}

.active-tells {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 2px dashed #ccc;
}

/* Transfers */
.transfers-section {
  background: #fff;
  padding: 16px 18px;
}

.transfer-card {
  border: 2px solid #000;
  padding: 12px;
  background: #f0f9ff;
  margin-bottom: 10px;
}

.transfer-expired {
  opacity: 0.55;
  background: #f3f4f6;
}

.transfer-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.transfer-task {
  font-weight: 900;
  font-size: 14px;
  flex: 1;
}

.source-badge {
  font-size: 11px;
  border: 2px solid #000;
  padding: 1px 6px;
  font-weight: 700;
  background: #e0e7ff;
}

.transfer-parties {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: #555;
  margin-bottom: 6px;
}

.party-sep {
  font-weight: 900;
}

.transfer-meta {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: #888;
  margin-bottom: 10px;
}

.transfer-expires {
  font-weight: 600;
}

.transfer-actions {
  display: flex;
  gap: 10px;
}

.add-time-btn {
  background: #fef08a;
  font-size: 13px;
  padding: 5px 12px;
}

.freeze-btn {
  background: #e0f2fe;
  font-size: 13px;
  padding: 5px 12px;
}

.transfer-inactive {
  font-size: 12px;
  color: #9ca3af;
  font-style: italic;
}

/* Rest Section */
.rest-section {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
}

.rest-btn {
  background: #d1fae5;
  font-size: 15px;
  padding: 10px 20px;
}

.panel-error {
  color: #dc2626;
  font-weight: 700;
  font-size: 13px;
  margin: 4px 0 0;
}

.panel-success {
  color: #16a34a;
  font-weight: 700;
  font-size: 13px;
  margin: 4px 0 0;
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
}

@media (max-width: 600px) {
  .stats-grid {
    grid-template-columns: 1fr 1fr;
  }
  .crystals-grid {
    gap: 12px;
  }
}
</style>
