<template>
  <div class="small-campfire-content">
    <!-- Warning Section -->
    <div class="warning-section">
      <div class="warning-icon">🔥</div>
      <div class="warning-content">
        <h4 class="warning-title">小火堆</h4>
        <p class="warning-message">
          可以解冻您自己的被冻结的带锁任务，让任务恢复倒计时。
        </p>
        <p class="warning-note">
          ⚠️ 使用后物品将被自动销毁，请谨慎使用！
        </p>
      </div>
    </div>

    <!-- Task Selection -->
    <div class="form-group">
      <div v-if="frozenTasks.length === 0" class="no-tasks-message">
        <p>暂无被冻结的带锁任务</p>
        <p class="hint">只能解冻自己的已被冻结的带锁任务</p>
      </div>

      <div v-else-if="frozenTasks[0]" class="frozen-task-info">
        <h4 class="info-title">🧊 被冻结的任务</h4>
        <div class="task-display-card">
          <div class="task-info">
            <h4 class="task-title">{{ frozenTasks[0].title }}</h4>
            <p class="task-meta">
              <span class="task-difficulty">{{ getDifficultyText(frozenTasks[0].difficulty) }}</span>
              <span class="task-status frozen">❄️ 已冻结</span>
            </p>
            <p v-if="frozenTasks[0].description" class="task-description">
              {{ stripHtmlAndTruncate(frozenTasks[0].description, 120) }}
            </p>
            <div v-if="frozenTasks[0].frozen_at" class="freeze-info">
              <span class="freeze-time">冻结时间：{{ formatFreezeTime(frozenTasks[0].frozen_at) }}</span>
            </div>
          </div>
        </div>
        <p class="auto-select-note">
          💡 将自动解冻上述任务
        </p>
      </div>
    </div>

    <!-- Item Info -->
    <div v-if="item" class="item-info-section">
      <h4 class="info-title">🔥 使用物品</h4>
      <div class="item-info-card">
        <span class="item-icon">{{ item.item_type.icon }}</span>
        <div class="item-details">
          <span class="item-name">{{ item.item_type.display_name }}</span>
          <span class="item-description">{{ item.item_type.description }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Task {
  id: string
  title: string
  difficulty: string
  status: string
  description?: string
  frozen_at?: string
}

interface Props {
  frozenTasks: Task[]
  item: any
}

const props = defineProps<Props>()

const getDifficultyText = (difficulty: string): string => {
  const map: Record<string, string> = {
    easy: '简单',
    normal: '普通',
    hard: '困难',
    hell: '地狱'
  }
  return map[difficulty] || difficulty
}

const formatFreezeTime = (dateString: string): string => {
  if (!dateString) return ''
  return new Date(dateString).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
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
.small-campfire-content {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.warning-section {
  display: flex;
  gap: 1rem;
  padding: 1rem;
  background: linear-gradient(135deg, #fff3e0, #ffe0b2);
  border: 2px solid #ff9800;
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
  color: #e65100;
}

.warning-message,
.warning-note {
  margin: 0;
  font-size: 0.9rem;
  color: #ef6c00;
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

.frozen-task-info {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.info-title {
  font-size: 0.95rem;
  font-weight: 700;
  margin: 0;
  color: #333;
}

.task-display-card {
  padding: 1rem;
  background: linear-gradient(135deg, #e3f2fd, #bbdefb);
  border: 3px solid #000;
  border-radius: 8px;
  box-shadow: 3px 3px 0 #000;
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

.task-status.frozen {
  padding: 0.25rem 0.5rem;
  background: rgba(33, 150, 243, 0.2);
  border-radius: 4px;
  font-weight: 600;
  color: #0d47a1;
}

.task-description {
  margin: 0 0 0.5rem;
  font-size: 0.85rem;
  opacity: 0.8;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.freeze-info {
  margin-top: 0.5rem;
  padding-top: 0.5rem;
  border-top: 1px solid rgba(0, 0, 0, 0.1);
}

.freeze-time {
  font-size: 0.8rem;
  color: #666;
}

.auto-select-note {
  margin: 0;
  padding: 0.75rem;
  background: rgba(255, 193, 7, 0.1);
  border-left: 4px solid #ffc107;
  border-radius: 4px;
  font-size: 0.9rem;
  color: #856404;
}

.item-info-section {
  margin-top: 0.5rem;
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
</style>
