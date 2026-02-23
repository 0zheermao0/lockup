<template>
  <div class="note-edit-content">
    <div class="form-group">
      <label class="form-label">纸条内容</label>
      <textarea
        :value="localContent"
        placeholder="请输入纸条内容（最多30个字符）..."
        class="form-textarea note-textarea"
        maxlength="30"
        rows="3"
        @input="handleInput"
      ></textarea>
      <div class="char-counter">{{ localContent.length }}/30</div>
    </div>

    <div class="warning-section">
      <div class="warning-icon">⚠️</div>
      <div class="warning-content">
        <h4 class="warning-title">重要提醒</h4>
        <p class="warning-message">
          纸条一旦被查看将自动销毁，请谨慎分享！
        </p>
        <p class="warning-note">
          查看者有30秒阅读时间，阅读后纸条永久消失。
        </p>
      </div>
    </div>

    <!-- Footer Buttons -->
    <div class="modal-footer">
      <button class="modal-btn secondary" @click="$emit('close')">取消</button>
      <button
        class="modal-btn primary"
        :disabled="!localContent.trim() || isProcessing"
        @click="handleConfirm"
      >
        <span v-if="isProcessing">保存中...</span>
        <span v-else>保存纸条</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

interface Props {
  initialContent: string
  isProcessing: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'confirm', data: { content: string }): void
  (e: 'close'): void
}>()

const localContent = ref(props.initialContent)

// Watch for initialContent changes
watch(() => props.initialContent, (newContent) => {
  localContent.value = newContent
})

const handleInput = (event: Event) => {
  const target = event.target as HTMLTextAreaElement
  localContent.value = target.value
}

const handleConfirm = () => {
  if (!localContent.value.trim() || props.isProcessing) return
  emit('confirm', { content: localContent.value.trim() })
}
</script>

<style scoped>
.note-edit-content {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-label {
  font-weight: 700;
  font-size: 0.95rem;
  color: #333;
}

.form-textarea {
  padding: 0.75rem;
  font-size: 1rem;
  border: 3px solid #000;
  border-radius: 8px;
  resize: vertical;
  min-height: 80px;
  font-family: inherit;
  box-shadow: 3px 3px 0 #000;
  transition: all 0.2s ease;
}

.form-textarea:focus {
  outline: none;
  transform: translate(-1px, -1px);
  box-shadow: 4px 4px 0 #000;
}

.char-counter {
  text-align: right;
  font-size: 0.85rem;
  color: #666;
}

.warning-section {
  display: flex;
  gap: 1rem;
  padding: 1rem;
  background: linear-gradient(135deg, #fff3cd, #ffeeba);
  border: 2px solid #ffc107;
  border-radius: 8px;
}

.warning-icon {
  font-size: 1.5rem;
  flex-shrink: 0;
}

.warning-content {
  flex: 1;
}

.warning-title {
  font-size: 1rem;
  font-weight: 700;
  margin: 0 0 0.5rem;
  color: #856404;
}

.warning-message,
.warning-note {
  margin: 0;
  font-size: 0.9rem;
  color: #856404;
  line-height: 1.5;
}

.warning-note {
  margin-top: 0.5rem;
  font-weight: 600;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  margin-top: 0.5rem;
  padding-top: 1rem;
  border-top: 2px solid #dee2e6;
}

.modal-btn {
  padding: 0.75rem 1.5rem;
  font-size: 0.9rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border: 3px solid #000;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 3px 3px 0 #000;
  min-width: 120px;
}

.modal-btn:hover:not(:disabled) {
  transform: translate(-1px, -1px);
  box-shadow: 4px 4px 0 #000;
}

.modal-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.modal-btn.secondary {
  background: linear-gradient(135deg, #6c757d, #5a6268);
  color: white;
}

.modal-btn.primary {
  background: linear-gradient(135deg, #28a745, #218838);
  color: white;
}

@media (max-width: 768px) {
  .modal-footer {
    flex-direction: column;
  }

  .modal-btn {
    width: 100%;
  }
}
</style>
