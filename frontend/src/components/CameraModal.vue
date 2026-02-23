<template>
  <div class="camera-modal" @click.self="close">
    <div class="camera-container">
      <div class="camera-header">
        <h3>{{ title }}</h3>
        <button @click="close" class="btn-close">✕</button>
      </div>

      <div class="camera-preview">
        <video
          ref="videoRef"
          autoplay
          playsinline
          class="video-feed"
        ></video>
        <canvas ref="canvasRef" style="display: none;"></canvas>

        <!-- 拍照后的预览 -->
        <img
          v-if="capturedImage"
          :src="capturedImage"
          class="captured-preview"
          alt="Captured"
        />

        <!-- 快门闪光效果 -->
        <div v-if="showFlash" class="shutter-flash"></div>
      </div>

      <div class="camera-controls">
        <p class="hint">{{ hintText }}</p>

        <div v-if="!capturedImage" class="capture-btn-container">
          <button @click="capture" class="btn-capture">
            <span class="shutter"></span>
          </button>
        </div>

        <div v-else class="action-buttons">
          <button @click="retake" class="btn-retake">
            <span class="icon">↺</span>
            重拍
          </button>
          <button
            @click="confirm"
            class="btn-confirm"
            :disabled="processing"
          >
            {{ processing ? '处理中...' : '确认使用' }}
          </button>
        </div>
      </div>

      <!-- 处理进度 -->
      <div v-if="processing" class="processing-overlay">
        <div class="spinner"></div>
        <p>{{ processingMessage }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'

const props = withDefaults(defineProps<{
  maxSize: number  // 最大文件大小（字节）
  title?: string   // 可选的标题
  hint?: string    // 可选的提示文字
}>(), {
  title: '拍照验证',
  hint: '请拍摄清晰的照片'
})

// 计算提示文字
const hintText = computed(() => props.hint)

const emit = defineEmits<{
  close: []
  capture: [file: File]
}>()

const videoRef = ref<HTMLVideoElement>()
const canvasRef = ref<HTMLCanvasElement>()
const capturedImage = ref<string>()
const processing = ref(false)
const processingMessage = ref('')
const showFlash = ref(false)
let stream: MediaStream | null = null

// 启动摄像头
onMounted(async () => {
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'environment' }
    })
    if (videoRef.value) {
      videoRef.value.srcObject = stream
    }
  } catch (error) {
    console.error('无法访问摄像头:', error)
    alert('无法访问摄像头，请检查权限设置')
    close()
  }
})

// 关闭摄像头
onUnmounted(() => {
  stopCamera()
})

const stopCamera = () => {
  if (stream) {
    stream.getTracks().forEach(track => track.stop())
    stream = null
  }
}

const capture = () => {
  if (!videoRef.value || !canvasRef.value) return

  // Trigger flash animation
  showFlash.value = true
  setTimeout(() => {
    showFlash.value = false
  }, 150)

  const video = videoRef.value
  const canvas = canvasRef.value

  // 设置画布尺寸与视频一致
  canvas.width = video.videoWidth
  canvas.height = video.videoHeight

  // 绘制视频帧到画布
  const ctx = canvas.getContext('2d')
  ctx?.drawImage(video, 0, 0)

  // 获取图片数据
  capturedImage.value = canvas.toDataURL('image/jpeg', 0.9)
}

const retake = () => {
  capturedImage.value = undefined
}

const confirm = async () => {
  if (!capturedImage.value || !canvasRef.value) return

  processing.value = true
  processingMessage.value = '处理图片...'

  try {
    const canvas = canvasRef.value
    let blob = await new Promise<Blob | null>(resolve => {
      canvas.toBlob(resolve, 'image/jpeg', 0.9)
    })

    if (!blob) {
      throw new Error('图片处理失败')
    }

    // 如果文件太大，进行压缩
    if (blob.size > props.maxSize) {
      processingMessage.value = '压缩图片...'
      blob = await compressImage(canvas, props.maxSize)
    }

    // 创建文件对象
    const file = new File([blob], `unlock_verification_${Date.now()}.jpg`, {
      type: 'image/jpeg'
    })

    emit('capture', file)
    stopCamera()
  } catch (error) {
    console.error('图片处理失败:', error)
    alert('图片处理失败，请重试')
  } finally {
    processing.value = false
  }
}

const compressImage = async (canvas: HTMLCanvasElement, maxSize: number): Promise<Blob> => {
  let quality = 0.9
  let blob: Blob | null = null

  while (quality > 0.1) {
    blob = await new Promise<Blob | null>(resolve => {
      canvas.toBlob(resolve, 'image/jpeg', quality)
    })

    if (blob && blob.size <= maxSize) {
      break
    }

    quality -= 0.1

    // 如果质量降低还不够，缩小尺寸
    if (quality <= 0.5 && blob && blob.size > maxSize) {
      const newWidth = canvas.width * 0.8
      const newHeight = canvas.height * 0.8

      const tempCanvas = document.createElement('canvas')
      tempCanvas.width = newWidth
      tempCanvas.height = newHeight

      const tempCtx = tempCanvas.getContext('2d')
      tempCtx?.drawImage(canvas, 0, 0, newWidth, newHeight)

      return compressImage(tempCanvas, maxSize)
    }
  }

  if (!blob) {
    throw new Error('无法压缩图片到指定大小')
  }

  return blob
}

const close = () => {
  stopCamera()
  emit('close')
}
</script>

<style scoped>
.camera-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.camera-container {
  background: #1a1a1a;
  border-radius: 16px;
  width: 90%;
  max-width: 500px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.camera-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #333;
}

.camera-header h3 {
  margin: 0;
  color: #fff;
  font-size: 18px;
}

.btn-close {
  background: none;
  border: none;
  color: #fff;
  font-size: 24px;
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: background 0.2s;
}

.btn-close:hover {
  background: rgba(255, 255, 255, 0.1);
}

.camera-preview {
  position: relative;
  aspect-ratio: 4/3;
  background: #000;
  overflow: hidden;
}

.video-feed,
.captured-preview {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.captured-preview {
  position: absolute;
  top: 0;
  left: 0;
}

.shutter-flash {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: white;
  opacity: 0.8;
  animation: flash 0.15s ease-out forwards;
  pointer-events: none;
}

@keyframes flash {
  0% {
    opacity: 0.8;
  }
  100% {
    opacity: 0;
  }
}

.camera-controls {
  padding: 20px;
  text-align: center;
}

.hint {
  color: #999;
  margin: 0 0 20px;
  font-size: 14px;
}

.capture-btn-container {
  display: flex;
  justify-content: center;
}

.btn-capture {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  border: 4px solid #fff;
  background: transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.2s;
}

.btn-capture:hover {
  transform: scale(1.05);
}

.btn-capture:active {
  transform: scale(0.95);
}

.shutter {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: #fff;
  display: block;
}

.action-buttons {
  display: flex;
  gap: 16px;
  justify-content: center;
}

.btn-retake,
.btn-confirm {
  padding: 12px 24px;
  border-radius: 8px;
  border: none;
  font-size: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.2s;
}

.btn-retake {
  background: #333;
  color: #fff;
}

.btn-retake:hover {
  background: #444;
}

.btn-confirm {
  background: #4CAF50;
  color: #fff;
}

.btn-confirm:hover:not(:disabled) {
  background: #45a049;
}

.btn-confirm:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.processing-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #fff;
  gap: 16px;
}

.spinner {
  width: 48px;
  height: 48px;
  border: 4px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
