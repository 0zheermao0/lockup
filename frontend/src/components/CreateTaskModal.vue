<template>
  <div v-if="isVisible" class="modal-overlay" @click="closeModal">
    <div class="modal-content" @click.stop>
      <div class="modal-header">
        <h2>创建任务</h2>
        <button @click="closeModal" class="close-btn">×</button>
      </div>

      <form @submit.prevent="handleSubmit" class="modal-body">
        <!-- Task Type Selection -->
        <div class="form-group">
          <div class="form-row-inline">
            <label class="inline-label">任务类型</label>
            <div class="task-type-selector-compact">
              <button
                type="button"
                @click="form.task_type = 'lock'"
                :class="['task-type-btn-compact', { active: form.task_type === 'lock' }]"
              >
                🔒 带锁任务
              </button>
              <button
                type="button"
                @click="form.task_type = 'board'"
                :class="['task-type-btn-compact', { active: form.task_type === 'board' }]"
              >
                📋 任务板
              </button>
            </div>
          </div>
        </div>

        <div class="form-group">
          <label for="title">任务标题</label>
          <input
            id="title"
            v-model="form.title"
            type="text"
            placeholder="输入任务标题..."
            maxlength="100"
            required
          />
        </div>

        <div class="form-group">
          <label for="description">任务描述 <span class="optional">(可选)</span></label>
          <RichTextEditor
            v-model="form.description"
            :placeholder="form.task_type === 'lock' ? '描述一下你的自律挑战...' : '详细描述任务需求和要求...'"
            :max-length="500"
            min-height="100px"
          />
        </div>

        <!-- Publish Options and Image Upload Row -->
        <div class="form-group">
          <div class="publish-image-row">
            <!-- Left Column: Publish Options -->
            <div class="publish-options-column">
              <label class="section-label">发布选项</label>
              <label class="checkbox-label-enhanced">
                <input
                  type="checkbox"
                  v-model="form.autoPost"
                  class="checkbox-input-enhanced"
                />
                <span class="checkbox-text-enhanced">
                  自动发布动态
                  <small class="checkbox-desc-enhanced">创建任务后自动分享到动态</small>
                </span>
              </label>
            </div>

            <!-- Right Column: Image Upload (conditional) -->
            <div class="image-upload-column">
              <label class="section-label">任务图片 <span class="optional">(可选)</span></label>
              <div v-if="form.autoPost" class="image-upload-container-mini">
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
                  class="upload-placeholder-mini"
                  @click="triggerImageUpload"
                >
                  <div class="upload-icon-mini">📷</div>
                  <div class="upload-text-mini">点击上传</div>
                  <div class="upload-hint-mini">JPG、PNG、SVG、GIF</div>
                  <div class="upload-size-hint-mini">最大2.5MB</div>
                </div>
                <div v-else class="image-preview-mini">
                  <img :src="imagePreview" alt="预览图片" />
                  <button
                    type="button"
                    @click="removeImage"
                    class="remove-image-btn-mini"
                    title="移除图片"
                  >
                    ×
                  </button>
                </div>
              </div>
              <div v-else class="upload-disabled-hint">
                <span>勾选自动发布动态后可上传图片</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Duration Type and Strict Mode (for lock tasks) -->
        <div v-if="form.task_type === 'lock'" class="form-group">
          <div class="form-row-inline-combined">
            <!-- Duration Type -->
            <div class="form-section-compact">
              <label class="inline-label">持续类型</label>
              <div class="radio-group-compact">
                <label class="radio-option-compact">
                  <input
                    type="radio"
                    v-model="form.duration_type"
                    value="fixed"
                  />
                  <span>固定时间</span>
                </label>
                <label class="radio-option-compact">
                  <input
                    type="radio"
                    v-model="form.duration_type"
                    value="random"
                  />
                  <span>随机时间</span>
                </label>
              </div>
            </div>
            <!-- Strict Mode -->
            <div class="form-section-compact">
              <label class="inline-label">严格模式</label>
              <label class="checkbox-label-compact">
                <input
                  type="checkbox"
                  v-model="form.strict_mode"
                  class="checkbox-input-compact"
                />
                <span class="checkbox-text-compact">
                  启用严格模式
                  <small class="checkbox-desc-compact">打卡时自动添加验证码</small>
                </span>
              </label>
            </div>
          </div>
        </div>

        <!-- Lock Task Fields -->
        <template v-if="form.task_type === 'lock'">
          <div class="form-row">
            <div class="form-group">
              <label for="difficulty">难度等级</label>
              <select id="difficulty" v-model="form.difficulty" required>
                <option value="easy">简单 - 适合初学者</option>
                <option value="normal">普通 - 日常挑战</option>
                <option value="hard">困难 - 需要坚强意志</option>
                <option value="hell">地狱 - 极限挑战</option>
              </select>
            </div>

            <div class="form-group">
              <label for="unlock_type">解锁方式</label>
              <select id="unlock_type" v-model="form.unlock_type" required>
                <option value="time">定时解锁</option>
                <option value="vote">投票解锁</option>
              </select>
            </div>
          </div>


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

          <div v-if="form.unlock_type === 'vote'" class="form-group">
            <label for="vote_agreement_ratio">同意比例要求</label>
            <select id="vote_agreement_ratio" v-model="form.vote_agreement_ratio" required>
              <option value="0.5">50% - 简单多数</option>
              <option value="0.6">60% - 普通多数</option>
              <option value="0.7">70% - 绝对多数</option>
              <option value="0.8">80% - 超级多数</option>
              <option value="0.9">90% - 压倒性多数</option>
            </select>
            <small class="help-text">
              只要有人投票且同意比例达到要求即可解锁，无最低投票人数限制
            </small>
          </div>

        </template>

        <!-- Task Board Fields -->
        <template v-if="form.task_type === 'board'">
          <div class="form-row">
            <div class="form-group">
              <label for="reward">奖励金额</label>
              <input
                id="reward"
                v-model.number="form.reward"
                type="number"
                min="1"
                max="10000"
                placeholder="完成任务的奖励"
                required
              />
            </div>
            <div class="form-group">
              <label for="max_duration">最大完成时间 (小时)</label>
              <input
                id="max_duration"
                v-model.number="form.max_duration"
                type="number"
                min="1"
                placeholder="任务最长完成时间"
                required
              />
            </div>
          </div>

          <div class="form-group">
            <label for="max_participants">最大参与人数 <span class="optional">(默认1为单人任务)</span></label>
            <input
              id="max_participants"
              v-model.number="form.max_participants"
              type="number"
              min="1"
              max="50"
              placeholder="多人任务的最大参与人数"
            />
            <small class="form-hint">
              设置为空或1为单人任务，设置为2或以上为多人任务。多人任务允许多人同时参与并提交作品。
            </small>
          </div>

          <div class="form-group">
            <label for="completion_rate_threshold">
              任务完成率门槛 <span class="optional">(可选，默认0%无限制)</span>
            </label>
            <div class="threshold-input-group">
              <input
                id="completion_rate_threshold"
                v-model.number="form.completion_rate_threshold"
                type="number"
                min="0"
                max="100"
                step="1"
                placeholder="0"
              />
              <span class="threshold-unit">%</span>
            </div>
            <small class="form-hint">
              设置参与者的最低任务完成率要求。完成率低于此门槛的用户无法接取任务。
              设置为0或留空表示无限制。
            </small>
          </div>

        </template>

        <div class="modal-footer">
          <button type="button" @click="closeModal" class="cancel-btn">取消</button>
          <button type="submit" :disabled="submitting" class="submit-btn">
            {{ submitting ? '创建中...' : '创建任务' }}
          </button>
        </div>
      </form>

      <div v-if="successMessage" class="success-message">
        {{ successMessage }}
      </div>
    </div>

    <!-- NotificationToast for error handling -->
    <NotificationToast
      :is-visible="showToast"
      :type="toastData.type"
      :title="toastData.title"
      :message="toastData.message"
      :secondary-message="toastData.secondaryMessage"
      :details="toastData.details"
      @close="showToast = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch, onUnmounted } from 'vue'
import { tasksApi } from '../lib/api-tasks'
import { postsApi } from '../lib/api'
import type { TaskCreateRequest } from '../types/index'
import DurationSelector from './DurationSelector.vue'
import RichTextEditor from './RichTextEditor.vue'
import NotificationToast from './NotificationToast.vue'
import { handleApiError, formatErrorForNotification } from '../utils/errorHandling'

interface Props {
  isVisible: boolean
  initialTaskType?: 'lock' | 'board'
}

interface Emits {
  (e: 'close'): void
  (e: 'success'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const submitting = ref(false)
const successMessage = ref('')
const imageInput = ref<HTMLInputElement>()
const imagePreview = ref<string>('')
const imageFile = ref<File | null>(null)

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
  autoPost: true, // 默认勾选自动发布动态
  // Lock task fields
  duration_type: 'fixed',
  duration_value: 60, // 默认1小时
  duration_max: undefined,
  difficulty: 'normal',
  unlock_type: 'time',
  strict_mode: false, // 默认不启用严格模式
  // Board task fields
  reward: undefined,
  max_duration: 24, // 默认24小时
  max_participants: 1, // 默认单人任务
  completion_rate_threshold: 0 // 默认0%（无限制）
})

// Watch for modal visibility changes
watch(() => props.isVisible, (newValue) => {
  if (newValue) {
    resetForm()
    // 禁用body滚动
    document.body.style.overflow = 'hidden'
  } else {
    // 恢复body滚动
    document.body.style.overflow = ''
  }
})

const resetForm = () => {
  // Use initial task type if provided, otherwise default to 'lock'
  form.task_type = props.initialTaskType || 'lock'
  form.title = ''
  form.description = ''
  form.autoPost = true
  // Lock task fields
  form.duration_type = 'fixed'
  form.duration_value = 60
  form.difficulty = 'normal'
  form.unlock_type = 'time'
  form.duration_max = 120 // 默认2小时作为随机时间的最大值
  form.vote_agreement_ratio = undefined
  form.strict_mode = false // 默认不启用严格模式
  // Board task fields
  form.reward = undefined
  form.max_duration = 24
  form.max_participants = 1
  form.completion_rate_threshold = 0
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
  }

  submitting.value = true

  try {
    // Clean up form data based on task type
    const cleanedForm = { ...form }

    // Map frontend field to backend field
    if (form.autoPost !== undefined) {
      cleanedForm.auto_publish = form.autoPost
    }
    delete cleanedForm.autoPost

    if (form.task_type === 'lock') {
      // Remove board-specific fields for lock tasks
      delete cleanedForm.reward
      delete cleanedForm.max_duration
      delete cleanedForm.completion_rate_threshold
    } else if (form.task_type === 'board') {
      // Remove lock-specific fields for board tasks
      delete cleanedForm.duration_type
      delete cleanedForm.duration_value
      delete cleanedForm.duration_max
      delete cleanedForm.difficulty
      delete cleanedForm.unlock_type
      delete cleanedForm.vote_agreement_ratio
      delete cleanedForm.strict_mode

      // Clean up completion_rate_threshold - remove if 0 or null/undefined
      if (cleanedForm.completion_rate_threshold === 0 ||
          cleanedForm.completion_rate_threshold === null ||
          cleanedForm.completion_rate_threshold === undefined) {
        delete cleanedForm.completion_rate_threshold
      }
    }

    // Debug: Log the data being sent
    console.log('Form data before cleaning:', form)
    console.log('Cleaned form data being sent:', cleanedForm)

    // Create the task through API (auto-publish is now handled on backend)
    let newTask
    if (imageFile.value && form.autoPost) {
      // 如果有图片且选择了自动发布，使用FormData
      const formData = new FormData()

      // 添加所有任务字段
      Object.keys(cleanedForm).forEach(key => {
        const typedKey = key as keyof typeof cleanedForm
        if (cleanedForm[typedKey] !== undefined && cleanedForm[typedKey] !== null) {
          formData.append(key, String(cleanedForm[typedKey]))
        }
      })

      // 添加图片
      formData.append('images', imageFile.value)

      newTask = await tasksApi.createTaskWithImages(formData)
      console.log('Task created successfully with images:', newTask)
    } else {
      // 没有图片或不自动发布，使用JSON
      newTask = await tasksApi.createTask(cleanedForm)
      console.log('Task created successfully:', newTask)
    }

    // 显示成功消息
    const successMsg = form.autoPost
      ? `${form.task_type === 'lock' ? '带锁任务' : '任务板'}创建成功，并已自动发布动态！`
      : `${form.task_type === 'lock' ? '带锁任务' : '任务板'}创建成功！`
    successMessage.value = successMsg
    emit('success')

    // 延迟1.5秒后关闭窗口
    setTimeout(() => {
      if (successMessage.value) {
        closeModal()
      }
    }, 1500)

  } catch (error: any) {
    console.error('Error creating task:', error)

    // 使用新的错误处理工具函数
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
  } else if (newValue === 'board') {
    // Reset lock fields
    form.duration_type = 'fixed'
    form.duration_value = 60
    form.duration_max = undefined
    form.difficulty = 'normal'
    form.unlock_type = 'time'
    form.vote_agreement_ratio = undefined
    form.strict_mode = false
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
    // 如果切换到随机时间，设置默认的最大时间
    const minValue = form.duration_value || 60
    if (!form.duration_max || form.duration_max <= minValue) {
      form.duration_max = Math.max(minValue * 2, 120) // 至少是最短时间的2倍，或2小时
    }
  } else {
    form.duration_max = undefined
  }
})

// 组件卸载时确保恢复滚动
onUnmounted(() => {
  document.body.style.overflow = ''
})

</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  z-index: 1000;
  padding-top: 5vh;
  overflow: hidden;
}

.modal-content {
  background: white;
  border-radius: 8px;
  border: 2px solid #000;
  box-shadow: 8px 8px 0 #000;
  width: 100%;
  max-width: 600px;
  max-height: 90vh;
  overflow-y: auto;
  position: relative;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 2px solid #e9ecef;
}

.modal-header h2 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0.5rem;
  border-radius: 4px;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover {
  background-color: #f8f9fa;
}

.modal-body {
  padding: 1.5rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: #333;
}

.form-group input,
.form-group textarea,
.form-group select {
  width: 100%;
  padding: 0.75rem;
  border: 2px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
  box-sizing: border-box;
}

.form-group input:focus,
.form-group textarea:focus,
.form-group select:focus {
  outline: none;
  border-color: #007bff;
}

.form-group textarea {
  resize: vertical;
  min-height: 80px;
}

.radio-group {
  display: flex;
  gap: 1rem;
}

.radio-option {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  font-weight: normal;
}

.radio-option input[type="radio"] {
  width: auto;
  margin: 0;
}

.task-type-selector {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  margin-bottom: 0.5rem;
}

.task-type-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 1rem;
  border: 2px solid #ddd;
  border-radius: 8px;
  background: white;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 1rem;
  font-weight: 600;
}

.task-type-btn:hover {
  border-color: #007bff;
  background-color: #f8f9fa;
}

.task-type-btn.active {
  border-color: #007bff;
  background-color: #007bff;
  color: white;
}

.task-type-desc {
  font-size: 0.75rem;
  font-weight: normal;
  margin-top: 0.25rem;
  opacity: 0.8;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #e9ecef;
}

.cancel-btn, .submit-btn {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 600;
  font-size: 1rem;
}

.cancel-btn {
  background-color: #6c757d;
  color: white;
}

.cancel-btn:hover {
  background-color: #5a6268;
}

.submit-btn {
  background-color: #28a745;
  color: white;
}

.submit-btn:hover:not(:disabled) {
  background-color: #218838;
}

.submit-btn:disabled {
  background-color: #6c757d;
  cursor: not-allowed;
}

.success-message {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background-color: #d4edda;
  color: #155724;
  padding: 1rem 2rem;
  border: 1px solid #c3e6cb;
  border-radius: 4px;
  font-weight: 600;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
  z-index: 10;
}

.help-text {
  display: block;
  margin-top: 0.5rem;
  font-size: 0.75rem;
  color: #666;
  font-style: italic;
}

.duration-section {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  margin-bottom: 1.5rem;
}

.optional {
  font-size: 0.75rem;
  color: #666;
  font-weight: normal;
  font-style: italic;
}

/* Image Upload Styles */
.image-upload-container {
  position: relative;
  border: 2px dashed #ddd;
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.2s;
}

.image-upload-container:hover {
  border-color: #007bff;
  background-color: #f8f9fa;
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
  min-height: 120px;
  background-color: #fafafa;
  transition: all 0.2s;
}

.upload-placeholder:hover {
  background-color: #f0f0f0;
}

.upload-icon {
  font-size: 2rem;
  margin-bottom: 0.5rem;
  opacity: 0.6;
}

.upload-text {
  font-size: 1rem;
  font-weight: 600;
  color: #333;
  margin-bottom: 0.25rem;
}

.upload-hint {
  font-size: 0.75rem;
  color: #666;
}

.image-preview {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #f8f9fa;
  min-height: 120px;
}

.image-preview img {
  max-width: 100%;
  max-height: 200px;
  object-fit: contain;
  border-radius: 4px;
}

.remove-image-btn {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  background: rgba(220, 53, 69, 0.9);
  color: white;
  border: none;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  cursor: pointer;
  font-size: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.remove-image-btn:hover {
  background: rgba(220, 53, 69, 1);
  transform: scale(1.1);
}

/* Checkbox Styles */
.checkbox-label {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  cursor: pointer;
  padding: 1rem;
  border: 2px solid #e9ecef;
  border-radius: 8px;
  transition: all 0.2s;
  background-color: #fafafa;
}

.checkbox-label:hover {
  border-color: #007bff;
  background-color: #f8f9fa;
}

.checkbox-input {
  width: auto !important;
  margin: 0;
  transform: scale(1.2);
}

.checkbox-input:checked + .checkbox-text {
  color: #007bff;
  font-weight: 600;
}

.checkbox-text {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-weight: 500;
}

.checkbox-desc {
  font-size: 0.75rem;
  color: #666;
  font-weight: normal;
  font-style: italic;
}

/* Compact Layout Styles */
.form-row-inline {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.form-row-inline-combined {
  display: flex;
  align-items: flex-start;
  gap: 1.5rem;
  flex-wrap: wrap;
}

.form-section-compact {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex: 1;
  min-width: 250px;
}

.inline-label {
  font-weight: 600;
  color: #333;
  font-size: 1rem;
  min-width: 80px;
  flex-shrink: 0;
}

/* Compact Task Type Selector */
.task-type-selector-compact {
  display: flex;
  gap: 0.75rem;
  flex: 1;
}

.task-type-btn-compact {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.5rem 1rem;
  border: 2px solid #ddd;
  border-radius: 6px;
  background: white;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 0.875rem;
  font-weight: 600;
  flex: 1;
  min-height: 40px;
}

.task-type-btn-compact:hover {
  border-color: #007bff;
  background-color: #f8f9fa;
}

.task-type-btn-compact.active {
  border-color: #007bff;
  background-color: #007bff;
  color: white;
}

/* Compact Checkbox */
.checkbox-label-compact {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  flex: 1;
}

.checkbox-input-compact {
  width: auto !important;
  margin: 0;
  transform: scale(1.1);
}

.checkbox-text-compact {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  font-weight: 500;
  font-size: 0.9rem;
}

.checkbox-desc-compact {
  font-size: 0.7rem;
  color: #666;
  font-weight: normal;
  font-style: italic;
}

/* Compact Radio Group */
.radio-group-compact {
  display: flex;
  gap: 0.75rem;
  flex: 1;
}

.radio-option-compact {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  cursor: pointer;
  font-weight: 500;
  font-size: 0.85rem;
  white-space: nowrap;
}

.radio-option-compact input[type="radio"] {
  width: auto !important;
  margin: 0;
  transform: scale(1.1);
}

/* Compact Image Upload */
.image-upload-container-compact {
  position: relative;
  border: 2px dashed #ddd;
  border-radius: 6px;
  overflow: hidden;
  transition: all 0.2s;
}

.image-upload-container-compact:hover {
  border-color: #007bff;
  background-color: #f8f9fa;
}

.upload-placeholder-compact {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  cursor: pointer;
  text-align: center;
  min-height: 80px;
  background-color: #fafafa;
  transition: all 0.2s;
}

.upload-placeholder-compact:hover {
  background-color: #f0f0f0;
}

.upload-icon-compact {
  font-size: 1.5rem;
  margin-bottom: 0.25rem;
  opacity: 0.6;
}

.upload-text-compact {
  font-size: 0.875rem;
  font-weight: 600;
  color: #333;
  margin-bottom: 0.1rem;
}

.upload-hint-compact {
  font-size: 0.7rem;
  color: #666;
}

.image-preview-compact {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #f8f9fa;
  min-height: 80px;
}

.image-preview-compact img {
  max-width: 100%;
  max-height: 120px;
  object-fit: contain;
  border-radius: 4px;
}

.remove-image-btn-compact {
  position: absolute;
  top: 0.25rem;
  right: 0.25rem;
  background: rgba(220, 53, 69, 0.9);
  color: white;
  border: none;
  border-radius: 50%;
  width: 20px;
  height: 20px;
  cursor: pointer;
  font-size: 0.8rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.remove-image-btn-compact:hover {
  background: rgba(220, 53, 69, 1);
  transform: scale(1.1);
}

/* Enhanced Publish and Image Upload Layout */
.publish-image-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
  align-items: start;
}

.publish-options-column,
.image-upload-column {
  display: flex;
  flex-direction: column;
}

.section-label {
  font-weight: 600;
  font-size: 0.9rem;
  color: #333;
  margin-bottom: 0.75rem;
  display: block;
}

/* Enhanced checkbox styling */
.checkbox-label-enhanced {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  cursor: pointer;
  padding: 0.75rem;
  border: 2px solid #e9ecef;
  border-radius: 6px;
  background: #fafafa;
  transition: all 0.2s ease;
}

.checkbox-label-enhanced:hover {
  border-color: #007bff;
  background: #f8f9fa;
}

.checkbox-input-enhanced {
  width: 18px;
  height: 18px;
  margin: 0;
  cursor: pointer;
  flex-shrink: 0;
  margin-top: 2px;
}

.checkbox-text-enhanced {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-weight: 600;
  color: #333;
}

.checkbox-desc-enhanced {
  font-size: 0.75rem;
  font-weight: 400;
  color: #666;
  line-height: 1.3;
}

/* Mini image upload component */
.image-upload-container-mini {
  position: relative;
  border: 2px dashed #ddd;
  border-radius: 6px;
  overflow: hidden;
  transition: all 0.2s;
  max-width: 200px;
}

.image-upload-container-mini:hover {
  border-color: #007bff;
  background-color: #f8f9fa;
}

.upload-placeholder-mini {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 0.75rem;
  cursor: pointer;
  text-align: center;
  min-height: 100px;
  background-color: #fafafa;
  transition: all 0.2s;
}

.upload-placeholder-mini:hover {
  background-color: #f0f0f0;
}

.upload-icon-mini {
  font-size: 1.2rem;
  margin-bottom: 0.25rem;
  opacity: 0.6;
}

.upload-text-mini {
  font-size: 0.8rem;
  font-weight: 600;
  color: #333;
  margin-bottom: 0.25rem;
}

.upload-hint-mini {
  font-size: 0.7rem;
  color: #666;
  line-height: 1.2;
}

.upload-size-hint-mini {
  font-size: 0.65rem;
  color: #007bff;
  font-weight: 600;
  margin-top: 0.125rem;
  line-height: 1.2;
}

.image-preview-mini {
  position: relative;
  width: 100%;
  height: 100px;
}

.image-preview-mini img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.remove-image-btn-mini {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 20px;
  height: 20px;
  border: none;
  background: rgba(220, 53, 69, 0.8);
  color: white;
  border-radius: 50%;
  cursor: pointer;
  font-size: 12px;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  line-height: 1;
}

.remove-image-btn-mini:hover {
  background: rgba(220, 53, 69, 1);
  transform: scale(1.1);
}

.upload-disabled-hint {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100px;
  max-width: 200px;
  padding: 0.75rem;
  background: #f8f9fa;
  border: 2px dashed #dee2e6;
  border-radius: 6px;
  text-align: center;
}

.upload-disabled-hint span {
  font-size: 0.75rem;
  color: #6c757d;
  font-style: italic;
  line-height: 1.3;
}

/* Mobile responsive */
@media (max-width: 768px) {
  .modal-overlay {
    padding: 0.5rem;
  }

  .modal-header {
    padding: 1rem;
  }

  .modal-body {
    padding: 1rem;
  }

  .form-row {
    grid-template-columns: 1fr;
  }

  .radio-group {
    flex-direction: column;
    gap: 0.5rem;
  }

  .modal-footer {
    flex-direction: column;
  }

  /* Mobile compact layout */
  .form-row-inline {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }

  .form-row-inline-combined {
    flex-direction: column;
    gap: 1rem;
  }

  .form-section-compact {
    min-width: auto;
    width: 100%;
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }

  /* Mobile layout for publish-image row */
  .publish-image-row {
    grid-template-columns: 1fr;
    gap: 1rem;
  }

  .image-upload-container-mini {
    max-width: 100%;
  }

  .upload-disabled-hint {
    max-width: 100%;
  }

  .inline-label {
    min-width: auto;
    margin-bottom: 0.25rem;
  }

  .task-type-selector-compact {
    width: 100%;
  }

  .task-type-btn-compact {
    font-size: 0.8rem;
    padding: 0.4rem 0.8rem;
  }

  .checkbox-label-compact {
    width: 100%;
  }

  .checkbox-text-compact {
    font-size: 0.85rem;
  }

  .checkbox-desc-compact {
    font-size: 0.65rem;
  }

  .radio-group-compact {
    width: 100%;
    gap: 0.75rem;
  }

  .radio-option-compact {
    font-size: 0.85rem;
  }
}

/* Threshold input styles */
.threshold-input-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.threshold-input-group input {
  flex: 1;
  max-width: 100px;
}

.threshold-unit {
  font-weight: 500;
  color: var(--text-secondary, #6c757d);
  font-size: 0.9rem;
}

.form-hint {
  display: block;
  margin-top: 4px;
  font-size: 0.875rem;
  color: var(--text-muted, #6c757d);
  line-height: 1.4;
}














</style>