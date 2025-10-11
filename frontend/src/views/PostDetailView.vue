<template>
  <div class="post-detail">
    <!-- Header -->
    <header class="header">
      <div class="header-content">
        <button @click="goBack" class="back-btn">← 返回</button>
        <h1>动态详情</h1>
      </div>
    </header>

    <!-- Main Content -->
    <main class="main-content">
      <div class="container">
        <!-- Loading -->
        <div v-if="loading" class="loading">
          加载中...
        </div>

        <!-- Error -->
        <div v-else-if="error" class="error">
          {{ error }}
        </div>

        <!-- Post Detail -->
        <div v-else-if="post" class="post-detail-content">
          <article class="post-card">
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
                @click="openImageModal(image.image)"
              />
            </div>

            <div v-if="post.location" class="location-info">
              📍 纬度: {{ post.latitude?.toFixed(6) }}，经度: {{ post.longitude?.toFixed(6) }}
            </div>

            <div class="post-actions">
              <button
                @click="toggleLike"
                :class="['like-btn', { liked: post.user_has_liked }]"
              >
                {{ post.user_has_liked ? '❤️' : '🤍' }}
                {{ post.likes_count }}
              </button>
              <span class="comment-count">💬 {{ post.comments_count || 0 }}</span>

              <!-- 删除按钮 (只对发帖人或超级管理员显示) -->
              <button
                v-if="canDeletePost"
                @click="deletePost"
                class="delete-btn"
                title="删除动态"
              >
                🗑️
              </button>
            </div>
          </article>

          <!-- Comments Section -->
          <section class="comments-section">
            <h3>评论 ({{ post.comments_count || 0 }})</h3>

            <!-- Comment Form -->
            <form @submit.prevent="submitComment" class="comment-form">
              <textarea
                v-model="newComment"
                placeholder="写评论..."
                rows="3"
                :disabled="submittingComment"
              ></textarea>
              <button
                type="submit"
                :disabled="!newComment.trim() || submittingComment"
                class="submit-comment-btn"
              >
                {{ submittingComment ? '发布中...' : '发布评论' }}
              </button>
            </form>

            <!-- Comments List -->
            <div v-if="post.comments && post.comments.length > 0" class="comments-list">
              <div
                v-for="comment in post.comments"
                :key="comment.id"
                class="comment-item"
              >
                <div class="comment-header">
                  <div class="comment-user">
                    <div class="avatar">
                      {{ comment.user.username.charAt(0).toUpperCase() }}
                    </div>
                    <div>
                      <div class="username">{{ comment.user.username }}</div>
                      <div class="time">{{ formatDistanceToNow(comment.created_at) }}</div>
                    </div>
                  </div>
                </div>
                <div class="comment-content">
                  {{ comment.content }}
                </div>
                <div class="comment-actions">
                  <button
                    @click="toggleCommentLike(comment)"
                    :class="['like-comment-btn', { liked: comment.is_liked }]"
                  >
                    {{ comment.is_liked ? '❤️' : '🤍' }}
                    {{ comment.likes_count || 0 }}
                  </button>
                </div>
              </div>
            </div>

            <div v-else class="no-comments">
              还没有评论，快来抢沙发吧！
            </div>
          </section>
        </div>
      </div>
    </main>

    <!-- Image Modal -->
    <div v-if="showImageModal" class="image-modal" @click="closeImageModal">
      <div class="image-modal-content" @click.stop>
        <img :src="selectedImage" alt="查看图片" />
        <button @click="closeImageModal" class="close-modal-btn">×</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { usePostsStore } from '../stores/posts'
import { postsApi } from '../lib/api'
import { formatDistanceToNow } from '../lib/utils'
import type { Post } from '../types/index.js'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const postsStore = usePostsStore()

const post = ref<Post | null>(null)
const loading = ref(true)
const error = ref('')
const newComment = ref('')
const submittingComment = ref(false)
const showImageModal = ref(false)
const selectedImage = ref('')

const canDeletePost = computed(() => {
  if (!post.value) return false
  return authStore.user?.id === post.value.user.id || authStore.user?.is_superuser
})

const goBack = () => {
  router.back()
}

const fetchPost = async () => {
  const postId = route.params.id as string
  if (!postId) {
    error.value = '无效的动态ID'
    loading.value = false
    return
  }

  try {
    const fetchedPost = await postsApi.getPost(postId)
    post.value = fetchedPost
  } catch (err: any) {
    if (err.status === 404) {
      error.value = '动态不存在'
    } else {
      error.value = '加载失败'
    }
    console.error('Error fetching post:', err)
  } finally {
    loading.value = false
  }
}

const toggleLike = async () => {
  if (!post.value) return

  try {
    if (post.value.user_has_liked) {
      await postsStore.unlikePost(post.value.id)
    } else {
      await postsStore.likePost(post.value.id)
    }
    // 更新本地状态
    post.value.user_has_liked = !post.value.user_has_liked
    post.value.likes_count += post.value.user_has_liked ? 1 : -1
  } catch (error) {
    console.error('Error toggling like:', error)
  }
}

const deletePost = async () => {
  if (!post.value || !confirm('确定要删除这条动态吗？')) {
    return
  }

  try {
    await postsStore.deletePost(post.value.id)
    router.push('/')
  } catch (error) {
    console.error('Error deleting post:', error)
    alert('删除失败，请重试')
  }
}

const submitComment = async () => {
  if (!post.value || !newComment.value.trim()) return

  submittingComment.value = true
  try {
    const newCommentData = await postsApi.createComment(post.value.id, {
      content: newComment.value.trim()
    })

    // 添加新评论到本地状态
    if (post.value.comments) {
      post.value.comments.push(newCommentData)
    } else {
      post.value.comments = [newCommentData]
    }

    // 更新评论数量
    post.value.comments_count += 1

    // 清空输入框
    newComment.value = ''

    console.log('评论发布成功')
  } catch (error: any) {
    console.error('Error submitting comment:', error)
    alert('评论发布失败，请重试')
  } finally {
    submittingComment.value = false
  }
}

const openImageModal = (imageUrl: string) => {
  selectedImage.value = imageUrl
  showImageModal.value = true
}

const toggleCommentLike = async (comment: any) => {
  try {
    if (comment.is_liked) {
      const response = await postsApi.unlikeComment(comment.id)
      comment.likes_count = response.likes_count
      comment.is_liked = false
    } else {
      const response = await postsApi.likeComment(comment.id)
      comment.likes_count = response.likes_count
      comment.is_liked = true
    }
  } catch (error) {
    console.error('Error toggling comment like:', error)
  }
}

const closeImageModal = () => {
  showImageModal.value = false
  selectedImage.value = ''
}

onMounted(() => {
  fetchPost()
})
</script>

<style scoped>
.post-detail {
  min-height: 100vh;
  background-color: #f5f5f5;
}

.header {
  background: white;
  border-bottom: 2px solid #000;
  padding: 1rem 0;
}

.header-content {
  max-width: 800px;
  margin: 0 auto;
  padding: 0 1rem;
  display: flex;
  align-items: center;
  gap: 1rem;
}

.back-btn {
  background: none;
  border: 1px solid #666;
  border-radius: 4px;
  padding: 0.5rem 1rem;
  cursor: pointer;
  font-size: 0.875rem;
}

.back-btn:hover {
  background-color: #f8f9fa;
}

.header h1 {
  font-size: 1.5rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0;
}

.main-content {
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem 1rem;
}

.loading,
.error {
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

.post-card {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  border: 2px solid #000;
  box-shadow: 4px 4px 0 #000;
  margin-bottom: 2rem;
}

.post-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.5rem;
}

.user-info {
  display: flex;
  gap: 0.75rem;
  align-items: center;
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background-color: #007bff;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
}

.username {
  font-weight: bold;
  font-size: 1.1rem;
}

.time {
  font-size: 0.875rem;
  color: #666;
  margin-top: 0.25rem;
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
  margin-bottom: 1.5rem;
  white-space: pre-wrap;
  line-height: 1.6;
  font-size: 1.1rem;
}

.post-images {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.post-image {
  width: 100%;
  max-height: 400px;
  object-fit: cover;
  border: 2px solid #000;
  border-radius: 8px;
  cursor: pointer;
  transition: transform 0.2s;
}

.post-image:hover {
  transform: scale(1.02);
}

.location-info {
  background-color: #f8f9fa;
  padding: 1rem;
  border-radius: 4px;
  border: 1px solid #e9ecef;
  margin-bottom: 1.5rem;
  font-family: monospace;
  font-size: 0.875rem;
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
  margin-left: auto;
}

.delete-btn:hover {
  background-color: #dc3545;
  color: white;
}

.comment-count {
  color: #666;
  font-size: 0.875rem;
}

.comments-section {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  border: 2px solid #000;
  box-shadow: 4px 4px 0 #000;
}

.comments-section h3 {
  margin: 0 0 1.5rem 0;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.comment-form {
  margin-bottom: 2rem;
}

.comment-form textarea {
  width: 100%;
  padding: 0.75rem;
  border: 2px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
  font-family: inherit;
  resize: vertical;
  box-sizing: border-box;
  margin-bottom: 1rem;
}

.comment-form textarea:focus {
  outline: none;
  border-color: #007bff;
}

.submit-comment-btn {
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 0.75rem 1.5rem;
  cursor: pointer;
  font-weight: 600;
}

.submit-comment-btn:hover:not(:disabled) {
  background-color: #0056b3;
}

.submit-comment-btn:disabled {
  background-color: #6c757d;
  cursor: not-allowed;
}

.comments-list {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.comment-item {
  padding: 1rem;
  border: 1px solid #e9ecef;
  border-radius: 4px;
  background-color: #f8f9fa;
}

.comment-header {
  margin-bottom: 0.75rem;
}

.comment-user {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.comment-user .avatar {
  width: 32px;
  height: 32px;
  font-size: 0.875rem;
}

.comment-content {
  white-space: pre-wrap;
  line-height: 1.5;
  margin-bottom: 0.75rem;
}

.comment-actions {
  display: flex;
  gap: 0.5rem;
}

.like-comment-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  background-color: #fff;
  font-size: 0.875rem;
}

.like-comment-btn:hover {
  background-color: #e9ecef;
}

.like-comment-btn.liked {
  background-color: #dc3545;
  color: white;
}

.no-comments {
  text-align: center;
  color: #666;
  font-style: italic;
  padding: 2rem;
}

.image-modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.image-modal-content {
  position: relative;
  max-width: 90%;
  max-height: 90%;
}

.image-modal-content img {
  width: 100%;
  height: auto;
  max-height: 90vh;
  object-fit: contain;
}

.close-modal-btn {
  position: absolute;
  top: 10px;
  right: 10px;
  background: rgba(0, 0, 0, 0.7);
  color: white;
  border: none;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  cursor: pointer;
  font-size: 1.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-modal-btn:hover {
  background: rgba(0, 0, 0, 0.9);
}

/* Mobile responsive */
@media (max-width: 768px) {
  .header-content {
    padding: 0 1rem;
  }

  .main-content {
    padding: 1rem;
  }

  .post-card,
  .comments-section {
    padding: 1rem;
  }

  .post-images {
    grid-template-columns: 1fr;
  }

  .image-modal-content {
    max-width: 95%;
    max-height: 95%;
  }
}
</style>