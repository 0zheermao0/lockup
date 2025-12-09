<template>
  <teleport to="body">
    <div
      v-if="isVisible"
      class="profile-modal-overlay"
      @click="handleOverlayClick"
    >
      <div
        ref="modalContent"
        class="profile-modal-content"
        @click.stop
      >
        <!-- Modal Header -->
        <div class="modal-header">
          <h2 class="modal-title">用户资料</h2>
          <button
            @click="$emit('close')"
            class="close-btn"
            title="关闭"
          >
            ×
          </button>
        </div>

        <!-- Loading State -->
        <div v-if="loading" class="modal-body loading-state">
          <div class="loading-spinner"></div>
          <p>加载中...</p>
        </div>

        <!-- Error State -->
        <div v-else-if="error" class="modal-body error-state">
          <div class="error-icon">⚠️</div>
          <p class="error-message">{{ error }}</p>
          <button @click="retry" class="retry-btn">重试</button>
        </div>

        <!-- Profile Content -->
        <div v-else-if="userProfile" class="modal-body">
          <!-- User Basic Info -->
          <div class="profile-section">
            <div class="user-header">
              <div class="avatar-section">
                <div class="avatar-large">
                  {{ userProfile.username.charAt(0).toUpperCase() }}
                </div>
                <LockIndicator
                  :user="userProfile"
                  size="normal"
                  :show-time="true"
                  class="profile-lock-indicator"
                  @navigate="handleLockIndicatorNavigation"
                />
              </div>
              <div class="user-basic-info">
                <h3 class="username">{{ userProfile.username }}</h3>
                <div class="level-badge">
                  等级 {{ userProfile.level || 1 }}
                </div>
                <div v-if="userProfile.bio" class="bio">
                  {{ userProfile.bio }}
                </div>
              </div>
            </div>
          </div>

          <!-- User Stats -->
          <div class="profile-section">
            <h4 class="section-title">📊 用户统计</h4>
            <div class="stats-grid">
              <div class="stat-item">
                <span class="stat-label">积分</span>
                <span class="stat-value coins">🪙 {{ userProfile.coins || 0 }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">活跃度</span>
                <span class="stat-value">{{ userProfile.activity_score || 0 }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">发布动态</span>
                <span class="stat-value">{{ userProfile.total_posts || 0 }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">获得点赞</span>
                <span class="stat-value">{{ userProfile.total_likes_received || 0 }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">完成任务</span>
                <span class="stat-value">{{ userProfile.total_tasks_completed || 0 }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">最后活跃</span>
                <span class="stat-value">{{ formatLastActive(userProfile.last_active) }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">总带锁时长</span>
                <span class="stat-value">{{ formatTotalLockDuration(userProfile.total_lock_duration || 0) }}</span>
              </div>
            </div>
          </div>

          <!-- Current Lock Status -->
          <div v-if="userProfile.active_lock_task" class="profile-section">
            <h4 class="section-title">🔒 当前锁状态</h4>
            <LockStatus
              :lockTask="userProfile.active_lock_task"
              :showActions="false"
              :showWhenFree="true"
              size="normal"
              class="profile-lock-status"
              @navigate="handleLockStatusNavigation"
            />
          </div>

          <!-- Member Since -->
          <div class="profile-section">
            <h4 class="section-title">📅 成员信息</h4>
            <div class="member-info">
              <div class="info-item">
                <span class="info-label">加入时间</span>
                <span class="info-value">{{ formatDateTime(userProfile.created_at) }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">资料更新</span>
                <span class="info-value">{{ formatDateTime(userProfile.updated_at) }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Modal Footer -->
        <div class="modal-footer">
          <button
            @click="$emit('close')"
            class="footer-btn close-footer-btn"
          >
            关闭
          </button>
          <button
            v-if="userProfile && userProfile.id !== currentUserId"
            @click="viewFullProfile"
            class="footer-btn view-profile-btn"
          >
            查看完整资料
          </button>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup lang="ts">
import { ref, watch, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { authApi } from '../lib/api'
import LockIndicator from './LockIndicator.vue'
import LockStatus from './LockStatus.vue'
import { formatDistanceToNow } from '../lib/utils'
import type { User } from '../types'

interface Props {
  isVisible: boolean
  userId?: number
  user?: User // If user object is already available
}

const props = defineProps<Props>()

const emit = defineEmits<{
  close: []
}>()

const router = useRouter()
const authStore = useAuthStore()

// State
const userProfile = ref<User | null>(null)
const loading = ref(false)
const error = ref('')
const modalContent = ref<HTMLElement>()

// Computed
const currentUserId = computed(() => authStore.user?.id)

// Methods
const fetchUserProfile = async () => {
  if (!props.userId && !props.user) {
    error.value = '无效的用户信息'
    return
  }

  // Determine the user ID to fetch
  let userIdToFetch = props.userId

  // If user object is provided, use it directly if it has all the needed fields
  if (props.user) {
    // Check if the user object has the complete data we need
    const hasCompleteData = props.user.hasOwnProperty('coins') &&
                           props.user.hasOwnProperty('activity_score') &&
                           props.user.hasOwnProperty('last_active')

    if (hasCompleteData) {
      userProfile.value = props.user
      return
    } else if (props.user.id) {
      // If user object doesn't have complete data, use its ID to fetch complete data
      userIdToFetch = props.user.id
    }
  }

  if (!userIdToFetch) {
    error.value = '无法确定用户ID'
    return
  }

  try {
    loading.value = true
    error.value = ''

    if (userIdToFetch === currentUserId.value) {
      // For current user, use the full profile endpoint
      userProfile.value = await authApi.getCurrentUser()
    } else {
      // For other users, use the new getUserById endpoint
      userProfile.value = await authApi.getUserById(userIdToFetch)
    }
  } catch (err: any) {
    console.error('Error fetching user profile:', err)
    error.value = err.message || '获取用户资料失败'
  } finally {
    loading.value = false
  }
}

const retry = () => {
  fetchUserProfile()
}

const handleOverlayClick = () => {
  emit('close')
}

const viewFullProfile = () => {
  if (userProfile.value) {
    emit('close')
    router.push({ name: 'profile', params: { id: userProfile.value.id.toString() } })
  }
}

const handleLockIndicatorNavigation = (taskId: string) => {
  console.log(`ProfileModal: Received LockIndicator navigation request for task ${taskId}, closing modal`)
  emit('close')
}

const handleLockStatusNavigation = (taskId: string) => {
  console.log(`ProfileModal: Received LockStatus navigation request for task ${taskId}, closing modal`)
  emit('close')
}

const formatDateTime = (dateString: string): string => {
  return new Date(dateString).toLocaleDateString('zh-CN')
}

const formatLastActive = (dateString: string): string => {
  return formatDistanceToNow(dateString)
}

const formatTotalLockDuration = (minutes: number) => {
  if (minutes < 60) {
    return `${minutes}分钟`
  } else if (minutes < 1440) {
    const hours = Math.floor(minutes / 60)
    const remainingMinutes = minutes % 60
    return remainingMinutes > 0 ? `${hours}小时${remainingMinutes}分钟` : `${hours}小时`
  } else {
    const days = Math.floor(minutes / 1440)
    const remainingMinutes = minutes % 1440
    if (remainingMinutes < 60) {
      return remainingMinutes > 0 ? `${days}天${remainingMinutes}分钟` : `${days}天`
    } else {
      const hours = Math.floor(remainingMinutes / 60)
      const remainingMinutesAfterHours = remainingMinutes % 60
      if (remainingMinutesAfterHours > 0) {
        return `${days}天${hours}小时${remainingMinutesAfterHours}分钟`
      } else {
        return `${days}天${hours}小时`
      }
    }
  }
}

// Handle Escape key
const handleKeydown = (event: KeyboardEvent) => {
  if (event.key === 'Escape') {
    emit('close')
  }
}

// Watch for visibility changes
watch(() => props.isVisible, (visible) => {
  if (visible) {
    fetchUserProfile()
    document.addEventListener('keydown', handleKeydown)
    document.body.style.overflow = 'hidden'
  } else {
    document.removeEventListener('keydown', handleKeydown)
    document.body.style.overflow = ''
  }
})

// Watch for user changes
watch(() => props.user, () => {
  if (props.isVisible) {
    fetchUserProfile()
  }
}, { deep: true })

onMounted(() => {
  if (props.isVisible) {
    fetchUserProfile()
  }
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
  document.body.style.overflow = ''
})
</script>

<style scoped>
/* Neo-Brutalism Profile Modal */
.profile-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
  animation: fadeIn 0.2s ease-out;
}

.profile-modal-content {
  background: white;
  border: 4px solid #000;
  max-width: 600px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 12px 12px 0 #000;
  animation: slideIn 0.3s ease-out;
  transform: rotate(-1deg);
}

/* Modal Header */
.modal-header {
  background: #007bff;
  color: white;
  padding: 1.5rem 2rem;
  border-bottom: 4px solid #000;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transform: rotate(1deg);
  margin: -4px -4px 0 -4px;
}

.modal-title {
  font-size: 1.5rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0;
}

.close-btn {
  background: #dc3545;
  color: white;
  border: 3px solid #000;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  cursor: pointer;
  font-size: 1.5rem;
  font-weight: 900;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 3px 3px 0 #000;
  transition: all 0.2s ease;
}

.close-btn:hover {
  transform: translate(-1px, -1px);
  box-shadow: 4px 4px 0 #000;
}

/* Modal Body */
.modal-body {
  padding: 2rem;
  transform: rotate(1deg);
}

/* Loading and Error States */
.loading-state,
.error-state {
  text-align: center;
  padding: 3rem 2rem;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #007bff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 1rem;
}

.error-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.error-message {
  color: #dc3545;
  font-weight: 700;
  margin-bottom: 1.5rem;
}

.retry-btn {
  background: #ffc107;
  color: #000;
  border: 3px solid #000;
  padding: 0.75rem 1.5rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  cursor: pointer;
  box-shadow: 4px 4px 0 #000;
  transition: all 0.2s ease;
}

.retry-btn:hover {
  transform: translate(-1px, -1px);
  box-shadow: 5px 5px 0 #000;
}

/* Profile Sections */
.profile-section {
  background: #f8f9fa;
  border: 3px solid #000;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  box-shadow: 6px 6px 0 #000;
  transform: rotate(-0.5deg);
}

.profile-section:nth-child(even) {
  transform: rotate(0.5deg);
  background: #e7f3ff;
}

.section-title {
  font-size: 1.2rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 1rem 0;
  color: #000;
}

/* User Header */
.user-header {
  display: flex;
  gap: 1.5rem;
  align-items: center;
  margin-bottom: 1rem;
}

.avatar-section {
  position: relative;
  display: flex;
  align-items: center;
}

.avatar-large {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: linear-gradient(135deg, #007bff, #0056b3);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 900;
  font-size: 2rem;
  border: 4px solid #000;
  box-shadow: 4px 4px 0 #000;
}

.profile-lock-indicator {
  position: absolute;
  top: -5px;
  right: -10px;
  z-index: 2;
}

.user-basic-info {
  flex: 1;
}

.username {
  font-size: 1.5rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 0.5rem 0;
  color: #000;
}

.level-badge {
  background: #28a745;
  color: white;
  padding: 0.25rem 0.75rem;
  border: 2px solid #000;
  font-size: 0.875rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  display: inline-block;
  margin-bottom: 0.5rem;
  box-shadow: 2px 2px 0 #000;
}

.bio {
  color: #555;
  line-height: 1.5;
  font-style: italic;
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
}

.stat-item {
  background: white;
  border: 2px solid #000;
  padding: 1rem;
  text-align: center;
  box-shadow: 3px 3px 0 #000;
  transition: all 0.2s ease;
}

.stat-item:hover {
  transform: translate(-1px, -1px);
  box-shadow: 4px 4px 0 #000;
}

.stat-label {
  display: block;
  font-size: 0.75rem;
  color: #666;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 0.5rem;
}

.stat-value {
  display: block;
  font-size: 1.25rem;
  font-weight: 900;
  color: #000;
}

.stat-value.coins {
  color: #ffc107;
}

/* Member Info */
.member-info {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem;
  background: white;
  border: 2px solid #000;
  box-shadow: 2px 2px 0 #000;
}

.info-label {
  font-weight: 700;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  font-size: 0.875rem;
}

.info-value {
  font-weight: 900;
  color: #000;
}

/* Profile Lock Status */
.profile-lock-status {
  border: none !important;
  box-shadow: none !important;
  transform: none !important;
}

/* Modal Footer */
.modal-footer {
  background: #f8f9fa;
  border-top: 4px solid #000;
  padding: 1.5rem 2rem;
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  transform: rotate(-1deg);
  margin: 0 -4px -4px -4px;
}

.footer-btn {
  padding: 0.75rem 1.5rem;
  border: 3px solid #000;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  cursor: pointer;
  box-shadow: 4px 4px 0 #000;
  transition: all 0.2s ease;
}

.close-footer-btn {
  background: #6c757d;
  color: white;
}

.view-profile-btn {
  background: #007bff;
  color: white;
}

.footer-btn:hover {
  transform: translate(-1px, -1px);
  box-shadow: 5px 5px 0 #000;
}

/* Animations */
@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-50px) rotate(-1deg) scale(0.9);
  }
  to {
    opacity: 1;
    transform: translateY(0) rotate(-1deg) scale(1);
  }
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* Mobile Responsive */
@media (max-width: 768px) {
  .profile-modal-overlay {
    padding: 0.5rem;
  }

  .profile-modal-content {
    max-height: 95vh;
  }

  .modal-header,
  .modal-body,
  .modal-footer {
    padding: 1rem;
  }

  .user-header {
    flex-direction: column;
    text-align: center;
    gap: 1rem;
  }

  .avatar-large {
    width: 60px;
    height: 60px;
    font-size: 1.5rem;
  }

  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 0.75rem;
  }

  .stat-item {
    padding: 0.75rem;
  }

  .modal-footer {
    flex-direction: column;
  }

  .footer-btn {
    width: 100%;
  }
}
</style>