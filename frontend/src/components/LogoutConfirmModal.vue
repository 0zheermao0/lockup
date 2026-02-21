<template>
  <div v-if="isVisible" class="modal-overlay" @click.self="closeModal">
    <div class="confirm-modal">
      <div class="modal-header">
        <h2>确认登出</h2>
        <button @click="closeModal" class="close-btn">✕</button>
      </div>

      <div class="modal-content">
        <div class="confirm-icon">🚪</div>
        <p class="confirm-message">确定要退出登录吗？</p>
        <p class="confirm-submessage">退出后需要重新登录才能访问您的账户</p>

        <div class="confirm-buttons">
          <button
            @click="closeModal"
            class="confirm-btn cancel-btn"
          >
            <span>取消</span>
          </button>
          <button
            @click="confirmLogout"
            class="confirm-btn logout-btn"
          >
            <span>确认登出</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  isVisible: boolean
}

interface Emits {
  (e: 'close'): void
  (e: 'confirm'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const closeModal = () => {
  emit('close')
}

const confirmLogout = () => {
  emit('confirm')
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

.confirm-modal {
  background: white;
  border: 3px solid #000;
  border-radius: 12px;
  box-shadow: 8px 8px 0 #000;
  max-width: 400px;
  width: 100%;
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
  padding: 1.25rem 1.5rem;
  border-bottom: 3px solid #000;
  background: linear-gradient(135deg, #dc3545, #c82333);
}

.modal-header h2 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: white;
}

.close-btn {
  background: white;
  color: #dc3545;
  border: 2px solid #000;
  border-radius: 50%;
  width: 36px;
  height: 36px;
  font-size: 1rem;
  font-weight: bold;
  cursor: pointer;
  box-shadow: 2px 2px 0 #000;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
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
  text-align: center;
}

.confirm-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.confirm-message {
  font-size: 1.1rem;
  font-weight: 700;
  color: #333;
  margin: 0 0 0.5rem 0;
}

.confirm-submessage {
  font-size: 0.9rem;
  color: #666;
  margin: 0 0 2rem 0;
}

.confirm-buttons {
  display: flex;
  gap: 1rem;
}

.confirm-btn {
  flex: 1;
  padding: 0.875rem 1rem;
  border: 3px solid #000;
  border-radius: 8px;
  font-weight: 700;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.2s ease;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  box-shadow: 4px 4px 0 #000;
}

.cancel-btn {
  background: linear-gradient(135deg, #6c757d, #5a6268);
  color: white;
}

.cancel-btn:hover {
  transform: translate(-2px, -2px);
  box-shadow: 6px 6px 0 #000;
}

.cancel-btn:active {
  transform: translate(1px, 1px);
  box-shadow: 2px 2px 0 #000;
}

.logout-btn {
  background: linear-gradient(135deg, #dc3545, #c82333);
  color: white;
}

.logout-btn:hover {
  transform: translate(-2px, -2px);
  box-shadow: 6px 6px 0 #000;
}

.logout-btn:active {
  transform: translate(1px, 1px);
  box-shadow: 2px 2px 0 #000;
}

/* Mobile responsive */
@media (max-width: 768px) {
  .modal-overlay {
    padding: 0.5rem;
  }

  .confirm-modal {
    border-radius: 8px;
    box-shadow: 4px 4px 0 #000;
  }

  .modal-header {
    padding: 1rem;
  }

  .modal-header h2 {
    font-size: 1.1rem;
  }

  .modal-content {
    padding: 1.5rem 1rem;
  }

  .confirm-icon {
    font-size: 2.5rem;
  }

  .confirm-message {
    font-size: 1rem;
  }

  .confirm-submessage {
    font-size: 0.85rem;
  }

  .confirm-buttons {
    flex-direction: column;
    gap: 0.75rem;
  }

  .confirm-btn {
    padding: 0.75rem;
    font-size: 0.9rem;
  }
}
</style>
