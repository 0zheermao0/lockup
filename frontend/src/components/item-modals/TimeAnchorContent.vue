<template>
  <div class="time-anchor-content">
    <!-- Warning Section -->
    <div class="warning-section">
      <div class="warning-icon">⚓</div>
      <div class="warning-content">
        <h4 class="warning-title">时间锚点</h4>
        <p class="warning-message">
          保存当前任务状态，如果任务失败可以恢复到保存点。
        </p>
        <p class="warning-note">
          使用后道具将被自动销毁，请谨慎使用！
        </p>
      </div>
    </div>

    <!-- Saved State Info -->
    <div v-if="savedTaskInfo" class="saved-state-info">
      <div class="info-header">
        <span class="info-icon">💾</span>
        <h4 class="info-title">已保存状态</h4>
      </div>
      <div class="saved-info-details">
        <p><strong>任务:</strong> {{ savedTaskInfo.taskTitle || '未知任务' }}</p>
        <p><strong>保存状态:</strong> {{ savedTaskInfo.savedStatus || '未知' }}</p>
        <p v-if="savedTaskInfo.savedAt"><strong>保存时间:</strong> {{ formatDate(savedTaskInfo.savedAt) }}</p>
      </div>
    </div>

    <!-- Action Selection -->
    <div class="form-group">
      <label class="form-label">选择操作</label>
      <div class="radio-group">
        <label class="radio-option">
          <input v-model="localAction" type="radio" value="save" />
          <span>{{ savedTaskInfo ? '重新保存任务状态' : '保存任务状态' }}</span>
        </label>
        <label v-if="savedTaskInfo" class="radio-option">
          <input v-model="localAction" type="radio" value="restore" />
          <span>恢复任务状态</span>
        </label>
      </div>
    </div>

    <!-- Task Selection -->
    <div class="form-group">
      <label class="form-label">选择任务</label>

      <div v-if="localAction === 'save' && tasks.length === 0" class="no-tasks-message">
        <p>暂无可保存的带锁任务</p>
        <p class="hint">只能保存自己的活跃状态或投票状态的带锁任务</p>
      </div>

      <div v-if="localAction === 'save' && tasks.length > 0" class="tasks-list">
        <div
          v-for="task in tasks"
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

      <!-- Restore Task Info -->
      <div v-if="localAction === 'restore'" class="restore-task-info">
        <div v-if="savedTaskInfo" class="saved-task-display">
          <h4 class="saved-task-title">将恢复以下任务状态：</h4>
          <div class="saved-task-card">
            <div class="task-info">
              <h4 class="task-title">{{ savedTaskInfo.taskTitle || '未知任务' }}</h4>
              <p class="task-meta">
                <span class="task-status failed">{{ savedTaskInfo.savedStatus || '未知状态' }}</span>
                <span class="saved-time">保存于: {{ savedTaskInfo.savedAt ? formatDate(savedTaskInfo.savedAt) : '未知时间' }}</span>
              </p>
            </div>
          </div>
        </div>

        <div v-else class="no-restore-available">
          <div class="warning-section">
            <div class="warning-icon">⚠️</div>
            <div class="warning-content">
              <h4 class="warning-title">无法恢复</h4>
              <p class="warning-message">
                此时间锚点尚未保存任何任务状态
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Footer Buttons -->
    <div class="modal-footer">
      <button class="modal-btn secondary" @click="$emit('close')">取消</button>
      <button
        class="modal-btn primary"
        :disabled="isConfirmDisabled"
        @click="handleConfirm"
      >
        <span v-if="isProcessing">使用中...</span>
        <span v-else>{{ localAction === 'save' ? '确认保存' : '确认恢复' }}</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'

interface Task {
  id: string
  title: string
  difficulty: string
  status: string
  description?: string
}

interface SavedTaskInfo {
  taskId?: string
  taskTitle?: string
  savedStatus?: string
  savedAt?: string
}

interface Props {
  item: any
  tasks: Task[]
  savedTaskInfo?: SavedTaskInfo | null
  isProcessing: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'confirm', data: { action: 'save' | 'restore'; taskId?: string }): void
  (e: 'close'): void
}>()

// Local state
const localAction = ref<'save' | 'restore'>('save')
const selectedTaskId = ref('')

// Watch for savedTaskInfo to set initial action
watch(() => props.savedTaskInfo, (info) => {
  if (!info) {
    localAction.value = 'save'
  }
}, { immediate: true })

// Computed
const isConfirmDisabled = computed(() => {
  if (props.isProcessing) return true
  if (localAction.value === 'save') {
    return !selectedTaskId.value
  }
  // restore
  return !props.savedTaskInfo
})

// Methods
const selectTask = (id: string) => {
  selectedTaskId.value = id
}

const handleConfirm = () => {
  emit('confirm', {
    action: localAction.value,
    taskId: localAction.value === 'save' ? selectedTaskId.value : props.savedTaskInfo?.taskId
  })
}

const formatDate = (dateString: string): string => {
  return new Date(dateString).toLocaleString('zh-CN')
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
.time-anchor-content {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.warning-section {
  display: flex;
  gap: 1rem;
  padding: 1rem;
  background: linear-gradient(135deg, #e8f5e9, #c8e6c9);
  border: 2px solid #4caf50;
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
  color: #1b5e20;
}

.warning-message,
.warning-note {
  margin: 0;
  font-size: 0.9rem;
  color: #2e7d32;
  line-height: 1.5;
}

.warning-note {
  margin-top: 0.5rem;
  font-weight: 600;
}

.saved-state-info {
  padding: 1rem;
  background: linear-gradient(135deg, #e3f2fd, #bbdefb);
  border: 2px solid #2196f3;
  border-radius: 8px;
}

.info-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.info-icon {
  font-size: 1.25rem;
}

.info-title {
  font-size: 1rem;
  font-weight: 700;
  margin: 0;
  color: #0d47a1;
}

.saved-info-details {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.saved-info-details p {
  margin: 0;
  font-size: 0.9rem;
  color: #1565c0;
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

.radio-group {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.radio-option {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  background: white;
  border: 2px solid #dee2e6;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.radio-option:hover {
  border-color: #007bff;
}

.radio-option input[type="radio"] {
  width: 20px;
  height: 20px;
  cursor: pointer;
}

.radio-option span {
  font-size: 0.95rem;
  font-weight: 600;
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
  max-height: 200px;
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

.restore-task-info {
  padding: 1rem;
  background: #f8f9fa;
  border: 2px solid #dee2e6;
  border-radius: 8px;
}

.saved-task-title {
  font-size: 0.95rem;
  font-weight: 700;
  margin: 0 0 0.75rem;
  color: #333;
}

.saved-task-card {
  padding: 1rem;
  background: white;
  border: 2px solid #000;
  border-radius: 8px;
}

.saved-task-card .task-meta {
  flex-wrap: wrap;
}

.task-status.failed {
  background: rgba(220, 53, 69, 0.2);
  color: #dc3545;
}

.saved-time {
  font-size: 0.8rem;
  color: #666;
}

.no-restore-available {
  padding: 1rem;
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
