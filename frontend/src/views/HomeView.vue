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
          <button @click="handleLogout" class="logout-btn">退出</button>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="main-content">
      <div class="container">
        <!-- Sidebar -->
        <aside class="sidebar">
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
            <button class="action-btn purple">小游戏</button>
          </div>
        </aside>

        <!-- Posts Feed -->
        <section class="posts-feed">
          <h2>社区动态</h2>

          <div v-if="postsStore.loading" class="loading">
            加载中...
          </div>

          <div v-else-if="postsStore.error" class="error">
            {{ postsStore.error }}
          </div>

          <div v-else-if="postsStore.posts.length === 0" class="empty">
            还没有动态，快来发布第一条吧！
          </div>

          <div v-else class="posts-list">
            <article
              v-for="post in postsStore.posts"
              :key="post.id"
              class="post-card"
              @click="goToPostDetail(post.id)"
            >
              <div class="post-header">
                <div class="user-info">
                  <div class="avatar">
                    {{ post.user.username.charAt(0).toUpperCase() }}
                  </div>
                  <div>
                    <div class="username">{{ post.user.username }}</div>
                    <div class="time">{{ formatDistanceToNow(post.created_at) }}</div>
                  </div>
                </div>
                <div v-if="post.post_type === 'checkin'" class="checkin-badge">
                  打卡
                </div>
              </div>

              <div class="post-content">
                {{ post.content }}
              </div>

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
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { usePostsStore } from '../stores/posts'
import { formatDistanceToNow } from '../lib/utils'
import CreatePostModal from '../components/CreatePostModal.vue'
import type { Post } from '../types/index.js'

const router = useRouter()
const authStore = useAuthStore()
const postsStore = usePostsStore()

// 创建动态模态框状态
const showCreateModal = ref(false)
const isCheckinMode = ref(false)

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
  postsStore.fetchPosts()
}

const toggleLike = async (post: Post) => {
  try {
    if (post.user_has_liked) {
      await postsStore.unlikePost(post.id)
    } else {
      await postsStore.likePost(post.id)
    }
  } catch (error) {
    console.error('Error toggling like:', error)
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

onMounted(() => {
  postsStore.fetchPosts()
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
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.user-stats {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.level {
  padding: 0.25rem 0.75rem;
  background-color: #007bff;
  color: white;
  border-radius: 20px;
  font-size: 0.875rem;
  font-weight: bold;
}

.coins {
  font-weight: bold;
}

.logout-btn {
  padding: 0.5rem 1rem;
  background: none;
  border: 1px solid #666;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.875rem;
}

.logout-btn:hover {
  background-color: #f8f9fa;
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

.user-card,
.actions-card {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  border: 2px solid #000;
  box-shadow: 4px 4px 0 #000;
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

.action-btn.purple {
  background-color: #6f42c1;
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
.empty {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  border: 2px solid #000;
  box-shadow: 4px 4px 0 #000;
  text-align: center;
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

.username {
  font-weight: bold;
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
}
</style>