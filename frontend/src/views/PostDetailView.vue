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
                    :class="getLevelCSSClass(post.user.level || 1)"
                    :style="{ color: getLevelUsernameColor(post.user.level || 1) }"
                    @click.stop="openProfileModal(post.user)"
                    :title="`查看 ${post.user.username} 的资料 (${getLevelDisplayName(post.user.level || 1)})`"
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
                    <span class="upload-hint">点击选择图片 (最多3张，每张不超过2.5MB)</span>
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

            <!-- Comments List - Two Layer Structure -->
            <div ref="commentsContainer" class="comments-list comments-scroll-container" v-show="comments.length > 0">
              <div
                v-for="comment in comments"
                :key="comment.id"
                class="comment-floor"
              >
                <!-- First Layer Comment (Floor) -->
                <div class="comment-item first-layer">
                  <div class="comment-main">
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
                            :class="getLevelCSSClass(comment.user.level || 1)"
                            :style="{ color: getLevelUsernameColor(comment.user.level || 1) }"
                            @click.stop="openProfileModal(comment.user)"
                            :title="`查看 ${comment.user.username} 的资料 (${getLevelDisplayName(comment.user.level || 1)})`"
                          >
                            {{ comment.user.username }}
                          </div>
                          <div class="reply-indicator">回复 主贴</div>
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
                  </div>

                  <div class="comment-actions">
                    <button
                      @click="toggleCommentLike(comment)"
                      :class="['like-comment-btn', { liked: comment.is_liked }]"
                    >
                      {{ comment.is_liked ? '❤️' : '🤍' }}
                      {{ comment.likes_count || 0 }}
                    </button>
                    <button
                      @click="toggleReplyForm(comment.id)"
                      class="reply-comment-btn"
                    >
                      💬 回复
                    </button>
                    <button
                      v-if="(comment.replies_count || 0) > 0"
                      @click="toggleReplies(comment.id)"
                      class="view-replies-btn"
                      :class="{ active: expandedReplies[comment.id] }"
                    >
                      {{ expandedReplies[comment.id] ? '收起回复' : `查看 ${comment.replies_count || 0} 条回复` }}
                    </button>
                  </div>
                </div>

                <!-- Reply Form -->
                <div v-if="activeReplyForm?.parentId === comment.id && !activeReplyForm?.targetId" class="reply-form">
                  <form @submit.prevent="submitReply(comment.id)" class="reply-form-inner">
                    <RichTextEditor
                      v-model="newReply"
                      :placeholder="`回复 ${comment.user.username}...`"
                      :disabled="submittingReply"
                      :max-length="500"
                      min-height="80px"
                      :show-char-count="true"
                    />
                    <div class="reply-form-actions">
                      <button
                        type="button"
                        @click="cancelReply"
                        class="cancel-reply-btn"
                      >
                        取消
                      </button>
                      <button
                        type="submit"
                        :disabled="!newReply.trim() || submittingReply"
                        class="submit-reply-btn"
                      >
                        {{ submittingReply ? '发布中...' : '发布回复' }}
                      </button>
                    </div>
                  </form>
                </div>

                <!-- Second Layer Replies -->
                <div v-if="expandedReplies[comment.id]" class="replies-container">
                  <div v-if="loadingReplies[comment.id]" class="loading-replies">
                    正在加载回复...
                  </div>
                  <div v-else-if="(replies[comment.id]?.length || 0) > 0" class="replies-list">
                    <div
                      v-for="reply in (replies[comment.id] || [])"
                      :key="reply.id"
                      class="comment-item second-layer"
                    >
                      <div class="comment-main">
                        <div class="comment-header">
                          <div class="comment-user">
                            <div class="avatar-container">
                              <div class="avatar small">
                                {{ reply.user.username.charAt(0).toUpperCase() }}
                              </div>
                              <LockIndicator
                                :user="reply.user"
                                size="mini"
                                :show-time="false"
                                class="avatar-lock-indicator"
                              />
                            </div>
                            <div>
                              <div
                                class="username clickable"
                                @click.stop="openProfileModal(reply.user)"
                                :title="`查看 ${reply.user.username} 的资料`"
                              >
                                {{ reply.user.username }}
                              </div>
                              <div class="reply-indicator" v-if="reply.reply_to_user">
                                回复
                                <span
                                  class="reply-target clickable"
                                  @click.stop="openProfileModal(reply.reply_to_user)"
                                >
                                  @{{ reply.reply_to_user.username }}
                                </span>
                              </div>
                              <div class="time">{{ formatDistanceToNow(reply.created_at) }}</div>
                            </div>
                          </div>
                        </div>
                        <div class="comment-content" v-html="reply.content"></div>

                        <!-- Reply Images -->
                        <div v-if="reply.images && reply.images.length > 0" class="comment-images">
                          <img
                            v-for="(image, index) in reply.images"
                            :key="index"
                            :src="image.image"
                            :alt="`回复图片 ${index + 1}`"
                            class="comment-image"
                            @click="openImageModal(image.image)"
                          />
                        </div>
                      </div>

                      <div class="comment-actions">
                        <button
                          @click="toggleCommentLike(reply)"
                          :class="['like-comment-btn', { liked: reply.is_liked }]"
                        >
                          {{ reply.is_liked ? '❤️' : '🤍' }}
                          {{ reply.likes_count || 0 }}
                        </button>
                        <button
                          @click="startReplyToReply(comment.id, reply)"
                          class="reply-comment-btn small"
                        >
                          回复
                        </button>
                      </div>
                      <!-- Reply Form for specific reply -->
                      <div v-if="activeReplyForm?.parentId === comment.id && activeReplyForm?.targetId === reply.id" class="reply-form">
                        <form @submit.prevent="submitReply(comment.id)" class="reply-form-inner">
                          <RichTextEditor
                            v-model="newReply"
                            :placeholder="`回复 ${reply.user.username}...`"
                            :disabled="submittingReply"
                            :max-length="500"
                            min-height="80px"
                            :show-char-count="true"
                          />
                          <div class="reply-form-actions">
                            <button
                              type="button"
                              @click="cancelReply"
                              class="cancel-reply-btn"
                            >
                              取消
                            </button>
                            <button
                              type="submit"
                              :disabled="!newReply.trim() || submittingReply"
                              class="submit-reply-btn"
                            >
                              {{ submittingReply ? '发布中...' : '发布回复' }}
                            </button>
                          </div>
                        </form>
                      </div>
                    </div>

                    <!-- Load More Replies Button -->
                    <div
                      v-if="repliesPagination[comment.id]?.has_next"
                      class="load-more-replies-container"
                    >
                      <button
                        @click="loadMoreReplies(comment.id)"
                        :disabled="loadingReplies[comment.id]"
                        class="load-more-replies-btn"
                      >
                        {{ loadingReplies[comment.id] ? '加载中...' : '加载更多回复' }}
                      </button>
                    </div>
                  </div>
                  <div v-else class="no-replies">
                    暂无回复
                  </div>
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

            <!-- Load More Button -->
            <div v-else-if="commentsLoaded && pagination?.has_next" class="load-more-container">
              <button
                @click="loadMoreComments"
                :disabled="loadingComments"
                class="load-more-btn"
              >
                {{ loadingComments ? '加载中...' : '加载更多评论' }}
              </button>
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
import { getLevelCSSClass, getLevelDisplayName, getLevelUsernameColor } from '../lib/level-colors'
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

// Two-layer comment system state
const replies = ref<Record<string, Comment[]>>({}) // replies[commentId] = Reply[]
const expandedReplies = ref<Record<string, boolean>>({}) // which replies are expanded
const loadingReplies = ref<Record<string, boolean>>({}) // which replies are loading
const repliesPagination = ref<Record<string, any>>({}) // pagination info for each comment's replies
const activeReplyForm = ref<{ parentId: string; targetId?: string } | null>(null) // which comment has active reply form
const newReply = ref('')
const submittingReply = ref(false)
const replyTargetUser = ref<any>(null) // for second-layer replies

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

// Comments scroll event handler - now monitors window scroll
const handleCommentsScroll = () => {
  if (loadingComments.value || !pagination.value?.has_next) {
    return
  }

  // Get window scroll position
  const windowHeight = window.innerHeight
  const documentHeight = document.documentElement.scrollHeight
  const scrollTop = window.pageYOffset || document.documentElement.scrollTop
  const distanceFromBottom = documentHeight - scrollTop - windowHeight

  // Check if user has scrolled near the bottom (300px threshold)
  if (distanceFromBottom < 300) {
    // Clear any existing timeout to prevent rapid firing
    if (loadTimeout) {
      clearTimeout(loadTimeout)
    }

    // Debounce the load more action
    loadTimeout = setTimeout(() => {
      loadMoreComments()
    }, 200)
  }
}

// Setup scroll listener for comments
const setupScrollListener = async () => {
  await nextTick()
  // Remove any existing listener to prevent duplicates
  window.removeEventListener('scroll', handleCommentsScroll)
  // Add the scroll listener to window
  window.addEventListener('scroll', handleCommentsScroll, { passive: true })
  console.log('Scroll listener attached to window')
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

    // 验证文件是否存在
    if (!file) {
      continue
    }

    // 验证文件类型
    if (!file.type.startsWith('image/')) {
      alert(`文件 ${file.name} 不是图片格式，请选择图片文件`)
      continue
    }

    // 验证文件大小（2.5MB限制）
    if (file.size > 2.5 * 1024 * 1024) {
      alert(`图片 ${file.name} 超过了2.5MB大小限制，请压缩图片或选择较小的文件`)
      continue
    }

    // 检查是否已达到最大数量限制
    if (selectedCommentImages.value.length >= 3) {
      alert('最多只能上传3张图片')
      break
    }

    const reader = new FileReader()
    reader.onload = (e) => {
      selectedCommentImages.value.push({
        file: file,
        preview: e.target?.result as string
      })
    }
    reader.onerror = () => {
      alert(`读取图片 ${file.name} 失败，请重试`)
    }
    reader.readAsDataURL(file)
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

// Two-layer comment system functions
const toggleReplyForm = (commentId: string) => {
  if (activeReplyForm.value?.parentId === commentId && !activeReplyForm.value?.targetId) {
    activeReplyForm.value = null
    newReply.value = ''
    replyTargetUser.value = null
  } else {
    activeReplyForm.value = { parentId: commentId }
    newReply.value = ''
    replyTargetUser.value = null
  }
}

const cancelReply = () => {
  activeReplyForm.value = null
  newReply.value = ''
  replyTargetUser.value = null
}

const submitReply = async (parentCommentId: string) => {
  if (!newReply.value.trim() || submittingReply.value) return

  submittingReply.value = true
  try {
    // 确定实际被回复的评论ID
    let actualReplyToCommentId = null
    if (activeReplyForm.value?.targetId) {
      // 回复特定的二层评论
      actualReplyToCommentId = activeReplyForm.value.targetId
    } else {
      // 回复一层评论
      actualReplyToCommentId = parentCommentId
    }

    const replyData = {
      content: newReply.value.trim(),
      parent: actualReplyToCommentId, // 使用实际被回复的评论ID作为parent
      // 传递被回复的用户ID，如果有的话
      reply_to_user_id: replyTargetUser.value?.id || null
    }

    const newReplyData = await postsApi.createComment(post.value!.id, replyData)

    // Update local state - add to replies
    // 确定应该添加到哪个根评论的回复列表中
    const rootCommentId = newReplyData.root_reply_id || parentCommentId
    if (!replies.value[rootCommentId]) {
      replies.value[rootCommentId] = []
    }
    replies.value[rootCommentId].unshift(newReplyData)

    // Update root comment reply count
    const rootComment = comments.value.find(c => c.id === rootCommentId)
    if (rootComment) {
      rootComment.replies_count = (rootComment.replies_count || 0) + 1
    }

    // Update post comment count
    if (post.value) {
      post.value.comments_count += 1
    }

    // Clear form
    newReply.value = ''
    activeReplyForm.value = null
    replyTargetUser.value = null

    console.log('回复发布成功')
  } catch (error: any) {
    console.error('Error submitting reply:', error)
    alert('回复发布失败，请重试')
  } finally {
    submittingReply.value = false
  }
}

const startReplyToReply = (parentCommentId: string, targetReply: any) => {
  activeReplyForm.value = { parentId: parentCommentId, targetId: targetReply.id }
  replyTargetUser.value = targetReply.user
  newReply.value = ''
}

const toggleReplies = async (commentId: string) => {
  if (expandedReplies.value[commentId]) {
    // Collapse replies
    expandedReplies.value[commentId] = false
  } else {
    // Expand replies - load if not loaded yet
    if (!replies.value[commentId]) {
      await loadReplies(commentId)
    }
    expandedReplies.value[commentId] = true
  }
}

const loadReplies = async (commentId: string, page: number = 1, append: boolean = false) => {
  if (loadingReplies.value[commentId]) return

  loadingReplies.value[commentId] = true
  try {
    const response = await postsApi.getCommentReplies(commentId, {
      page,
      page_size: 5 // 每次加载5条回复
    })

    if (append && replies.value[commentId]) {
      // 追加更多回复
      replies.value[commentId].push(...response.replies)
    } else {
      // 初始加载或重置
      replies.value[commentId] = response.replies
    }

    // 保存分页信息
    repliesPagination.value[commentId] = response.pagination
  } catch (error) {
    console.error('Error loading replies:', error)
    alert('加载回复失败，请重试')
  } finally {
    loadingReplies.value[commentId] = false
  }
}

const loadMoreReplies = async (commentId: string) => {
  const pagination = repliesPagination.value[commentId]
  if (!pagination || !pagination.has_next) return

  await loadReplies(commentId, pagination.page + 1, true)
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
  window.removeEventListener('scroll', handleCommentsScroll)
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
  max-width: 100%;
  overflow: hidden;
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
  transition: all 0.2s ease;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  margin: -0.25rem -0.5rem;
  font-weight: 700;
  border: 2px solid transparent;
}

.username.clickable:hover {
  color: white;
  transform: translate(-1px, -1px);
  box-shadow: 2px 2px 0 #000;
  border-color: #000;
}

/* Level-specific hover effects */
.username.clickable.level-1:hover {
  background-color: #6c757d !important;
  color: white !important;
}

.username.clickable.level-2:hover {
  background-color: #17a2b8 !important;
  color: white !important;
}

.username.clickable.level-3:hover {
  background-color: #ffc107 !important;
  color: white !important;
}

.username.clickable.level-4:hover {
  background-color: #fd7e14 !important;
  color: white !important;
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
  max-width: 100%;
  overflow: hidden;
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
  gap: 0.75rem;
}

/* Comments scroll container for auto-loading */
.comments-scroll-container {
  /* Remove fixed height to allow natural expansion */
  overflow-y: visible;
  padding-right: 0.5rem;
  margin-right: -0.5rem;
  min-height: auto;
  height: auto;
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
  word-wrap: break-word;
  word-break: break-word;
  overflow-wrap: break-word;
  max-width: 100%;
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

/* Comment structure styling */
.comment-main {
  flex: 1;
  min-width: 0; /* Allows content to shrink properly */
  overflow: hidden; /* Prevent overflow */
  max-width: calc(100% - 120px); /* Reserve space for actions */
}

.comment-actions {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  flex-shrink: 0;
  align-items: flex-end;
}

.like-comment-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  background-color: #fff;
  font-size: 0.75rem;
  white-space: nowrap;
  min-width: fit-content;
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

/* Two-Layer Comment System Styles */
.comment-floor {
  margin-bottom: 0.75rem;
  border: 1px solid #e9ecef;
  border-radius: 6px;
  background: white;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  min-height: auto;
  height: auto;
  display: flex;
  flex-direction: column;
  max-width: 100%;
}

.comment-item.first-layer {
  background: white;
  padding: 0.75rem;
  border-bottom: 1px solid #e9ecef;
  min-height: auto;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
}

.comment-item.second-layer {
  background: #f8f9fa;
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid #e9ecef;
  position: relative;
  min-height: auto;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
}

.comment-item.second-layer:before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: #007bff;
}

.comment-item.second-layer:last-child {
  border-bottom: none;
}

.reply-indicator {
  font-size: 0.75rem;
  color: #666;
  font-weight: 600;
  margin-top: 0.25rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.reply-target {
  color: #007bff;
  font-weight: 700;
  text-decoration: none;
  transition: all 0.2s ease;
  padding: 0.125rem 0.25rem;
  border-radius: 3px;
}

.reply-target:hover {
  background: #007bff;
  color: white;
  transform: translate(-1px, -1px);
  box-shadow: 2px 2px 0 #000;
}

.avatar.small {
  width: 28px;
  height: 28px;
  font-size: 0.75rem;
}

.reply-comment-btn {
  background: #28a745;
  color: white;
  border: 1px solid #28a745;
  border-radius: 4px;
  padding: 0.25rem 0.5rem;
  cursor: pointer;
  font-size: 0.75rem;
  font-weight: 500;
  transition: all 0.2s ease;
  white-space: nowrap;
  min-width: fit-content;
}

.reply-comment-btn:hover {
  background: #218838;
  border-color: #218838;
}

.reply-comment-btn.small {
  padding: 0.125rem 0.375rem;
  font-size: 0.7rem;
}

.view-replies-btn {
  background: #6f42c1;
  color: white;
  border: 1px solid #6f42c1;
  border-radius: 4px;
  padding: 0.25rem 0.5rem;
  cursor: pointer;
  font-size: 0.75rem;
  font-weight: 500;
  transition: all 0.2s ease;
  white-space: nowrap;
  min-width: fit-content;
}

.view-replies-btn:hover {
  background: #5a32a3;
  border-color: #5a32a3;
}

.view-replies-btn.active {
  background: #dc3545;
  border-color: #dc3545;
}

.view-replies-btn.active:hover {
  background: #c82333;
  border-color: #c82333;
}

.reply-form {
  background: #f8f9fa;
  padding: 1rem;
  border-top: 1px solid #e9ecef;
}

.reply-form-inner {
  max-width: 100%;
}

.reply-form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 1rem;
}

.cancel-reply-btn {
  background: #6c757d;
  color: white;
  border: 1px solid #6c757d;
  border-radius: 4px;
  padding: 0.375rem 0.75rem;
  cursor: pointer;
  font-weight: 500;
  font-size: 0.875rem;
  transition: all 0.2s ease;
}

.cancel-reply-btn:hover {
  background: #5a6268;
  border-color: #5a6268;
}

.submit-reply-btn {
  background: #007bff;
  color: white;
  border: 1px solid #007bff;
  border-radius: 4px;
  padding: 0.375rem 0.75rem;
  cursor: pointer;
  font-weight: 500;
  font-size: 0.875rem;
  transition: all 0.2s ease;
}

.submit-reply-btn:hover:not(:disabled) {
  background: #0056b3;
  border-color: #0056b3;
}

.submit-reply-btn:disabled {
  background: #6c757d;
  border-color: #6c757d;
  cursor: not-allowed;
}

.replies-container {
  background: #f8f9fa;
  border-top: 1px solid #e9ecef;
  min-height: auto;
  height: auto;
  flex-grow: 1;
}

.replies-list {
  display: flex;
  flex-direction: column;
  min-height: auto;
  height: auto;
  gap: 0;
}

.loading-replies {
  text-align: center;
  color: #666;
  font-style: italic;
  padding: 1rem;
  background: #f8f9fa;
}

.no-replies {
  text-align: center;
  color: #999;
  font-style: italic;
  padding: 1rem;
  background: #f8f9fa;
}

/* Load More Button */
.load-more-container {
  text-align: center;
  padding: 2rem 0;
  margin-top: 1rem;
}

.load-more-btn {
  background: #007bff;
  color: white;
  border: 3px solid #000;
  border-radius: 8px;
  padding: 1rem 2rem;
  cursor: pointer;
  font-size: 1rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1px;
  transition: all 0.2s ease;
  box-shadow: 4px 4px 0 #000;
}

.load-more-btn:hover:not(:disabled) {
  background: #0056b3;
  transform: translate(-2px, -2px);
  box-shadow: 6px 6px 0 #000;
}

.load-more-btn:disabled {
  background: #6c757d;
  cursor: not-allowed;
  transform: none;
  box-shadow: 4px 4px 0 #000;
}

/* Load More Replies Button */
.load-more-replies-container {
  text-align: center;
  padding: 0.75rem;
  background: #f8f9fa;
  border-top: 1px solid #e9ecef;
}

.load-more-replies-btn {
  background: #6c757d;
  color: white;
  border: 1px solid #6c757d;
  border-radius: 4px;
  padding: 0.375rem 0.75rem;
  cursor: pointer;
  font-size: 0.75rem;
  font-weight: 500;
  transition: all 0.2s ease;
}

.load-more-replies-btn:hover:not(:disabled) {
  background: #5a6268;
  border-color: #5a6268;
}

.load-more-replies-btn:disabled {
  background: #adb5bd;
  border-color: #adb5bd;
  cursor: not-allowed;
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

  /* Mobile optimizations for two-layer comments */
  .comment-floor {
    margin-bottom: 1.5rem;
    box-shadow: 3px 3px 0 #000;
  }

  .comment-item.first-layer {
    padding: 1rem;
    gap: 0.75rem;
  }

  .comment-item.second-layer {
    padding: 0.75rem 1rem;
    gap: 0.5rem;
  }

  .load-more-btn {
    padding: 0.75rem 1.5rem;
    font-size: 0.875rem;
  }

  .reply-comment-btn,
  .view-replies-btn {
    padding: 0.25rem 0.5rem;
    font-size: 0.75rem;
  }

  .reply-form {
    padding: 1rem;
  }
}
</style>