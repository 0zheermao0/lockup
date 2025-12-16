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
                <UserAvatar
                  :user="userProfile"
                  size="xl"
                  :clickable="false"
                  :show-lock-indicator="false"
                />
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

          <!-- Telegram 联系方式 (对其他用户显示) -->
          <section v-if="!isOwnProfile && userProfile.telegram_username" class="telegram-contact-section">
            <h3>📱 Telegram 联系</h3>
            <div class="telegram-contact-content">
              <button
                @click="openTelegramChat(userProfile.telegram_username)"
                class="telegram-chat-btn"
              >
                💬 在 Telegram 中聊天
              </button>
            </div>
          </section>

          <!-- Telegram 绑定设置 (只对自己显示) -->
          <section v-if="isOwnProfile" class="telegram-section">
            <h3>🤖 Telegram Bot 绑定</h3>
            <div class="telegram-content">
              <!-- 绑定状态 -->
              <div v-if="telegramStatus" class="telegram-status">
                <div v-if="telegramStatus.is_bound" class="bound-status">
                  <div class="status-header">
                    <span class="status-badge bound">✅ 已绑定</span>
                    <span v-if="telegramStatus.telegram_username" class="telegram-username">@{{ telegramStatus.telegram_username }}</span>
                    <span v-else class="telegram-username-missing">用户名未设置</span>
                  </div>
                  <div class="status-details">
                    <p>绑定时间: {{ formatDate(telegramStatus.bound_at) }}</p>
                    <div class="notification-setting">
                      <label class="notification-toggle">
                        <input
                          type="checkbox"
                          :checked="telegramStatus.notifications_enabled"
                          @change="toggleTelegramNotifications"
                          :disabled="telegramActionLoading"
                        />
                        <span>接收 Telegram 通知</span>
                      </label>
                      <label class="notification-toggle">
                        <input
                          type="checkbox"
                          :checked="userProfile.show_telegram_account"
                          @change="toggleShowTelegramAccount"
                          :disabled="telegramActionLoading"
                        />
                        <span>展示 Telegram 账号</span>
                      </label>
                    </div>
                  </div>

                  <div class="telegram-actions">
                    <button
                      @click="unbindTelegram"
                      :disabled="telegramActionLoading"
                      class="unbind-btn"
                    >
                      {{ telegramActionLoading ? '处理中...' : '解除绑定' }}
                    </button>
                  </div>
                </div>

                <div v-else class="unbound-status">
                  <div class="status-header">
                    <span class="status-badge unbound">❌ 未绑定</span>
                  </div>
                  <div class="bind-instructions">
                    <p>绑定 Telegram Bot 后可以：</p>
                    <ul>
                      <li>🔔 接收应用通知到 Telegram</li>
                      <li>⏰ 给朋友分享的任务加时</li>
                      <li>🎮 参与朋友分享的游戏挑战</li>
                      <li>🤝 与其他绑定用户互动</li>
                    </ul>
                    <div class="bind-methods">
                      <p><strong>一键绑定：</strong></p>
                      <div class="bind-option">
                        <span>点击下面的按钮，系统会自动准备绑定并打开 Telegram Bot，然后在 Bot 中发送 /start 即可完成绑定</span>
                        <button
                          @click="openTelegramBot"
                          class="telegram-bind-btn"
                          :disabled="telegramActionLoading"
                        >
                          🚀 {{ telegramActionLoading ? '准备中...' : '打开 Telegram Bot' }}
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div v-if="telegramLoading" class="loading-status">
                <span>加载 Telegram 状态中...</span>
              </div>

              <div v-if="telegramError" class="error-status">
                <span>{{ telegramError }}</span>
                <button @click="fetchTelegramStatus" class="retry-btn">重试</button>
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
import { telegramApi, type TelegramStatus } from '../lib/api-telegram'
import { smartGoBack } from '../utils/navigation'
import LockStatus from '../components/LockStatus.vue'
import UserAvatar from '../components/UserAvatar.vue'
import type { User } from '../types/index'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const userProfile = ref<User | null>(null)
const loading = ref(true)
const error = ref('')
const editMode = ref(false)
const saving = ref(false)
const avatarInput = ref<HTMLInputElement>()

// Telegram 相关状态
const telegramStatus = ref<TelegramStatus | null>(null)
const telegramLoading = ref(false)
const telegramError = ref('')
const telegramActionLoading = ref(false)

const editForm = reactive({
  username: '',
  bio: '',
  location_precision: 1,
  show_telegram_account: false
})

const isOwnProfile = computed(() => {
  if (!userProfile.value || !authStore.user) return false
  return userProfile.value.id === authStore.user.id
})


const goBack = () => {
  smartGoBack(router, { defaultRoute: 'home' })
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
    editForm.show_telegram_account = userProfile.value.show_telegram_account || false
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
      location_precision: editForm.location_precision,
      show_telegram_account: editForm.show_telegram_account
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

// Telegram 相关方法
const fetchTelegramStatus = async () => {
  if (!isOwnProfile.value) return

  telegramLoading.value = true
  telegramError.value = ''

  try {
    telegramStatus.value = await telegramApi.getTelegramStatus()
  } catch (error: any) {
    console.error('Error fetching Telegram status:', error)
    telegramError.value = error.data?.error || '获取 Telegram 状态失败'
  } finally {
    telegramLoading.value = false
  }
}

const openTelegramBot = async () => {
  if (!authStore.user) return

  telegramActionLoading.value = true

  try {
    // 使用新的绑定流程：先调用 initiate-binding API
    const response = await telegramApi.initiateTelegramBinding()

    // 打开 Telegram Bot
    window.open(response.bot_url, '_blank')

    console.log(response.message)
    console.log(response.next_step)
  } catch (error: any) {
    console.error('Error initiating Telegram binding:', error)
    alert(error.data?.error || '启动绑定失败，请重试')
  } finally {
    telegramActionLoading.value = false
  }
}


const toggleTelegramNotifications = async () => {
  if (!telegramStatus.value?.is_bound) return

  telegramActionLoading.value = true

  try {
    const response = await telegramApi.toggleTelegramNotifications()
    if (telegramStatus.value) {
      telegramStatus.value.notifications_enabled = response.notifications_enabled
    }
    console.log(response.message)
  } catch (error: any) {
    console.error('Error toggling Telegram notifications:', error)
    alert(error.data?.error || '设置失败，请重试')
  } finally {
    telegramActionLoading.value = false
  }
}

const unbindTelegram = async () => {
  if (!telegramStatus.value?.is_bound) return

  if (!confirm('确定要解除 Telegram 绑定吗？解除后将无法接收 Telegram 通知。')) {
    return
  }

  telegramActionLoading.value = true

  try {
    await telegramApi.unbindTelegram()
    telegramStatus.value = {
      is_bound: false,
      notifications_enabled: true,
      can_receive_notifications: false
    }
    console.log('Telegram 绑定已解除')
  } catch (error: any) {
    console.error('Error unbinding Telegram:', error)
    alert(error.data?.error || '解绑失败，请重试')
  } finally {
    telegramActionLoading.value = false
  }
}

const toggleShowTelegramAccount = async () => {
  if (!userProfile.value) return

  telegramActionLoading.value = true

  try {
    const newValue = !userProfile.value.show_telegram_account
    const updatedProfile = await authApi.updateProfile({
      show_telegram_account: newValue
    })

    // 更新本地数据
    userProfile.value = { ...userProfile.value, ...updatedProfile }

    // 更新全局用户状态
    authStore.user = userProfile.value

    console.log(`Telegram 账号展示已${newValue ? '开启' : '关闭'}`)
  } catch (error: any) {
    console.error('Error toggling show telegram account:', error)
    alert(error.data?.error || '设置失败，请重试')
  } finally {
    telegramActionLoading.value = false
  }
}

const getTelegramDeepLink = (username: string) => {
  return `https://t.me/${username}`
}

const selectAndCopyLink = (event: Event) => {
  const input = event.target as HTMLInputElement
  input.select()
  input.setSelectionRange(0, 99999) // For mobile devices
}

const copyTelegramLink = async () => {
  if (!telegramStatus.value?.telegram_username) return

  const link = getTelegramDeepLink(telegramStatus.value.telegram_username)

  try {
    await navigator.clipboard.writeText(link)
    console.log('Telegram 链接已复制到剪贴板')
  } catch (error) {
    // Fallback for older browsers
    const textArea = document.createElement('textarea')
    textArea.value = link
    document.body.appendChild(textArea)
    textArea.select()
    document.execCommand('copy')
    document.body.removeChild(textArea)
    console.log('Telegram 链接已复制到剪贴板 (fallback)')
  }
}

const formatDate = (dateString?: string) => {
  if (!dateString) return ''
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const openTelegramChat = (username: string) => {
  // 直接跳转到 Telegram 聊天
  const telegramUrl = `https://t.me/${username}`
  window.open(telegramUrl, '_blank')
}


onMounted(async () => {
  await fetchUserProfile()

  // 如果是自己的资料页，加载 Telegram 状态
  if (isOwnProfile.value) {
    await fetchTelegramStatus()
  }
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

.lock-status-section, .stats-section, .settings-section, .telegram-section {
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

  .lock-status-section, .stats-section, .settings-section, .telegram-section {
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

/* Telegram 相关样式 */
.telegram-section h3 {
  margin: 0 0 1.5rem 0;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.telegram-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.telegram-status {
  width: 100%;
}

.status-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
}

.status-badge {
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-weight: 600;
  font-size: 0.875rem;
}

.status-badge.bound {
  background-color: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}

.status-badge.unbound {
  background-color: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

.telegram-username {
  font-weight: 600;
  color: #007bff;
  font-family: monospace;
}

.status-details {
  margin-bottom: 1rem;
  padding: 1rem;
  background-color: #f8f9fa;
  border-radius: 6px;
  border: 1px solid #e9ecef;
}

.status-details p {
  margin: 0 0 0.5rem 0;
  color: #666;
  font-size: 0.875rem;
}

.notification-setting {
  margin-top: 1rem;
}

.notification-toggle {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  font-weight: 500;
}

.notification-toggle input[type="checkbox"] {
  width: auto;
  margin: 0;
  transform: scale(1.2);
}

.notification-setting {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.telegram-actions {
  display: flex;
  gap: 1rem;
}

.unbind-btn {
  background-color: #dc3545;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 0.5rem 1rem;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 500;
}

.unbind-btn:hover:not(:disabled) {
  background-color: #c82333;
}

.unbind-btn:disabled {
  background-color: #6c757d;
  cursor: not-allowed;
}

.bind-instructions {
  margin-top: 1rem;
}

.bind-instructions p {
  margin: 0 0 1rem 0;
  font-weight: 500;
}

.bind-instructions ul {
  margin: 0 0 1.5rem 1.5rem;
  padding: 0;
}

.bind-instructions li {
  margin-bottom: 0.5rem;
  color: #666;
}

.bind-methods {
  background-color: #f8f9fa;
  padding: 1.5rem;
  border-radius: 6px;
  border: 1px solid #e9ecef;
}

.bind-option {
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid #e9ecef;
}

.bind-option:last-child {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
}

.bind-option span {
  display: block;
  margin-bottom: 0.75rem;
  font-weight: 500;
  color: #333;
}

.telegram-bind-btn {
  background: linear-gradient(135deg, #0088cc, #0066aa);
  color: white;
  border: none;
  border-radius: 6px;
  padding: 0.75rem 1.5rem;
  cursor: pointer;
  font-weight: 600;
  font-size: 0.9rem;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.telegram-bind-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #0066aa, #004488);
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(0, 136, 204, 0.3);
}

.telegram-bind-btn:disabled {
  background: #6c757d;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.link-copy {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.link-input {
  flex: 1;
  padding: 0.5rem;
  border: 2px solid #ddd;
  border-radius: 4px;
  font-size: 0.875rem;
  font-family: monospace;
  background-color: #f8f9fa;
  color: #666;
}

.link-input:focus {
  outline: none;
  border-color: #007bff;
}

.copy-btn {
  background-color: #28a745;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 0.5rem 1rem;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 500;
  white-space: nowrap;
  transition: background-color 0.2s;
}

.copy-btn:hover {
  background-color: #218838;
}

.telegram-deep-link {
  margin-top: 1rem;
  padding: 1rem;
  background-color: #e7f3ff;
  border: 1px solid #b3d9ff;
  border-radius: 6px;
}

.deep-link-section h4 {
  margin: 0 0 0.5rem 0;
  font-size: 1rem;
  font-weight: 600;
  color: #0066cc;
}

.deep-link-description {
  margin: 0 0 1rem 0;
  font-size: 0.875rem;
  color: #555;
  line-height: 1.4;
}

.loading-status, .error-status {
  padding: 1rem;
  border-radius: 6px;
  text-align: center;
}

.loading-status {
  background-color: #e3f2fd;
  color: #1565c0;
  border: 1px solid #bbdefb;
}

.error-status {
  background-color: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

.retry-btn {
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 0.5rem 1rem;
  cursor: pointer;
  font-size: 0.875rem;
  margin-left: 1rem;
}

.retry-btn:hover {
  background-color: #0056b3;
}

/* Mobile 响应式 - Telegram */
@media (max-width: 768px) {
  .telegram-section {
    padding: 1.5rem;
  }

  .status-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }

  .bind-methods {
    padding: 1rem;
  }

  .link-copy {
    flex-direction: column;
    gap: 0.75rem;
  }

  .link-input {
    width: 100%;
  }

  .telegram-actions {
    flex-direction: column;
    gap: 0.75rem;
  }

  .telegram-bind-btn {
    width: 100%;
    justify-content: center;
  }
}

/* Telegram 联系方式样式 */
.telegram-contact-section {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  border: 2px solid #000;
  box-shadow: 4px 4px 0 #000;
}

.telegram-contact-section h3 {
  margin: 0 0 1.5rem 0;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.telegram-contact-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.telegram-info {
  text-align: center;
}

.telegram-info .telegram-username {
  display: block;
  font-size: 1.2rem;
  font-weight: 600;
  color: #0088cc;
  font-family: monospace;
  margin-bottom: 0.5rem;
}

.telegram-description {
  color: #666;
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.4;
}

.telegram-chat-btn {
  background: linear-gradient(135deg, #0088cc, #0066aa);
  color: white;
  border: none;
  border-radius: 6px;
  padding: 1rem 2rem;
  cursor: pointer;
  font-weight: 600;
  font-size: 1rem;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  align-self: center;
  min-width: 200px;
}

.telegram-chat-btn:hover {
  background: linear-gradient(135deg, #0066aa, #004488);
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(0, 136, 204, 0.3);
}

/* Mobile 响应式 - Telegram 联系方式 */
@media (max-width: 768px) {
  .telegram-contact-section {
    padding: 1.5rem;
  }

  .telegram-chat-btn {
    width: 100%;
    min-width: auto;
  }
}
</style>