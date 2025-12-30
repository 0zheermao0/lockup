<template>
  <div v-if="isVisible" class="modal-overlay" @click="handleOverlayClick">
    <div class="modal-content" @click.stop>
      <div class="modal-header">
        <h3>{{ isCheckinMode ? '发布打卡动态' : '发布动态' }}</h3>
        <button @click="closeModal" class="close-btn">×</button>
      </div>

      <div class="modal-body">
        <form @submit.prevent="handleSubmit">
          <!-- 动态类型切换 -->
          <div class="post-type-toggle">
            <button
              type="button"
              @click="isCheckinMode = false"
              :class="['type-btn', { active: !isCheckinMode }]"
            >
              📝 普通动态
            </button>
            <button
              type="button"
              @click="isCheckinMode = true"
              :class="['type-btn', { active: isCheckinMode }]"
            >
              📍 打卡动态
            </button>
          </div>

          <!-- 内容输入 -->
          <div class="form-group">
            <label for="content">
              {{ isCheckinMode ? '打卡内容' : '动态内容' }}
            </label>
            <RichTextEditor
              v-model="form.content"
              :placeholder="isCheckinMode ? '分享你的打卡体验...' : '分享你的想法...'"
              :disabled="isLoading"
              :max-length="1000"
              min-height="120px"
            />

            <!-- 严格模式验证码提示 -->
            <div v-if="isCheckinMode" class="verification-code-section">
              <div v-if="loadingStrictTask" class="verification-loading">
                🔄 检查严格模式任务...
              </div>
              <div v-else-if="hasActiveStrictTask" class="verification-code-display">
                <div class="verification-icon">🔒</div>
                <div class="verification-info">
                  <div class="verification-title">严格模式验证码</div>
                  <div class="verification-code">{{ verificationCodeText }}</div>
                  <div class="verification-note">此验证码将自动添加到你的打卡内容中</div>
                </div>
              </div>
              <div v-else class="verification-none">
                <div class="verification-icon">ℹ️</div>
                <div class="verification-info">
                  <div class="verification-note">当前没有活跃的严格模式带锁任务</div>
                </div>
              </div>
            </div>
          </div>

          <!-- 图片上传 -->
          <div class="form-group">
            <label>图片 (可选)</label>
            <div class="image-upload-area">
              <input
                ref="fileInput"
                type="file"
                multiple
                accept="image/*"
                @change="handleImageSelect"
                class="file-input"
                :disabled="isLoading"
              />
              <div @click="triggerFileInput" class="upload-zone">
                <div v-if="selectedImages.length === 0" class="upload-placeholder">
                  📷 点击选择图片
                  <span class="upload-hint">支持多张图片</span>
                </div>
                <div v-else class="selected-images">
                  <div
                    v-for="(image, index) in selectedImages"
                    :key="index"
                    class="image-preview"
                  >
                    <img :src="image.preview" :alt="`图片 ${index + 1}`" />
                    <button
                      type="button"
                      @click.stop="removeImage(index)"
                      class="remove-image"
                    >
                      ×
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>


          <!-- 成功信息 -->
          <div v-if="successMessage" class="success">
            {{ successMessage }}
          </div>

          <!-- 提交按钮 -->
          <div class="form-actions">
            <button
              type="button"
              @click="closeModal"
              class="cancel-btn"
              :disabled="isLoading"
            >
              取消
            </button>
            <button
              type="submit"
              :disabled="isLoading || !form.content.trim()"
              class="submit-btn"
            >
              {{ isLoading ? '发布中...' : '发布' }}
            </button>
          </div>
        </form>
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
import { ref, reactive, watch, computed, onMounted } from 'vue'
import { usePostsStore } from '../stores/posts'
import { useAuthStore } from '../stores/auth'
import { tasksApi } from '../lib/api'
import RichTextEditor from './RichTextEditor.vue'
import NotificationToast from './NotificationToast.vue'
import type { LockTask } from '../types/index'
import { handleApiError, formatErrorForNotification } from '../utils/errorHandling'

interface Props {
  isVisible: boolean
  defaultCheckinMode?: boolean
}

interface Emits {
  (e: 'close'): void
  (e: 'success'): void
}

const props = withDefaults(defineProps<Props>(), {
  defaultCheckinMode: false
})

const emit = defineEmits<Emits>()

const postsStore = usePostsStore()
const authStore = useAuthStore()

// 表单状态
const isCheckinMode = ref(props.defaultCheckinMode)
const isLoading = ref(false)
const successMessage = ref('')

// NotificationToast 状态
const showToast = ref(false)
const toastData = ref({
  type: 'error' as 'success' | 'error' | 'warning' | 'info',
  title: '',
  message: '',
  secondaryMessage: '',
  details: {} as Record<string, any>
})

const form = reactive({
  content: ''
})

// 严格模式任务状态
const activeStrictTask = ref<LockTask | null>(null)
const loadingStrictTask = ref(false)

// 计算属性：是否有活跃的严格模式任务
const hasActiveStrictTask = computed(() => {
  return activeStrictTask.value && activeStrictTask.value.strict_mode && activeStrictTask.value.strict_code
})

// 计算属性：验证码显示文本
const verificationCodeText = computed(() => {
  if (hasActiveStrictTask.value) {
    return `验证码：${activeStrictTask.value?.strict_code}`
  }
  return ''
})

// 图片相关
const fileInput = ref<HTMLInputElement>()
const selectedImages = ref<Array<{ file: File; preview: string }>>([])

// 监听props变化
watch(() => props.isVisible, (visible) => {
  if (visible) {
    resetForm()
    // 如果打开时是打卡模式，获取严格模式任务
    if (isCheckinMode.value) {
      fetchActiveStrictTask()
    }
  }
})

watch(() => props.defaultCheckinMode, (mode) => {
  isCheckinMode.value = mode
})

// 监听打卡模式变化，获取严格模式任务
watch(isCheckinMode, (isCheckin) => {
  if (isCheckin) {
    fetchActiveStrictTask()
  } else {
    activeStrictTask.value = null
  }
})

// 获取活跃的严格模式任务
const fetchActiveStrictTask = async () => {
  if (!authStore.user) return

  try {
    loadingStrictTask.value = true
    const tasks = await tasksApi.getTasksList({
      task_type: 'lock',
      my_tasks: true
    })

    // 查找严格模式的活跃任务（包括pending状态，因为新创建的任务还未开始）
    const strictTask = tasks.find(task =>
      task.task_type === 'lock' &&
      (task.status === 'pending' || task.status === 'active' || task.status === 'voting') &&
      task.strict_mode === true &&
      task.strict_code
    )

    activeStrictTask.value = strictTask || null
  } catch (err) {
    console.error('Error fetching active strict task:', err)
    activeStrictTask.value = null
  } finally {
    loadingStrictTask.value = false
  }
}

const resetForm = () => {
  form.content = ''
  selectedImages.value = []
  successMessage.value = ''
  showToast.value = false
  isCheckinMode.value = props.defaultCheckinMode
  activeStrictTask.value = null
}

const closeModal = () => {
  if (!isLoading.value) {
    emit('close')
  }
}

const handleOverlayClick = () => {
  closeModal()
}

// 图片处理
const triggerFileInput = () => {
  if (!isLoading.value) {
    fileInput.value?.click()
  }
}

const handleImageSelect = (event: Event) => {
  const files = (event.target as HTMLInputElement).files
  if (!files) return

  for (let i = 0; i < files.length; i++) {
    const file = files[i]
    if (!file) continue

    // 验证文件类型
    if (!file.type.startsWith('image/')) {
      showToast.value = true
      const errorData = formatErrorForNotification({
        title: '文件类型不支持',
        message: `不支持 ${file.name} 的文件类型`,
        actionSuggestion: '请选择图片文件（JPG、PNG、GIF等）',
        severity: 'error'
      })
      toastData.value = {
        ...errorData,
        details: {}
      }
      continue
    }

    // 验证文件大小（5MB限制）
    if (file.size > 5 * 1024 * 1024) {
      showToast.value = true
      const errorData = formatErrorForNotification({
        title: '文件过大',
        message: `图片 ${file.name} 超过了5MB大小限制`,
        actionSuggestion: '请压缩图片或选择较小的文件',
        severity: 'error'
      })
      toastData.value = {
        ...errorData,
        details: {}
      }
      continue
    }

    // 检查图片数量限制（最多9张）
    if (selectedImages.value.length >= 9) {
      showToast.value = true
      const errorData = formatErrorForNotification({
        title: '图片数量过多',
        message: '最多只能上传9张图片',
        actionSuggestion: '请删除一些图片后再添加新的',
        severity: 'warning'
      })
      toastData.value = {
        ...errorData,
        details: {}
      }
      break
    }

    const reader = new FileReader()
    reader.onload = (e) => {
      selectedImages.value.push({
        file: file,
        preview: e.target?.result as string
      })
    }
    reader.onerror = () => {
      showToast.value = true
      const errorData = formatErrorForNotification({
        title: '图片读取失败',
        message: `无法读取图片 ${file.name}`,
        actionSuggestion: '请检查文件是否损坏或重新选择',
        severity: 'error'
      })
      toastData.value = {
        ...errorData,
        details: {}
      }
    }
    reader.readAsDataURL(file)
  }

  // 清空input值，允许重复选择同一文件
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

const removeImage = (index: number) => {
  selectedImages.value.splice(index, 1)
}


// 提交处理
const handleSubmit = async () => {
  if (isLoading.value) return

  // 内容验证
  if (!form.content.trim()) {
    showToast.value = true
    const errorData = formatErrorForNotification({
      title: '内容不能为空',
      message: '请输入动态内容',
      actionSuggestion: '请填写动态的具体内容',
      severity: 'error'
    })
    toastData.value = {
      ...errorData,
      details: {}
    }
    return
  }

  // 内容长度验证
  if (form.content.trim().length > 1000) {
    showToast.value = true
    const errorData = formatErrorForNotification({
      title: '内容过长',
      message: '动态内容超过了1000字符的限制',
      actionSuggestion: '请缩短动态内容',
      severity: 'error'
    })
    toastData.value = {
      ...errorData,
      details: {}
    }
    return
  }

  successMessage.value = ''
  showToast.value = false
  isLoading.value = true

  try {
    const postData = {
      content: form.content.trim(),
      post_type: (isCheckinMode.value ? 'checkin' : 'normal') as 'normal' | 'checkin',
      images: selectedImages.value.map(img => img.file)
    }

    await postsStore.createPost(postData)

    // 显示成功消息
    successMessage.value = '发布成功！'
    emit('success')

    // 延迟1.5秒后关闭窗口
    setTimeout(() => {
      if (successMessage.value) { // 确保用户没有重新打开窗口
        closeModal()
      }
    }, 1500)
  } catch (error: any) {
    console.error('Error creating post:', error)

    // 使用新的错误处理工具函数
    const userFriendlyError = handleApiError(error, 'post')
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
    isLoading.value = false
  }
}

// 组件挂载时，如果是打卡模式，获取严格模式任务
onMounted(() => {
  if (isCheckinMode.value) {
    fetchActiveStrictTask()
  }
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 8px;
  border: 2px solid #000;
  box-shadow: 4px 4px 0 #000;
  width: 90%;
  max-width: 600px;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  padding: 1.5rem;
  border-bottom: 2px solid #e9ecef;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h3 {
  margin: 0;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover {
  background-color: #f8f9fa;
  border-radius: 50%;
}

.modal-body {
  padding: 1.5rem;
}

.post-type-toggle {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
}

.type-btn {
  flex: 1;
  padding: 0.75rem;
  border: 2px solid #ddd;
  background: white;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.2s;
}

.type-btn.active {
  border-color: #007bff;
  background-color: #007bff;
  color: white;
}

.type-btn:hover:not(.active) {
  border-color: #007bff;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: #333;
}


.image-upload-area {
  position: relative;
}

.file-input {
  display: none;
}

.upload-zone {
  border: 2px dashed #ddd;
  border-radius: 8px;
  padding: 2rem;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.2s;
}

.upload-zone:hover {
  border-color: #007bff;
}

.upload-placeholder {
  color: #666;
  font-size: 1.1rem;
}

.upload-hint {
  display: block;
  font-size: 0.875rem;
  color: #999;
  margin-top: 0.5rem;
}

.selected-images {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 1rem;
}

.image-preview {
  position: relative;
  aspect-ratio: 1;
  border-radius: 8px;
  overflow: hidden;
  border: 2px solid #ddd;
}

.image-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.remove-image {
  position: absolute;
  top: 4px;
  right: 4px;
  background: rgba(0, 0, 0, 0.7);
  color: white;
  border: none;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
}

.remove-image:hover {
  background: rgba(0, 0, 0, 0.9);
}


.success {
  color: #28a745;
  margin: 1rem 0;
  padding: 0.75rem;
  background-color: #d4edda;
  border: 1px solid #c3e6cb;
  border-radius: 4px;
  font-size: 0.875rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.success::before {
  content: '✅';
  font-size: 1rem;
}


.form-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  margin-top: 2rem;
  padding-top: 1rem;
  border-top: 2px solid #e9ecef;
}

.cancel-btn,
.submit-btn {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 600;
}

.cancel-btn {
  background-color: #6c757d;
  color: white;
}

.cancel-btn:hover:not(:disabled) {
  background-color: #5a6268;
}

.submit-btn {
  background-color: #007bff;
  color: white;
}

.submit-btn:hover:not(:disabled) {
  background-color: #0056b3;
}

.submit-btn:disabled,
.cancel-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 验证码显示样式 */
.verification-code-section {
  margin-top: 0.75rem;
  padding: 0.75rem;
  border: 2px solid #e9ecef;
  border-radius: 6px;
  background: linear-gradient(135deg, #f8f9fa, #e9ecef);
  box-shadow: inset 2px 2px 0 rgba(0, 0, 0, 0.1);
}

.verification-loading,
.verification-code-display,
.verification-none {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.verification-icon {
  font-size: 1.5rem;
  flex-shrink: 0;
}

.verification-info {
  flex: 1;
}

.verification-title {
  font-weight: 700;
  color: #333;
  font-size: 0.9rem;
  margin-bottom: 0.25rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.verification-code {
  font-family: 'Courier New', monospace;
  font-size: 1.1rem;
  font-weight: 800;
  color: #007bff;
  background: white;
  padding: 0.5rem 0.75rem;
  border: 2px solid #000;
  border-radius: 4px;
  box-shadow: 2px 2px 0 #000;
  display: inline-block;
  margin-bottom: 0.5rem;
  letter-spacing: 2px;
}

.verification-note {
  font-size: 0.8rem;
  color: #666;
  font-style: italic;
}

.verification-loading {
  color: #6c757d;
  font-weight: 500;
}

.verification-none {
  color: #6c757d;
}

.verification-none .verification-note {
  color: #6c757d;
  font-style: normal;
}

/* 移动端优化 */
@media (max-width: 768px) {
  .modal-content {
    width: 95%;
    max-height: 95vh;
  }

  .modal-header,
  .modal-body {
    padding: 1rem;
  }

  .post-type-toggle {
    flex-direction: column;
  }

  .selected-images {
    grid-template-columns: repeat(2, 1fr);
  }

  .form-actions {
    flex-direction: column-reverse;
  }

  .cancel-btn,
  .submit-btn {
    width: 100%;
  }
}
</style>