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
              :max-length="1500"
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
            <label>图片 <span class="image-count">{{ selectedImages.length }}/9</span></label>
            <div class="image-upload-area">
              <!-- Hidden file inputs -->
              <input
                ref="fileInput"
                type="file"
                multiple
                accept="image/*"
                @change="handleImageSelect"
                class="file-input"
                :disabled="isLoading"
              />
              <input
                ref="cameraInput"
                type="file"
                accept="image/*"
                capture="environment"
                @change="handleImageSelect"
                class="file-input"
                :disabled="isLoading"
              />

              <!-- Upload Zone -->
              <div v-if="selectedImages.length === 0" class="upload-zone-empty">
                <div class="upload-options">
                  <button
                    type="button"
                    @click="openCamera"
                    class="upload-option-btn camera-btn"
                    :disabled="isLoading"
                  >
                    <span class="option-icon">📷</span>
                    <span class="option-label">拍照</span>
                  </button>
                  <div class="option-divider"></div>
                  <button
                    type="button"
                    @click="openGallery"
                    class="upload-option-btn gallery-btn"
                    :disabled="isLoading"
                  >
                    <span class="option-icon">🖼️</span>
                    <span class="option-label">相册</span>
                  </button>
                </div>
                <span class="upload-hint">最多9张，每张不超过2.5MB</span>
              </div>

              <!-- Image Grid with Add Button -->
              <div v-else class="image-grid-container">
                <div class="selected-images">
                  <div
                    v-for="(image, index) in selectedImages"
                    :key="index"
                    class="image-preview"
                    :style="{ animationDelay: `${index * 0.05}s` }"
                  >
                    <img :src="image.preview" :alt="`图片 ${index + 1}`" />
                    <button
                      type="button"
                      @click="removeImage(index)"
                      class="remove-image"
                      :disabled="isLoading"
                    >
                      ×
                    </button>
                  </div>
                  <!-- Add More Button -->
                  <button
                    v-if="selectedImages.length < 9"
                    type="button"
                    @click="showImageSourceOptions"
                    class="add-more-btn"
                    :disabled="isLoading"
                  >
                    <span class="add-icon">+</span>
                    <span class="add-label">添加</span>
                  </button>
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

    <!-- Image Source Action Sheet -->
    <Transition name="slide-up">
      <div v-if="showImageSourceSheet" class="action-sheet-overlay" @click="showImageSourceSheet = false">
        <div class="action-sheet" @click.stop>
          <div class="action-sheet-header">
            <span>选择图片来源</span>
          </div>
          <button
            type="button"
            @click="selectCameraSource"
            class="action-sheet-btn primary"
          >
            <span class="btn-icon">📷</span>
            <span>拍照</span>
          </button>
          <button
            type="button"
            @click="selectGallerySource"
            class="action-sheet-btn primary"
          >
            <span class="btn-icon">🖼️</span>
            <span>从相册选择</span>
          </button>
          <div class="action-sheet-divider"></div>
          <button
            type="button"
            @click="showImageSourceSheet = false"
            class="action-sheet-btn cancel"
          >
            取消
          </button>
        </div>
      </div>
    </Transition>

    <!-- Camera Modal -->
    <CameraModal
      v-if="showCameraModal"
      :max-size="cameraMaxSize"
      :title="isCheckinMode ? '拍照打卡' : '拍照'"
      @click.stop
      @close="showCameraModal = false"
      @capture="handleCameraCapture"
    />

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
import { ref, reactive, watch, computed, onMounted, onUnmounted } from 'vue'
import { usePostsStore } from '../stores/posts'
import { useAuthStore } from '../stores/auth'
import { tasksApi } from '../lib/api'
import RichTextEditor from './RichTextEditor.vue'
import NotificationToast from './NotificationToast.vue'
import CameraModal from './CameraModal.vue'
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
const cameraInput = ref<HTMLInputElement>()
const selectedImages = ref<Array<{ file: File; preview: string }>>([])
const showImageSourceSheet = ref(false)
const showCameraModal = ref(false)
const cameraMaxSize = 2.5 * 1024 * 1024 // 2.5MB

// 监听props变化
watch(() => props.isVisible, (visible) => {
  if (visible) {
    resetForm()
    // 禁用body滚动
    document.body.style.overflow = 'hidden'
    // 如果打开时是打卡模式，获取严格模式任务
    if (isCheckinMode.value) {
      fetchActiveStrictTask()
    }
  } else {
    // 恢复body滚动
    document.body.style.overflow = ''
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
  showImageSourceSheet.value = false
  showCameraModal.value = false
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

// 图片处理 - 图片来源选择
const showImageSourceOptions = () => {
  if (isLoading.value || selectedImages.value.length >= 9) return
  showImageSourceSheet.value = true
}

const selectCameraSource = () => {
  showImageSourceSheet.value = false
  // Small delay to allow sheet to close before opening camera
  setTimeout(() => {
    openCamera()
  }, 100)
}

const selectGallerySource = () => {
  showImageSourceSheet.value = false
  // Small delay to allow sheet to close before opening gallery
  setTimeout(() => {
    openGallery()
  }, 100)
}

const openCamera = () => {
  if (isLoading.value || selectedImages.value.length >= 9) return

  // Check if we're on a mobile device with camera support
  const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent)

  if (isMobile && cameraInput.value) {
    // Use native camera capture on mobile
    cameraInput.value.click()
  } else {
    // Use CameraModal on desktop or as fallback
    showCameraModal.value = true
  }
}

const openGallery = () => {
  if (!isLoading.value && fileInput.value) {
    fileInput.value.click()
  }
}

const handleCameraCapture = (file: File) => {
  // Check image count limit
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
    return
  }

  // Validate file size
  if (file.size > cameraMaxSize) {
    showToast.value = true
    const errorData = formatErrorForNotification({
      title: '文件过大',
      message: '图片超过了2.5MB大小限制',
      actionSuggestion: '请压缩图片或选择较小的文件',
      severity: 'error'
    })
    toastData.value = {
      ...errorData,
      details: {}
    }
    return
  }

  // Create preview and add to selected images
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
      message: '无法读取拍摄的图片',
      actionSuggestion: '请检查文件是否损坏或重新拍摄',
      severity: 'error'
    })
    toastData.value = {
      ...errorData,
      details: {}
    }
  }
  reader.readAsDataURL(file)
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

    // 验证文件大小（2.5MB限制）
    if (file.size > 2.5 * 1024 * 1024) {
      showToast.value = true
      const errorData = formatErrorForNotification({
        title: '文件过大',
        message: `图片 ${file.name} 超过了2.5MB大小限制`,
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

  // 内容长度验证（去除HTML标签后统计纯文本长度）
  const tempDiv = document.createElement('div')
  tempDiv.innerHTML = form.content
  const textContent = tempDiv.textContent || ''
  if (textContent.trim().length > 1500) {
    showToast.value = true
    const errorData = formatErrorForNotification({
      title: '内容过长',
      message: '动态内容超过了1500字符的限制',
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
  background-color: rgba(0, 0, 0, 0.5);
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

/* Image count label */
.image-count {
  font-size: 0.875rem;
  color: #666;
  font-weight: 500;
  margin-left: 0.5rem;
}

/* Empty upload zone with dual options */
.upload-zone-empty {
  border: 2px dashed #ddd;
  border-radius: 8px;
  padding: 1.5rem;
  text-align: center;
  transition: all 0.2s ease;
}

.upload-zone-empty:hover {
  border-color: #007bff;
  background-color: #f8f9fa;
}

.upload-options {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0;
  margin-bottom: 0.75rem;
}

.upload-option-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem 2rem;
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all 0.2s ease;
  min-width: 100px;
}

.upload-option-btn:hover:not(:disabled) {
  transform: scale(1.05);
}

.upload-option-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.option-icon {
  font-size: 2rem;
  line-height: 1;
}

.option-label {
  font-size: 0.875rem;
  color: #333;
  font-weight: 500;
}

.option-divider {
  width: 1px;
  height: 48px;
  background: #ddd;
}

.upload-hint {
  display: block;
  font-size: 0.75rem;
  color: #999;
}

/* Image grid container */
.image-grid-container {
  padding: 0.5rem 0;
}

.selected-images {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: 0.75rem;
}

.image-preview {
  position: relative;
  aspect-ratio: 1;
  border-radius: 8px;
  overflow: hidden;
  border: 2px solid #ddd;
  animation: fadeInScale 0.3s ease-out forwards;
  opacity: 0;
  transform: scale(0.9);
}

@keyframes fadeInScale {
  to {
    opacity: 1;
    transform: scale(1);
  }
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
  transition: all 0.2s ease;
}

.remove-image:hover:not(:disabled) {
  background: rgba(0, 0, 0, 0.9);
  transform: scale(1.1);
}

.remove-image:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Add more button */
.add-more-btn {
  aspect-ratio: 1;
  border-radius: 8px;
  border: 2px dashed #ddd;
  background: transparent;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.25rem;
  transition: all 0.2s ease;
  min-height: 100px;
}

.add-more-btn:hover:not(:disabled) {
  border-color: #007bff;
  background-color: #f8f9fa;
  transform: scale(1.02);
}

.add-more-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.add-icon {
  font-size: 1.5rem;
  color: #666;
  line-height: 1;
}

.add-label {
  font-size: 0.75rem;
  color: #666;
}

/* Action Sheet */
.action-sheet-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  z-index: 1100;
  backdrop-filter: blur(2px);
}

.action-sheet {
  background: white;
  width: 100%;
  max-width: 500px;
  border-radius: 16px 16px 0 0;
  padding: 0.5rem;
  margin: 0 auto;
  box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.15);
}

.action-sheet-header {
  text-align: center;
  padding: 1rem;
  font-size: 0.875rem;
  color: #666;
  font-weight: 500;
}

.action-sheet-btn {
  width: 100%;
  padding: 1rem;
  border: none;
  background: transparent;
  font-size: 1rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  border-radius: 8px;
  transition: background 0.2s ease;
  min-height: 56px;
}

.action-sheet-btn:hover {
  background: #f8f9fa;
}

.action-sheet-btn.primary {
  color: #007bff;
  font-weight: 500;
}

.action-sheet-btn.cancel {
  color: #666;
  font-weight: 500;
}

.action-sheet-divider {
  height: 8px;
  background: #f8f9fa;
  margin: 0.25rem -0.5rem;
  border-top: 1px solid #e9ecef;
  border-bottom: 1px solid #e9ecef;
}

.btn-icon {
  font-size: 1.25rem;
}

/* Slide-up transition */
.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.3s ease-out;
}

.slide-up-enter-from,
.slide-up-leave-to {
  opacity: 0;
}

.slide-up-enter-from .action-sheet,
.slide-up-leave-to .action-sheet {
  transform: translateY(100%);
}

.slide-up-enter-active .action-sheet,
.slide-up-leave-active .action-sheet {
  transition: transform 0.3s ease-out;
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
  .modal-overlay {
    padding-top: 3vh;
    padding-bottom: 3vh;
  }

  .modal-content {
    width: 95%;
    max-height: 94vh;
  }

  .modal-header,
  .modal-body {
    padding: 1rem;
  }

  .post-type-toggle {
    flex-direction: column;
  }

  .upload-options {
    gap: 0.5rem;
  }

  .upload-option-btn {
    padding: 0.75rem 1.5rem;
    min-width: 80px;
  }

  .option-icon {
    font-size: 1.75rem;
  }

  .selected-images {
    grid-template-columns: repeat(3, 1fr);
    gap: 0.5rem;
  }

  .image-preview {
    min-height: 80px;
  }

  .add-more-btn {
    min-height: 80px;
  }

  .remove-image {
    width: 20px;
    height: 20px;
    font-size: 12px;
  }

  .action-sheet {
    max-width: 100%;
  }

  .form-actions {
    flex-direction: column-reverse;
  }

  .cancel-btn,
  .submit-btn {
    width: 100%;
  }
}

/* Small mobile screens */
@media (max-width: 360px) {
  .selected-images {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>