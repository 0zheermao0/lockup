<template>
  <div class="universal-key-content">
    <!-- Warning Section -->
    <div class="warning-section">
      <div class="warning-icon">⚠️</div>
      <div class="warning-content">
        <h4 class="warning-title">重要提醒</h4>
        <p class="warning-message">
          万能钥匙可以直接完成任何可完成的带锁任务，并获得正常的完成奖励。
        </p>
        <p class="warning-note">
          使用后钥匙将被销毁，请谨慎选择！
        </p>
      </div>
    </div>

    <!-- Task Selection -->
    <div class="form-group">
      <label class="form-label">选择要完成的任务</label>

      <div v-if="availableTasks.length === 0" class="no-tasks-message">
        <p>暂无可完成的带锁任务</p>
        <p class="hint">只能完成自己的活跃状态或投票状态的带锁任务</p>
      </div>

      <div v-else class="tasks-list">
        <div
          v-for="task in availableTasks"
          :key="task.id"
          class="task-item"
          :class="{ 'selected': selectedTaskId === task.id }"
          @click="selectTask(task.id)"
        >
          <div class="task-info">
            <h4 class="task-title">{{ task.title }}</h4>
            <p class="task-meta">
              <span class="task-difficulty">{{ getDifficultyText(task.difficulty) }}</span>
              <span class="task-status">{{ getStatusText(task.status) }}</span>
            </p>
            <p v-if="task.description" class="task-description">
              {{ stripHtmlAndTruncate(task.description, 120) }}
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Item Info -->
    <div v-if="item" class="item-info-section">
      <h4 class="info-title">🗝️ 使用物品</h4>
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
        :disabled="!selectedTaskId || isProcessing"
        @click="handleConfirm"
      >
        <span v-if="isProcessing">使用中...</span>
        <span v-else>使用万能钥匙</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Item } from '@/types'

interface Task {
  id: string
  title: string
  difficulty: string
  status: string
  description?: string
}

interface Props {
  item: Item | null
  availableTasks: Task[]
  selectedTaskId: string
  isProcessing: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'update:selectedTaskId', id: string): void
  (e: 'confirm', data: { taskId: string }): void
  (e: 'close'): void
}>()

const selectTask = (id: string) => {
  emit('update:selectedTaskId', id)
}

const handleConfirm = () => {
  if (!props.selectedTaskId || props.isProcessing) return
  emit('confirm', { taskId: props.selectedTaskId })
}

const getDifficultyText = (difficulty: string): string => {
  const map: Record<string, string> = {
    easy: '简单',
    normal: '普通',
    hard: '困难',
    hell: '地狱'
  }
  return map[difficulty] || difficulty
}

const getStatusText = (status: string): string => {
  const map: Record<string, string> = {
    active: '进行中',
    voting: '投票中',
    voting_passed: '投票通过',
    pending: '待开始',
    completed: '已完成',
    failed: '已失败'
  }
  return map[status] || status
}

const stripHtmlAndTruncate = (html: string, maxLength: number = 120): string => {
  if (!html) return ''
  const tempDiv = document.createElement('div')
  tempDiv.innerHTML = html
  const text = tempDiv.textContent || tempDiv.innerText || ''
  if (text.length <= maxLength) return text
  return text.slice(0, maxLength) + '...'
}
</script>

<style scoped>
.universal-key-content {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
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

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.form-label {
  font-weight: 700;
  font-size: 0.95rem;
  color: #333;
}

.no-tasks-message {
  text-align: center;
  padding: 2rem;
  background: #f8f9fa;
  border: 2px dashed #dee2e6;
  border-radius: 8px;
}

.no-tasks-message p {
  margin: 0;
  color: #6c757d;
}

.no-tasks-message .hint {
  margin-top: 0.5rem;
  font-size: 0.85rem;
}

.tasks-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  max-height: 300px;
  overflow-y: auto;
}

.task-item {
  display: flex;
  gap: 1rem;
  padding: 1rem;
  background: white;
  border: 3px solid #000;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 3px 3px 0 #000;
}

.task-item:hover {
  transform: translate(-2px, -2px);
  box-shadow: 5px 5px 0 #000;
}

.task-item.selected {
  background: linear-gradient(135deg, #007bff, #0056b3);
  color: white;
  border-color: #000;
}

.task-info {
  flex: 1;
  min-width: 0;
}

.task-title {
  font-size: 1rem;
  font-weight: 700;
  margin: 0 0 0.5rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-meta {
  display: flex;
  gap: 0.75rem;
  margin: 0 0 0.5rem;
  font-size: 0.85rem;
}

.task-difficulty {
  padding: 0.25rem 0.5rem;
  background: rgba(0, 0, 0, 0.1);
  border-radius: 4px;
  font-weight: 600;
}

.task-status {
  padding: 0.25rem 0.5rem;
  background: rgba(40, 167, 69, 0.2);
  border-radius: 4px;
  font-weight: 600;
}

.task-item.selected .task-difficulty,
.task-item.selected .task-status {
  background: rgba(255, 255, 255, 0.2);
}

.task-description {
  margin: 0;
  font-size: 0.85rem;
  opacity: 0.8;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
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

  .tasks-list {
    max-height: 200px;
  }
}
</style>
