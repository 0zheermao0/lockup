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

          <!-- 位置信息（仅打卡模式） -->
          <div v-if="isCheckinMode" class="form-group">
            <div class="location-section">
              <div class="location-header">
                <label>📍 位置信息</label>
                <button
                  type="button"
                  @click="getCurrentLocation"
                  :disabled="isLoadingLocation || isLoading"
                  class="location-btn"
                >
                  {{ isLoadingLocation ? '获取中...' : '获取当前位置' }}
                </button>
              </div>

              <div v-if="locationError" class="error">
                {{ locationError }}
              </div>

              <div v-if="form.location" class="location-info">
                <div class="coordinates">
                  纬度: {{ form.location.latitude.toFixed(6) }}，
                  经度: {{ form.location.longitude.toFixed(6) }}
                </div>
                <button
                  type="button"
                  @click="clearLocation"
                  class="clear-location"
                >
                  清除位置
                </button>
              </div>
            </div>
          </div>

          <!-- 成功信息 -->
          <div v-if="successMessage" class="success">
            {{ successMessage }}
          </div>

          <!-- 错误信息 -->
          <div v-if="error" class="error">
            {{ error }}
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
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import { usePostsStore } from '../stores/posts'
import RichTextEditor from './RichTextEditor.vue'

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

// 表单状态
const isCheckinMode = ref(props.defaultCheckinMode)
const isLoading = ref(false)
const isLoadingLocation = ref(false)
const error = ref('')
const locationError = ref('')
const successMessage = ref('')

const form = reactive({
  content: '',
  location: null as { latitude: number; longitude: number } | null
})

// 图片相关
const fileInput = ref<HTMLInputElement>()
const selectedImages = ref<Array<{ file: File; preview: string }>>([])

// 监听props变化
watch(() => props.isVisible, (visible) => {
  if (visible) {
    resetForm()
  }
})

watch(() => props.defaultCheckinMode, (mode) => {
  isCheckinMode.value = mode
})

const resetForm = () => {
  form.content = ''
  form.location = null
  selectedImages.value = []
  error.value = ''
  locationError.value = ''
  successMessage.value = ''
  isCheckinMode.value = props.defaultCheckinMode
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
    if (file.type.startsWith('image/')) {
      const reader = new FileReader()
      reader.onload = (e) => {
        selectedImages.value.push({
          file,
          preview: e.target?.result as string
        })
      }
      reader.readAsDataURL(file)
    }
  }

  // 清空input值，允许重复选择同一文件
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

const removeImage = (index: number) => {
  selectedImages.value.splice(index, 1)
}

// 位置处理
const getCurrentLocation = () => {
  if (!navigator.geolocation) {
    locationError.value = '浏览器不支持地理位置'
    return
  }

  isLoadingLocation.value = true
  locationError.value = ''

  navigator.geolocation.getCurrentPosition(
    (position) => {
      form.location = {
        latitude: position.coords.latitude,
        longitude: position.coords.longitude
      }
      isLoadingLocation.value = false
    },
    (error) => {
      isLoadingLocation.value = false
      switch (error.code) {
        case error.PERMISSION_DENIED:
          locationError.value = '位置访问被拒绝'
          break
        case error.POSITION_UNAVAILABLE:
          locationError.value = '位置信息不可用'
          break
        case error.TIMEOUT:
          locationError.value = '获取位置超时'
          break
        default:
          locationError.value = '获取位置失败'
          break
      }
    },
    {
      enableHighAccuracy: true,
      timeout: 10000,
      maximumAge: 300000 // 5分钟缓存
    }
  )
}

const clearLocation = () => {
  form.location = null
  locationError.value = ''
}

// 提交处理
const handleSubmit = async () => {
  if (isLoading.value || !form.content.trim()) return

  error.value = ''
  successMessage.value = ''
  isLoading.value = true

  try {
    const postData = {
      content: form.content.trim(),
      post_type: isCheckinMode.value ? 'checkin' : 'normal',
      images: selectedImages.value.map(img => img.file),
      location: form.location
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
  } catch (err: any) {
    error.value = err.response?.data?.message || err.message || '发布失败'
  } finally {
    isLoading.value = false
  }
}
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

.location-section {
  border: 2px solid #e9ecef;
  border-radius: 8px;
  padding: 1rem;
}

.location-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.location-header label {
  margin: 0;
}

.location-btn {
  padding: 0.5rem 1rem;
  background-color: #28a745;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.875rem;
}

.location-btn:hover:not(:disabled) {
  background-color: #218838;
}

.location-btn:disabled {
  background-color: #6c757d;
  cursor: not-allowed;
}

.location-info {
  background-color: #f8f9fa;
  padding: 1rem;
  border-radius: 4px;
  border: 1px solid #e9ecef;
}

.coordinates {
  font-family: monospace;
  font-size: 0.875rem;
  margin-bottom: 0.5rem;
}

.clear-location {
  background: none;
  border: none;
  color: #dc3545;
  cursor: pointer;
  font-size: 0.875rem;
  text-decoration: underline;
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

.error {
  color: #dc3545;
  margin: 1rem 0;
  padding: 0.75rem;
  background-color: #f8d7da;
  border: 1px solid #f5c6cb;
  border-radius: 4px;
  font-size: 0.875rem;
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

  .location-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
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