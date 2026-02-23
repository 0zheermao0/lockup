<template>
  <div class="sun-bottle-content">
    <!-- Initial State -->
    <div v-if="!sunBottleResults" class="warning-section">
      <div class="warning-icon">☀️</div>
      <div class="warning-content">
        <h4 class="warning-title">太阳瓶</h4>
        <p class="warning-message">
          将解冻当前所有被冻结的带锁任务！这是一个全局效果，会恢复所有被冻结任务的倒计时。
        </p>
        <p class="warning-note">
          ⚠️ 使用后物品将被自动销毁，此操作不可撤销！
        </p>
      </div>
    </div>

    <!-- Results State -->
    <div v-else class="sun-results-section">
      <h4 class="info-title">☀️ 太阳瓶使用结果</h4>

      <div class="sun-results-grid">
        <div class="sun-result-card">
          <div class="result-header">
            <span class="result-icon">🔥</span>
            <span class="result-label">解冻任务数</span>
          </div>
          <div class="result-content">{{ sunBottleResults.unfrozen_tasks_count }}</div>
        </div>

        <div class="sun-result-card">
          <div class="result-header">
            <span class="result-icon">👥</span>
            <span class="result-label">影响用户数</span>
          </div>
          <div class="result-content">{{ sunBottleResults.affected_users_count }}</div>
        </div>
      </div>

      <div v-if="sunBottleResults.unfrozen_tasks && sunBottleResults.unfrozen_tasks.length > 0" class="unfrozen-tasks-list">
        <h5 class="tasks-title">被解冻的任务：</h5>
        <div class="task-list">
          <div
            v-for="task in sunBottleResults.unfrozen_tasks"
            :key="task.task_id"
            class="unfrozen-task-item"
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
interface UnfrozenTask {
  task_id: string
  task_title: string
  owner: string
}

interface SunBottleResults {
  unfrozen_tasks_count: number
  affected_users_count: number
  unfrozen_tasks?: UnfrozenTask[]
  item_destroyed?: boolean
}

interface Props {
  sunBottleResults: SunBottleResults | null
}

defineProps<Props>()
</script>

<style scoped>
.sun-bottle-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
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

.sun-results-section {
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

.sun-results-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
}

.sun-result-card {
  display: flex;
  flex-direction: column;
  padding: 1rem;
  background: linear-gradient(135deg, #fff3e0, #ffe0b2);
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
  color: #e65100;
}

.unfrozen-tasks-list {
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

.unfrozen-task-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem;
  background: white;
  border: 2px solid #dee2e6;
  border-radius: 6px;
}

.unfrozen-task-item .task-title {
  font-weight: 600;
  font-size: 0.9rem;
}

.unfrozen-task-item .task-owner {
  font-size: 0.85rem;
  color: #666;
}

@media (max-width: 768px) {
  .sun-results-grid {
    grid-template-columns: 1fr;
  }
}
</style>
