<template>
  <div v-if="isVisible" class="modal-overlay" @click.self="closeModal">
    <div class="vote-modal">
      <div class="modal-header">
        <h2>投票确认</h2>
        <button @click="closeModal" class="close-btn">✕</button>
      </div>

      <div class="modal-content">
        <div class="task-info">
          <h3>{{ task?.title }}</h3>
          <p class="task-description">{{ task?.description }}</p>
        </div>

        <div class="vote-question">
          <h4>您是否同意解锁此任务？</h4>
          <p class="vote-note">选择后将记录您的投票，无法修改</p>
        </div>

        <div class="vote-buttons">
          <button
            @click="submitVote(true)"
            class="vote-btn agree-btn"
            :disabled="isSubmitting"
          >
            <span class="vote-icon">✅</span>
            <span class="vote-text">同意解锁</span>
          </button>
          <button
            @click="submitVote(false)"
            class="vote-btn disagree-btn"
            :disabled="isSubmitting"
          >
            <span class="vote-icon">❌</span>
            <span class="vote-text">拒绝解锁</span>
          </button>
        </div>

        <div v-if="isSubmitting" class="submitting-state">
          <div class="spinner">🔄</div>
          <span>提交投票中...</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { LockTask } from '../types/index'

interface Props {
  isVisible: boolean
  task: LockTask | null
}

interface Emits {
  (e: 'close'): void
  (e: 'vote', agree: boolean): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const isSubmitting = ref(false)

const closeModal = () => {
  if (!isSubmitting.value) {
    emit('close')
  }
}

const submitVote = async (agree: boolean) => {
  if (isSubmitting.value) return

  isSubmitting.value = true
  try {
    emit('vote', agree)
  } finally {
    isSubmitting.value = false
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

.vote-modal {
  background: white;
  border: 3px solid #000;
  border-radius: 12px;
  box-shadow: 8px 8px 0 #000;
  max-width: 500px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  position: relative;
  animation: modal-bounce 0.3s ease-out;
}

@keyframes modal-bounce {
  0% {
    transform: scale(0.8) translateY(-20px);
    opacity: 0;
  }
  50% {
    transform: scale(1.05) translateY(0);
    opacity: 0.8;
  }
  100% {
    transform: scale(1) translateY(0);
    opacity: 1;
  }
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 3px solid #000;
  background: linear-gradient(135deg, #ffc107, #ffeb3b);
}

.modal-header h2 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: #000;
}

.close-btn {
  background: #dc3545;
  color: white;
  border: 2px solid #000;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  font-size: 1.2rem;
  font-weight: bold;
  cursor: pointer;
  box-shadow: 2px 2px 0 #000;
  transition: all 0.2s ease;
}

.close-btn:hover {
  transform: translate(-1px, -1px);
  box-shadow: 3px 3px 0 #000;
}

.close-btn:active {
  transform: translate(1px, 1px);
  box-shadow: 1px 1px 0 #000;
}

.modal-content {
  padding: 2rem;
}

.task-info {
  margin-bottom: 2rem;
  padding: 1rem;
  background: #f8f9fa;
  border: 2px solid #000;
  border-radius: 8px;
}

.task-info h3 {
  margin: 0 0 0.5rem 0;
  font-size: 1.2rem;
  font-weight: bold;
  color: #333;
}

.task-description {
  margin: 0;
  color: #666;
  line-height: 1.5;
}

.vote-question {
  text-align: center;
  margin-bottom: 2rem;
}

.vote-question h4 {
  margin: 0 0 0.5rem 0;
  font-size: 1.1rem;
  font-weight: bold;
  color: #333;
}

.vote-note {
  margin: 0;
  font-size: 0.9rem;
  color: #666;
  font-style: italic;
}

.vote-buttons {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
}

.vote-btn {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 1.5rem 1rem;
  border: 3px solid #000;
  border-radius: 8px;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
  overflow: hidden;
}

.vote-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none !important;
}

.agree-btn {
  background: linear-gradient(135deg, #28a745, #20c997);
  color: white;
  box-shadow: 4px 4px 0 #000;
}

.agree-btn:hover:not(:disabled) {
  transform: translate(-2px, -2px);
  box-shadow: 6px 6px 0 #000;
}

.agree-btn:active:not(:disabled) {
  transform: translate(1px, 1px);
  box-shadow: 2px 2px 0 #000;
}

.disagree-btn {
  background: linear-gradient(135deg, #dc3545, #e74c3c);
  color: white;
  box-shadow: 4px 4px 0 #000;
}

.disagree-btn:hover:not(:disabled) {
  transform: translate(-2px, -2px);
  box-shadow: 6px 6px 0 #000;
}

.disagree-btn:active:not(:disabled) {
  transform: translate(1px, 1px);
  box-shadow: 2px 2px 0 #000;
}

.vote-icon {
  font-size: 2rem;
}

.vote-text {
  font-size: 1rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.submitting-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 1rem;
  background: #fff3cd;
  border: 2px solid #ffeaa7;
  border-radius: 8px;
  color: #856404;
  font-weight: 500;
}

.spinner {
  font-size: 1.2rem;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Mobile responsive */
@media (max-width: 768px) {
  .modal-overlay {
    padding: 0.5rem;
  }

  .vote-modal {
    border-radius: 8px;
    box-shadow: 4px 4px 0 #000;
  }

  .modal-header {
    padding: 1rem;
  }

  .modal-header h2 {
    font-size: 1.2rem;
  }

  .modal-content {
    padding: 1rem;
  }

  .vote-buttons {
    flex-direction: column;
  }

  .vote-btn {
    padding: 1rem;
  }

  .vote-icon {
    font-size: 1.5rem;
  }

  .vote-text {
    font-size: 0.9rem;
  }
}
</style>