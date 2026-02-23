<template>
  <div class="time-hourglass-content">
    <!-- Initial State -->
    <div v-if="!hourglassResults" class="warning-section">
      <div class="warning-icon">⏳</div>
      <div class="warning-content">
        <h4 class="warning-title">时间沙漏</h4>
        <p class="warning-message">
          将当前带锁任务状态回退到30分钟前，撤销最近30分钟内的加减时、冻结等操作。
        </p>
        <p class="warning-note">
          ⚠️ 使用后物品将被自动销毁，此操作不可撤销！
        </p>
      </div>
    </div>

    <!-- Results State -->
    <div v-else class="hourglass-results-section">
      <h4 class="info-title">⏳ 时间回退结果</h4>

      <div class="hourglass-results-grid">
        <div class="hourglass-result-card">
          <div class="result-header">
            <span class="result-icon">🔄</span>
            <span class="result-label">回退操作数</span>
          </div>
          <div class="result-content">{{ hourglassResults.reverted_events_count }}</div>
        </div>

        <div class="hourglass-result-card">
          <div class="result-header">
            <span class="result-icon">⏰</span>
            <span class="result-label">新结束时间</span>
          </div>
          <div class="result-content">
            {{ hourglassResults.new_end_time ? formatDate(hourglassResults.new_end_time) : '无' }}
          </div>
        </div>

        <div v-if="hourglassResults.is_frozen" class="hourglass-result-card frozen">
          <div class="result-header">
            <span class="result-icon">❄️</span>
            <span class="result-label">冻结状态</span>
          </div>
          <div class="result-content">任务已冻结</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface HourglassResults {
  reverted_events_count: number
  new_end_time?: string
  is_frozen: boolean
  rollback_id?: string
}

interface Props {
  hourglassResults: HourglassResults | null
}

const props = defineProps<Props>()

const formatDate = (dateString: string): string => {
  return new Date(dateString).toLocaleString('zh-CN')
}
</script>

<style scoped>
.time-hourglass-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.warning-section {
  display: flex;
  gap: 1rem;
  padding: 1rem;
  background: linear-gradient(135deg, #f3e5f5, #e1bee7);
  border: 2px solid #9c27b0;
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
  color: #4a148c;
}

.warning-message,
.warning-note {
  margin: 0;
  font-size: 0.9rem;
  color: #6a1b9a;
  line-height: 1.5;
}

.warning-note {
  margin-top: 0.5rem;
  font-weight: 600;
}

.hourglass-results-section {
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

.hourglass-results-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.hourglass-result-card {
  display: flex;
  flex-direction: column;
  padding: 1rem;
  background: white;
  border: 3px solid #000;
  border-radius: 8px;
  box-shadow: 3px 3px 0 #000;
}

.hourglass-result-card.frozen {
  background: linear-gradient(135deg, #e3f2fd, #bbdefb);
  border-color: #2196f3;
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
  font-size: 1.1rem;
  font-weight: 700;
  color: #333;
}

@media (max-width: 768px) {
  .hourglass-results-grid {
    grid-template-columns: 1fr;
  }
}
</style>
