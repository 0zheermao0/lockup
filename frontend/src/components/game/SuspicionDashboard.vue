<template>
  <div class="suspicion-dashboard">

    <!-- Header -->
    <div class="suspicion-dashboard__header">
      <span class="suspicion-dashboard__title">嫌疑积分面板</span>
      <span class="suspicion-dashboard__tokens">
        🪙 {{ inspectionTokens }}/10
      </span>
    </div>

    <!-- Player rows -->
    <div v-if="resolvedEntries.length > 0" class="suspicion-dashboard__list">
      <div
        v-for="entry in resolvedEntries"
        :key="entry.playerId"
        class="suspicion-dashboard__row"
      >
        <!-- Avatar + name -->
        <div class="suspicion-dashboard__player">
          <div class="suspicion-dashboard__avatar">
            <img
              v-if="entry.avatar"
              :src="entry.avatar"
              :alt="entry.username"
              class="suspicion-dashboard__avatar-img"
            />
            <span v-else class="suspicion-dashboard__avatar-fallback">
              {{ entry.username.charAt(0).toUpperCase() }}
            </span>
          </div>
          <span class="suspicion-dashboard__username">{{ entry.username }}</span>
        </div>

        <!-- Bar + score + badges -->
        <div class="suspicion-dashboard__score-section">
          <div class="suspicion-dashboard__bar-track">
            <div
              class="suspicion-dashboard__bar-fill"
              :class="{
                'suspicion-dashboard__bar-fill--pulse': entry.score >= 80,
              }"
              :style="{
                width: `${Math.min(entry.score, 100)}%`,
                backgroundColor: scoreColor(entry.score),
              }"
            />
          </div>
          <div class="suspicion-dashboard__score-right">
            <span
              v-if="entry.score >= 80"
              class="suspicion-dashboard__warn-icon"
            >⚠️</span>
            <span class="suspicion-dashboard__score-value">{{ entry.score }}</span>
            <span
              v-if="entry.score >= 80"
              class="suspicion-dashboard__badge suspicion-dashboard__badge--red suspicion-dashboard__badge--pulse"
            >
              高度嫌疑
            </span>
            <span
              v-else-if="entry.score >= 30"
              class="suspicion-dashboard__badge suspicion-dashboard__badge--orange"
            >
              可体检
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-else class="suspicion-dashboard__empty">
      暂无嫌疑记录
    </div>

  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  suspicionData: Record<string, number>
  players: Array<{ id: number; username: string; avatar: string | null }>
  inspectionTokens: number
}>()

interface ResolvedEntry {
  playerId: string
  username: string
  avatar: string | null
  score: number
}

const resolvedEntries = computed((): ResolvedEntry[] => {
  return Object.entries(props.suspicionData).map(([playerId, score]) => {
    const player = props.players.find((p) => String(p.id) === playerId)
    return {
      playerId,
      username: player?.username ?? `用户#${playerId}`,
      avatar: player?.avatar ?? null,
      score,
    }
  }).sort((a, b) => b.score - a.score)
})

function scoreColor(score: number): string {
  if (score >= 80) return '#ff3300'
  if (score >= 30) return '#ffaa00'
  return '#00cc44'
}
</script>

<style scoped>
.suspicion-dashboard {
  background: #fff;
  border: 2px solid #000;
  box-shadow: 4px 4px 0 #000;
  font-family: 'Inter', sans-serif;
  overflow: hidden;
}

.suspicion-dashboard__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  border-bottom: 2px solid #000;
  background: #f5f5f5;
}

.suspicion-dashboard__title {
  font-size: 0.95em;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.suspicion-dashboard__tokens {
  font-size: 0.85em;
  font-weight: 700;
  padding: 2px 8px;
  border: 2px solid #000;
  box-shadow: 2px 2px 0 #000;
  background: #fff;
}

.suspicion-dashboard__list {
  display: flex;
  flex-direction: column;
}

.suspicion-dashboard__row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  border-bottom: 1px solid #e0e0e0;
}

.suspicion-dashboard__row:last-child {
  border-bottom: none;
}

.suspicion-dashboard__player {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 120px;
  flex-shrink: 0;
}

.suspicion-dashboard__avatar {
  width: 32px;
  height: 32px;
  border: 2px solid #000;
  box-shadow: 2px 2px 0 #000;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #e8e8e8;
  flex-shrink: 0;
}

.suspicion-dashboard__avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.suspicion-dashboard__avatar-fallback {
  font-size: 0.9em;
  font-weight: 800;
}

.suspicion-dashboard__username {
  font-size: 0.85em;
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.suspicion-dashboard__score-section {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.suspicion-dashboard__bar-track {
  flex: 1;
  height: 10px;
  background: #e0e0e0;
  border: 2px solid #000;
  overflow: hidden;
  min-width: 60px;
}

.suspicion-dashboard__bar-fill {
  height: 100%;
  transition: width 0.4s ease, background-color 0.4s ease;
}

.suspicion-dashboard__bar-fill--pulse {
  animation: suspicion-pulse 1.5s ease-in-out infinite;
}

.suspicion-dashboard__score-right {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.suspicion-dashboard__warn-icon {
  font-size: 0.85em;
}

.suspicion-dashboard__score-value {
  font-size: 0.85em;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  min-width: 2.5ch;
  text-align: right;
}

.suspicion-dashboard__badge {
  font-size: 0.7em;
  font-weight: 700;
  padding: 1px 6px;
  border: 2px solid #000;
  text-transform: uppercase;
  white-space: nowrap;
}

.suspicion-dashboard__badge--orange {
  background: #ffaa00;
  color: #000;
  border-color: #cc8800;
  box-shadow: 2px 2px 0 #cc8800;
}

.suspicion-dashboard__badge--red {
  background: #ff3300;
  color: #fff;
  border-color: #cc2200;
  box-shadow: 2px 2px 0 #cc2200;
}

.suspicion-dashboard__badge--pulse {
  animation: suspicion-pulse 1.5s ease-in-out infinite;
}

.suspicion-dashboard__empty {
  padding: 24px 14px;
  text-align: center;
  font-size: 0.85em;
  color: #888;
  font-style: italic;
}

@keyframes suspicion-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
</style>
