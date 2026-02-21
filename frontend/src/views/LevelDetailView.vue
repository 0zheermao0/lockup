<template>
  <div class="level-detail-page">
    <!-- 顶部导航 -->
    <header class="page-header">
      <button class="back-btn" @click="$router.back()">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="m15 18-6-6 6-6"/>
        </svg>
      </button>
      <h1>等级详情</h1>
    </header>

    <!-- 当前等级卡片 -->
    <section class="current-level-card">
      <div class="level-badge" :class="getLevelCSSClass(currentLevel)" :style="getLevelCSSProperties(currentLevel)">
        {{ getLevelDisplayName(currentLevel) }}
      </div>
      <div class="level-name">{{ levelName }}</div>
      <div class="activity-score">
        当前活跃度: <strong>{{ authStore.user?.activity_score || 0 }}</strong>
      </div>
    </section>

    <!-- 升级进度条 - 多维度 -->
    <section class="progress-section" v-if="!isMaxLevel">
      <h2>升级进度</h2>
      <div class="overall-progress">
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: overallProgress + '%', background: levelColor }"></div>
        </div>
        <span class="progress-text">{{ overallProgress }}%</span>
      </div>

      <!-- 各维度进度 -->
      <div class="dimensions-list">
        <div v-for="dim in dimensions" :key="dim.name" class="dimension-item">
          <div class="dim-header">
            <span class="dim-name">{{ dim.label }}</span>
            <span class="dim-value">{{ formatNumber(dim.current) }}/{{ formatNumber(dim.required) }}{{ dim.unit }}</span>
          </div>
          <div class="dim-progress-bar">
            <div class="dim-progress-fill" :class="{ 'met': dim.is_met }" :style="{ width: dim.percentage + '%' }"></div>
          </div>
          <span class="dim-status" :class="{ 'met': dim.is_met }">
            {{ dim.is_met ? '✓ 已满足' : '未满足' }}
          </span>
        </div>
      </div>
    </section>

    <!-- 已满级提示 -->
    <section class="max-level-tip" v-else>
      <div class="crown-icon">👑</div>
      <p>恭喜！您已达到最高等级</p>
      <span class="sub-text">继续保持活跃，享受社区特权</span>
    </section>

    <!-- 活跃度记录 -->
    <section class="activity-logs-section">
      <h2>活跃度记录</h2>
      <div class="logs-list" v-if="!userStatsStore.activityLogsLoading || userStatsStore.activityLogs.length > 0">
        <div v-for="log in userStatsStore.activityLogs" :key="log.id" class="log-item">
          <div class="log-icon" :class="log.action_type">
            {{ log.action_type === 'activity_gain' ? '📈' : '⏰' }}
          </div>
          <div class="log-content">
            <div class="log-title">{{ log.action_type_display }}</div>
            <div class="log-desc">{{ getLogDescription(log) }}</div>
            <div class="log-time">{{ log.time_ago }}</div>
          </div>
          <div class="log-change" :class="{ 'positive': log.points_change > 0 }">
            {{ log.points_change > 0 ? '+' : '' }}{{ log.points_change }}
          </div>
        </div>
      </div>
      <div v-else-if="userStatsStore.activityLogsLoading" class="loading-state">
        <div class="spinner"></div>
        <span>加载中...</span>
      </div>
      <div v-else class="empty-state">
        <span class="empty-icon">📭</span>
        <p>暂无记录</p>
      </div>

      <!-- 加载更多 -->
      <div class="load-more" v-if="userStatsStore.hasMoreActivityLogs">
        <button
          @click="loadMoreLogs"
          :disabled="userStatsStore.activityLogsLoading"
          class="load-more-btn"
        >
          {{ userStatsStore.activityLogsLoading ? '加载中...' : '加载更多' }}
        </button>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useUserStatsStore } from '@/stores/userStats'
import { getLevelCSSClass, getLevelCSSProperties, getLevelDisplayName, getLevelColorScheme } from '@/lib/level-colors'
import type { ActivityLog } from '@/types'

const authStore = useAuthStore()
const userStatsStore = useUserStatsStore()

const currentLevel = computed(() => authStore.user?.level || 1)
const isMaxLevel = computed(() => currentLevel.value >= 4)

const levelName = computed(() => {
  const names = {
    1: '初级探索者',
    2: '进阶冒险家',
    3: '资深挑战者',
    4: '传奇大师'
  }
  return names[currentLevel.value as keyof typeof names] || '未知等级'
})

const levelColor = computed(() => {
  const colors = getLevelColorScheme(currentLevel.value)
  return colors.background
})

const dimensions = computed(() => userStatsStore.levelProgress?.dimensions || [])
const overallProgress = computed(() => userStatsStore.levelProgress?.overall_progress || 0)

function formatNumber(num: number): string {
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'k'
  }
  if (num % 1 === 0) {
    return num.toString()
  }
  return num.toFixed(1)
}

function getLogDescription(log: ActivityLog): string {
  if (log.action_type === 'activity_gain') {
    return `活跃度增加，当前总计: ${log.new_total}`
  } else if (log.action_type === 'time_decay') {
    const days = log.metadata?.days_inactive || 0
    return `${days}天未活跃，活跃度衰减`
  }
  return `当前总计: ${log.new_total}`
}

async function loadMoreLogs() {
  await userStatsStore.loadMoreActivityLogs()
}

onMounted(async () => {
  await Promise.all([
    userStatsStore.fetchActivityLogs(1),
    userStatsStore.fetchLevelProgress()
  ])
})
</script>

<style scoped>
.level-detail-page {
  min-height: 100vh;
  background: var(--bg-color, #f5f5f5);
  padding-bottom: 2rem;
}

/* 顶部导航 */
.page-header {
  display: flex;
  align-items: center;
  padding: 1rem;
  background: var(--card-bg, #fff);
  border-bottom: 2px solid var(--border-color, #000);
  position: sticky;
  top: 0;
  z-index: 10;
}

.back-btn {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-color, #f5f5f5);
  border: 2px solid var(--border-color, #000);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  margin-right: 1rem;
}

.back-btn:hover {
  transform: translate(-2px, -2px);
  box-shadow: 3px 3px 0 var(--border-color, #000);
}

.back-btn:active {
  transform: translate(0, 0);
  box-shadow: none;
}

.page-header h1 {
  font-size: 1.25rem;
  font-weight: 700;
  margin: 0;
}

/* 当前等级卡片 */
.current-level-card {
  margin: 1rem;
  padding: 1.5rem;
  background: var(--card-bg, #fff);
  border: 2px solid var(--border-color, #000);
  border-radius: 12px;
  box-shadow: 4px 4px 0 var(--border-color, #000);
  text-align: center;
}

.level-badge {
  display: inline-block;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  font-weight: 700;
  font-size: 1.1rem;
  margin-bottom: 0.75rem;
  border: 2px solid var(--level-border, #000);
}

.level-name {
  font-size: 1.25rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
  color: var(--text-color, #333);
}

.activity-score {
  font-size: 1rem;
  color: var(--text-secondary, #666);
}

.activity-score strong {
  color: var(--text-color, #333);
  font-size: 1.25rem;
}

/* 升级进度 */
.progress-section {
  margin: 1rem;
  padding: 1.5rem;
  background: var(--card-bg, #fff);
  border: 2px solid var(--border-color, #000);
  border-radius: 12px;
  box-shadow: 4px 4px 0 var(--border-color, #000);
}

.progress-section h2,
.activity-logs-section h2 {
  font-size: 1.1rem;
  font-weight: 700;
  margin: 0 0 1rem 0;
  padding-bottom: 0.75rem;
  border-bottom: 2px solid var(--border-color, #eee);
}

.overall-progress {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.progress-bar {
  flex: 1;
  height: 24px;
  background: var(--bg-color, #e0e0e0);
  border: 2px solid var(--border-color, #000);
  border-radius: 6px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  transition: width 0.5s ease;
  border-radius: 4px;
}

.progress-text {
  font-weight: 700;
  font-size: 1rem;
  min-width: 50px;
  text-align: right;
}

/* 各维度进度 */
.dimensions-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.dimension-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.dim-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.9rem;
}

.dim-name {
  font-weight: 600;
  color: var(--text-color, #333);
}

.dim-value {
  color: var(--text-secondary, #666);
  font-weight: 500;
}

.dim-progress-bar {
  height: 12px;
  background: var(--bg-color, #e0e0e0);
  border: 1px solid var(--border-color, #ccc);
  border-radius: 4px;
  overflow: hidden;
}

.dim-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #6c757d, #adb5bd);
  transition: width 0.3s ease;
  border-radius: 3px;
}

.dim-progress-fill.met {
  background: linear-gradient(90deg, #28a745, #34ce57);
}

.dim-status {
  font-size: 0.8rem;
  color: var(--text-secondary, #999);
  font-weight: 500;
}

.dim-status.met {
  color: #28a745;
}

/* 满级提示 */
.max-level-tip {
  margin: 1rem;
  padding: 2rem;
  background: linear-gradient(135deg, #ffc107, #ff8f00);
  border: 2px solid var(--border-color, #000);
  border-radius: 12px;
  box-shadow: 4px 4px 0 var(--border-color, #000);
  text-align: center;
  color: #000;
}

.crown-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
}

.max-level-tip p {
  font-size: 1.5rem;
  font-weight: 700;
  margin: 0 0 0.5rem 0;
}

.sub-text {
  font-size: 0.9rem;
  opacity: 0.8;
}

/* 活跃度记录 */
.activity-logs-section {
  margin: 1rem;
  padding: 1.5rem;
  background: var(--card-bg, #fff);
  border: 2px solid var(--border-color, #000);
  border-radius: 12px;
  box-shadow: 4px 4px 0 var(--border-color, #000);
}

.logs-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.log-item {
  display: flex;
  align-items: center;
  padding: 1rem;
  background: var(--bg-color, #f8f9fa);
  border: 2px solid var(--border-color, #e0e0e0);
  border-radius: 8px;
  transition: all 0.2s;
}

.log-item:hover {
  border-color: var(--border-color, #000);
  transform: translate(-1px, -1px);
  box-shadow: 2px 2px 0 var(--border-color, #000);
}

.log-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--card-bg, #fff);
  border: 2px solid var(--border-color, #000);
  border-radius: 8px;
  font-size: 1.25rem;
  margin-right: 1rem;
  flex-shrink: 0;
}

.log-content {
  flex: 1;
  min-width: 0;
}

.log-title {
  font-weight: 600;
  font-size: 0.95rem;
  color: var(--text-color, #333);
  margin-bottom: 0.25rem;
}

.log-desc {
  font-size: 0.8rem;
  color: var(--text-secondary, #666);
  margin-bottom: 0.25rem;
}

.log-time {
  font-size: 0.75rem;
  color: var(--text-tertiary, #999);
}

.log-change {
  font-weight: 700;
  font-size: 1.1rem;
  color: var(--text-secondary, #666);
  margin-left: 1rem;
}

.log-change.positive {
  color: #28a745;
}

/* 加载状态 */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  gap: 1rem;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--border-color, #e0e0e0);
  border-top-color: var(--primary-color, #007bff);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  color: var(--text-secondary, #999);
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.empty-state p {
  margin: 0;
  font-size: 1rem;
}

/* 加载更多 */
.load-more {
  margin-top: 1.5rem;
  text-align: center;
}

.load-more-btn {
  padding: 0.75rem 2rem;
  background: var(--bg-color, #f5f5f5);
  border: 2px solid var(--border-color, #000);
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.load-more-btn:hover:not(:disabled) {
  transform: translate(-2px, -2px);
  box-shadow: 3px 3px 0 var(--border-color, #000);
}

.load-more-btn:active:not(:disabled) {
  transform: translate(0, 0);
  box-shadow: none;
}

.load-more-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 响应式 */
@media (max-width: 640px) {
  .current-level-card,
  .progress-section,
  .max-level-tip,
  .activity-logs-section {
    margin: 0.75rem;
    padding: 1rem;
  }

  .log-item {
    padding: 0.75rem;
  }

  .log-icon {
    width: 36px;
    height: 36px;
    font-size: 1rem;
  }
}
</style>
