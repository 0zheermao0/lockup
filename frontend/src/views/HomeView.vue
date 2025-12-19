<template>
  <div class="home">
    <!-- Header -->
    <header class="header">
      <div class="header-content">
        <h1>锁芯社区</h1>
        <div class="user-info">
          <div class="user-stats">
            <span class="level">等级 {{ authStore.user?.level || 1 }}</span>
            <span class="coins">🪙 {{ authStore.user?.coins || 0 }}</span>
          </div>
          <div class="header-actions">
            <!-- 通知铃铛 -->
            <div class="notification-circle">
              <NotificationBell />
            </div>

            <!-- 用户头像 -->
            <UserAvatar
              :user="authStore.user"
              size="normal"
              :clickable="true"
              :show-lock-indicator="true"
              :title="`${authStore.user?.username} 的个人资料`"
              @click="goToProfile"
            />

            <!-- 退出按钮 -->
            <button @click="handleLogout" class="logout-circle" title="退出登录">
              <span class="logout-icon">⏻</span>
            </button>
          </div>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="main-content">
      <div class="container">
        <!-- Sidebar -->
        <aside class="sidebar">
          <!-- Lock Status -->
          <div v-if="authStore.user?.active_lock_task" class="lock-status-card">
            <LockStatus
              :lockTask="authStore.user?.active_lock_task"
              :showActions="true"
              :showWhenFree="false"
              size="small"
            />
          </div>

          <div class="user-card">
            <h3>用户信息</h3>
            <div class="info-item">
              <span class="label">用户名</span>
              <span class="value">{{ authStore.user?.username }}</span>
            </div>
            <div class="info-item">
              <span class="label">活跃度</span>
              <span class="value">{{ authStore.user?.activity_score || 0 }}</span>
            </div>
            <div class="info-item">
              <span class="label">发布动态</span>
              <span class="value">{{ authStore.user?.total_posts || 0 }}</span>
            </div>
            <div class="info-item">
              <span class="label">获得点赞</span>
              <span class="value">{{ authStore.user?.total_likes_received || 0 }}</span>
            </div>
          </div>

          <div class="actions-card">
            <h3>快速操作</h3>
            <button @click="openCreateModal(false)" class="action-btn blue">📝 发布动态</button>
            <button @click="openCreateModal(true)" class="action-btn green">✅ 打卡任务</button>
            <button @click="goToTasks" class="action-btn orange">📋 任务管理</button>
            <button @click="goToGames" class="action-btn purple">🎮 小游戏</button>
          </div>

          <div class="actions-card">
            <h3>商店系统</h3>
            <button @click="goToStore" class="action-btn yellow">🛍️ 商店</button>
            <button @click="goToInventory" class="action-btn teal">🎒 背包</button>
            <button @click="goToExplore" class="action-btn brown">🗺️ 探索</button>
          </div>
        </aside>

        <!-- Mobile Quick Access Bar -->
        <div class="mobile-quick-access">
          <!-- Single Row Layout -->
          <div class="mobile-main-row">
            <!-- Lock Status (if exists) -->
            <div
              v-if="authStore.user?.active_lock_task"
              class="mobile-lock-status-inline"
              :class="{
                'ready': authStore.user.active_lock_task.is_expired && !authStore.user.active_lock_task.time_display_hidden,
                'time-hidden': authStore.user.active_lock_task.time_display_hidden
              }"
              @click="goToTaskDetail(authStore.user.active_lock_task.id)"
              :title="authStore.user.active_lock_task.is_expired ? '点击完成任务' : '点击查看任务详情'"
            >
              <div class="lock-inline-icon">🔒</div>
              <div class="lock-inline-info">
                <div class="lock-inline-title">{{ authStore.user.active_lock_task.title }}</div>
                <div class="lock-inline-time">
                  <span v-if="authStore.user.active_lock_task.time_display_hidden">
                    🔒 时间已隐藏
                  </span>
                  <span v-else>
                    {{ authStore.user.active_lock_task.is_expired ? '可完成' : formatTimeRemaining(authStore.user.active_lock_task.time_remaining_ms || 0) }}
                  </span>
                </div>
              </div>
              <div class="lock-inline-btn" :class="{ 'ready': authStore.user.active_lock_task.is_expired }">
                {{ authStore.user.active_lock_task.is_expired ? '✅' : '👁️' }}
              </div>
            </div>

            <!-- User Stats (only when no lock) -->
            <div v-if="!authStore.user?.active_lock_task" class="mobile-user-stats-inline">
              <div class="stat-inline">
                <span class="stat-emoji">⚡</span>
                <span class="stat-value">{{ authStore.user?.activity_score || 0 }}</span>
              </div>
              <div class="stat-inline">
                <span class="stat-emoji">🪙</span>
                <span class="stat-value">{{ authStore.user?.coins || 0 }}</span>
              </div>
            </div>

            <!-- Action Buttons -->
            <div class="mobile-actions-inline" :class="{ 'with-lock': authStore.user?.active_lock_task, 'without-lock': !authStore.user?.active_lock_task }">
              <button @click="openCreateModal(false)" class="mobile-btn primary" title="发布动态">📝</button>
              <button @click="openCreateModal(true)" class="mobile-btn success" title="打卡任务">✅</button>
              <button @click="goToTasks" class="mobile-btn info" title="任务管理">📋</button>

              <!-- Always show more button to prevent overflow -->
              <button @click="showMoreActions = !showMoreActions" class="mobile-btn secondary" title="更多">
                {{ showMoreActions ? '▲' : '▼' }}
              </button>
            </div>
          </div>

          <!-- Expandable More Actions (all secondary actions) -->
          <div v-if="showMoreActions" class="mobile-actions-more">
            <button @click="goToStore" class="mobile-action-btn-small" title="商店">🛍️ 商店</button>
            <button @click="goToGames" class="mobile-action-btn-small" title="小游戏">🎮 游戏</button>
            <button @click="goToInventory" class="mobile-action-btn-small" title="背包">🎒 背包</button>
            <button @click="goToExplore" class="mobile-action-btn-small" title="探索">🗺️ 探索</button>
          </div>
        </div>

        <!-- Posts Feed -->
        <section class="posts-feed">
          <!-- Header with title and broadcast -->
          <div class="posts-feed-header">
            <h2>社区动态</h2>
            <!-- Task Broadcast Component -->
            <TaskBroadcast />
          </div>

          <div v-if="isInitialLoading" class="loading">
            加载中...
          </div>

          <div v-else-if="error" class="error">
            {{ error }}
          </div>

          <div v-else-if="isEmpty" class="empty">
            还没有动态，快来发布第一条吧！
          </div>

          <div v-else class="posts-list">
            <article
              v-for="post in posts"
              :key="post.id"
              class="post-card"
              @click="goToPostDetail(post.id)"
            >
              <div class="post-header">
                <div class="user-info">
                  <UserAvatar
                    :user="post.user"
                    size="small"
                    :clickable="true"
                    :show-lock-indicator="true"
                    :title="`查看 ${post.user.username} 的资料`"
                    @click.stop="openProfileModal(post.user)"
                  />
                  <div>
                    <div
                      class="username clickable"
                      @click.stop="openProfileModal(post.user)"
                      :title="`查看 ${post.user.username} 的资料`"
                    >
                      {{ post.user.username }}
                    </div>
                    <div class="time">{{ formatDistanceToNow(post.created_at) }}</div>
                  </div>
                </div>
                <div v-if="post.post_type === 'checkin'" class="checkin-badge">
                  打卡
                </div>
              </div>

              <div class="post-content" v-html="post.content"></div>

              <div v-if="post.images && post.images.length > 0" class="post-images">
                <img
                  v-for="(image, index) in post.images"
                  :key="index"
                  :src="image.image"
                  :alt="`图片 ${index + 1}`"
                  class="post-image"
                />
              </div>

              <div class="post-actions">
                <button
                  @click.stop="toggleLike(post)"
                  :class="['like-btn', { liked: post.user_has_liked }]"
                >
                  {{ post.user_has_liked ? '❤️' : '🤍' }}
                  {{ post.likes_count }}
                </button>
                <span class="comment-count">💬 {{ post.comments_count || 0 }}</span>
                <span v-if="post.location" class="location">📍 位置信息</span>

                <!-- 删除按钮 (只对发帖人或超级管理员显示) -->
                <button
                  v-if="canDeletePost(post)"
                  @click.stop="deletePost(post)"
                  class="delete-btn"
                  title="删除动态"
                >
                  🗑️
                </button>
              </div>
            </article>

            <!-- 加载更多指示器 -->
            <div v-if="isLoadingMore" class="loading-more">
              正在加载更多...
            </div>

            <!-- 没有更多内容提示 -->
            <div v-else-if="!hasMore && posts.length > 0" class="no-more">
              没有更多动态了
            </div>
          </div>
        </section>
      </div>
    </main>

    <!-- 创建动态模态框 -->
    <CreatePostModal
      :is-visible="showCreateModal"
      :default-checkin-mode="isCheckinMode"
      @close="closeCreateModal"
      @success="handlePostCreated"
    />

    <!-- 用户资料模态框 -->
    <ProfileModal
      :is-visible="showProfileModal"
      :user="selectedUser"
      @close="closeProfileModal"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { usePostsStore } from '../stores/posts'
import { useNotificationStore } from '../stores/notifications'
import { useInfiniteScroll } from '../composables/useInfiniteScroll'
import { formatDistanceToNow } from '../lib/utils'
import CreatePostModal from '../components/CreatePostModal.vue'
import LockStatus from '../components/LockStatus.vue'
import ProfileModal from '../components/ProfileModal.vue'
import NotificationBell from '../components/NotificationBell.vue'
import TaskBroadcast from '../components/TaskBroadcast.vue'
import UserAvatar from '../components/UserAvatar.vue'
import type { Post } from '../types/index'

const router = useRouter()
const authStore = useAuthStore()
const postsStore = usePostsStore()
const notificationStore = useNotificationStore()

// 创建动态模态框状态
const showCreateModal = ref(false)
const isCheckinMode = ref(false)

// 用户资料模态框状态
const showProfileModal = ref(false)
const selectedUser = ref<any>(null)

// 移动端更多操作展开状态
const showMoreActions = ref(false)

// 无限滚动设置
const {
  items: posts,
  loading,
  error,
  hasMore,
  isEmpty,
  isLoadingMore,
  isInitialLoading,
  initialize,
  refresh
} = useInfiniteScroll(
  postsStore.getPaginatedPosts,
  {
    initialPageSize: 10,
    threshold: 200,
    loadDelay: 300
  }
)

const handleLogout = () => {
  authStore.logout()
  router.push('/login')
}

const openCreateModal = (checkinMode: boolean = false) => {
  isCheckinMode.value = checkinMode
  showCreateModal.value = true
}

const closeCreateModal = () => {
  showCreateModal.value = false
}

const handlePostCreated = () => {
  // 刷新动态列表
  refresh()
}

const toggleLike = async (post: Post) => {
  try {
    if (post.user_has_liked) {
      await postsStore.unlikePost(post.id)
      // 更新本地状态
      post.user_has_liked = false
      post.likes_count--
    } else {
      await postsStore.likePost(post.id)
      // 更新本地状态
      post.user_has_liked = true
      post.likes_count++
    }

    // 刷新通知以获取新的点赞通知
    try {
      await notificationStore.refreshNotifications()
    } catch (notifError) {
      console.error('Failed to refresh notifications after like:', notifError)
    }
  } catch (error) {
    console.error('Error toggling like:', error)
    // 如果出错，恢复原始状态
    if (post.user_has_liked) {
      post.user_has_liked = false
      post.likes_count--
    } else {
      post.user_has_liked = true
      post.likes_count++
    }
  }
}

const canDeletePost = (post: Post) => {
  // 当前用户是发帖人或者是超级管理员
  return authStore.user?.id === post.user.id || authStore.user?.is_superuser
}

const deletePost = async (post: Post) => {
  if (!confirm('确定要删除这条动态吗？')) {
    return
  }

  try {
    await postsStore.deletePost(post.id)
  } catch (error) {
    console.error('Error deleting post:', error)
    alert('删除失败，请重试')
  }
}

const goToPostDetail = (postId: string) => {
  router.push({ name: 'post-detail', params: { id: postId } })
}

const goToProfile = () => {
  router.push({ name: 'profile', params: { id: 'me' } })
}

const goToTasks = () => {
  router.push({ name: 'tasks' })
}

const goToGames = () => {
  router.push({ name: 'games' })
}

const goToStore = () => {
  router.push({ name: 'store' })
}

const goToInventory = () => {
  router.push({ name: 'inventory' })
}

const goToExplore = () => {
  router.push({ name: 'explore' })
}

const openProfileModal = (user: any) => {
  selectedUser.value = user
  showProfileModal.value = true
}

const closeProfileModal = () => {
  showProfileModal.value = false
  selectedUser.value = null
}

const goToTaskDetail = (taskId: string) => {
  router.push({ name: 'task-detail', params: { id: taskId } })
}

// 时间格式化函数（与LockStatus组件保持一致）
const formatTimeRemaining = (milliseconds: number) => {
  if (milliseconds <= 0) return '已结束'

  const hours = Math.floor(milliseconds / (1000 * 60 * 60))
  const minutes = Math.floor((milliseconds % (1000 * 60 * 60)) / (1000 * 60))

  if (hours > 0) {
    return `${hours}h${minutes}m`
  } else if (minutes > 0) {
    return `${minutes}m`
  } else {
    return '<1m'
  }
}

onMounted(() => {
  initialize()
})
</script>

<style scoped>
.home {
  min-height: 100vh;
  background-color: #f5f5f5;
}

.header {
  background: white;
  border-bottom: 2px solid #000;
  padding: 1rem 0;
  box-shadow: 0 2px 0 rgba(0, 0, 0, 0.1);
}

.header-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header h1 {
  font-size: 1.8rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0;
  color: #000;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.user-stats {
  display: flex;
  gap: 1rem;
  align-items: center;
  padding: 0.5rem 1rem;
  border: 1px solid #e0e0e0;
  border-radius: 20px;
  background: #f8f9fa;
}

.level {
  background-color: #007bff;
  color: white;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.coins {
  font-weight: 600;
  font-size: 0.9rem;
  color: #333;
}

/* 通知铃铛圆圈容器 */
.notification-circle {
  position: relative;
}


/* 退出按钮正圆 */
.logout-circle {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #dc3545;
  border: 2px solid #000;
  box-shadow: 2px 2px 0 rgba(0, 0, 0, 0.2);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  color: white;
}

.logout-circle:hover {
  transform: translateY(-1px);
  box-shadow: 3px 3px 0 rgba(0, 0, 0, 0.3);
  background: #c82333;
}

.logout-icon {
  font-size: 1rem;
  font-weight: 700;
}

.main-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem 1rem;
}

.container {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 2rem;
}

.sidebar {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  position: sticky;
  top: 2rem;
  height: fit-content;
  max-height: calc(100vh - 4rem);
  overflow-y: auto;
  padding-right: 8px;
  margin-right: -8px;
}

/* Custom scrollbar for Neo-Brutalism style */
.sidebar::-webkit-scrollbar {
  width: 8px;
}

.sidebar::-webkit-scrollbar-track {
  background: #f1f1f1;
  border: 2px solid #000;
  border-radius: 4px;
}

.sidebar::-webkit-scrollbar-thumb {
  background: linear-gradient(135deg, #667eea, #764ba2);
  border: 2px solid #000;
  border-radius: 4px;
}

.sidebar::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(135deg, #f093fb, #f5576c);
}

.lock-status-card,
.user-card,
.actions-card {
  background: white;
  padding: 1rem;
  border-radius: 8px;
  border: 3px solid #000;
  box-shadow: 4px 4px 0 #000;
  transition: all 0.3s cubic-bezier(0.4, 0.0, 0.2, 1);
  transform: translateZ(0);
  will-change: transform, box-shadow;
}

.lock-status-card:hover,
.user-card:hover,
.actions-card:hover {
  transform: translate(-2px, -2px);
  box-shadow: 6px 6px 0 #000;
}

.lock-status-card {
  padding: 0; /* LockStatus component handles its own padding */
  overflow: hidden;
}

.user-card h3,
.actions-card h3 {
  margin: 0 0 0.75rem 0;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: #000;
  text-shadow: 1px 1px 0 rgba(0, 0, 0, 0.1);
  position: relative;
  font-size: 0.9rem;
}

.user-card h3::after,
.actions-card h3::after {
  content: '';
  position: absolute;
  bottom: -4px;
  left: 0;
  width: 30px;
  height: 3px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  border-radius: 2px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.5rem;
  padding: 0.375rem 0;
  border-bottom: 1px solid #f0f0f0;
  transition: all 0.2s ease;
}

.info-item:hover {
  background-color: #f8f9fa;
  margin: 0 -0.5rem 0.5rem -0.5rem;
  padding: 0.375rem 0.5rem;
  border-radius: 4px;
  border-bottom: 1px solid #e9ecef;
}

.info-item:last-child {
  border-bottom: none;
  margin-bottom: 0;
}

.label {
  color: #666;
  font-size: 0.875rem;
  font-weight: 500;
}

.value {
  font-weight: 700;
  color: #333;
  padding: 0.25rem 0.5rem;
  background: linear-gradient(135deg, #f8f9fa, #e9ecef);
  border: 1px solid #dee2e6;
  border-radius: 4px;
  font-size: 0.875rem;
  min-width: 40px;
  text-align: center;
}

.action-btn {
  width: 100%;
  padding: 0.625rem;
  border: 3px solid #000;
  border-radius: 6px;
  font-weight: 900;
  color: white;
  margin-bottom: 0.5rem;
  cursor: pointer;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  box-shadow: 3px 3px 0 #000;
  transition: all 0.2s cubic-bezier(0.4, 0.0, 0.2, 1);
  font-size: 0.8rem;
  position: relative;
  overflow: hidden;
}

.action-btn.blue {
  background: linear-gradient(135deg, #007bff, #0056b3);
}

.action-btn.green {
  background: linear-gradient(135deg, #28a745, #218838);
}

.action-btn.orange {
  background: linear-gradient(135deg, #fd7e14, #e76500);
}

.action-btn.purple {
  background: linear-gradient(135deg, #6f42c1, #5a2d91);
}

.action-btn.yellow {
  background: linear-gradient(135deg, #ffc107, #e0a800);
  color: #212529;
}

.action-btn.teal {
  background: linear-gradient(135deg, #20c997, #17a2b8);
}

.action-btn.brown {
  background: linear-gradient(135deg, #8d6e63, #6d4c41);
}

.action-btn:hover {
  transform: translate(-2px, -2px);
  box-shadow: 5px 5px 0 #000, 0 5px 10px rgba(0, 0, 0, 0.2);
}

.action-btn:active {
  transform: translate(0, 0);
  box-shadow: 2px 2px 0 #000, 0 2px 4px rgba(0, 0, 0, 0.1);
}

.posts-feed-header {
  display: flex;
  align-items: center;
  margin-bottom: 1.5rem;
  gap: 1.5rem;
}

.posts-feed h2 {
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0;
  flex-shrink: 0;
}

.posts-feed-header .task-broadcast {
  flex: 1;
  max-width: calc(100% - 120px); /* 减去标题宽度和间距 */
}

.loading,
.error,
.empty,
.loading-more,
.no-more {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  border: 2px solid #000;
  box-shadow: 4px 4px 0 #000;
  text-align: center;
}

.loading-more {
  margin-top: 1.5rem;
  background-color: #f8f9fa;
  color: #666;
  padding: 1rem;
  font-size: 0.875rem;
}

.no-more {
  margin-top: 1.5rem;
  background-color: #e9ecef;
  color: #666;
  padding: 1rem;
  font-size: 0.875rem;
  font-style: italic;
}

.error {
  color: #dc3545;
  background-color: #f8d7da;
  border-color: #dc3545;
}

.posts-list {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.post-card {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  border: 2px solid #000;
  box-shadow: 4px 4px 0 #000;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  max-width: 100%;
  overflow: hidden;
}

.post-card:hover {
  transform: translateY(-2px);
  box-shadow: 6px 6px 0 #000;
}

.post-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.post-header .user-info {
  display: flex;
  gap: 0.75rem;
  align-items: center;
}


.username {
  font-weight: bold;
}

.username.clickable {
  cursor: pointer;
  color: #007bff;
  transition: all 0.2s ease;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  margin: -0.25rem -0.5rem;
}

.username.clickable:hover {
  background-color: #007bff;
  color: white;
  transform: translate(-1px, -1px);
  box-shadow: 2px 2px 0 #000;
}

.time {
  font-size: 0.875rem;
  color: #666;
}

.checkin-badge {
  background-color: #28a745;
  color: white;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: bold;
}

.post-content {
  margin-bottom: 1rem;
  white-space: pre-wrap;
  line-height: 1.5;
  word-wrap: break-word;
  word-break: break-word;
  overflow-wrap: break-word;
  max-width: 100%;
}

/* Rich text content styling */
.post-content h1,
.post-content h2,
.post-content h3 {
  margin: 0.5rem 0;
  font-weight: 900;
}

.post-content ul {
  margin: 0.5rem 0;
  padding-left: 2rem;
}

.post-content li {
  margin: 0.25rem 0;
}

.post-content strong {
  font-weight: 900;
}

.post-content em {
  font-style: italic;
}

.post-images {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.post-image {
  width: 100%;
  height: 120px;
  object-fit: cover;
  border: 2px solid #000;
  border-radius: 4px;
}

.post-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding-top: 1rem;
  border-top: 2px solid #e9ecef;
}

.like-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.5rem 0.75rem;
  border-radius: 4px;
  background-color: #f8f9fa;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 500;
}

.like-btn.liked {
  background-color: #dc3545;
  color: white;
}

.like-btn:hover {
  opacity: 0.8;
}

.delete-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.5rem 0.75rem;
  border-radius: 4px;
  background-color: #f8f9fa;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 500;
  margin-left: auto;
}

.delete-btn:hover {
  background-color: #dc3545;
  color: white;
}

.comment-count,
.location {
  color: #666;
  font-size: 0.875rem;
}

/* Mobile Quick Access Bar */
.mobile-quick-access {
  display: none;
  flex-direction: column;
  background: white;
  border: 3px solid #000;
  border-radius: 8px;
  box-shadow: 6px 6px 0 #000;
  margin-bottom: 1.5rem;
  padding: 0.5rem;
  gap: 0.5rem;
  position: sticky;
  top: 1rem;
  z-index: 10;
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  transition: all 0.3s cubic-bezier(0.4, 0.0, 0.2, 1);
}

/* Main Row Layout */
.mobile-main-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  min-height: 40px;
}

/* Inline Lock Status */
.mobile-lock-status-inline {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem 0.5rem;
  background: linear-gradient(135deg, #ff6b6b, #ee5a24);
  border-radius: 6px;
  border: 2px solid #000;
  color: white;
  font-size: 0.8rem;
  flex: 1;
  min-width: 0;
  max-width: 50%;
  cursor: pointer;
  transition: all 0.2s ease;
  user-select: none;
}

.mobile-lock-status-inline:hover {
  background: linear-gradient(135deg, #ff5252, #e64a19);
  transform: translate(-1px, -1px);
  box-shadow: 3px 3px 0 #000;
}

.mobile-lock-status-inline:active {
  transform: translate(0, 0);
  box-shadow: 1px 1px 0 #000;
}

.mobile-lock-status-inline.ready {
  background: linear-gradient(135deg, #28a745, #20c997);
  animation: pulse-ready 2s infinite;
}

.mobile-lock-status-inline.ready:hover {
  background: linear-gradient(135deg, #25a244, #1dc5a0);
}

/* 移动端时间隐藏状态样式 */
.mobile-lock-status-inline.time-hidden {
  background: linear-gradient(135deg, #343a40, #495057);
  animation: none; /* 移除脉冲动画 */
}

.mobile-lock-status-inline.time-hidden:hover {
  background: linear-gradient(135deg, #495057, #6c757d);
}

.lock-inline-icon {
  font-size: 1rem;
  flex-shrink: 0;
}

.lock-inline-info {
  flex: 1;
  min-width: 0;
  line-height: 1.1;
}

.lock-inline-title {
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 0.8rem;
}

.lock-inline-time {
  font-size: 0.7rem;
  opacity: 0.9;
  font-family: 'Courier New', monospace;
}

.lock-inline-btn {
  width: 28px;
  height: 28px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  color: white;
  font-size: 0.9rem;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  pointer-events: none;
}

.mobile-lock-status-inline:hover .lock-inline-btn {
  background: rgba(255, 255, 255, 0.3);
  border-color: rgba(255, 255, 255, 0.5);
  transform: scale(1.05);
}

.lock-inline-btn.ready {
  background: rgba(255, 255, 255, 0.9);
  color: #28a745;
  border-color: rgba(255, 255, 255, 0.9);
  font-weight: 600;
}

/* Inline User Stats */
.mobile-user-stats-inline {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  flex: 1;
  padding: 0 0.5rem;
}

.stat-inline {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  background: linear-gradient(135deg, #f8f9fa, #e9ecef);
  border: 1px solid #dee2e6;
  border-radius: 12px;
  font-size: 0.8rem;
}

.stat-emoji {
  font-size: 1rem;
}

.stat-value {
  font-weight: 600;
  color: #333;
  font-size: 0.8rem;
}

/* Inline Actions */
.mobile-actions-inline {
  display: flex;
  gap: 0.375rem;
  align-items: center;
}

.mobile-actions-inline.with-lock {
  flex: 1;
  justify-content: flex-end;
}

.mobile-actions-inline.without-lock {
  flex: 1;
  justify-content: flex-end;
}

/* Prevent button overflow by ensuring flex-shrink */
.mobile-actions-inline {
  flex-shrink: 0;
  min-width: 0;
  overflow: hidden;
}

.mobile-user-stats-inline {
  flex-shrink: 1;
  min-width: 0;
}

.mobile-btn {
  height: 36px;
  min-width: 36px;
  border: 2px solid #000;
  border-radius: 6px;
  color: white;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 2px 2px 0 #000;
  font-weight: 600;
  padding: 0 0.5rem;
  flex: 0 1 auto;
}

.mobile-btn.primary { background: linear-gradient(135deg, #007bff, #0056b3); }
.mobile-btn.success { background: linear-gradient(135deg, #28a745, #1e7e34); }
.mobile-btn.info { background: linear-gradient(135deg, #17a2b8, #138496); }
.mobile-btn.warning { background: linear-gradient(135deg, #ffc107, #e0a800); color: #212529; }
.mobile-btn.purple { background: linear-gradient(135deg, #6f42c1, #5a2d91); }
.mobile-btn.secondary {
  background: linear-gradient(135deg, #6c757d, #545b62);
  font-size: 0.8rem;
  min-width: 32px;
}

.mobile-btn:hover {
  transform: translate(-1px, -1px);
  box-shadow: 3px 3px 0 #000;
}

.mobile-btn:active {
  transform: translate(0, 0);
  box-shadow: 1px 1px 0 #000;
}

/* Expandable More Actions */
.mobile-actions-more {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.5rem;
  padding-top: 0.5rem;
  border-top: 2px solid #e9ecef;
}

/* Small action buttons in expandable area */

.mobile-action-btn-small {
  padding: 0.5rem 0.75rem;
  border: 2px solid #000;
  border-radius: 4px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.25rem;
  box-shadow: 2px 2px 0 #000;
  font-weight: 600;
  text-align: center;
}

.mobile-action-btn-small:hover {
  transform: translate(-1px, -1px);
  box-shadow: 3px 3px 0 #000;
  background: linear-gradient(135deg, #f093fb, #f5576c);
}

/* Mobile responsive */
@media (max-width: 768px) {
  .container {
    grid-template-columns: 1fr;
  }

  .sidebar {
    display: none;
  }

  .mobile-quick-access {
    display: flex;
    order: 1;
  }

  .posts-feed {
    order: 2;
  }

  .posts-feed-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.75rem;
    margin-bottom: 1rem;
  }

  .posts-feed-header .task-broadcast {
    max-width: 100%;
    width: 100%;
  }

  .header {
    padding: 0.75rem 0;
  }

  .header-content {
    flex-direction: column;
    gap: 0.75rem;
  }

  .header h1 {
    font-size: 1.5rem;
  }

  .user-info {
    width: 100%;
    justify-content: space-between;
  }

  .user-stats {
    padding: 0.4rem 0.8rem;
    gap: 0.75rem;
  }

  .level {
    padding: 0.2rem 0.6rem;
    font-size: 0.7rem;
  }

  .coins {
    font-size: 0.8rem;
  }

  .header-actions {
    gap: 0.6rem;
  }

  .logout-circle {
    width: 30px;
    height: 30px;
  }

  .logout-icon {
    font-size: 0.875rem;
  }

  .mobile-quick-access {
    margin-bottom: 1rem;
    padding: 0.375rem;
  }

  .mobile-main-row {
    gap: 0.375rem;
  }

  .mobile-lock-status-inline {
    padding: 0.25rem 0.375rem;
    font-size: 0.75rem;
    max-width: 55%;
  }

  .lock-inline-title {
    font-size: 0.75rem;
  }

  .lock-inline-time {
    font-size: 0.65rem;
  }

  .lock-inline-btn {
    width: 24px;
    height: 24px;
    font-size: 0.8rem;
  }

  .mobile-btn {
    height: 32px;
    min-width: 32px;
    font-size: 0.9rem;
    padding: 0 0.375rem;
  }

  .mobile-btn.secondary {
    min-width: 28px;
    font-size: 0.75rem;
  }

  .stat-inline {
    padding: 0.2rem 0.375rem;
    font-size: 0.75rem;
  }

  .stat-emoji {
    font-size: 0.9rem;
  }

  .stat-value {
    font-size: 0.75rem;
  }
}

/* Extra small screens - additional optimizations */
@media (max-width: 380px) {
  .mobile-lock-status-inline {
    max-width: 55%;
    padding: 0.25rem;
  }

  .mobile-user-stats-inline {
    max-width: 45%;
    gap: 0.5rem;
  }

  .mobile-actions-inline {
    gap: 0.25rem;
    flex: 1;
    justify-content: flex-end;
  }

  .mobile-actions-inline.with-lock,
  .mobile-actions-inline.without-lock {
    gap: 0.25rem;
    flex: 1;
  }

  .mobile-btn {
    min-width: 28px;
    height: 30px;
    font-size: 0.9rem;
    padding: 0 0.25rem;
  }

  .mobile-btn.secondary {
    min-width: 24px;
    font-size: 0.75rem;
  }

  .mobile-main-row {
    gap: 0.25rem;
  }
}

/* Extra small screens */
@media (max-width: 320px) {
  .mobile-user-stats-inline {
    display: none; /* Hide stats on very small screens to save space */
  }

  .mobile-lock-status-inline {
    max-width: 65%;
  }

  .mobile-btn {
    min-width: 26px;
    height: 28px;
    font-size: 0.8rem;
    padding: 0 0.2rem;
  }
}
</style>