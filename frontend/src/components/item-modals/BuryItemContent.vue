<template>
  <div class="bury-item-content">
    <div class="form-group">
      <label class="form-label">掩埋区域</label>
      <select v-model="localZone" class="form-select">
        <option value="">选择区域</option>
        <option value="forest">🌲 神秘森林</option>
        <option value="mountain">🏔️ 雾山</option>
        <option value="beach">🏖️ 月光海滩</option>
        <option value="desert">🏜️ 沙漠绿洲</option>
        <option value="cave">🕳️ 深邃洞穴</option>
      </select>
    </div>

    <div class="form-group">
      <label class="form-label">寻找提示</label>
      <input
        v-model="localHint"
        placeholder="留下寻找提示..."
        class="form-input"
        maxlength="200"
      >
      <div class="char-counter">{{ localHint.length }}/200</div>
    </div>

    <div v-if="item" class="item-info-section">
      <h4 class="info-title">📦 掩埋物品</h4>
      <div class="item-info-card">
        <span class="item-icon">{{ item.item_type.icon }}</span>
        <div class="item-details">
          <span class="item-name">{{ item.item_type.display_name }}</span>
          <span class="item-description">{{ item.item_type.description }}</span>
        </div>
      </div>
    </div>

    <!-- Footer Buttons -->
    <div class="modal-footer">
      <button class="modal-btn secondary" @click="$emit('close')">取消</button>
      <button
        class="modal-btn primary"
        :disabled="!localZone || !localHint.trim() || isProcessing"
        @click="handleConfirm"
      >
        <span v-if="isProcessing">掩埋中...</span>
        <span v-else>掩埋物品</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

interface Props {
  item: any
  isProcessing: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'confirm', data: { locationZone: string; locationHint: string }): void
  (e: 'close'): void
}>()

const localZone = ref('')
const localHint = ref('')

const handleConfirm = () => {
  if (!localZone.value || !localHint.value.trim() || props.isProcessing) return
  emit('confirm', {
    locationZone: localZone.value,
    locationHint: localHint.value.trim()
  })
}
</script>

<style scoped>
.bury-item-content {
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

.form-select,
.form-input {
  padding: 0.75rem;
  font-size: 1rem;
  border: 3px solid #000;
  border-radius: 8px;
  background: white;
  box-shadow: 3px 3px 0 #000;
  transition: all 0.2s ease;
}

.form-select:focus,
.form-input:focus {
  outline: none;
  transform: translate(-1px, -1px);
  box-shadow: 4px 4px 0 #000;
}

.form-select {
  cursor: pointer;
}

.char-counter {
  text-align: right;
  font-size: 0.85rem;
  color: #666;
}

.item-info-section {
  margin-top: 0.5rem;
}

.info-title {
  font-size: 0.95rem;
  font-weight: 700;
  margin: 0 0 0.75rem;
  color: #333;
}

.item-info-card {
  display: flex;
  gap: 1rem;
  padding: 1rem;
  background: linear-gradient(135deg, #f8f9fa, #e9ecef);
  border: 2px solid #000;
  border-radius: 8px;
}

.item-icon {
  font-size: 2rem;
  flex-shrink: 0;
}

.item-details {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.item-name {
  font-weight: 700;
  font-size: 1rem;
}

.item-description {
  font-size: 0.85rem;
  color: #666;
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
