<template>
  <div class="blizzard-bottle-content">
    <!-- Initial State -->
    <div v-if="!blizzardResults" class="warning-section">
      <div class="warning-icon">🌨️</div>
      <div class="warning-content">
        <h4 class="warning-title">暴雪瓶</h4>
        <p class="warning-message">
          将冻结当前所有处于带锁状态的用户任务！这是一个全局效果，会影响所有正在进行的带锁任务。
        </p>
        <p class="warning-note">
          ⚠️ 使用后物品将被自动销毁，此操作不可撤销！
        </p>
      </div>
    </div>

    <!-- Results State -->
    <div v-else class="blizzard-results-section">
      <h4 class="info-title">🌨️ 暴雪释放结果</h4>

      <div class="blizzard-results-grid">
        <div class="blizzard-result-card">
          <div class="result-header">
            <span class="result-icon">❄️</span>
            <span class="result-label">冻结任务数</span>
          </div>
          <div class="result-content">{{ blizzardResults.frozen_tasks_count }}</div>
        </div>

        <div class="blizzard-result-card">
          <div class="result-header">
            <span class="result-icon">👥</span>
            <span class="result-label">影响用户数</span>
          </div>
          <div class="result-content">{{ blizzardResults.affected_users_count }}</div>
        </div>
      </div>

      <div v-if="blizzardResults.frozen_tasks && blizzardResults.frozen_tasks.length > 0" class="frozen-tasks-list">
        <h5 class="tasks-title">被冻结的任务：</h5>
        <div class="task-list">
          <div
            v-for="task in blizzardResults.frozen_tasks"
            :key="task.task_id"
            class="frozen-task-item"
          >
            <span class="task-title">{{ task.task_title }}</span>
            <span class="task-owner">{{ task.owner }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface FrozenTask {
  task_id: string
  task_title: string
  owner: string
}

interface BlizzardResults {
  frozen_tasks_count: number
  affected_users_count: number
  frozen_tasks?: FrozenTask[]
  item_destroyed?: boolean
}

interface Props {
  blizzardResults: BlizzardResults | null
}

defineProps<Props>()
</script>

<style scoped>
.blizzard-bottle-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.warning-section {
  display: flex;
  gap: 1rem;
  padding: 1rem;
  background: linear-gradient(135deg, #e3f2fd, #bbdefb);
  border: 2px solid #2196f3;
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
  color: #0d47a1;
}

.warning-message,
.warning-note {
  margin: 0;
  font-size: 0.9rem;
  color: #1565c0;
  line-height: 1.5;
}

.warning-note {
  margin-top: 0.5rem;
  font-weight: 600;
}

.blizzard-results-section {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.info-title {
  font-size: 1.1rem;
  font-weight: 700;
  margin: 0;
  color: #333;
}

.blizzard-results-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
}

.blizzard-result-card {
  display: flex;
  flex-direction: column;
  padding: 1rem;
  background: linear-gradient(135deg, #e3f2fd, #bbdefb);
  border: 3px solid #000;
  border-radius: 8px;
  box-shadow: 3px 3px 0 #000;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.result-icon {
  font-size: 1.25rem;
}

.result-label {
  font-size: 0.85rem;
  font-weight: 600;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.result-content {
  font-size: 1.5rem;
  font-weight: 800;
  color: #0d47a1;
}

.frozen-tasks-list {
  margin-top: 0.5rem;
}

.tasks-title {
  font-size: 0.95rem;
  font-weight: 700;
  margin: 0 0 0.75rem;
  color: #333;
}

.task-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: 200px;
  overflow-y: auto;
}

.frozen-task-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem;
  background: white;
  border: 2px solid #dee2e6;
  border-radius: 6px;
}

.frozen-task-item .task-title {
  font-weight: 600;
  font-size: 0.9rem;
}

.frozen-task-item .task-owner {
  font-size: 0.85rem;
  color: #666;
}

@media (max-width: 768px) {
  .blizzard-results-grid {
    grid-template-columns: 1fr;
  }
}
</style>
