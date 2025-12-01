<template>
  <div v-if="isVisible" class="modal-overlay" @click="handleOverlayClick">
    <div class="modal-content" @click.stop>
      <div class="modal-header">
        <h3>📤 提交任务完成证明</h3>
        <button @click="closeModal" class="close-btn">×</button>
      </div>

      <div class="modal-body">
        <form @submit.prevent="handleSubmit">
          <!-- Task Info Display -->
          <div v-if="task" class="task-info-section">
            <div class="task-summary">
              <h4 class="task-title">{{ task.title }}</h4>
              <div class="task-meta">
                <span class="task-difficulty" :class="task.difficulty">
                  {{ getDifficultyText(task.difficulty) }}
                </span>
                <span class="task-status" :class="task.status">
                  {{ getStatusText(task.status) }}
                </span>
              </div>
            </div>
          </div>

          <!-- Rich Text Content Input -->
          <div class="form-group">
            <label for="completion_proof">
              <span class="required">*</span> 完成证明
            </label>
            <RichTextEditor
              v-model="form.content"
              placeholder="详细描述你的任务完成情况，可以使用上方工具栏进行格式化..."
              :disabled="isLoading"
              :max-length="2000"
              min-height="150px"
            />
          </div>

          <!-- Photo Upload Section -->
          <div class="form-group">
            <label>📷 证明照片 (可选)</label>
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
                  📷 点击选择照片
                  <span class="upload-hint">支持多张照片，为你的证明添加视觉支持</span>
                </div>
                <div v-else class="selected-images">
                  <div
                    v-for="(image, index) in selectedImages"
                    :key="index"
                    class="image-preview"
                  >
                    <img :src="image.preview" :alt="`证明照片 ${index + 1}`" />
                    <button
                      type="button"
                      @click.stop="removeImage(index)"
                      class="remove-image"
                      title="删除照片"
                    >
                      ×
                    </button>
                  </div>
                  <div @click="triggerFileInput" class="add-more-photos">
                    <span>+</span>
                    <span class="add-text">添加更多</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Preview Section -->
          <div v-if="form.content || selectedImages.length > 0" class="preview-section">
            <h4>📋 提交预览</h4>
            <div class="preview-container">
              <div v-if="form.content" class="preview-content">
                <h5>完成证明:</h5>
                <div class="preview-text" v-html="form.content"></div>
              </div>
              <div v-if="selectedImages.length > 0" class="preview-images">
                <h5>附件照片 ({{ selectedImages.length }}张):</h5>
                <div class="preview-image-grid">
                  <div
                    v-for="(image, index) in selectedImages"
                    :key="index"
                    class="preview-image-item"
                  >
                    <img :src="image.preview" :alt="`预览 ${index + 1}`" />
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Submission Guidelines -->
          <div class="guidelines-section">
            <h4>✅ 提交指南</h4>
            <ul class="guidelines-list">
              <li>详细描述你的完成过程和结果</li>
              <li>上传相关的证明照片（可选但推荐）</li>
              <li>确保内容真实可靠，审核者会仔细查看</li>
              <li>避免提交无关或虚假信息</li>
            </ul>
          </div>

          <!-- Success/Error Messages -->
          <div v-if="successMessage" class="success">
            {{ successMessage }}
          </div>

          <div v-if="error" class="error">
            {{ error }}
          </div>

          <!-- Form Actions -->
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
              {{ isLoading ? '提交中...' : '提交证明' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import { tasksApi } from '../lib/api'
import RichTextEditor from './RichTextEditor.vue'
import type { LockTask } from '../types/index.js'

interface Props {
  isVisible: boolean
  task: LockTask | null
}

interface Emits {
  (e: 'close'): void
  (e: 'success'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// Form state
const isLoading = ref(false)
const error = ref('')
const successMessage = ref('')

const form = reactive({
  content: ''
})


// Image upload state
const fileInput = ref<HTMLInputElement>()
const selectedImages = ref<Array<{ file: File; preview: string }>>([])


// Watch for visibility changes
watch(() => props.isVisible, (visible) => {
  if (visible) {
    resetForm()
  }
})

const resetForm = () => {
  form.content = ''
  selectedImages.value = []
  error.value = ''
  successMessage.value = ''
}

const closeModal = () => {
  if (!isLoading.value) {
    emit('close')
  }
}

const handleOverlayClick = () => {
  closeModal()
}


// Image handling
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
    if (file && file.type.startsWith('image/')) {
      const reader = new FileReader()
      reader.onload = (e) => {
        selectedImages.value.push({
          file: file,
          preview: e.target?.result as string
        })
      }
      reader.readAsDataURL(file)
    }
  }

  // Clear input value to allow selecting same file again
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

const removeImage = (index: number) => {
  selectedImages.value.splice(index, 1)
}

// Form submission
const handleSubmit = async () => {
  if (isLoading.value || !form.content.trim() || !props.task) return

  // Character limit check - compute content length here
  const tempDiv = document.createElement('div')
  tempDiv.innerHTML = form.content
  const contentLength = tempDiv.textContent?.length || 0

  if (contentLength > 2000) {
    error.value = '内容超过2000字符限制'
    return
  }

  error.value = ''
  successMessage.value = ''
  isLoading.value = true

  try {
    // Convert HTML content to text for API submission
    // In a real implementation, you might want to send the HTML
    // or convert to markdown format
    const tempDiv = document.createElement('div')
    tempDiv.innerHTML = form.content
    const textContent = tempDiv.textContent || tempDiv.innerText || ''

    await tasksApi.submitTask(props.task.id, textContent)

    // TODO: In a real implementation, you would also upload images
    // This would require additional API endpoints for file upload
    if (selectedImages.value.length > 0) {
      // Simulate image upload
      console.log('Would upload images:', selectedImages.value.map(img => img.file.name))
    }

    successMessage.value = '提交成功！等待审核...'
    emit('success')

    // Auto-close after delay
    setTimeout(() => {
      if (successMessage.value) {
        closeModal()
      }
    }, 2000)

  } catch (err: any) {
    error.value = err.response?.data?.error || err.message || '提交失败，请重试'
  } finally {
    isLoading.value = false
  }
}

// Helper functions
const getDifficultyText = (difficulty: string) => {
  const texts = {
    easy: '简单',
    normal: '普通',
    hard: '困难',
    hell: '地狱'
  }
  return texts[difficulty as keyof typeof texts] || difficulty
}

const getStatusText = (status: string) => {
  const texts = {
    pending: '待开始',
    active: '进行中',
    completed: '已完成',
    failed: '已失败',
    open: '开放中',
    taken: '已接取',
    submitted: '已提交'
  }
  return texts[status as keyof typeof texts] || status
}
</script>

<style scoped>
/* Neo-Brutalism Modal Design */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.2s ease-out;
}

.modal-content {
  background: white;
  border: 4px solid #000;
  max-width: 800px;
  width: 90%;
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

.modal-header h3 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
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

/* Task Info Section */
.task-info-section {
  background: #f8f9fa;
  border: 3px solid #000;
  padding: 1.5rem;
  margin-bottom: 2rem;
  box-shadow: 6px 6px 0 #000;
  transform: rotate(-0.5deg);
}

.task-summary {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
}

.task-title {
  font-size: 1.2rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0;
  color: #000;
}

.task-meta {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.task-difficulty, .task-status {
  padding: 0.25rem 0.75rem;
  border: 2px solid #000;
  font-size: 0.875rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  box-shadow: 2px 2px 0 #000;
}

.task-difficulty.easy { background: #28a745; color: white; }
.task-difficulty.normal { background: #ffc107; color: #000; }
.task-difficulty.hard { background: #fd7e14; color: white; }
.task-difficulty.hell { background: #dc3545; color: white; }

.task-status.taken { background: #6f42c1; color: white; }

/* Form Styling */
.form-group {
  margin-bottom: 2rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.75rem;
  font-weight: 900;
  color: #000;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  font-size: 0.875rem;
}

.required {
  color: #dc3545;
  font-weight: 900;
}


/* Image Upload */
.image-upload-area {
  position: relative;
}

.file-input {
  display: none;
}

.upload-zone {
  border: 3px dashed #000;
  background: white;
  padding: 2rem;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 4px 4px 0 #000;
}

.upload-zone:hover {
  background: #f8f9fa;
  transform: translate(-1px, -1px);
  box-shadow: 5px 5px 0 #000;
}

.upload-placeholder {
  color: #666;
  font-size: 1.1rem;
  font-weight: 700;
}

.upload-hint {
  display: block;
  font-size: 0.875rem;
  color: #999;
  margin-top: 0.5rem;
  font-weight: 400;
}

.selected-images {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 1rem;
}

.image-preview {
  position: relative;
  aspect-ratio: 1;
  border: 3px solid #000;
  overflow: hidden;
  box-shadow: 3px 3px 0 #000;
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
  background: #dc3545;
  color: white;
  border: 2px solid #000;
  border-radius: 50%;
  width: 28px;
  height: 28px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 900;
  box-shadow: 2px 2px 0 #000;
}

.remove-image:hover {
  background: #c82333;
  transform: translate(-1px, -1px);
  box-shadow: 3px 3px 0 #000;
}

.add-more-photos {
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

.add-more-photos:hover {
  background: #e9ecef;
  color: #000;
}

.add-more-photos span:first-child {
  font-size: 2rem;
  line-height: 1;
}

.add-text {
  font-size: 0.75rem;
  margin-top: 0.25rem;
}

/* Preview Section */
.preview-section {
  background: #e7f3ff;
  border: 3px solid #000;
  padding: 1.5rem;
  margin-bottom: 2rem;
  box-shadow: 6px 6px 0 #000;
  transform: rotate(0.5deg);
}

.preview-section h4 {
  font-size: 1.2rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 1rem 0;
  color: #000;
}

.preview-container {
  background: white;
  border: 2px solid #000;
  padding: 1rem;
  box-shadow: 3px 3px 0 #000;
}

.preview-content h5,
.preview-images h5 {
  font-size: 0.875rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 0 0 0.75rem 0;
  color: #666;
}

.preview-text {
  line-height: 1.6;
  margin-bottom: 1rem;
}

/* Rich text preview styling */
.preview-text h1,
.preview-text h2,
.preview-text h3 {
  margin: 0.5rem 0;
  font-weight: 900;
}

.preview-text ul {
  margin: 0.5rem 0;
  padding-left: 2rem;
}

.preview-text li {
  margin: 0.25rem 0;
}

.preview-text strong {
  font-weight: 900;
}

.preview-text em {
  font-style: italic;
}

.preview-image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
  gap: 0.5rem;
}

.preview-image-item {
  aspect-ratio: 1;
  border: 2px solid #000;
  overflow: hidden;
  box-shadow: 2px 2px 0 #000;
}

.preview-image-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* Guidelines Section */
.guidelines-section {
  background: #fff3cd;
  border: 3px solid #000;
  padding: 1.5rem;
  margin-bottom: 2rem;
  box-shadow: 6px 6px 0 #000;
  transform: rotate(-0.5deg);
}

.guidelines-section h4 {
  font-size: 1.2rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 1rem 0;
  color: #000;
}

.guidelines-list {
  margin: 0;
  padding-left: 1.5rem;
  list-style: none;
}

.guidelines-list li {
  position: relative;
  margin-bottom: 0.5rem;
  font-weight: 500;
  line-height: 1.5;
}

.guidelines-list li::before {
  content: '✓';
  position: absolute;
  left: -1.5rem;
  color: #28a745;
  font-weight: 900;
}

/* Success/Error Messages */
.success {
  background: #d4edda;
  color: #155724;
  border: 3px solid #28a745;
  padding: 1rem;
  margin: 1rem 0;
  font-weight: 700;
  box-shadow: 4px 4px 0 #28a745;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.success::before {
  content: '✅';
  font-size: 1.2rem;
}

.error {
  background: #f8d7da;
  color: #721c24;
  border: 3px solid #dc3545;
  padding: 1rem;
  margin: 1rem 0;
  font-weight: 700;
  box-shadow: 4px 4px 0 #dc3545;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.error::before {
  content: '❌';
  font-size: 1.2rem;
}

/* Form Actions */
.form-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 3px solid #000;
}

.cancel-btn,
.submit-btn {
  padding: 0.75rem 2rem;
  border: 3px solid #000;
  cursor: pointer;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  font-size: 1rem;
  box-shadow: 4px 4px 0 #000;
  transition: all 0.2s ease;
}

.cancel-btn {
  background: #6c757d;
  color: white;
}

.cancel-btn:hover:not(:disabled) {
  background: #5a6268;
  transform: translate(-1px, -1px);
  box-shadow: 5px 5px 0 #000;
}

.submit-btn {
  background: #28a745;
  color: white;
}

.submit-btn:hover:not(:disabled) {
  background: #218838;
  transform: translate(-1px, -1px);
  box-shadow: 5px 5px 0 #000;
}

.submit-btn:disabled,
.cancel-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
  box-shadow: 4px 4px 0 #000;
}

/* Animations */
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
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

/* Mobile Responsive */
@media (max-width: 768px) {
  .modal-content {
    width: 95%;
    max-height: 95vh;
    transform: none;
  }

  .modal-header,
  .modal-body {
    padding: 1rem;
    transform: none;
  }

  .task-summary {
    flex-direction: column;
    align-items: flex-start;
  }

  .toolbar {
    padding: 0.5rem;
  }

  .toolbar-btn {
    min-width: 30px;
    min-height: 30px;
    font-size: 0.875rem;
  }

  .selected-images {
    grid-template-columns: repeat(2, 1fr);
  }

  .preview-image-grid {
    grid-template-columns: repeat(3, 1fr);
  }

  .form-actions {
    flex-direction: column-reverse;
  }

  .cancel-btn,
  .submit-btn {
    width: 100%;
  }

  .task-info-section,
  .preview-section,
  .guidelines-section {
    transform: none;
  }
}
</style>