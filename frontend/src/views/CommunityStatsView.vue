<template>
  <div class="community-stats">
    <!-- Header -->
    <header class="stats-header">
      <div class="header-content">
        <button @click="goBack" class="back-btn" title="返回">
          ← 返回
        </button>
        <h1>🏆 社区排行榜</h1>
        <div class="update-info">
          <span v-if="loading" class="loading-text">加载中...</span>
          <span v-else-if="error" class="error-text">加载失败</span>
          <span v-else class="update-time">{{ updateTimeText }}</span>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="stats-content">
      <div v-if="loading" class="loading-state">
        <div class="loading-spinner"></div>
        <p>正在加载排行榜数据...</p>
      </div>

      <div v-else-if="error" class="error-state">
        <div class="error-icon">⚠️</div>
        <p>{{ error }}</p>
        <button @click="loadLeaderboard" class="retry-btn">重试</button>
      </div>

      <div v-else class="leaderboard-grid">
        <!-- Leaderboard Cards -->
        <div
          v-for="(category, key) in leaderboardCategories"
          :key="key"
          class="leaderboard-card"
          :class="{ 'has-data': category.data.length > 0 }"
        >
          <div class="card-header" :style="getCardGradient(key)">
            <div class="card-icon">{{ category.icon }}</div>
            <div class="card-title">
              <h3>{{ category.title }}</h3>
              <p class="card-description">{{ category.description }}</p>
            </div>
          </div>

          <div class="card-content">
            <div v-if="category.data.length === 0" class="no-data">
              <span class="no-data-icon">📊</span>
              <p>暂无数据</p>
            </div>

            <div
              v-for="(entry, index) in category.data"
              :key="entry.user.id"
              class="leaderboard-item"
              :class="[`rank-${entry.rank}`, { 'clickable': true }]"
              @click="openUserProfile(entry.user)"
            >
              <div class="rank-badge">
                <span v-if="entry.rank === 1" class="medal">🥇</span>
                <span v-else-if="entry.rank === 2" class="medal">🥈</span>
                <span v-else-if="entry.rank === 3" class="medal">🥉</span>
                <span v-else class="rank-number">{{ entry.rank }}</span>
              </div>

              <!-- User Avatar -->
              <div class="leaderboard-avatar">
                <img
                  v-if="entry.user.avatar"
                  :src="entry.user.avatar"
                  :alt="entry.user.username"
                  class="avatar-img"
                />
                <div
                  v-else
                  class="avatar-fallback"
                  :style="{ background: getAvatarGradient(entry.user.username) }"
                >
                  {{ (entry.user.username || 'U').charAt(0).toUpperCase() }}
                </div>
              </div>

              <div class="user-info">
                <span
                  class="username"
                  :class="getLevelCSSClass(entry.user.level)"
                >
                  {{ entry.user.username }}
                </span>
                <span class="level-badge">Lv.{{ entry.user.level }}</span>
              </div>

              <div class="value">
                <span class="number">{{ formatNumber(entry.value) }}</span>
                <span class="unit">{{ category.unit }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>

    <!-- User Profile Modal -->
    <ProfileModal
      :is-visible="showProfileModal"
      :user="selectedUser"
      @close="closeProfileModal"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { userStatsApi } from '../lib/api'
import ProfileModal from '../components/ProfileModal.vue'
import { getLevelCSSClass } from '../lib/level-colors'
import type { CommunityLeaderboard, LeaderboardCategory } from '../types/index'

const router = useRouter()

const loading = ref(true)
const error = ref('')
const leaderboardData = ref<CommunityLeaderboard | null>(null)
const showProfileModal = ref(false)
const selectedUser = ref<any>(null)

const updateTimeText = computed(() => {
  if (!leaderboardData.value?.updated_at) return ''
  const date = new Date(leaderboardData.value.updated_at)
  return `更新于 ${date.toLocaleString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })}`
})

const leaderboardCategories = computed(() => {
  if (!leaderboardData.value) return {}
  return {
    most_likes_received: leaderboardData.value.most_likes_received,
    most_comments_received: leaderboardData.value.most_comments_received,
    most_activity_gained: leaderboardData.value.most_activity_gained,
    most_coins_earned: leaderboardData.value.most_coins_earned,
    most_posts_created: leaderboardData.value.most_posts_created,
    most_tasks_created: leaderboardData.value.most_tasks_created,
    most_tasks_completed: leaderboardData.value.most_tasks_completed
  } as Record<string, LeaderboardCategory>
})

const cardGradients: Record<string, string> = {
  most_likes_received: 'linear-gradient(135deg, #ff6b6b, #ee5a24)',
  most_comments_received: 'linear-gradient(135deg, #4ecdc4, #44a3aa)',
  most_activity_gained: 'linear-gradient(135deg, #a55eea, #8b5cf6)',
  most_coins_earned: 'linear-gradient(135deg, #f9ca24, #f0932b)',
  most_posts_created: 'linear-gradient(135deg, #686de0, #4834d4)',
  most_tasks_created: 'linear-gradient(135deg, #00d2d3, #01a3a4)',
  most_tasks_completed: 'linear-gradient(135deg, #1dd1a1, #10ac84)'
}

const getCardGradient = (key: string) => ({
  background: cardGradients[key] || 'linear-gradient(135deg, #667eea, #764ba2)'
})

const formatNumber = (num: number): string => {
  if (num >= 10000) {
    return (num / 10000).toFixed(1) + 'w'
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'k'
  }
  return num.toString()
}

const getAvatarGradient = (username: string | undefined): string => {
  const gradients = [
    'linear-gradient(135deg, #667eea, #764ba2)',
    'linear-gradient(135deg, #f093fb, #f5576c)',
    'linear-gradient(135deg, #4facfe, #00f2fe)',
    'linear-gradient(135deg, #43e97b, #38f9d7)',
    'linear-gradient(135deg, #fa709a, #fee140)',
    'linear-gradient(135deg, #a8edea, #fed6e3)',
    'linear-gradient(135deg, #ff9a9e, #fecfef)',
    'linear-gradient(135deg, #ffecd2, #fcb69f)'
  ] as const
  const name = username || 'U'
  const index = name.charCodeAt(0) % gradients.length
  return gradients[index as unknown as keyof typeof gradients] as unknown as string || gradients[0]
}

const loadLeaderboard = async () => {
  loading.value = true
  error.value = ''
  try {
    const data = await userStatsApi.getCommunityLeaderboard()
    leaderboardData.value = data
  } catch (err: any) {
    console.error('Failed to load leaderboard:', err)
    error.value = err.message || '加载排行榜失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

const goBack = () => {
  router.back()
}

const openUserProfile = (user: any) => {
  selectedUser.value = user
  showProfileModal.value = true
}

const closeProfileModal = () => {
  showProfileModal.value = false
  selectedUser.value = null
}

onMounted(() => {
  loadLeaderboard()
})
</script>

<style scoped>
.community-stats {
  min-height: 100vh;
  background-color: #f5f5f5;
}

/* Header Styles */
.stats-header {
  background: white;
  border-bottom: 3px solid #000;
  box-shadow: 0 4px 0 rgba(0, 0, 0, 0.1);
  padding: 1rem 0;
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-content {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 1.5rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.back-btn {
  padding: 0.5rem 1rem;
  background: linear-gradient(135deg, #6c757d, #5a6268);
  color: white;
  border: 2px solid #000;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 3px 3px 0 #000;
  transition: all 0.2s ease;
}

.back-btn:hover {
  transform: translate(-2px, -2px);
  box-shadow: 5px 5px 0 #000;
}

.back-btn:active {
  transform: translate(0, 0);
  box-shadow: 2px 2px 0 #000;
}

.stats-header h1 {
  font-size: 1.8rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 2px;
  margin: 0;
  color: #000;
  text-shadow: 2px 2px 0 rgba(0, 0, 0, 0.1);
}

.update-info {
  font-size: 0.875rem;
  color: #666;
}

.loading-text {
  color: #007bff;
}

.error-text {
  color: #dc3545;
}

.update-time {
  color: #28a745;
  font-weight: 500;
}

/* Main Content */
.stats-content {
  max-width: 1400px;
  margin: 0 auto;
  padding: 2rem 1.5rem;
}

/* Loading State */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  gap: 1rem;
}

.loading-spinner {
  width: 50px;
  height: 50px;
  border: 4px solid #ddd;
  border-top-color: #007bff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* Error State */
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  gap: 1rem;
  text-align: center;
}

.error-icon {
  font-size: 3rem;
}

.retry-btn {
  padding: 0.75rem 1.5rem;
  background: linear-gradient(135deg, #dc3545, #c82333);
  color: white;
  border: 2px solid #000;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 3px 3px 0 #000;
  transition: all 0.2s ease;
}

.retry-btn:hover {
  transform: translate(-2px, -2px);
  box-shadow: 5px 5px 0 #000;
}

/* Leaderboard Grid */
.leaderboard-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
  gap: 1.5rem;
}

/* Leaderboard Card */
.leaderboard-card {
  background: white;
  border: 3px solid #000;
  border-radius: 12px;
  box-shadow: 6px 6px 0 #000;
  overflow: hidden;
  transition: all 0.3s ease;
}

.leaderboard-card:hover {
  transform: translate(-3px, -3px);
  box-shadow: 9px 9px 0 rgba(0, 0, 0, 0.8);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.25rem;
  color: white;
  border-bottom: 3px solid #000;
}

.card-icon {
  font-size: 2rem;
  flex-shrink: 0;
}

.card-title h3 {
  margin: 0 0 0.25rem 0;
  font-size: 1.1rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.card-description {
  margin: 0;
  font-size: 0.8rem;
  opacity: 0.9;
  line-height: 1.3;
}

.card-content {
  padding: 1rem;
}

.no-data {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  color: #999;
}

.no-data-icon {
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

/* Leaderboard Items */
.leaderboard-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  border-radius: 8px;
  transition: all 0.2s ease;
  margin-bottom: 0.5rem;
}

.leaderboard-item:last-child {
  margin-bottom: 0;
}

.leaderboard-item.clickable {
  cursor: pointer;
}

.leaderboard-item.clickable:hover {
  background-color: #f8f9fa;
  transform: translateX(4px);
}

.leaderboard-item.rank-1 {
  background: linear-gradient(135deg, #fff9e6, #ffeaa7);
  border: 2px solid #f9ca24;
}

.leaderboard-item.rank-2 {
  background: linear-gradient(135deg, #f8f9fa, #dfe6e9);
  border: 2px solid #b2bec3;
}

.leaderboard-item.rank-3 {
  background: linear-gradient(135deg, #fdf2e9, #fab1a0);
  border: 2px solid #e17055;
}

.rank-badge {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

/* Leaderboard Avatar */
.leaderboard-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  overflow: hidden;
  flex-shrink: 0;
  border: 2px solid #000;
  box-shadow: 2px 2px 0 rgba(0, 0, 0, 0.2);
}

.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-fallback {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 1rem;
  color: white;
}

.medal {
  font-size: 1.5rem;
}

.rank-number {
  font-size: 1rem;
  font-weight: 700;
  color: #666;
}

.user-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.username {
  font-weight: 700;
  font-size: 0.95rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.level-badge {
  font-size: 0.7rem;
  color: #666;
  font-weight: 600;
}

.value {
  display: flex;
  align-items: baseline;
  gap: 0.25rem;
  flex-shrink: 0;
}

.value .number {
  font-size: 1.1rem;
  font-weight: 900;
  color: #000;
}

.value .unit {
  font-size: 0.75rem;
  color: #666;
  font-weight: 500;
}

/* Responsive */
@media (max-width: 1200px) {
  .leaderboard-grid {
    grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  }
}

@media (max-width: 768px) {
  .header-content {
    flex-wrap: wrap;
    gap: 0.75rem;
  }

  .stats-header h1 {
    font-size: 1.3rem;
    order: -1;
    width: 100%;
    text-align: center;
  }

  .back-btn {
    padding: 0.4rem 0.75rem;
    font-size: 0.875rem;
  }

  .update-info {
    font-size: 0.75rem;
  }

  .stats-content {
    padding: 1rem;
  }

  .leaderboard-grid {
    grid-template-columns: 1fr;
    gap: 1rem;
  }

  .leaderboard-card {
    border-width: 2px;
    box-shadow: 4px 4px 0 #000;
  }

  .card-header {
    padding: 1rem;
  }

  .card-icon {
    font-size: 1.75rem;
  }

  .card-title h3 {
    font-size: 1rem;
  }

  .card-description {
    font-size: 0.75rem;
  }

  .leaderboard-item {
    padding: 0.6rem;
  }

  .medal {
    font-size: 1.25rem;
  }

  .value .number {
    font-size: 1rem;
  }

  .leaderboard-avatar {
    width: 36px;
    height: 36px;
  }
}

@media (max-width: 380px) {
  .stats-header h1 {
    font-size: 1.1rem;
  }

  .card-header {
    flex-direction: column;
    text-align: center;
    gap: 0.5rem;
  }

  .user-info {
    max-width: 120px;
  }
}
</style>
