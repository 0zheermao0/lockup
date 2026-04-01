<template>
  <div class="phantom-city-view">
    <!-- Header -->
    <header class="pc-header">
      <div class="pc-header-inner">
        <RouterLink to="/games" class="neo-brutal-button back-btn">← 返回</RouterLink>
        <div class="pc-title-block">
          <h1 class="pc-title">男娘幻城</h1>
          <p class="pc-subtitle">文字版溜走塔科夫 × 狼人杀</p>
        </div>
        <div class="pc-header-right">
          <span v-if="store.currentFaction" class="faction-badge" :class="factionClass">
            {{ factionLabel }}
          </span>
        </div>
      </div>
    </header>

    <!-- Loading -->
    <div v-if="store.isLoading" class="pc-loading">
      <p class="loading-text">加载中…</p>
    </div>

    <div v-else class="pc-body">

      <!-- Detention Banner -->
      <div v-if="store.isDetained" class="detention-banner">
        <span class="detention-icon">🔒</span>
        <strong>你正处于收押状态！</strong>
        <span v-if="store.profile?.active_detention">
          剩余时间：{{ formatSeconds(store.profile.active_detention.time_remaining_seconds) }}
        </span>
        <RouterLink to="/phantom-city/profile" class="neo-brutal-button detention-profile-btn">
          查看详情
        </RouterLink>
      </div>

      <!-- Stats Bar (faction chosen) -->
      <div v-if="store.currentFaction" class="stats-bar neo-brutal-card">
        <div class="stat-item">
          <span class="stat-label">💎 备皮刀</span>
          <span class="stat-value">{{ store.crystals?.raw_crystals ?? 0 }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">✨ 脱毛仪</span>
          <span class="stat-value">{{ store.crystals?.purified_crystals ?? 0 }}</span>
        </div>
        <template v-if="store.currentFaction === 'mimic' && store.mimicProfile">
          <div class="stat-item suppression-item">
            <span class="stat-label">⚡ 发毛值</span>
            <div class="suppression-bar-wrap">
              <div
                class="suppression-bar-fill"
                :style="{ width: suppressionPercent + '%' }"
                :class="suppressionBarClass"
              ></div>
            </div>
            <span class="stat-value">{{ store.mimicProfile.suppression_value }}%</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">🔋 电量</span>
            <span class="stat-value">{{ store.mimicProfile.depilation_charge }}%</span>
          </div>
        </template>
        <template v-if="store.currentFaction === 'patrol' && store.patrolProfile">
          <div class="stat-item">
            <span class="stat-label">⚖️ 管控力</span>
            <span class="stat-value">{{ store.patrolProfile.authority_value }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">🎟️ 配额</span>
            <span class="stat-value">{{ store.patrolProfile.inspection_tokens }}</span>
          </div>
        </template>
      </div>

      <!-- Faction Selection (no faction) -->
      <div v-if="!store.currentFaction && !store.isLoading" class="faction-select-section">
        <h2 class="section-heading">选择你的阵营</h2>
        <p class="section-hint">一旦选择，本局游戏中无法更改</p>
        <div class="faction-cards">

          <!-- 小男娘 -->
          <div class="faction-card neo-brutal-card mimic-card">
            <div class="faction-icon">🎭</div>
            <h3 class="faction-name">小男娘</h3>
            <p class="faction-desc">伪装、走私、骗过审查</p>
            <ul class="faction-perks">
              <li>收集刀具并带出备皮间</li>
              <li>在安检口伪装身份</li>
              <li>打点小s员</li>
            </ul>
            <button
              class="neo-brutal-button mimic-btn"
              :disabled="choosingFaction"
              @click="handleChooseFaction('mimic')"
            >
              {{ choosingFaction ? '选择中…' : '选择小男娘' }}
            </button>
          </div>

          <!-- 小s -->
          <div class="faction-card neo-brutal-card patrol-card">
            <div class="faction-icon">🛡️</div>
            <h3 class="faction-name">小s</h3>
            <p class="faction-desc">识别、盘问、维护秩序</p>
            <ul class="faction-perks">
              <li>在安检口审查过境者</li>
              <li>识破伪装并实施收押</li>
              <li>威胁走私者</li>
            </ul>
            <button
              class="neo-brutal-button patrol-btn"
              :disabled="choosingFaction"
              @click="handleChooseFaction('patrol')"
            >
              {{ choosingFaction ? '选择中…' : '选择小s' }}
            </button>
          </div>
        </div>

        <p v-if="factionError" class="error-msg">{{ factionError }}</p>
      </div>

      <!-- Zone Navigation (faction chosen) -->
      <div v-if="store.currentFaction" class="zones-section">
        <h2 class="section-heading">
          当前位置：<span class="current-zone-label">{{ currentZoneLabel }}</span>
        </h2>

        <!-- No current zone: entry selection -->
        <div v-if="!store.currentZone" class="entry-section">
          <p class="section-hint">选择进入游戏的起始区域</p>
          <div class="entry-btns">
            <button class="zone-entry-btn salon-btn" @click="enterZone('salon')">
              🥂 进入闺房
            </button>
            <button class="zone-entry-btn checkpoint-btn" @click="enterZone('checkpoint')">
              🚧 进入安检口
            </button>
          </div>
          <p v-if="travelError" class="error-msg">{{ travelError }}</p>
        </div>

        <!-- 禁闭室（仅被捕时显示） -->
        <div v-if="store.isDetained" class="control-room-card neo-brutal-card">
          <span class="zone-icon">🔒</span>
          <div class="zone-info">
            <h3 class="zone-name">禁闭室</h3>
            <p class="zone-desc">你正处于收押状态</p>
          </div>
          <RouterLink to="/phantom-city/profile" class="neo-brutal-button">查看详情</RouterLink>
        </div>

        <!-- Profile link always visible -->
        <RouterLink to="/phantom-city/profile" class="profile-link neo-brutal-button">
          📋 游戏档案
        </RouterLink>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import { usePhantomCityStore } from '../stores/phantomCity'
import * as api from '../lib/api-game'

const store = usePhantomCityStore()
const router = useRouter()

const choosingFaction = ref(false)
const factionError = ref<string | null>(null)
const traveling = ref(false)
const travelError = ref<string | null>(null)

const ZONE_ROUTES: Record<string, string> = {
  black_market:       '/phantom-city/black-market',
  salon:              '/phantom-city/salon',
  armory:             '/phantom-city/armory',
  checkpoint:         '/phantom-city/checkpoint',
  sewer:              '/phantom-city/sewer',
  abandoned_camp:     '/phantom-city/abandoned-camp',
  ruins_outer:        '/phantom-city/ruins-outer',
  ruins:              '/phantom-city/ruins',
  ruins_deep:         '/phantom-city/ruins-deep',
  control_room:       '/phantom-city/profile',
  interrogation_room: '/phantom-city/profile',
}

const ZONE_LABELS: Record<string, string> = {
  black_market:       '黑市',
  salon:              '闺房',
  armory:             '储物柜',
  checkpoint:         '安检口',
  sewer:              '下水道',
  abandoned_camp:     '更衣室',
  ruins_outer:        '外围备皮间',
  ruins:              '备皮间',
  ruins_deep:         '深处备皮间',
  control_room:       '禁闭室',
  interrogation_room: '审问室',
}

// ── Computed ──

const factionLabel = computed(() => {
  if (store.currentFaction === 'mimic') return '🎭 小男娘'
  if (store.currentFaction === 'patrol') return '🛡️ 小s'
  return ''
})

const factionClass = computed(() => ({
  'faction-mimic': store.currentFaction === 'mimic',
  'faction-patrol': store.currentFaction === 'patrol',
}))

const suppressionPercent = computed(() => {
  return Math.min(100, store.mimicProfile?.suppression_value ?? 0)
})

const suppressionBarClass = computed(() => {
  const v = suppressionPercent.value
  if (v >= 80) return 'suppression-red'
  if (v >= 40) return 'suppression-orange'
  return 'suppression-green'
})

const currentZoneLabel = computed(() => {
  const name = store.currentZone?.name
  return name ? ZONE_LABELS[name] ?? name : '未知'
})

// ── Helpers ──

function formatSeconds(secs: number): string {
  const h = Math.floor(secs / 3600)
  const m = Math.floor((secs % 3600) / 60)
  const s = secs % 60
  if (h > 0) return `${h}h ${m}m`
  if (m > 0) return `${m}m ${s}s`
  return `${s}s`
}

// ── Actions ──

async function enterZone(zoneName: string) {
  traveling.value = true
  travelError.value = null
  try {
    await store.travelTo(zoneName)
    await store.loadZones()
    const routes: Record<string, string> = {
      salon:      '/phantom-city/salon',
      checkpoint: '/phantom-city/checkpoint',
    }
    const route = routes[zoneName]
    if (route) router.push(route)
  } catch (e: unknown) {
    travelError.value = e instanceof Error ? e.message : '移动失败，请重试'
  } finally {
    traveling.value = false
  }
}

async function handleChooseFaction(faction: 'mimic' | 'patrol') {
  choosingFaction.value = true
  factionError.value = null
  try {
    await api.chooseFaction(faction)
    await store.loadProfile()
    await store.loadZones()
    const dest = faction === 'mimic' ? '/phantom-city/salon' : '/phantom-city/checkpoint'
    router.push(dest)
  } catch (e: unknown) {
    factionError.value = e instanceof Error ? e.message : '选择失败，请重试'
  } finally {
    choosingFaction.value = false
  }
}

// ── Lifecycle ──

onMounted(async () => {
  await store.loadProfile()
  const zoneName = store.currentZone?.name
  if (zoneName) {
    const route = ZONE_ROUTES[zoneName]
    if (route) {
      router.push(route)
      return
    }
  }
  await store.loadZones()
})
</script>

<style scoped>
.phantom-city-view {
  min-height: 100vh;
  background: #f5f0e8;
  font-family: 'Courier New', Courier, monospace;
}

/* Header */
.pc-header {
  border-bottom: 2px solid #000;
  background: #fff;
  padding: 12px 16px;
}

.pc-header-inner {
  max-width: 960px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  gap: 16px;
}

.back-btn {
  font-size: 14px;
  padding: 6px 12px;
  white-space: nowrap;
}

.pc-title-block {
  flex: 1;
  text-align: center;
}

.pc-title {
  font-size: 24px;
  font-weight: 900;
  letter-spacing: 2px;
  margin: 0;
  color: #000;
}

.pc-subtitle {
  font-size: 12px;
  color: #555;
  margin: 2px 0 0;
}

.pc-header-right {
  min-width: 100px;
  display: flex;
  justify-content: flex-end;
}

.faction-badge {
  padding: 4px 10px;
  border: 2px solid #000;
  font-weight: 700;
  font-size: 13px;
}

.faction-mimic { background: #ff69b4; color: #000; }
.faction-patrol { background: #4a90d9; color: #fff; }

/* Loading */
.pc-loading {
  text-align: center;
  padding: 60px 16px;
}

.loading-text {
  font-size: 18px;
  font-weight: 700;
  color: #555;
}

/* Body */
.pc-body {
  max-width: 960px;
  margin: 0 auto;
  padding: 20px 16px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* Detention Banner */
.detention-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 18px;
  background: #ff2d2d;
  border: 2px solid #000;
  box-shadow: 4px 4px 0 #000;
  color: #fff;
  font-weight: 700;
  flex-wrap: wrap;
}

.detention-icon { font-size: 22px; }

.detention-profile-btn {
  margin-left: auto;
  background: #fff;
  color: #000;
  padding: 4px 12px;
  font-size: 13px;
}

/* Stats Bar */
.stats-bar {
  display: flex;
  gap: 20px;
  padding: 14px 18px;
  background: #fff;
  flex-wrap: wrap;
  align-items: center;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}

.stat-label { font-weight: 600; color: #555; }
.stat-value { font-weight: 900; color: #000; }

.suppression-bar-wrap {
  width: 80px;
  height: 10px;
  background: #eee;
  border: 1px solid #000;
}

.suppression-bar-fill {
  height: 100%;
  transition: width 0.3s ease;
}

.suppression-green { background: #22c55e; }
.suppression-orange { background: #f97316; }
.suppression-red { background: #ef4444; }

/* Faction Selection */
.faction-select-section { text-align: center; }

.section-heading {
  font-size: 22px;
  font-weight: 900;
  color: #000;
  margin: 0 0 6px;
}

.section-hint {
  font-size: 13px;
  color: #666;
  margin: 0 0 20px;
}

.faction-cards {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  max-width: 700px;
  margin: 0 auto;
}

.faction-card {
  padding: 28px 24px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.mimic-card { background: #fff0f8; }
.patrol-card { background: #f0f4ff; }

.faction-icon { font-size: 48px; }
.faction-name { font-size: 22px; font-weight: 900; margin: 0; }
.faction-desc { font-size: 14px; color: #555; margin: 0; }

.faction-perks {
  text-align: left;
  font-size: 13px;
  color: #333;
  padding-left: 20px;
  margin: 0;
  line-height: 1.8;
}

.mimic-btn {
  background: #ff69b4;
  border: 2px solid #000;
  box-shadow: 3px 3px 0 #000;
  font-weight: 700;
  padding: 10px 20px;
  cursor: pointer;
  font-size: 15px;
  transition: transform 0.1s;
}
.mimic-btn:hover:not(:disabled) { transform: translate(-2px, -2px); box-shadow: 5px 5px 0 #000; }

.patrol-btn {
  background: #4a90d9;
  color: #fff;
  border: 2px solid #000;
  box-shadow: 3px 3px 0 #000;
  font-weight: 700;
  padding: 10px 20px;
  cursor: pointer;
  font-size: 15px;
  transition: transform 0.1s;
}
.patrol-btn:hover:not(:disabled) { transform: translate(-2px, -2px); box-shadow: 5px 5px 0 #000; }

.error-msg {
  color: #dc2626;
  font-weight: 700;
  margin-top: 12px;
}

/* Zones Section */
.current-zone-label {
  color: #d97706;
  font-style: italic;
}

.entry-section {
  text-align: center;
  padding: 20px 0;
}

.entry-btns {
  display: flex;
  gap: 16px;
  justify-content: center;
  margin-top: 16px;
  flex-wrap: wrap;
}

.zone-entry-btn {
  padding: 14px 28px;
  font-size: 16px;
  font-weight: 700;
  border: 2px solid #000;
  box-shadow: 4px 4px 0 #000;
  cursor: pointer;
  font-family: inherit;
  transition: transform 0.1s;
}
.zone-entry-btn:hover { transform: translate(-2px, -2px); box-shadow: 6px 6px 0 #000; }
.salon-btn { background: #d1fae5; }
.checkpoint-btn { background: #fee2e2; }

/* Control room & profile */
.control-room-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  background: #1a1a1a;
  color: #fff;
  margin-top: 8px;
}

.profile-link {
  display: block;
  text-align: center;
  margin-top: 12px;
  padding: 10px;
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
.neo-brutal-button:hover { transform: translate(-1px, -1px); box-shadow: 4px 4px 0 #000; }
.neo-brutal-button:active { transform: translate(2px, 2px); box-shadow: 1px 1px 0 #000; }

/* Responsive */
@media (max-width: 700px) {
  .faction-cards { grid-template-columns: 1fr; }
  .pc-title { font-size: 18px; }
  .stats-bar { gap: 12px; }
}
</style>
