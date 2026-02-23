<template>
  <div v-if="isVisible" class="modal-overlay" @click="closeModal">
    <div class="modal-content" @click.stop>
      <div class="modal-header">
        <div class="modal-header__title-group">
          <h2>📋 创建新任务</h2>
          <p class="modal-header__subtitle">选择任务类型并配置详细信息</p>
        </div>
        <button @click="closeModal" class="close-btn" :disabled="submitting">×</button>
      </div>

      <form @submit.prevent="handleSubmit" class="modal-body">
        <!-- Task Type Selection -->
        <TaskFormSection
          title="任务类型"
          subtitle="选择您要创建的任务类型"
          icon="🎯"
        >
          <div class="task-type-selector">
            <button
              type="button"
              @click="form.task_type = 'lock'"
              :class="['task-type-card', { active: form.task_type === 'lock' }]"
            >
              <span class="task-type-card__icon">🔒</span>
              <span class="task-type-card__title">带锁任务</span>
              <span class="task-type-card__desc">创建自律挑战，设定锁定时间</span>
            </button>
            <button
              type="button"
              @click="form.task_type = 'board'"
              :class="['task-type-card', { active: form.task_type === 'board' }]"
            >
              <span class="task-type-card__icon">📋</span>
              <span class="task-type-card__title">任务板</span>
              <span class="task-type-card__desc">发布悬赏任务，设置积分奖励</span>
            </button>
          </div>
        </TaskFormSection>

        <!-- Basic Information -->
        <TaskFormSection
          title="基础信息"
          subtitle="填写任务的基本信息"
          icon="📝"
        >
          <div class="form-fields">
            <div class="form-field">
              <label class="form-field__label" for="title">
                任务标题 <span class="required">*</span>
              </label>
              <input
                id="title"
                v-model="form.title"
                type="text"
                placeholder="输入任务标题..."
                maxlength="100"
                required
                class="form-field__input"
              />
            </div>

            <div class="form-field">
              <label class="form-field__label" for="description">
                任务描述 <span class="optional">(可选)</span>
              </label>
              <RichTextEditor
                v-model="form.description"
                :placeholder="form.task_type === 'lock' ? '描述一下你的自律挑战...' : '详细描述任务需求和要求...'"
                :max-length="500"
                min-height="100px"
              />
            </div>
          </div>
        </TaskFormSection>

        <!-- Lock Task Configuration -->
        <template v-if="form.task_type === 'lock'">
          <TaskFormSection
            title="任务配置"
            subtitle="配置带锁任务的详细参数"
            icon="⚙️"
          >
            <div class="form-fields">
              <!-- Duration Type -->
              <div class="form-row">
                <div class="form-field form-field--half">
                  <label class="form-field__label">持续类型</label>
                  <div class="radio-group">
                    <label class="radio-option">
                      <input
                        type="radio"
                        v-model="form.duration_type"
                        value="fixed"
                      />
                      <span class="radio-option__text">固定时间</span>
                    </label>
                    <label class="radio-option">
                      <input
                        type="radio"
                        v-model="form.duration_type"
                        value="random"
                      />
                      <span class="radio-option__text">随机时间</span>
                    </label>
                  </div>
                </div>

                <div class="form-field form-field--half">
                  <label class="form-field__label">解锁方式</label>
                  <div class="radio-group">
                    <label class="radio-option">
                      <input
                        type="radio"
                        v-model="form.unlock_type"
                        value="time"
                      />
                      <span class="radio-option__text">定时解锁</span>
                    </label>
                    <label class="radio-option">
                      <input
                        type="radio"
                        v-model="form.unlock_type"
                        value="vote"
                      />
                      <span class="radio-option__text">投票解锁</span>
                    </label>
                  </div>
                </div>
              </div>

              <!-- Difficulty -->
              <div class="form-field">
                <label class="form-field__label" for="difficulty">难度等级</label>
                <select id="difficulty" v-model="form.difficulty" required class="form-field__select">
                  <option value="easy">简单 - 适合初学者</option>
                  <option value="normal">普通 - 日常挑战</option>
                  <option value="hard">困难 - 需要坚强意志</option>
                  <option value="hell">地狱 - 极限挑战</option>
                </select>
              </div>

              <!-- Duration -->
              <div class="duration-section">
                <DurationSelector
                  v-model="form.duration_value!"
                  :label="form.duration_type === 'fixed' ? '持续时间' : '最短时间'"
                  :min-minutes="1"
                  :required="true"
                />

                <DurationSelector
                  v-if="form.duration_type === 'random'"
                  v-model="form.duration_max!"
                  label="最长时间"
                  :min-minutes="form.duration_value || 1"
                  :required="true"
                />
              </div>

              <!-- Vote Agreement Ratio -->
              <div v-if="form.unlock_type === 'vote'" class="form-field">
                <label class="form-field__label" for="vote_agreement_ratio">同意比例要求</label>
                <select id="vote_agreement_ratio" v-model="form.vote_agreement_ratio" required class="form-field__select">
                  <option value="0.5">50% - 简单多数</option>
                  <option value="0.6">60% - 普通多数</option>
                  <option value="0.7">70% - 绝对多数</option>
                  <option value="0.8">80% - 超级多数</option>
                  <option value="0.9">90% - 压倒性多数</option>
                </select>
                <small class="form-field__hint">
                  只要有人投票且同意比例达到要求即可解锁，无最低投票人数限制
                </small>
              </div>

              <!-- Strict Mode -->
              <div class="form-field form-field--toggle">
                <ToggleSwitch
                  v-model="form.strict_mode"
                  label="启用严格模式"
                  size="small"
                />
                <span class="form-field__hint-below">打卡时自动添加验证码</span>
              </div>

                <!-- Temporary Unlock Config -->
              <div class="temporary-unlock-section">
                <div class="temporary-unlock-header" @click="form.allow_temporary_unlock = !form.allow_temporary_unlock">
                  <div class="temporary-unlock-toggle">
                    <ToggleSwitch
                      v-model="form.allow_temporary_unlock"
                      label="启用临时开锁"
                      size="small"
                      @click.stop
                    />
                    <span class="temporary-unlock-hint">允许任务执行过程中临时解除锁定</span>
                  </div>
                </div>

                <transition name="slide-fade">
                  <div v-if="form.allow_temporary_unlock" class="temporary-unlock-config">
                    <div class="form-row">
                      <div class="form-field form-field--half">
                        <label class="form-field__label">限制类型</label>
                        <div class="radio-group">
                          <label class="radio-option">
                            <input
                              type="radio"
                              v-model="form.temporary_unlock_limit_type"
                              value="daily_count"
                            />
                            <span class="radio-option__text">每日次数</span>
                          </label>
                          <label class="radio-option">
                            <input
                              type="radio"
                              v-model="form.temporary_unlock_limit_type"
                              value="cooldown"
                            />
                            <span class="radio-option__text">冷却间隔</span>
                          </label>
                        </div>
                      </div>

                      <div class="form-field form-field--half">
                        <label class="form-field__label">
                          {{ form.temporary_unlock_limit_type === 'daily_count' ? '每日次数' : '冷却间隔（小时）' }}
                        </label>
                        <input
                          type="number"
                          v-model.number="form.temporary_unlock_limit_value"
                          :min="1"
                          :max="form.temporary_unlock_limit_type === 'daily_count' ? 10 : 168"
                          class="form-field__input"
                          required
                        />
                        <small class="form-field__hint">
                          {{ form.temporary_unlock_limit_type === 'daily_count' ? '每天最多开锁次数' : '两次开锁之间的最小间隔' }}
                        </small>
                      </div>
                    </div>

                    <div class="form-field">
                      <label class="form-field__label">单次最大时长</label>
                      <div class="slider-group">
                        <input
                          type="range"
                          v-model.number="form.temporary_unlock_max_duration"
                          min="5"
                          max="240"
                          step="5"
                          class="slider"
                        />
                        <span class="slider-value">{{ form.temporary_unlock_max_duration }} 分钟</span>
                      </div>
                      <small class="form-field__hint">超时将自动结束并惩罚（自动置顶30分钟）</small>
                    </div>

                    <div class="form-row form-row--toggles">
                      <div class="form-field form-field--toggle">
                        <ToggleSwitch
                          v-model="form.temporary_unlock_require_approval"
                          label="需要钥匙持有者同意"
                          size="small"
                        />
                      </div>
                      <div class="form-field form-field--toggle">
                        <ToggleSwitch
                          v-model="form.temporary_unlock_require_photo"
                          label="需要拍照证明"
                          size="small"
                        />
                      </div>
                    </div>
                  </div>
                </transition>
              </div>
            </div>
          </TaskFormSection>
        </template>

        <!-- Board Task Configuration -->
        <template v-if="form.task_type === 'board'">
          <TaskFormSection
            title="任务配置"
            subtitle="配置任务板的奖励和限制"
            icon="⚙️"
          >
            <div class="form-fields">
              <div class="form-row">
                <div class="form-field form-field--half">
                  <label class="form-field__label" for="reward">
                    奖励金额 <span class="required">*</span>
                  </label>
                  <div class="input-with-suffix">
                    <input
                      id="reward"
                      v-model.number="form.reward"
                      type="number"
                      min="1"
                      max="10000"
                      placeholder="输入奖励积分"
                      required
                      class="form-field__input"
                    />
                    <span class="input-suffix">积分</span>
                  </div>
                </div>

                <div class="form-field form-field--half">
                  <label class="form-field__label" for="max_duration">
                    最大完成时间 <span class="required">*</span>
                  </label>
                  <div class="input-with-suffix">
                    <input
                      id="max_duration"
                      v-model.number="form.max_duration"
                      type="number"
                      min="1"
                      placeholder="任务最长完成时间"
                      required
                      class="form-field__input"
                    />
                    <span class="input-suffix">小时</span>
                  </div>
                </div>
              </div>

              <div class="form-field">
                <label class="form-field__label" for="max_participants">
                  最大参与人数 <span class="optional">(默认1为单人任务)</span>
                </label>
                <input
                  id="max_participants"
                  v-model.number="form.max_participants"
                  type="number"
                  min="1"
                  max="50"
                  placeholder="多人任务的最大参与人数"
                  class="form-field__input"
                />
                <small class="form-field__hint">
                  设置为空或1为单人任务，设置为2或以上为多人任务。多人任务允许多人同时参与并提交作品。
                </small>
              </div>

              <div class="form-field">
                <label class="form-field__label" for="completion_rate_threshold">
                  任务完成率门槛 <span class="optional">(可选，默认0%无限制)</span>
                </label>
                <div class="input-with-suffix">
                  <input
                    id="completion_rate_threshold"
                    v-model.number="form.completion_rate_threshold"
                    type="number"
                    min="0"
                    max="100"
                    step="1"
                    placeholder="0"
                    class="form-field__input"
                  />
                  <span class="input-suffix">%</span>
                </div>
                <small class="form-field__hint">
                  设置参与者的最低任务完成率要求。完成率低于此门槛的用户无法接取任务。设置为0或留空表示无限制。
                </small>
              </div>
            </div>
          </TaskFormSection>

          <!-- Daily Task Configuration (Board Tasks Only) -->
          <DailyTaskConfig
            v-model="dailyTaskConfig"
            :reward="form.reward || 0"
            :user-coins="userCoins"
            @validation-change="onDailyTaskValidationChange"
          />
        </template>

        <!-- Publish Options -->
        <TaskFormSection
          title="发布选项"
          subtitle="配置任务的发布方式"
          icon="🚀"
        >
          <div class="publish-options">
            <div class="form-field form-field--toggle">
              <ToggleSwitch
                v-model="form.autoPost"
                label="自动发布动态"
                size="small"
              />
              <span class="form-field__hint-below">创建任务后自动分享到动态</span>
            </div>

            <!-- Image Upload (conditional) -->
            <div v-if="form.autoPost" class="image-upload-section">
              <label class="form-field__label">任务图片 <span class="optional">(可选)</span></label>
              <div class="image-upload-container">
                <input
                  id="image"
                  type="file"
                  accept="image/*"
                  @change="handleImageUpload"
                  class="image-input"
                  ref="imageInput"
                />
                <div
                  v-if="!imagePreview"
                  class="upload-placeholder"
                  @click="triggerImageUpload"
                >
                  <div class="upload-icon">📷</div>
                  <div class="upload-text">点击上传图片</div>
                  <div class="upload-hint">支持 JPG、PNG、SVG、GIF 格式</div>
                  <div class="upload-size-hint">最大 2.5MB</div>
                </div>
                <div v-else class="image-preview">
                  <img :src="imagePreview" alt="预览图片" />
                  <button
                    type="button"
                    @click="removeImage"
                    class="remove-image-btn"
                    title="移除图片"
                  >
                    ×
                  </button>
                </div>
              </div>
            </div>
          </div>
        </TaskFormSection>

        <!-- Submit Button -->
        <div class="modal-footer">
          <button type="button" @click="closeModal" class="cancel-btn" :disabled="submitting">
            取消
          </button>
          <button
            type="submit"
            :disabled="submitting || !isFormValid"
            class="submit-btn"
            :class="{ 'is-loading': submitting }"
          >
            <span v-if="submitting" class="spinner"></span>
            <span>{{ submitting ? '创建中...' : '创建任务' }}</span>
          </button>
        </div>
      </form>

      <div v-if="successMessage" class="success-message">
        <div class="success-icon">✅</div>
        <div class="success-text">{{ successMessage }}</div>
      </div>
    </div>

    <!-- NotificationToast for error handling - rendered as sibling to prevent event bubbling -->
    <Teleport to="body">
      <NotificationToast
        :is-visible="showToast"
        :type="toastData.type"
        :title="toastData.title"
        :message="toastData.message"
        :secondary-message="toastData.secondaryMessage"
        :details="toastData.details"
        @close="showToast = false"
      />
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch, onUnmounted, computed, Teleport } from 'vue'
import { tasksApi } from '../lib/api-tasks'
import type { TaskCreateRequest } from '../types/index'
import { useAuthStore } from '../stores/auth'
import DurationSelector from './DurationSelector.vue'
import RichTextEditor from './RichTextEditor.vue'
import NotificationToast from './NotificationToast.vue'
import TaskFormSection from './task/TaskFormSection.vue'
import DailyTaskConfig from './task/DailyTaskConfig.vue'
import ToggleSwitch from './ui/ToggleSwitch.vue'
import { handleApiError, formatErrorForNotification } from '../utils/errorHandling'

interface Props {
  isVisible: boolean
  initialTaskType?: 'lock' | 'board'
}

interface Emits {
  (e: 'close'): void
  (e: 'success', autoPublished: boolean): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const authStore = useAuthStore()

const submitting = ref(false)
const successMessage = ref('')
const imageInput = ref<HTMLInputElement>()
const imagePreview = ref<string>('')
const imageFile = ref<File | null>(null)
const isDailyTaskValid = ref(true)

// Daily task config
const dailyTaskConfig = ref({
  isEnabled: false,
  duration: 7,
  publishTime: '08:00'
})

// NotificationToast 状态
const showToast = ref(false)
const toastData = ref({
  type: 'error' as 'success' | 'error' | 'warning' | 'info',
  title: '',
  message: '',
  secondaryMessage: '',
  details: {} as Record<string, any>
})

const form = reactive<TaskCreateRequest>({
  task_type: 'lock',
  title: '',
  description: '',
  autoPost: true,
  // Lock task fields
  duration_type: 'fixed',
  duration_value: 60,
  duration_max: undefined,
  difficulty: 'normal',
  unlock_type: 'time',
  strict_mode: false,
  // 临时开锁配置
  allow_temporary_unlock: false,
  temporary_unlock_limit_type: 'daily_count',
  temporary_unlock_limit_value: 3,
  temporary_unlock_max_duration: 30,
  temporary_unlock_require_approval: false,
  temporary_unlock_require_photo: false,
  // Board task fields
  reward: undefined,
  max_duration: 24,
  max_participants: 1,
  completion_rate_threshold: 0,
  // Daily task fields
  is_daily_task: false,
  daily_task_duration: undefined,
  daily_task_publish_time: undefined,
  daily_task_total_cost: undefined
})

// Computed
const userCoins = computed(() => authStore.user?.coins || 0)

const isFormValid = computed(() => {
  if (!form.title.trim()) return false
  if (form.task_type === 'board') {
    if (!form.reward || form.reward < 1) return false
    if (!form.max_duration || form.max_duration < 1) return false
    // If daily task is enabled, check validation
    if (dailyTaskConfig.value.isEnabled && !isDailyTaskValid.value) return false
  }
  if (form.task_type === 'lock') {
    if (form.duration_type === 'random') {
      if (!form.duration_max || !form.duration_value || form.duration_max <= form.duration_value) {
        return false
      }
    }
    if (form.unlock_type === 'vote' && !form.vote_agreement_ratio) {
      return false
    }
  }
  return true
})

// Watch for modal visibility changes
watch(() => props.isVisible, (newValue) => {
  if (newValue) {
    resetForm()
    document.body.style.overflow = 'hidden'
  } else {
    document.body.style.overflow = ''
  }
})

// Watch for daily task config changes
watch(dailyTaskConfig, (newValue) => {
  form.is_daily_task = newValue.isEnabled
  form.daily_task_duration = newValue.isEnabled ? newValue.duration : undefined
  form.daily_task_publish_time = newValue.isEnabled ? newValue.publishTime : undefined
  form.daily_task_total_cost = newValue.isEnabled ? (form.reward || 0) * newValue.duration : undefined
}, { deep: true })

// Watch for reward changes to update daily task total cost
watch(() => form.reward, (newValue) => {
  if (dailyTaskConfig.value.isEnabled) {
    form.daily_task_total_cost = (newValue || 0) * dailyTaskConfig.value.duration
  }
})

const resetForm = () => {
  form.task_type = props.initialTaskType || 'lock'
  form.title = ''
  form.description = ''
  form.autoPost = true
  // Lock task fields
  form.duration_type = 'fixed'
  form.duration_value = 60
  form.difficulty = 'normal'
  form.unlock_type = 'time'
  form.duration_max = 120
  form.vote_agreement_ratio = undefined
  form.strict_mode = false
  // Board task fields
  form.reward = undefined
  form.max_duration = 24
  form.max_participants = 1
  form.completion_rate_threshold = 0
  // 临时开锁配置
  form.allow_temporary_unlock = false
  form.temporary_unlock_limit_type = 'daily_count'
  form.temporary_unlock_limit_value = 3
  form.temporary_unlock_max_duration = 30
  form.temporary_unlock_require_approval = false
  form.temporary_unlock_require_photo = false
  // Daily task fields
  form.is_daily_task = false
  form.daily_task_duration = undefined
  form.daily_task_publish_time = undefined
  form.daily_task_total_cost = undefined
  // Reset daily task config
  dailyTaskConfig.value = {
    isEnabled: false,
    duration: 7,
    publishTime: '08:00'
  }
  // Reset image
  imagePreview.value = ''
  imageFile.value = null
  if (imageInput.value) {
    imageInput.value.value = ''
  }
  successMessage.value = ''
  submitting.value = false
  showToast.value = false
}

const closeModal = () => {
  if (!submitting.value) {
    emit('close')
  }
}

const onDailyTaskValidationChange = (isValid: boolean) => {
  isDailyTaskValid.value = isValid
}

// Image handling methods
const triggerImageUpload = () => {
  imageInput.value?.click()
}

const handleImageUpload = (event: Event) => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]

  if (!file) return

  // Validate file type
  if (!file.type.match(/^image\/(jpeg|jpg|png|gif|webp|bmp|svg\+xml)$/)) {
    showToast.value = true
    const errorData = formatErrorForNotification({
      title: '文件格式不支持',
      message: '请选择 JPG、PNG、SVG、GIF、WebP 或 BMP 格式的图片',
      actionSuggestion: '请重新选择支持的图片格式',
      severity: 'error'
    })
    toastData.value = {
      ...errorData,
      details: {
        '当前文件类型': file.type,
        '文件名': file.name
      }
    }
    return
  }

  // Validate file size (2.5MB max)
  if (file.size > 2.5 * 1024 * 1024) {
    showToast.value = true
    const errorData = formatErrorForNotification({
      title: '文件过大',
      message: '上传的图片超过了2.5MB大小限制',
      actionSuggestion: '请压缩图片或选择较小的文件',
      severity: 'error'
    })
    toastData.value = {
      ...errorData,
      details: {}
    }
    return
  }

  imageFile.value = file

  // Create preview
  const reader = new FileReader()
  reader.onload = (e) => {
    imagePreview.value = e.target?.result as string
  }
  reader.onerror = () => {
    showToast.value = true
    const errorData = formatErrorForNotification({
      title: '图片读取失败',
      message: '无法读取选择的图片文件',
      actionSuggestion: '请检查文件是否损坏或重新选择其他图片',
      severity: 'error'
    })
    toastData.value = {
      ...errorData,
      details: {
        '文件名': file.name,
        '文件大小': `${(file.size / 1024 / 1024).toFixed(2)}MB`
      }
    }
  }
  reader.readAsDataURL(file)
}

const removeImage = () => {
  imagePreview.value = ''
  imageFile.value = null
  if (imageInput.value) {
    imageInput.value.value = ''
  }
}

const handleSubmit = async () => {
  if (submitting.value) return

  // 基础验证
  if (!form.title.trim()) {
    showToast.value = true
    const errorData = formatErrorForNotification({
      title: '标题不能为空',
      message: '请输入任务标题',
      actionSuggestion: '请填写一个描述性的任务标题',
      severity: 'error'
    })
    toastData.value = {
      ...errorData,
      details: {}
    }
    return
  }

  // 带锁任务验证
  if (form.task_type === 'lock') {
    if (form.duration_type === 'random' && (!form.duration_max || !form.duration_value || form.duration_max <= form.duration_value)) {
      showToast.value = true
      const errorData = formatErrorForNotification({
        title: '最大时间设置错误',
        message: '随机时间类型的最大时间必须大于最小时间',
        actionSuggestion: '请重新设置时间范围，确保最大时间大于最小时间',
        severity: 'error'
      })
      toastData.value = {
        ...errorData,
        details: {}
      }
      return
    }

    if (form.unlock_type === 'vote') {
      if (!form.vote_agreement_ratio) {
        showToast.value = true
        const errorData = formatErrorForNotification({
          title: '投票比例必填',
          message: '投票解锁必须设置同意比例',
          actionSuggestion: '请设置投票通过所需的同意比例',
          severity: 'error'
        })
        toastData.value = {
          ...errorData,
          details: {}
        }
        return
      }
    }
  }

  // 任务板验证
  if (form.task_type === 'board') {
    if (!form.reward || form.reward < 1) {
      showToast.value = true
      const errorData = formatErrorForNotification({
        title: '奖励积分无效',
        message: '任务板必须设置有效的奖励积分',
        actionSuggestion: '请设置合理的奖励积分数量（至少1积分）',
        severity: 'error'
      })
      toastData.value = {
        ...errorData,
        details: {}
      }
      return
    }

    if (!form.max_duration || form.max_duration < 1) {
      showToast.value = true
      const errorData = formatErrorForNotification({
        title: '最大完成时间必填',
        message: '任务板必须设置最大完成时间',
        actionSuggestion: '请设置任务的最大完成时间（至少1小时）',
        severity: 'error'
      })
      toastData.value = {
        ...errorData,
        details: {}
      }
      return
    }

    // Daily task validation
    if (dailyTaskConfig.value.isEnabled) {
      const totalCost = (form.reward || 0) * dailyTaskConfig.value.duration
      if (userCoins.value < totalCost) {
        showToast.value = true
        const errorData = formatErrorForNotification({
          title: '积分不足',
          message: `创建日常任务需要 ${totalCost} 积分，您的余额不足`,
          actionSuggestion: '请减少持续天数或降低每日奖励',
          severity: 'error'
        })
        toastData.value = {
          ...errorData,
          details: {
            '所需积分': totalCost,
            '当前余额': userCoins.value,
            '还需积分': totalCost - userCoins.value
          }
        }
        return
      }
    }
  }

  submitting.value = true

  try {
    // Clean up form data based on task type
    const cleanedForm = { ...form }

    // Map frontend field to backend field
    if (form.autoPost !== undefined) {
      cleanedForm.auto_publish = form.autoPost
    }
    delete (cleanedForm as any).autoPost

    if (form.task_type === 'lock') {
      // Remove board-specific fields for lock tasks
      delete cleanedForm.reward
      delete cleanedForm.max_duration
      delete cleanedForm.completion_rate_threshold
      delete cleanedForm.is_daily_task
      delete cleanedForm.daily_task_duration
      delete cleanedForm.daily_task_publish_time
      delete cleanedForm.daily_task_total_cost

      // If temporary unlock is not enabled, remove related fields
      if (!cleanedForm.allow_temporary_unlock) {
        delete cleanedForm.temporary_unlock_limit_type
        delete cleanedForm.temporary_unlock_limit_value
        delete cleanedForm.temporary_unlock_max_duration
        delete cleanedForm.temporary_unlock_require_approval
        delete cleanedForm.temporary_unlock_require_photo
      }
    } else if (form.task_type === 'board') {
      // Remove lock-specific fields for board tasks
      delete cleanedForm.duration_type
      delete cleanedForm.duration_value
      delete cleanedForm.duration_max
      delete cleanedForm.difficulty
      delete cleanedForm.unlock_type
      delete cleanedForm.vote_agreement_ratio
      delete cleanedForm.strict_mode

      // Remove temporary unlock fields for board tasks
      delete cleanedForm.allow_temporary_unlock
      delete cleanedForm.temporary_unlock_limit_type
      delete cleanedForm.temporary_unlock_limit_value
      delete cleanedForm.temporary_unlock_max_duration
      delete cleanedForm.temporary_unlock_require_approval
      delete cleanedForm.temporary_unlock_require_photo

      // Clean up completion_rate_threshold - remove if 0 or null/undefined
      if (cleanedForm.completion_rate_threshold === 0 ||
          cleanedForm.completion_rate_threshold === null ||
          cleanedForm.completion_rate_threshold === undefined) {
        delete cleanedForm.completion_rate_threshold
      }

      // If daily task is not enabled, remove related fields
      if (!dailyTaskConfig.value.isEnabled) {
        delete cleanedForm.is_daily_task
        delete cleanedForm.daily_task_duration
        delete cleanedForm.daily_task_publish_time
        delete cleanedForm.daily_task_total_cost
      } else {
        // Set daily task fields
        cleanedForm.is_daily_task = true
        cleanedForm.daily_task_duration = dailyTaskConfig.value.duration
        cleanedForm.daily_task_publish_time = dailyTaskConfig.value.publishTime
        cleanedForm.daily_task_total_cost = (form.reward || 0) * dailyTaskConfig.value.duration
      }
    }

    // Debug: Log the data being sent
    console.log('Form data before cleaning:', form)
    console.log('Cleaned form data being sent:', cleanedForm)

    // Create the task through API
    let newTask
    if (imageFile.value && form.autoPost) {
      // If image exists and auto-publish is selected, use FormData
      const formData = new FormData()

      // Add all task fields
      Object.keys(cleanedForm).forEach(key => {
        const typedKey = key as keyof typeof cleanedForm
        const value = cleanedForm[typedKey]
        if (value !== undefined && value !== null) {
          formData.append(key, String(value))
        }
      })

      // Add image
      formData.append('images', imageFile.value)

      newTask = await tasksApi.createTaskWithImages(formData)
      console.log('Task created successfully with images:', newTask)
    } else {
      // No image or no auto-publish, use JSON
      newTask = await tasksApi.createTask(cleanedForm)
      console.log('Task created successfully:', newTask)
    }

    // Show success message
    const successMsg = form.autoPost
      ? `${form.task_type === 'lock' ? '带锁任务' : '任务板'}创建成功，并已自动发布动态！`
      : `${form.task_type === 'lock' ? '带锁任务' : '任务板'}创建成功！`
    successMessage.value = successMsg

    // Refresh user data to update coins
    await authStore.refreshUser()

    // Emit success event
    emit('success', !!form.autoPost)

    // Close modal after delay
    setTimeout(() => {
      if (successMessage.value) {
        closeModal()
      }
    }, 1500)

  } catch (error: any) {
    console.error('Error creating task:', error)

    // Use error handling utility
    const userFriendlyError = handleApiError(error, 'task')
    const formattedError = formatErrorForNotification(userFriendlyError)

    showToast.value = true
    toastData.value = {
      type: formattedError.type,
      title: formattedError.title,
      message: formattedError.message,
      secondaryMessage: '如果问题持续存在，请联系管理员',
      details: {
        '错误时间': new Date().toLocaleString(),
        '错误详情': error.message || '未知错误'
      }
    }
  } finally {
    submitting.value = false
  }
}

// Watch for task type changes to reset form
watch(() => form.task_type, (newValue) => {
  if (newValue === 'lock') {
    // Reset board fields
    form.reward = undefined
    form.max_duration = 24
    form.max_participants = 1
    form.completion_rate_threshold = 0
    // Initialize lock fields
    form.duration_type = 'fixed'
    form.duration_value = 60
    form.duration_max = 120
    form.strict_mode = false
    // Reset temporary unlock fields
    form.allow_temporary_unlock = false
    form.temporary_unlock_limit_type = 'daily_count'
    form.temporary_unlock_limit_value = 3
    form.temporary_unlock_max_duration = 30
    form.temporary_unlock_require_approval = false
    form.temporary_unlock_require_photo = false
    // Reset daily task
    dailyTaskConfig.value.isEnabled = false
  } else if (newValue === 'board') {
    // Reset lock fields
    form.duration_type = 'fixed'
    form.duration_value = 60
    form.duration_max = undefined
    form.difficulty = 'normal'
    form.unlock_type = 'time'
    form.vote_agreement_ratio = undefined
    form.strict_mode = false
    // Reset temporary unlock fields
    form.allow_temporary_unlock = false
    form.temporary_unlock_limit_type = 'daily_count'
    form.temporary_unlock_limit_value = 3
    form.temporary_unlock_max_duration = 30
    form.temporary_unlock_require_approval = false
    form.temporary_unlock_require_photo = false
  }
})

// Watch for unlock_type changes to reset vote_threshold
watch(() => form.unlock_type, (newValue) => {
  if (newValue !== 'vote') {
    form.vote_agreement_ratio = undefined
  }
})

// Watch for duration_type changes to reset duration_max
watch(() => form.duration_type, (newValue) => {
  if (newValue === 'random') {
    const minValue = form.duration_value || 60
    if (!form.duration_max || form.duration_max <= minValue) {
      form.duration_max = Math.max(minValue * 2, 120)
    }
  } else {
    form.duration_max = undefined
  }
})

// Watch for strict_mode changes to show notification when enabled
watch(() => form.strict_mode, (newValue) => {
  if (newValue) {
    showToast.value = true
    toastData.value = {
      type: 'warning',
      title: '⚠️ 严格模式已启用',
      message: '严格模式需要您每天发布包含验证码的打卡动态，并接受社区监督投票。',
      secondaryMessage: '如果未能按时打卡，或社区监督投票未通过（同意比例未达到要求），您的任务将被冻结！',
      details: {
        '打卡要求': '每天首次打卡自动包含验证码',
        '社区监督': '其他用户可对您的打卡进行投票',
        '冻结条件': '未按时打卡 或 投票未通过',
        '解冻方式': '支付积分或使用道具解除冻结'
      }
    }
  }
})

// Ensure body scroll is restored on unmount
onUnmounted(() => {
  document.body.style.overflow = ''
})
</script>

<style scoped>
/* Modal Overlay */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  z-index: 1000;
  padding: 2vh 1rem;
  overflow-y: auto;
}

/* Modal Content */
.modal-content {
  background: #f8fafc;
  border-radius: 1.25rem;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  width: 100%;
  max-width: 640px;
  max-height: 96vh;
  overflow-y: auto;
  position: relative;
}

/* Modal Header */
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 1.5rem 1.5rem 0.75rem;
  background: white;
  border-bottom: 1px solid #e2e8f0;
  position: sticky;
  top: 0;
  z-index: 10;
}

.modal-header__title-group h2 {
  margin: 0 0 0.25rem 0;
  font-size: 1.375rem;
  font-weight: 700;
  color: #1e293b;
}

.modal-header__subtitle {
  margin: 0;
  font-size: 0.875rem;
  color: #64748b;
}

.close-btn {
  background: #f1f5f9;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0;
  border-radius: 0.5rem;
  width: 2.25rem;
  height: 2.25rem;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #64748b;
  transition: all 0.2s ease;
}

.close-btn:hover:not(:disabled) {
  background: #e2e8f0;
  color: #1e293b;
}

.close-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Modal Body */
.modal-body {
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.875rem;
}

/* Task Type Selector */
.task-type-selector {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.task-type-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 1.25rem 1rem;
  background: white;
  border: 2px solid #e2e8f0;
  border-radius: 1rem;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: center;
}

.task-type-card:hover {
  border-color: #6366f1;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.15);
}

.task-type-card.active {
  border-color: #6366f1;
  background: linear-gradient(135deg, #eef2ff 0%, #e0e7ff 100%);
}

.task-type-card__icon {
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.task-type-card__title {
  font-size: 1rem;
  font-weight: 600;
  color: #1e293b;
  margin: 0 0 0.25rem 0;
}

.task-type-card__desc {
  font-size: 0.75rem;
  color: #64748b;
  line-height: 1.4;
}

/* Form Fields */
.form-fields {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

/* Toggle Field Layout - Fixes overlap issues */
.form-field--toggle {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  align-items: flex-start;
}

.form-field--toggle :deep(.toggle-switch) {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}

.form-field--toggle :deep(.toggle-switch__label) {
  font-size: 0.875rem;
  font-weight: 500;
  color: #374151;
  white-space: nowrap;
}

.form-field__hint-below {
  font-size: 0.8125rem;
  color: #6b7280;
  margin-left: calc(36px + 0.5rem); /* Align with toggle label */
  line-height: 1.4;
}

/* Toggle row layout */
.form-row--toggles {
  display: flex;
  gap: 1.5rem;
  flex-wrap: wrap;
}

.form-row--toggles .form-field--toggle {
  flex: 1;
  min-width: fit-content;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.form-field--half {
  flex: 1;
  min-width: 0;
}

.form-field--inline {
  flex-direction: row;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: nowrap;
}

/* ToggleSwitch在inline布局中的样式 */
.form-field--inline :deep(.toggle-switch) {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  flex-shrink: 0;
}

.form-field--inline :deep(.toggle-switch__track) {
  flex-shrink: 0;
}

.form-field--inline .toggle-wrapper {
  flex-shrink: 0;
  display: flex;
  align-items: center;
}

.form-field--inline :deep(.toggle-switch__label) {
  white-space: nowrap;
  font-size: 0.875rem;
  color: #374151;
}

.form-field--inline .form-field__hint-inline {
  color: #6b7280;
  font-size: 0.8125rem;
  flex: 1;
  min-width: 0;
}

.form-field__label {
  font-size: 0.875rem;
  font-weight: 600;
  color: #374151;
}

.required {
  color: #dc2626;
}

.optional {
  font-weight: 400;
  color: #9ca3af;
  font-size: 0.8125rem;
}

.form-field__input,
.form-field__select {
  padding: 0.625rem 0.875rem;
  font-size: 0.9375rem;
  color: #1f2937;
  background: white;
  border: 2px solid #e5e7eb;
  border-radius: 0.5rem;
  transition: all 0.2s ease;
}

.form-field__input:hover,
.form-field__select:hover {
  border-color: #d1d5db;
}

.form-field__input:focus,
.form-field__select:focus {
  outline: none;
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
}

.form-field__hint {
  font-size: 0.75rem;
  color: #6b7280;
  line-height: 1.4;
}

.form-field__hint-inline {
  font-size: 0.8125rem;
  color: #6b7280;
}

/* Form Row */
.form-row {
  display: flex;
  gap: 1rem;
}

/* Form Row with inline fields */
.form-row .form-field--inline {
  flex: 1;
  min-width: fit-content;
}

/* Input with Suffix */
.input-with-suffix {
  position: relative;
  display: flex;
  align-items: center;
}

.input-with-suffix .form-field__input {
  width: 100%;
  padding-right: 3.5rem;
}

.input-suffix {
  position: absolute;
  right: 0.875rem;
  font-size: 0.875rem;
  color: #6b7280;
  font-weight: 500;
}

/* Radio Group */
.radio-group {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.radio-option {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  font-size: 0.875rem;
  color: #4b5563;
}

.radio-option input[type="radio"] {
  width: 1.125rem;
  height: 1.125rem;
  accent-color: #6366f1;
}

/* Duration Section */
.duration-section {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

/* Temporary Unlock Section */
.temporary-unlock-section {
  background: #f8fafc;
  border: 2px solid #e2e8f0;
  border-radius: 0.75rem;
  overflow: hidden;
}

.temporary-unlock-header {
  padding: 0.875rem 1rem;
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.temporary-unlock-header:hover {
  background-color: #f1f5f9;
}

.temporary-unlock-toggle {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.temporary-unlock-toggle .toggle-switch {
  flex-shrink: 0;
}

.temporary-unlock-hint {
  font-size: 0.8125rem;
  color: #6b7280;
  flex: 1;
  min-width: 0;
}

.temporary-unlock-config {
  padding: 0 1rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

/* Slider */
.slider-group {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.slider {
  flex: 1;
  height: 6px;
  border-radius: 3px;
  background: #e5e7eb;
  outline: none;
  -webkit-appearance: none;
}

.slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #6366f1;
  cursor: pointer;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.slider::-moz-range-thumb {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #6366f1;
  cursor: pointer;
  border: none;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.slider-value {
  min-width: 80px;
  font-weight: 600;
  color: #374151;
  font-size: 0.875rem;
}

/* Publish Options */
.publish-options {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

/* Image Upload */
.image-upload-section {
  margin-top: 0.5rem;
}

.image-upload-container {
  position: relative;
  border: 2px dashed #d1d5db;
  border-radius: 0.75rem;
  overflow: hidden;
  transition: all 0.2s ease;
}

.image-upload-container:hover {
  border-color: #6366f1;
  background-color: #f8fafc;
}

.image-input {
  position: absolute;
  left: -9999px;
  opacity: 0;
}

.upload-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  cursor: pointer;
  text-align: center;
  min-height: 140px;
  background: white;
  transition: all 0.2s ease;
}

.upload-icon {
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.upload-text {
  font-size: 0.9375rem;
  font-weight: 600;
  color: #374151;
  margin-bottom: 0.25rem;
}

.upload-hint {
  font-size: 0.75rem;
  color: #6b7280;
  margin-bottom: 0.125rem;
}

.upload-size-hint {
  font-size: 0.6875rem;
  color: #6366f1;
  font-weight: 500;
}

.image-preview {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f8fafc;
  min-height: 140px;
}

.image-preview img {
  max-width: 100%;
  max-height: 200px;
  object-fit: contain;
  border-radius: 0.5rem;
}

.remove-image-btn {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  width: 28px;
  height: 28px;
  background: rgba(220, 53, 69, 0.9);
  color: white;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  font-size: 1.125rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  line-height: 1;
}

.remove-image-btn:hover {
  background: rgba(220, 53, 69, 1);
  transform: scale(1.1);
}

/* Modal Footer */
.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.875rem;
  padding: 1.25rem 1.5rem;
  background: white;
  border-top: 1px solid #e2e8f0;
  position: sticky;
  bottom: 0;
  z-index: 10;
}

.cancel-btn,
.submit-btn {
  padding: 0.625rem 1.25rem;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
  font-weight: 600;
  font-size: 0.9375rem;
  transition: all 0.2s ease;
}

.cancel-btn {
  background-color: #f1f5f9;
  color: #4b5563;
}

.cancel-btn:hover:not(:disabled) {
  background-color: #e2e8f0;
}

.submit-btn {
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  color: white;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 120px;
  justify-content: center;
}

.submit-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
}

.submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.submit-btn.is-loading {
  cursor: wait;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* Success Message */
.success-message {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: white;
  padding: 2rem;
  border-radius: 1rem;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  text-align: center;
  z-index: 20;
  min-width: 280px;
}

.success-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.success-text {
  font-size: 1.125rem;
  font-weight: 600;
  color: #1e293b;
}

/* Transitions */
.slide-fade-enter-active {
  transition: all 0.3s ease-out;
}

.slide-fade-leave-active {
  transition: all 0.2s ease-in;
}

.slide-fade-enter-from,
.slide-fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* Mobile Responsive */
@media (max-width: 640px) {
  .modal-overlay {
    padding: 0;
  }

  .modal-content {
    max-height: 100vh;
    border-radius: 0;
  }

  .modal-header {
    padding: 1rem 1rem 0.75rem;
  }

  .modal-header__title-group h2 {
    font-size: 1.125rem;
  }

  .modal-body {
    padding: 0.875rem;
    gap: 0.75rem;
  }

  .task-type-selector {
    gap: 0.75rem;
  }

  .task-type-card {
    padding: 1rem 0.75rem;
  }

  .task-type-card__icon {
    font-size: 1.75rem;
  }

  .task-type-card__title {
    font-size: 0.9375rem;
  }

  .task-type-card__desc {
    font-size: 0.6875rem;
  }

  .form-row {
    flex-direction: column;
    gap: 1rem;
  }

  .form-row--toggles {
    flex-direction: column;
    gap: 1rem;
  }

  .form-field__hint-below {
    margin-left: 0;
    font-size: 0.75rem;
  }

  .temporary-unlock-toggle {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }

  .temporary-unlock-hint {
    margin-left: calc(36px + 0.5rem);
  }

  .modal-footer {
    padding: 1rem;
    flex-direction: column-reverse;
  }

  .cancel-btn,
  .submit-btn {
    width: 100%;
    justify-content: center;
  }
}
</style>
