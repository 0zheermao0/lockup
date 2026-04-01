<template>
  <header class="zone-header">
    <div class="zone-header-inner">

      <!-- Left: Back + Title -->
      <RouterLink to="/games" class="neo-brutal-button back-btn">← 返回</RouterLink>
      <div class="zone-title-block">
        <h1 class="zone-title">{{ title }}</h1>
        <span v-if="dangerBadge" class="zone-badge danger-badge">{{ dangerBadge }}</span>
        <span v-if="playerBadge" class="zone-badge player-badge">{{ playerBadge }}</span>
        <span v-if="extraBadge" class="zone-badge extra-badge" :class="extraBadgeClass">{{ extraBadge }}</span>
      </div>

      <!-- Right: Status Bar -->
      <div v-if="store.profile" class="status-bar">

        <!-- Faction badge -->
        <div
          v-if="store.currentFaction"
          class="faction-badge"
          :class="store.currentFaction === 'mimic' ? 'faction-mimic' : 'faction-patrol'"
        >
          {{ store.currentFaction === 'mimic' ? '小男娘' : '小s' }}
        </div>

        <div class="stat-divider"></div>

        <!-- Mimic stats -->
        <template v-if="store.currentFaction === 'mimic' && store.mimicProfile">
          <div class="stat-item supp-item" :class="suppressionClass">
            <span class="stat-icon">⚡</span>
            <div class="supp-inner">
              <span class="stat-val">{{ store.mimicProfile.suppression_value }}%</span>
              <div class="supp-track">
                <div
                  class="supp-fill"
                  :style="{ width: suppressionPct + '%' }"
                  :class="suppressionFillClass"
                ></div>
              </div>
            </div>
          </div>
          <div class="stat-item">
            <span class="stat-icon">💧</span>
            <span class="stat-val">{{ store.mimicProfile.purity_score }}</span>
            <span class="stat-label">纯净</span>
          </div>
          <div class="stat-item" :class="{ 'stat-warn': store.mimicProfile.depilation_charge < 30 }">
            <span class="stat-icon">🔋</span>
            <span class="stat-val">{{ store.mimicProfile.depilation_charge }}%</span>
            <span class="stat-label">电量</span>
          </div>
        </template>

        <!-- Patrol stats -->
        <template v-if="store.currentFaction === 'patrol' && store.patrolProfile">
          <div class="stat-item">
            <span class="stat-icon">👑</span>
            <span class="stat-val">{{ store.patrolProfile.authority_value }}</span>
            <span class="stat-label">管控力</span>
          </div>
          <div class="stat-item">
            <span class="stat-icon">⭐</span>
            <span class="stat-val">{{ store.patrolProfile.reputation_score }}</span>
            <span class="stat-label">信誉</span>
          </div>
          <div class="stat-item">
            <span class="stat-icon">🎟️</span>
            <span class="stat-val">{{ store.patrolProfile.inspection_tokens }}</span>
            <span class="stat-label">配额</span>
          </div>
        </template>

        <!-- Crystals (both factions) -->
        <div class="stat-divider"></div>
        <div class="stat-item crystal-raw">
          <span class="stat-icon">💎</span>
          <span class="stat-val">{{ store.crystals?.raw_crystals ?? 0 }}</span>
          <span class="stat-label">备皮刀</span>
        </div>
        <div class="stat-item crystal-purified">
          <span class="stat-icon">💜</span>
          <span class="stat-val">{{ store.crystals?.purified_crystals ?? 0 }}</span>
          <span class="stat-label">脱毛仪</span>
        </div>

      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { usePhantomCityStore } from '../../stores/phantomCity'

defineProps<{
  title: string
  dangerBadge?: string
  playerBadge?: string
  extraBadge?: string
  extraBadgeClass?: string
}>()

const store = usePhantomCityStore()

const suppressionPct = computed(() =>
  Math.min(100, store.mimicProfile?.suppression_value ?? 0)
)

const suppressionClass = computed(() => {
  const v = suppressionPct.value
  if (v >= 80) return 'supp-red'
  if (v >= 40) return 'supp-orange'
  return 'supp-green'
})

const suppressionFillClass = computed(() => {
  const v = suppressionPct.value
  if (v >= 80) return 'fill-red'
  if (v >= 40) return 'fill-orange'
  return 'fill-green'
})
</script>

<style scoped>
.zone-header {
  border-bottom: 2px solid #000;
  background: #fff;
  padding: 10px 16px;
}

.zone-header-inner {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  gap: 12px;
}

.zone-title-block {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.zone-title {
  font-size: 18px;
  font-weight: 900;
  margin: 0;
  white-space: nowrap;
}

.zone-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 7px;
  border: 2px solid currentColor;
  white-space: nowrap;
}

.danger-badge {
  color: #dc2626;
  background: #fee2e2;
  animation: badge-pulse 1.5s infinite;
}

@keyframes badge-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.player-badge {
  color: #555;
  background: #f3f4f6;
}

.extra-badge {
  color: #d97706;
  background: #fef3c7;
  animation: badge-pulse 1.5s infinite;
}

/* Faction badge */
.faction-badge {
  font-size: 11px;
  font-weight: 900;
  padding: 3px 9px;
  border: 2px solid currentColor;
  white-space: nowrap;
  letter-spacing: 0.5px;
}

.faction-mimic {
  color: #be185d;
  background: #fdf2f8;
}

.faction-patrol {
  color: #1d4ed8;
  background: #eff6ff;
}

/* Status Bar */
.status-bar {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 6px;
  justify-content: flex-end;
  flex-wrap: wrap;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 3px;
  padding: 3px 7px;
  border: 1.5px solid #d1d5db;
  background: #f9fafb;
  font-family: 'Courier New', Courier, monospace;
  font-size: 12px;
  white-space: nowrap;
}

.stat-icon {
  font-size: 13px;
  line-height: 1;
}

.stat-val {
  font-weight: 900;
  font-size: 13px;
}

.stat-label {
  font-size: 10px;
  color: #6b7280;
  font-weight: 600;
}

/* Suppression item */
.supp-item {
  gap: 4px;
}

.supp-inner {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.supp-track {
  width: 50px;
  height: 5px;
  background: #e5e7eb;
  border: 1px solid #d1d5db;
}

.supp-fill {
  height: 100%;
  transition: width 0.3s ease;
}

.fill-green { background: #22c55e; }
.fill-orange { background: #f97316; }
.fill-red { background: #ef4444; }

/* Suppression color coding */
.supp-green .stat-val { color: #16a34a; }
.supp-orange .stat-val { color: #d97706; }
.supp-red .stat-val { color: #dc2626; }
.supp-red { border-color: #fca5a5 !important; background: #fef2f2 !important; }

/* Warn state */
.stat-warn {
  border-color: #fca5a5 !important;
  background: #fef2f2 !important;
}
.stat-warn .stat-val { color: #dc2626; }

/* Crystal colors */
.crystal-raw .stat-val { color: #d97706; }
.crystal-purified .stat-val { color: #7c3aed; }

/* Divider */
.stat-divider {
  width: 1px;
  height: 20px;
  background: #d1d5db;
  flex-shrink: 0;
}

/* Back button */
.back-btn {
  font-size: 13px;
  padding: 5px 10px;
  white-space: nowrap;
  flex-shrink: 0;
}

@media (max-width: 768px) {
  .zone-header-inner {
    flex-wrap: wrap;
    gap: 8px;
  }
  .status-bar {
    width: 100%;
    justify-content: flex-start;
  }
  .stat-label {
    display: none;
  }
  .zone-title {
    font-size: 16px;
  }
}
</style>
