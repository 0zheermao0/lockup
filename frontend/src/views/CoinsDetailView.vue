<template>
  <div class="coins-detail-page">
    <!-- 顶部导航 -->
    <header class="page-header">
      <button class="back-btn" @click="$router.back()">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="m15 18-6-6 6-6"/>
        </svg>
      </button>
      <h1>积分详情</h1>
    </header>

    <!-- 当前积分卡片 -->
    <section class="current-coins-card">
      <div class="coins-icon">🪙</div>
      <div class="coins-amount">{{ authStore.user?.coins || 0 }}</div>
      <div class="coins-label">当前积分</div>
    </section>

    <!-- 筛选标签 -->
    <section class="filter-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.value"
        :class="['tab-btn', { active: currentTab === tab.value }]"
        @click="handleTabChange(tab.value)"
      >
        {{ tab.label }}
      </button>
    </section>

    <!-- 积分记录列表 -->
    <section class="coins-logs-section">
      <div class="logs-list" v-if="!userStatsStore.coinsLogsLoading || userStatsStore.coinsLogs.length > 0">
        <div v-for="log in userStatsStore.coinsLogs" :key="log.id" class="log-item">
          <div class="log-icon" :class="{ 'income': log.amount > 0, 'expense': log.amount < 0 }">
            {{ getChangeIcon(log.change_type) }}
          </div>
          <div class="log-content">
            <div class="log-title">{{ log.description || log.change_type_display }}</div>
            <div class="log-type">{{ log.change_type_display }}</div>
            <div class="log-time">{{ log.time_ago }}</div>
          </div>
          <div class="log-change" :class="{ 'income': log.amount > 0, 'expense': log.amount < 0 }">
            {{ log.amount > 0 ? '+' : '' }}{{ log.amount }}
          </div>
        </div>
      </div>
      <div v-else-if="userStatsStore.coinsLogsLoading" class="loading-state">
        <div class="spinner"></div>
        <span>加载中...</span>
      </div>

      <!-- 空状态 -->
      <div v-else class="empty-state">
        <span class="empty-icon">📭</span>
        <p>暂无记录</p>
      </div>

      <!-- 加载更多 -->
      <div class="load-more" v-if="userStatsStore.hasMoreCoinsLogs">
        <button
          @click="loadMoreLogs"
          :disabled="userStatsStore.coinsLogsLoading"
          class="load-more-btn"
        >
          {{ userStatsStore.coinsLogsLoading ? '加载中...' : '加载更多' }}
        </button>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useUserStatsStore } from '@/stores/userStats'

const authStore = useAuthStore()
const userStatsStore = useUserStatsStore()

const tabs = [
  { label: '全部', value: 'all' },
  { label: '收入', value: 'income' },
  { label: '支出', value: 'expense' }
]

const currentTab = ref('all')

function getChangeIcon(changeType: string): string {
  const iconMap: Record<string, string> = {
    'hourly_reward': '⏰',
    'daily_login': '📅',
    'task_complete': '✅',
    'board_task_reward': '📋',
    'event_reward': '🎉',
    'admin_grant': '👑',
    'other_income': '💰',
    'task_creation': '📝',
    'store_purchase': '🛒',
    'event_cost': '🎮',
    'admin_deduct': '⚠️',
    'other_expense': '💸'
  }
  return iconMap[changeType] || '🪙'
}

async function handleTabChange(tabValue: string) {
  currentTab.value = tabValue
  const type = tabValue === 'all' ? undefined : tabValue
  await userStatsStore.fetchCoinsLogs(1, type)
}

async function loadMoreLogs() {
  const type = currentTab.value === 'all' ? undefined : currentTab.value
  await userStatsStore.loadMoreCoinsLogs(type)
}

onMounted(async () => {
  await userStatsStore.fetchCoinsLogs(1)
})
</script>

<style scoped>
.coins-detail-page {
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

/* 当前积分卡片 */
.current-coins-card {
  margin: 1rem;
  padding: 2rem;
  background: linear-gradient(135deg, #ffc107, #ff8f00);
  border: 2px solid var(--border-color, #000);
  border-radius: 12px;
  box-shadow: 4px 4px 0 var(--border-color, #000);
  text-align: center;
  color: #000;
}

.coins-icon {
  font-size: 4rem;
  margin-bottom: 0.5rem;
}

.coins-amount {
  font-size: 3rem;
  font-weight: 800;
  margin-bottom: 0.5rem;
  text-shadow: 2px 2px 0 rgba(0, 0, 0, 0.1);
}

.coins-label {
  font-size: 1rem;
  opacity: 0.8;
  font-weight: 500;
}

/* 筛选标签 */
.filter-tabs {
  display: flex;
  gap: 0.5rem;
  margin: 1rem;
  padding: 0.5rem;
  background: var(--card-bg, #fff);
  border: 2px solid var(--border-color, #000);
  border-radius: 10px;
  box-shadow: 3px 3px 0 var(--border-color, #000);
}

.tab-btn {
  flex: 1;
  padding: 0.75rem;
  background: transparent;
  border: 2px solid transparent;
  border-radius: 6px;
  font-weight: 600;
  font-size: 0.95rem;
  cursor: pointer;
  transition: all 0.2s;
  color: var(--text-secondary, #666);
}

.tab-btn:hover {
  background: var(--bg-color, #f5f5f5);
}

.tab-btn.active {
  background: var(--primary-color, #007bff);
  color: #fff;
  border-color: var(--border-color, #000);
}

/* 积分记录 */
.coins-logs-section {
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
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--card-bg, #fff);
  border: 2px solid var(--border-color, #000);
  border-radius: 10px;
  font-size: 1.5rem;
  margin-right: 1rem;
  flex-shrink: 0;
  transition: all 0.2s;
}

.log-icon.income {
  background: linear-gradient(135deg, #d4edda, #c3e6cb);
  border-color: #28a745;
}

.log-icon.expense {
  background: linear-gradient(135deg, #f8d7da, #f5c6cb);
  border-color: #dc3545;
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
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.log-type {
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
  font-size: 1.2rem;
  margin-left: 1rem;
  min-width: 50px;
  text-align: right;
}

.log-change.income {
  color: #28a745;
}

.log-change.expense {
  color: #dc3545;
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
  .current-coins-card,
  .coins-logs-section {
    margin: 0.75rem;
    padding: 1.5rem 1rem;
  }

  .filter-tabs {
    margin: 0.75rem;
  }

  .coins-amount {
    font-size: 2.5rem;
  }

  .log-item {
    padding: 0.75rem;
  }

  .log-icon {
    width: 40px;
    height: 40px;
    font-size: 1.25rem;
  }
}
</style>
