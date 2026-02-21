<template>
  <div v-if="isVisible" class="modal-overlay" @click="closeModal">
    <div class="modal-content" @click.stop>
      <!-- Header -->
      <div class="modal-header">
        <h2>分享任务</h2>
        <button @click="closeModal" class="close-btn">×</button>
      </div>

      <!-- Content -->
      <div class="modal-body">
        <!-- URL Display -->
        <div class="url-section">
          <label class="section-label">任务链接</label>
          <div class="url-container">
            <input
              ref="urlInput"
              :value="shareUrl"
              readonly
              class="url-input"
              @focus="($event.target as HTMLInputElement)?.select()"
            />
            <button @click="copyUrl" class="copy-btn" :class="{ copied: copySuccess }">
              {{ copySuccess ? '✓ 已复制' : '📋 复制' }}
            </button>
          </div>
        </div>

        <!-- Share Options -->
        <div class="share-section">
          <label class="section-label">分享到</label>
          <div class="share-buttons">
            <button @click="shareToX" class="share-btn x-btn">
              <span class="share-icon">𝕏</span>
              <span class="share-text">分享到 X</span>
            </button>

            <button @click="shareToTelegram" class="share-btn telegram-btn">
              <span class="share-icon">📱</span>
              <span class="share-text">分享到 Telegram</span>
            </button>

            <!-- Telegram Bot sharing for lock tasks -->
            <button
              v-if="canShareToTelegramBot"
              @click="shareToTelegramBot"
              class="share-btn telegram-bot-btn"
              title="分享到 Telegram Bot，朋友可以直接点击按钮为任务加时"
            >
              <span class="share-icon">🤖</span>
              <span class="share-text">Telegram Bot 加时分享</span>
            </button>
          </div>
        </div>

        <!-- Task Preview -->
        <div class="task-preview">
          <label class="section-label">任务预览</label>
          <div class="preview-content">
            <div class="preview-title">{{ taskTitle }}</div>
            <div class="preview-type">{{ taskTypeText }}</div>
            <div v-if="taskDescription" class="preview-description">
              {{ truncateText(taskDescription, 100) }}
            </div>
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div class="modal-footer">
        <button @click="closeModal" class="cancel-btn">关闭</button>
      </div>
    </div>

    <!-- Success Toast -->
    <div v-if="showToast" class="toast">
      {{ toastMessage }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'
import { useAuthStore } from '../stores/auth'
import { telegramApi } from '../lib/api-telegram'

interface Props {
  isVisible: boolean
  shareUrl: string
  taskTitle: string
  taskType: string
  taskDescription?: string
  taskId?: string
  taskStatus?: string
}

interface Emits {
  (e: 'close'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const authStore = useAuthStore()

const urlInput = ref<HTMLInputElement>()
const copySuccess = ref(false)
const showToast = ref(false)
const toastMessage = ref('')

const taskTypeText = computed(() => {
  const typeMap: Record<string, string> = {
    lock: '🔒 带锁任务',
    board: '📋 任务板'
  }
  return typeMap[props.taskType] || props.taskType
})

// Check if this is a shareable lock task (active or voting)
// Now supports sharing others' tasks too
const canShareToTelegramBot = computed(() => {
  return props.taskType === 'lock' &&
         props.taskId &&
         props.taskStatus &&
         ['active', 'voting'].includes(props.taskStatus) &&
         authStore.isAuthenticated
})

// Bot username for generating deeplinks
const BOT_USERNAME = 'lock_up_bot'

// Check if user is the task owner
const isOwnTask = computed(() => {
  // This would need to be passed from parent component or determined from task data
  return true // For now, assume user can share their own tasks
})

const closeModal = () => {
  copySuccess.value = false
  emit('close')
}

const copyUrl = async () => {
  try {
    await navigator.clipboard.writeText(props.shareUrl)
    copySuccess.value = true
    showToast.value = true
    toastMessage.value = '链接已复制到剪贴板！'

    // Auto-hide copy success state
    setTimeout(() => {
      copySuccess.value = false
    }, 2000)

    // Auto-hide toast
    setTimeout(() => {
      showToast.value = false
    }, 3000)
  } catch (error) {
    console.error('Failed to copy URL:', error)
    // Fallback: select the text for manual copy
    urlInput.value?.select()
    urlInput.value?.setSelectionRange(0, 99999) // For mobile devices

    showToast.value = true
    toastMessage.value = '请手动复制链接'
    setTimeout(() => {
      showToast.value = false
    }, 3000)
  }
}

const shareToX = () => {
  const text = `查看这个${taskTypeText.value}：${props.taskTitle}`
  const url = props.shareUrl
  const tweetText = encodeURIComponent(`${text}\n\n${url}`)
  const xUrl = `https://x.com/intent/tweet?text=${tweetText}`

  window.open(xUrl, '_blank', 'width=600,height=400')

  showToast.value = true
  toastMessage.value = '正在打开 X 分享页面...'
  setTimeout(() => {
    showToast.value = false
  }, 3000)
}

const shareToTelegram = () => {
  const text = `查看这个${taskTypeText.value}：${props.taskTitle}`
  const url = props.shareUrl
  const shareText = encodeURIComponent(`${text}\n\n${url}`)
  const telegramUrl = `https://t.me/share/url?url=${encodeURIComponent(url)}&text=${encodeURIComponent(text)}`

  window.open(telegramUrl, '_blank', 'width=600,height=400')

  showToast.value = true
  toastMessage.value = '正在打开 Telegram 分享页面...'
  setTimeout(() => {
    showToast.value = false
  }, 3000)
}

const shareToTelegramBot = async () => {
  if (!props.taskId || !canShareToTelegramBot.value) {
    showToast.value = true
    toastMessage.value = '无法分享此任务到 Telegram Bot'
    setTimeout(() => {
      showToast.value = false
    }, 3000)
    return
  }

  try {
    showToast.value = true
    toastMessage.value = '正在打开 Telegram...'

    // Get share data from API (for message text and callback data)
    const shareResult = await telegramApi.shareTaskToTelegram(props.taskId)
    const shareData = shareResult.share_data

    // Build deeplink with startgroup parameter
    // This allows user to select a group/user to share to
    // Format: https://t.me/{bot_username}?startgroup={task_id}
    const deeplinkUrl = `https://t.me/${BOT_USERNAME}?startgroup=${props.taskId}`

    // Open Telegram with the deeplink
    window.open(deeplinkUrl, '_blank')

    toastMessage.value = '请选择要分享到的聊天'
    setTimeout(() => {
      showToast.value = false
      emit('close') // Close the modal after opening Telegram
    }, 2000)

  } catch (error: any) {
    console.error('Error sharing to Telegram Bot:', error)

    let errorMessage = '分享到 Telegram Bot 失败'
    if (error.data?.error) {
      errorMessage = error.data.error
    } else if (error.status === 404) {
      errorMessage = '任务不存在'
    } else if (error.status === 400) {
      errorMessage = '只能分享进行中的带锁任务'
    }

    toastMessage.value = `❌ ${errorMessage}`
    setTimeout(() => {
      showToast.value = false
    }, 4000)
  }
}

const truncateText = (text: string, maxLength: number): string => {
  if (text.length <= maxLength) return text
  return text.slice(0, maxLength) + '...'
}
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
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

.modal-content {
  background: white;
  border-radius: 8px;
  border: 4px solid #000;
  box-shadow: 12px 12px 0 #000;
  width: 100%;
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
  position: relative;
  transform: translateY(0);
  animation: modalSlideIn 0.3s ease-out;
}

@keyframes modalSlideIn {
  from {
    transform: translateY(-20px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 4px solid #000;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
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
  border: 3px solid white;
  color: white;
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0.5rem;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  font-weight: 900;
}

.close-btn:hover {
  background: white;
  color: #667eea;
  transform: rotate(90deg);
}

.modal-body {
  padding: 2rem;
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.section-label {
  display: block;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 1rem;
  color: #333;
  font-size: 0.875rem;
}

.url-section {
  display: flex;
  flex-direction: column;
}

.url-container {
  display: flex;
  gap: 0.75rem;
  align-items: stretch;
}

.url-input {
  flex: 1;
  padding: 1rem;
  border: 3px solid #000;
  border-radius: 6px;
  font-size: 0.875rem;
  font-family: 'Monaco', 'Menlo', monospace;
  background: #f8f9fa;
  color: #333;
  cursor: pointer;
}

.url-input:focus {
  outline: none;
  background: white;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.3);
}

.copy-btn {
  padding: 1rem 1.5rem;
  border: 3px solid #000;
  border-radius: 6px;
  background: #28a745;
  color: white;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
  font-size: 0.875rem;
}

.copy-btn:hover {
  background: #218838;
  transform: translateY(-2px);
  box-shadow: 4px 4px 0 #000;
}

.copy-btn.copied {
  background: #17a2b8;
  animation: copySuccess 0.5s ease;
}

@keyframes copySuccess {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}

.share-section {
  display: flex;
  flex-direction: column;
}

.share-buttons {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.share-btn {
  flex: 1;
  min-width: 200px;
  padding: 1.25rem;
  border: 3px solid #000;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 1rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  font-size: 0.875rem;
}

.share-btn:hover {
  transform: translateY(-3px);
  box-shadow: 6px 6px 0 #000;
}

.x-btn {
  background: linear-gradient(135deg, #1da1f2, #0d8bd9);
  color: white;
}

.x-btn:hover {
  background: linear-gradient(135deg, #0d8bd9, #0a7bc4);
}

.telegram-btn {
  background: linear-gradient(135deg, #0088cc, #006699);
  color: white;
}

.telegram-btn:hover {
  background: linear-gradient(135deg, #006699, #004466);
}

.telegram-bot-btn {
  background: linear-gradient(135deg, #28a745, #20c997);
  color: white;
  position: relative;
  overflow: hidden;
}

.telegram-bot-btn:hover {
  background: linear-gradient(135deg, #20c997, #17a2b8);
}

.telegram-bot-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  transition: left 0.5s;
}

.telegram-bot-btn:hover::before {
  left: 100%;
}

.share-icon {
  font-size: 1.5rem;
  font-weight: 900;
}

.share-text {
  font-size: 0.875rem;
}

.task-preview {
  display: flex;
  flex-direction: column;
}

.preview-content {
  padding: 1.5rem;
  border: 3px solid #000;
  border-radius: 8px;
  background: #f8f9fa;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.preview-title {
  font-weight: 900;
  font-size: 1.1rem;
  color: #333;
}

.preview-type {
  font-weight: 600;
  color: #666;
  font-size: 0.875rem;
}

.preview-description {
  color: #666;
  line-height: 1.5;
  font-size: 0.875rem;
}

.modal-footer {
  padding: 1.5rem;
  border-top: 4px solid #000;
  display: flex;
  justify-content: flex-end;
  background: #f8f9fa;
}

.cancel-btn {
  padding: 1rem 2rem;
  border: 3px solid #000;
  border-radius: 6px;
  background: #6c757d;
  color: white;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.cancel-btn:hover {
  background: #5a6268;
  transform: translateY(-2px);
  box-shadow: 4px 4px 0 #000;
}

.toast {
  position: fixed;
  bottom: 2rem;
  right: 2rem;
  background: #28a745;
  color: white;
  padding: 1rem 1.5rem;
  border: 3px solid #000;
  border-radius: 6px;
  box-shadow: 6px 6px 0 #000;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  font-size: 0.875rem;
  z-index: 1001;
  animation: toastSlideIn 0.3s ease-out;
}

@keyframes toastSlideIn {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

/* Mobile responsive */
@media (max-width: 768px) {
  .modal-content {
    margin: 0.5rem;
    max-width: calc(100vw - 1rem);
  }

  .modal-header,
  .modal-body,
  .modal-footer {
    padding: 1rem;
  }

  .modal-body {
    gap: 1.5rem;
  }

  .url-container {
    flex-direction: column;
    gap: 0.5rem;
  }

  .share-buttons {
    flex-direction: column;
  }

  .share-btn {
    min-width: auto;
    justify-content: center;
  }

  .toast {
    bottom: 1rem;
    right: 1rem;
    left: 1rem;
    text-align: center;
  }
}
</style>