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
            <div @click="goToProfile" class="profile-avatar" :title="`${authStore.user?.username} 的个人资料`">
              <span class="avatar-text">{{ authStore.user?.username?.charAt(0).toUpperCase() || 'U' }}</span>
              <LockIndicator
                v-if="authStore.user?.active_lock_task"
                :user="authStore.user"
                size="mini"
                :show-time="false"
                class="avatar-lock-indicator"
              />
            </div>

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
          <div class="lock-status-card">
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
            <button @click="openCreateModal(false)" class="action-btn blue">发布动态</button>
            <button @click="openCreateModal(true)" class="action-btn green">打卡任务</button>
            <button @click="goToTasks" class="action-btn orange">任务管理</button>
            <button @click="goToGames" class="action-btn purple">小游戏</button>
          </div>

          <div class="actions-card">
            <h3>商店系统</h3>
            <button @click="goToStore" class="action-btn yellow">🛍️ 商店</button>
            <button @click="goToInventory" class="action-btn teal">🎒 背包</button>
            <button @click="goToExplore" class="action-btn brown">🗺️ 探索</button>
          </div>
        </aside>

        <!-- Posts Feed -->
        <section class="posts-feed">
          <h2>社区动态</h2>

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
                  <div class="avatar-container">
                    <div class="avatar">
                      {{ post.user.username.charAt(0).toUpperCase() }}
                    </div>
                    <LockIndicator
                      :user="post.user"
                      size="mini"
                      :show-time="false"
                      class="avatar-lock-indicator"
                    />
                  </div>
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
import LockIndicator from '../components/LockIndicator.vue'
import ProfileModal from '../components/ProfileModal.vue'
import NotificationBell from '../components/NotificationBell.vue'
import type { Post } from '../types/index.js'

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

/* 用户头像正圆 */
.profile-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea, #764ba2);
  border: 2px solid #000;
  box-shadow: 2px 2px 0 rgba(0, 0, 0, 0.2);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  transition: all 0.2s ease;
}

.profile-avatar:hover {
  transform: translateY(-1px);
  box-shadow: 3px 3px 0 rgba(0, 0, 0, 0.3);
  background: linear-gradient(135deg, #f093fb, #f5576c);
}

.avatar-text {
  color: white;
  font-weight: 700;
  font-size: 1rem;
  text-transform: uppercase;
}

.avatar-lock-indicator {
  position: absolute;
  top: -2px;
  right: -2px;
  z-index: 2;
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
  gap: 1.5rem;
}

.lock-status-card,
.user-card,
.actions-card {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  border: 2px solid #000;
  box-shadow: 4px 4px 0 #000;
}

.lock-status-card {
  padding: 0; /* LockStatus component handles its own padding */
  overflow: hidden;
}

.user-card h3,
.actions-card h3 {
  margin: 0 0 1rem 0;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.75rem;
}

.label {
  color: #666;
  font-size: 0.875rem;
}

.value {
  font-weight: bold;
}

.action-btn {
  width: 100%;
  padding: 0.75rem;
  border: none;
  border-radius: 4px;
  font-weight: bold;
  color: white;
  margin-bottom: 0.75rem;
  cursor: pointer;
}

.action-btn.blue {
  background-color: #007bff;
}

.action-btn.green {
  background-color: #28a745;
}

.action-btn.orange {
  background-color: #fd7e14;
}

.action-btn.purple {
  background-color: #6f42c1;
}

.action-btn.yellow {
  background-color: #ffc107;
  color: #212529;
}

.action-btn.teal {
  background-color: #20c997;
}

.action-btn.brown {
  background-color: #8d6e63;
}

.action-btn:hover {
  opacity: 0.9;
}

.posts-feed h2 {
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 1.5rem;
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

.avatar-container {
  position: relative;
  display: flex;
  align-items: center;
}

.avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background-color: #007bff;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 0.875rem;
}

.avatar-lock-indicator {
  position: absolute;
  top: -2px;
  right: -8px;
  z-index: 2;
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

/* Mobile responsive */
@media (max-width: 768px) {
  .container {
    grid-template-columns: 1fr;
  }

  .sidebar {
    order: 2;
  }

  .posts-feed {
    order: 1;
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

  .profile-avatar {
    width: 32px;
    height: 32px;
  }

  .avatar-text {
    font-size: 0.875rem;
  }

  .logout-circle {
    width: 30px;
    height: 30px;
  }

  .logout-icon {
    font-size: 0.875rem;
  }
}
</style>