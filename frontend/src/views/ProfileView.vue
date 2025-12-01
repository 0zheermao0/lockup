<template>
  <div class="profile">
    <!-- Header -->
    <header class="header">
      <div class="header-content">
        <button @click="goBack" class="back-btn">← 返回</button>
        <h1>用户资料</h1>
        <button
          v-if="isOwnProfile"
          @click="toggleEditMode"
          class="edit-btn"
        >
          {{ editMode ? '取消' : '编辑' }}
        </button>
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

        <!-- Profile Content -->
        <div v-else-if="userProfile" class="profile-content">
          <!-- Profile Header -->
          <section class="profile-header">
            <div class="avatar-section">
              <div class="avatar-container">
                <img
                  v-if="userProfile.avatar"
                  :src="userProfile.avatar"
                  :alt="userProfile.username"
                  class="avatar"
                />
                <div v-else class="avatar-placeholder">
                  {{ userProfile.username.charAt(0).toUpperCase() }}
                </div>
                <button
                  v-if="isOwnProfile && editMode"
                  @click="triggerAvatarUpload"
                  class="avatar-upload-btn"
                  title="更换头像"
                >
                  📷
                </button>
                <input
                  ref="avatarInput"
                  type="file"
                  accept="image/*"
                  @change="handleAvatarUpload"
                  style="display: none"
                />
              </div>
            </div>

            <div class="profile-info">
              <!-- Username -->
              <div class="info-row">
                <span class="label">用户名</span>
                <span v-if="!editMode" class="value">{{ userProfile.username }}</span>
                <input
                  v-else
                  v-model="editForm.username"
                  type="text"
                  class="edit-input"
                  placeholder="用户名"
                />
              </div>

              <!-- Bio -->
              <div class="info-row">
                <span class="label">个人简介</span>
                <span v-if="!editMode" class="value">{{ userProfile.bio || '这个人很懒，什么都没留下' }}</span>
                <textarea
                  v-else
                  v-model="editForm.bio"
                  class="edit-textarea"
                  placeholder="写点什么介绍一下自己..."
                  maxlength="200"
                ></textarea>
              </div>

              <!-- Level and Coins -->
              <div class="info-row">
                <span class="label">等级</span>
                <span class="value level-badge">LV {{ userProfile.level }}</span>
              </div>

              <div class="info-row">
                <span class="label">金币</span>
                <span class="value coins">🪙 {{ userProfile.coins }}</span>
              </div>
            </div>
          </section>

          <!-- Lock Status Section -->
          <section class="lock-status-section">
            <h3>锁定状态</h3>
            <LockStatus
              :lockTask="userProfile.active_lock_task"
              :showActions="isOwnProfile"
              :showWhenFree="true"
              size="normal"
            />
          </section>

          <!-- Stats Section -->
          <section class="stats-section">
            <h3>活动统计</h3>
            <div class="stats-grid">
              <div class="stat-item">
                <div class="stat-number">{{ userProfile.total_posts }}</div>
                <div class="stat-label">发布动态</div>
              </div>
              <div class="stat-item">
                <div class="stat-number">{{ userProfile.total_likes_received }}</div>
                <div class="stat-label">获得点赞</div>
              </div>
              <div class="stat-item">
                <div class="stat-number">{{ userProfile.activity_score }}</div>
                <div class="stat-label">活跃度</div>
              </div>
              <div class="stat-item">
                <div class="stat-number">{{ userProfile.total_tasks_completed || 0 }}</div>
                <div class="stat-label">完成任务</div>
              </div>
              <div class="stat-item">
                <div class="stat-number">{{ formatTotalLockDuration(userProfile.total_lock_duration || 0) }}</div>
                <div class="stat-label">总带锁时长</div>
              </div>
            </div>
          </section>

          <!-- Settings Section (只对自己显示) -->
          <section v-if="isOwnProfile" class="settings-section">
            <h3>隐私设置</h3>
            <div class="setting-item">
              <span class="setting-label">位置精度</span>
              <select
                v-if="editMode"
                v-model="editForm.location_precision"
                class="setting-select"
              >
                <option :value="1">精确到米</option>
                <option :value="2">精确到百米</option>
                <option :value="3">精确到公里</option>
                <option :value="4">仅显示城市</option>
              </select>
              <span v-else class="setting-value">
                {{ getLocationPrecisionText(userProfile.location_precision) }}
              </span>
            </div>
          </section>

          <!-- Save Button -->
          <div v-if="editMode && isOwnProfile" class="edit-actions">
            <button
              @click="saveProfile"
              :disabled="saving"
              class="save-btn"
            >
              {{ saving ? '保存中...' : '保存修改' }}
            </button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { authApi } from '../lib/api'
import LockStatus from '../components/LockStatus.vue'
import type { User } from '../types/index.js'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const userProfile = ref<User | null>(null)
const loading = ref(true)
const error = ref('')
const editMode = ref(false)
const saving = ref(false)
const avatarInput = ref<HTMLInputElement>()

const editForm = reactive({
  username: '',
  bio: '',
  location_precision: 1
})

const isOwnProfile = computed(() => {
  if (!userProfile.value || !authStore.user) return false
  return userProfile.value.id === authStore.user.id
})

const goBack = () => {
  router.back()
}

const fetchUserProfile = async () => {
  const userId = route.params.id as string

  try {
    // Always fetch fresh data from API for accurate profile information
    if (!userId || userId === 'me' || (authStore.user && userId === authStore.user.id.toString())) {
      // For own profile, fetch from profile API to get updated data
      const response = await authApi.getCurrentUser()
      userProfile.value = response
      // Update auth store with fresh data
      authStore.user = response
    } else {
      // For other users, fetch by user ID
      const response = await authApi.getUserById(parseInt(userId))
      userProfile.value = response
    }
    initEditForm()
  } catch (err: any) {
    if (err.status === 404) {
      error.value = '用户不存在'
    } else if (err.status === 401) {
      error.value = '用户未登录'
    } else {
      error.value = '加载失败'
    }
    console.error('Error fetching user profile:', err)
  } finally {
    loading.value = false
  }
}

const initEditForm = () => {
  if (userProfile.value) {
    editForm.username = userProfile.value.username
    editForm.bio = userProfile.value.bio || ''
    editForm.location_precision = userProfile.value.location_precision
  }
}

const toggleEditMode = () => {
  if (editMode.value) {
    // 取消编辑，恢复原始数据
    initEditForm()
  }
  editMode.value = !editMode.value
}

const triggerAvatarUpload = () => {
  avatarInput.value?.click()
}

const handleAvatarUpload = async (event: Event) => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]

  if (!file) return

  // 验证文件类型
  if (!file.type.startsWith('image/')) {
    alert('请选择图片文件')
    return
  }

  // 验证文件大小 (5MB)
  if (file.size > 5 * 1024 * 1024) {
    alert('图片大小不能超过5MB')
    return
  }

  try {
    const response = await authApi.uploadAvatar(file)

    // 更新用户头像
    if (userProfile.value) {
      userProfile.value.avatar = response.avatar_url
    }

    // 更新全局用户状态
    if (authStore.user) {
      authStore.user.avatar = response.avatar_url
    }

    console.log('头像上传成功')
  } catch (error: any) {
    console.error('Error uploading avatar:', error)
    alert(error.data?.error || '头像上传失败，请重试')
  }
}

const saveProfile = async () => {
  if (!userProfile.value) return

  saving.value = true
  try {
    const updatedProfile = await authApi.updateProfile({
      username: editForm.username,
      bio: editForm.bio,
      location_precision: editForm.location_precision
    })

    // 更新本地数据
    userProfile.value = { ...userProfile.value, ...updatedProfile }

    // 更新全局用户状态
    authStore.user = userProfile.value

    editMode.value = false
    console.log('资料更新成功')
  } catch (error: any) {
    console.error('Error updating profile:', error)
    alert('保存失败，请重试')
  } finally {
    saving.value = false
  }
}

const getLocationPrecisionText = (precision: number) => {
  const texts = {
    1: '精确到米',
    2: '精确到百米',
    3: '精确到公里',
    4: '仅显示城市'
  }
  return texts[precision as keyof typeof texts] || '未知'
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

onMounted(() => {
  fetchUserProfile()
})
</script>

<style scoped>
.profile {
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
  justify-content: space-between;
}

.back-btn, .edit-btn {
  background: none;
  border: 1px solid #666;
  border-radius: 4px;
  padding: 0.5rem 1rem;
  cursor: pointer;
  font-size: 0.875rem;
}

.back-btn:hover, .edit-btn:hover {
  background-color: #f8f9fa;
}

.edit-btn {
  background-color: #007bff;
  color: white;
  border-color: #007bff;
}

.edit-btn:hover {
  background-color: #0056b3;
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

.loading, .error {
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

.profile-content {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.profile-header {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  border: 2px solid #000;
  box-shadow: 4px 4px 0 #000;
  display: flex;
  gap: 2rem;
  align-items: flex-start;
}

.avatar-section {
  flex-shrink: 0;
}

.avatar-container {
  position: relative;
  width: 120px;
  height: 120px;
}

.avatar, .avatar-placeholder {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  border: 3px solid #000;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2rem;
  font-weight: bold;
  object-fit: cover;
}

.avatar-placeholder {
  background-color: #007bff;
  color: white;
}

.avatar-upload-btn {
  position: absolute;
  bottom: 0;
  right: 0;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #007bff;
  color: white;
  border: 2px solid white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
}

.avatar-upload-btn:hover {
  background: #0056b3;
}

.profile-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.info-row {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.label {
  min-width: 80px;
  font-weight: bold;
  color: #666;
}

.value {
  flex: 1;
}

.edit-input, .edit-textarea {
  flex: 1;
  padding: 0.5rem;
  border: 2px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
}

.edit-input:focus, .edit-textarea:focus {
  outline: none;
  border-color: #007bff;
}

.edit-textarea {
  resize: vertical;
  min-height: 80px;
}

.level-badge {
  background-color: #28a745;
  color: white;
  padding: 0.25rem 0.75rem;
  border-radius: 20px;
  font-size: 0.875rem;
  font-weight: bold;
}

.coins {
  font-weight: bold;
  color: #f39c12;
}

.lock-status-section, .stats-section, .settings-section {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  border: 2px solid #000;
  box-shadow: 4px 4px 0 #000;
}

.lock-status-section h3, .stats-section h3, .settings-section h3 {
  margin: 0 0 1.5rem 0;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1.5rem;
}

.stat-item {
  text-align: center;
  padding: 1rem;
  background-color: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e9ecef;
}

.stat-number {
  font-size: 2rem;
  font-weight: bold;
  color: #007bff;
  margin-bottom: 0.5rem;
}

.stat-label {
  font-size: 0.875rem;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 0;
  border-bottom: 1px solid #e9ecef;
}

.setting-item:last-child {
  border-bottom: none;
}

.setting-label {
  font-weight: 500;
}

.setting-select {
  padding: 0.5rem;
  border: 2px solid #ddd;
  border-radius: 4px;
  font-size: 0.875rem;
}

.setting-select:focus {
  outline: none;
  border-color: #007bff;
}

.setting-value {
  color: #666;
  font-size: 0.875rem;
}

.edit-actions {
  display: flex;
  justify-content: center;
  margin-top: 1rem;
}

.save-btn {
  background-color: #28a745;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 1rem 2rem;
  cursor: pointer;
  font-weight: 600;
  font-size: 1rem;
}

.save-btn:hover:not(:disabled) {
  background-color: #218838;
}

.save-btn:disabled {
  background-color: #6c757d;
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

  .lock-status-section, .stats-section, .settings-section {
    padding: 1.5rem;
  }

  .profile-header {
    flex-direction: column;
    align-items: center;
    text-align: center;
    padding: 1.5rem;
  }

  .info-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }

  .label {
    min-width: auto;
  }

  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  @media (max-width: 480px) {
    .stats-grid {
      grid-template-columns: 1fr;
    }
  }

  .setting-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }
}
</style>