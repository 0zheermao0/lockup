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
                <div class="avatar-container">
                  <div class="avatar">
                    {{ post.user.username.charAt(0).toUpperCase() }}
                  </div>
                  <LockIndicator
                    :user="post.user"
                    size="small"
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
              <RichTextEditor
                v-model="newComment"
                placeholder="写评论..."
                :disabled="submittingComment"
                :max-length="500"
                min-height="100px"
                :show-char-count="true"
              />

              <!-- Image Upload Section -->
              <div class="comment-image-upload">
                <input
                  ref="commentFileInput"
                  type="file"
                  multiple
                  accept="image/*"
                  @change="handleCommentImageSelect"
                  class="file-input"
                  :disabled="submittingComment"
                />
                <div @click="triggerCommentFileInput" class="upload-zone">
                  <div v-if="selectedCommentImages.length === 0" class="upload-placeholder">
                    📷 添加图片 (可选)
                    <span class="upload-hint">点击选择图片</span>
                  </div>
                  <div v-else class="selected-images">
                    <div
                      v-for="(image, index) in selectedCommentImages"
                      :key="index"
                      class="image-preview"
                    >
                      <img :src="image.preview" :alt="`评论图片 ${index + 1}`" />
                      <button
                        type="button"
                        @click.stop="removeCommentImage(index)"
                        class="remove-image"
                        title="删除图片"
                      >
                        ×
                      </button>
                    </div>
                    <div @click="triggerCommentFileInput" class="add-more-photos">
                      <span>+</span>
                      <span class="add-text">添加更多</span>
                    </div>
                  </div>
                </div>
              </div>

              <div class="comment-form-actions">
                <button
                  type="submit"
                  :disabled="!newComment.trim() || submittingComment"
                  class="submit-comment-btn"
                >
                  {{ submittingComment ? '发布中...' : '发布评论' }}
                </button>
              </div>
            </form>

            <!-- Comments List -->
            <div ref="commentsContainer" class="comments-list comments-scroll-container" v-show="comments.length > 0">
              <div
                v-for="comment in comments"
                :key="comment.id"
                class="comment-item"
              >
                <div class="comment-header">
                  <div class="comment-user">
                    <div class="avatar-container">
                      <div class="avatar">
                        {{ comment.user.username.charAt(0).toUpperCase() }}
                      </div>
                      <LockIndicator
                        :user="comment.user"
                        size="mini"
                        :show-time="false"
                        class="avatar-lock-indicator"
                      />
                    </div>
                    <div>
                      <div
                        class="username clickable"
                        @click.stop="openProfileModal(comment.user)"
                        :title="`查看 ${comment.user.username} 的资料`"
                      >
                        {{ comment.user.username }}
                      </div>
                      <div class="time">{{ formatDistanceToNow(comment.created_at) }}</div>
                    </div>
                  </div>
                </div>
                <div class="comment-content" v-html="comment.content"></div>

                <!-- Comment Images -->
                <div v-if="comment.images && comment.images.length > 0" class="comment-images">
                  <img
                    v-for="(image, index) in comment.images"
                    :key="index"
                    :src="image.image"
                    :alt="`评论图片 ${index + 1}`"
                    class="comment-image"
                    @click="openImageModal(image.image)"
                  />
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

            <!-- Loading indicator and no comments message -->
            <div v-if="loadingComments && comments.length > 0" class="loading-more">
              正在加载更多评论...
            </div>

            <div v-else-if="!commentsLoaded && comments.length === 0" class="no-comments">
              还没有评论，快来抢沙发吧！
            </div>

            <div v-else-if="commentsLoaded && !pagination?.has_next && comments.length > 0" class="no-more">
              没有更多评论了
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

    <!-- Profile Modal -->
    <ProfileModal
      :is-visible="showProfileModal"
      :user="selectedUser"
      @close="closeProfileModal"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { usePostsStore } from '../stores/posts'
import { useNotificationStore } from '../stores/notifications'
import { postsApi } from '../lib/api'
import { formatDistanceToNow } from '../lib/utils'
import { smartGoBack } from '../utils/navigation'
import LockIndicator from '../components/LockIndicator.vue'
import ProfileModal from '../components/ProfileModal.vue'
import RichTextEditor from '../components/RichTextEditor.vue'
import type { Post, Comment } from '../types/index'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const postsStore = usePostsStore()
const notificationStore = useNotificationStore()

const post = ref<Post | null>(null)
const loading = ref(true)
const error = ref('')
const newComment = ref('')
const submittingComment = ref(false)
const showImageModal = ref(false)
const selectedImage = ref('')
const showProfileModal = ref(false)
const selectedUser = ref<any>(null)

// Comment image upload state
const commentFileInput = ref<HTMLInputElement>()
const selectedCommentImages = ref<Array<{ file: File; preview: string }>>([])

// Comments lazy loading state
const comments = ref<Comment[]>([])
const loadingComments = ref(false)
const commentsLoaded = ref(false)
const pagination = ref<{
  page: number
  page_size: number
  total_pages: number
  total_count: number
  has_next: boolean
  has_previous: boolean
} | null>(null)
const currentPage = ref(1)
const pageSize = 5

// Comments scroll container ref for auto-loading
const commentsContainer = ref<HTMLElement>()
let loadTimeout: ReturnType<typeof setTimeout> | null = null

const openProfileModal = (user: any) => {
  selectedUser.value = user
  showProfileModal.value = true
}

const closeProfileModal = () => {
  showProfileModal.value = false
  selectedUser.value = null
}

const canDeletePost = computed(() => {
  if (!post.value) return false
  return authStore.user?.id === post.value.user.id || authStore.user?.is_superuser
})

const goBack = () => {
  smartGoBack(router, { defaultRoute: 'home' })
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
    // After fetching post, load initial comments
    await loadComments(1, true)
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

const loadComments = async (page: number = 1, reset: boolean = false) => {
  if (!post.value) return

  loadingComments.value = true
  try {
    const response = await postsApi.getPostComments(post.value.id, {
      page,
      page_size: pageSize
    })

    if (reset) {
      comments.value = response.comments
    } else {
      comments.value.push(...response.comments)
    }

    pagination.value = response.pagination
    currentPage.value = page
    commentsLoaded.value = true
  } catch (err) {
    console.error('Error loading comments:', err)
  } finally {
    loadingComments.value = false
  }
}

const loadMoreComments = async () => {
  if (!pagination.value?.has_next || loadingComments.value) return
  await loadComments(currentPage.value + 1, false)
}

// Comments scroll event handler
const handleCommentsScroll = () => {
  if (!commentsContainer.value || loadingComments.value || !pagination.value?.has_next) {
    console.log('Scroll handler early return:', {
      hasContainer: !!commentsContainer.value,
      isLoading: loadingComments.value,
      hasNext: pagination.value?.has_next
    })
    return
  }

  const container = commentsContainer.value
  const scrollHeight = container.scrollHeight
  const scrollTop = container.scrollTop
  const clientHeight = container.clientHeight
  const distanceFromBottom = scrollHeight - scrollTop - clientHeight

  console.log('Scroll event:', {
    scrollHeight,
    scrollTop,
    clientHeight,
    distanceFromBottom,
    threshold: 200
  })

  // Check if user has scrolled near the bottom (200px threshold)
  if (distanceFromBottom < 200) {
    console.log('Near bottom, loading more comments...')
    // Clear any existing timeout to prevent rapid firing
    if (loadTimeout) {
      clearTimeout(loadTimeout)
    }

    // Debounce the load more action
    loadTimeout = setTimeout(() => {
      loadMoreComments()
    }, 100)
  }
}

// Setup scroll listener for comments
const setupScrollListener = async () => {
  await nextTick()
  if (commentsContainer.value) {
    // Remove any existing listener to prevent duplicates
    commentsContainer.value.removeEventListener('scroll', handleCommentsScroll)
    // Add the scroll listener
    commentsContainer.value.addEventListener('scroll', handleCommentsScroll, { passive: true })
    console.log('Scroll listener attached to comments container')
  } else {
    console.warn('Comments container not found when setting up scroll listener')
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

// Comment image handling
const triggerCommentFileInput = () => {
  if (!submittingComment.value) {
    commentFileInput.value?.click()
  }
}

const handleCommentImageSelect = (event: Event) => {
  const files = (event.target as HTMLInputElement).files
  if (!files) return

  for (let i = 0; i < files.length; i++) {
    const file = files[i]
    if (file && file.type.startsWith('image/')) {
      const reader = new FileReader()
      reader.onload = (e) => {
        selectedCommentImages.value.push({
          file: file,
          preview: e.target?.result as string
        })
      }
      reader.readAsDataURL(file)
    }
  }

  // Clear input value to allow selecting same file again
  if (commentFileInput.value) {
    commentFileInput.value.value = ''
  }
}

const removeCommentImage = (index: number) => {
  selectedCommentImages.value.splice(index, 1)
}

const submitComment = async () => {
  if (!post.value || !newComment.value.trim()) return

  submittingComment.value = true
  try {
    const commentData = {
      content: newComment.value.trim(),
      images: selectedCommentImages.value.map(img => img.file)
    }

    const newCommentData = await postsApi.createComment(post.value.id, commentData)

    // 添加新评论到本地状态（添加到开头，因为现在是倒序排序）
    comments.value.unshift(newCommentData)

    // 更新评论数量
    post.value.comments_count += 1

    // 更新分页信息
    if (pagination.value) {
      pagination.value.total_count += 1
    }

    // 清空输入框和选中的图片
    newComment.value = ''
    selectedCommentImages.value = []

    // 刷新通知以获取新评论的通知
    try {
      await notificationStore.refreshNotifications()
    } catch (notifError) {
      console.error('Failed to refresh notifications after comment:', notifError)
    }

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

    // 刷新通知以获取新的评论点赞通知
    try {
      await notificationStore.refreshNotifications()
    } catch (notifError) {
      console.error('Failed to refresh notifications after comment like:', notifError)
    }
  } catch (error) {
    console.error('Error toggling comment like:', error)
  }
}

const closeImageModal = () => {
  showImageModal.value = false
  selectedImage.value = ''
}

onMounted(async () => {
  await fetchPost()
  // Set up scroll listener after initial load
  setupScrollListener()
})

// Watch for comments being loaded and set up scroll listener
watch(commentsLoaded, (newVal) => {
  if (newVal && comments.value.length > 0) {
    setupScrollListener()
  }
})

onUnmounted(() => {
  // Clean up scroll listener and timeout
  if (commentsContainer.value) {
    commentsContainer.value.removeEventListener('scroll', handleCommentsScroll)
  }
  if (loadTimeout) {
    clearTimeout(loadTimeout)
  }
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

.avatar-container {
  position: relative;
  display: flex;
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

.avatar-lock-indicator {
  position: absolute;
  top: -2px;
  right: -8px;
  z-index: 2;
}

.username {
  font-weight: bold;
  font-size: 1.1rem;
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

/* Comments scroll container for auto-loading */
.comments-scroll-container {
  max-height: 600px;
  overflow-y: auto;
  padding-right: 0.5rem;
  margin-right: -0.5rem;
}

.comments-scroll-container::-webkit-scrollbar {
  width: 8px;
}

.comments-scroll-container::-webkit-scrollbar-track {
  background: #f1f1f1;
  border: 2px solid #000;
  border-radius: 4px;
}

.comments-scroll-container::-webkit-scrollbar-thumb {
  background: linear-gradient(135deg, #667eea, #764ba2);
  border: 2px solid #000;
  border-radius: 4px;
}

.comments-scroll-container::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(135deg, #f093fb, #f5576c);
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

.comment-user .avatar-container {
  position: relative;
  display: flex;
  align-items: center;
}

.comment-user .avatar {
  width: 32px;
  height: 32px;
  font-size: 0.875rem;
}

.comment-user .avatar-lock-indicator {
  position: absolute;
  top: -2px;
  right: -6px;
  z-index: 2;
}

.comment-content {
  white-space: pre-wrap;
  line-height: 1.5;
  margin-bottom: 0.75rem;
}

/* Rich text comment styling */
.comment-content h1,
.comment-content h2,
.comment-content h3 {
  margin: 0.5rem 0;
  font-weight: 900;
}

.comment-content ul {
  margin: 0.5rem 0;
  padding-left: 2rem;
}

.comment-content li {
  margin: 0.25rem 0;
}

.comment-content strong {
  font-weight: 900;
}

.comment-content em {
  font-style: italic;
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

.loading-more {
  text-align: center;
  color: #666;
  font-style: italic;
  padding: 1rem;
  background-color: #f8f9fa;
  border-radius: 4px;
  margin-top: 1rem;
}

.no-more {
  text-align: center;
  color: #999;
  font-size: 0.875rem;
  padding: 1rem;
  margin-top: 1rem;
  border-top: 1px solid #e9ecef;
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

/* Comment Image Upload Styling */
.comment-image-upload {
  margin: 1rem 0;
}

.comment-image-upload .file-input {
  display: none;
}

.comment-image-upload .upload-zone {
  border: 3px dashed #000;
  background: white;
  padding: 1.5rem;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 4px 4px 0 #000;
  margin-bottom: 1rem;
}

.comment-image-upload .upload-zone:hover {
  background: #f8f9fa;
  transform: translate(-1px, -1px);
  box-shadow: 5px 5px 0 #000;
}

.comment-image-upload .upload-placeholder {
  color: #666;
  font-size: 1rem;
  font-weight: 700;
}

.comment-image-upload .upload-hint {
  display: block;
  font-size: 0.875rem;
  color: #999;
  margin-top: 0.5rem;
  font-weight: 400;
}

.comment-image-upload .selected-images {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: 0.75rem;
}

.comment-image-upload .image-preview {
  position: relative;
  aspect-ratio: 1;
  border: 3px solid #000;
  overflow: hidden;
  box-shadow: 3px 3px 0 #000;
}

.comment-image-upload .image-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.comment-image-upload .remove-image {
  position: absolute;
  top: 4px;
  right: 4px;
  background: #dc3545;
  color: white;
  border: 2px solid #000;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 900;
  box-shadow: 2px 2px 0 #000;
}

.comment-image-upload .remove-image:hover {
  background: #c82333;
  transform: translate(-1px, -1px);
  box-shadow: 3px 3px 0 #000;
}

.comment-image-upload .add-more-photos {
  aspect-ratio: 1;
  border: 3px dashed #000;
  background: #f8f9fa;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-weight: 900;
  color: #666;
  transition: all 0.2s ease;
}

.comment-image-upload .add-more-photos:hover {
  background: #e9ecef;
  color: #000;
}

.comment-image-upload .add-more-photos span:first-child {
  font-size: 1.5rem;
  line-height: 1;
}

.comment-image-upload .add-text {
  font-size: 0.75rem;
  margin-top: 0.25rem;
}

/* Comment Images Display */
.comment-images {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 0.75rem;
  margin: 0.75rem 0;
}

.comment-image {
  width: 100%;
  max-height: 200px;
  object-fit: cover;
  border: 2px solid #000;
  border-radius: 4px;
  cursor: pointer;
  transition: transform 0.2s ease;
  box-shadow: 3px 3px 0 #000;
}

.comment-image:hover {
  transform: translate(-1px, -1px);
  box-shadow: 4px 4px 0 #000;
}

/* Comment Form Actions */
.comment-form-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 2px solid #e9ecef;
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

  .comment-image-upload .selected-images {
    grid-template-columns: repeat(2, 1fr);
  }

  .comment-images {
    grid-template-columns: repeat(2, 1fr);
  }

  .comment-image-upload .upload-zone {
    padding: 1rem;
  }
}
</style>