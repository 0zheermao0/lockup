<template>
  <div class="detection-radar-content">
    <!-- Initial State -->
    <div v-if="!detectionResults" class="warning-section">
      <div class="warning-icon">🎯</div>
      <div class="warning-content">
        <h4 class="warning-title">探测雷达</h4>
        <p class="warning-message">
          可以揭示您自己的带锁任务的隐藏时间信息。
        </p>
        <p class="warning-note">
          ⚠️ 使用后物品将被自动销毁，请谨慎使用！
        </p>
      </div>
    </div>

    <!-- Results State -->
    <div v-else class="detection-results-section">
      <h4 class="info-title">📊 探测结果</h4>

      <div class="detection-results-grid">
        <div class="detection-result-card">
          <div class="result-header">
            <span class="result-icon">📝</span>
            <span class="result-label">任务标题</span>
          </div>
          <div class="result-content">{{ detectionResults.task_title }}</div>
        </div>

        <div class="detection-result-card">
          <div class="result-header">
            <span class="result-icon">📊</span>
            <span class="result-label">任务状态</span>
          </div>
          <div class="result-content">{{ detectionResults.status_text }}</div>
        </div>

        <div class="detection-result-card highlight">
          <div class="result-header">
            <span class="result-icon">⏰</span>
            <span class="result-label">剩余时间</span>
          </div>
          <div class="result-content time-display">
            {{ formatTimeRemaining(detectionResults.time_remaining_ms) }}
          </div>
        </div>

        <div v-if="detectionResults.is_frozen" class="detection-result-card frozen">
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
interface DetectionResults {
  task_title: string
  status_text: string
  time_remaining_ms: number
  is_frozen: boolean
}

interface Props {
  detectionResults: DetectionResults | null
}

defineProps<Props>()

const formatTimeRemaining = (milliseconds: number): string => {
  if (milliseconds <= 0) return '已结束'

  const hours = Math.floor(milliseconds / (1000 * 60 * 60))
  const minutes = Math.floor((milliseconds % (1000 * 60 * 60)) / (1000 * 60))
  const seconds = Math.floor((milliseconds % (1000 * 60)) / 1000)

  if (hours > 0) {
    return `${hours}小时${minutes}分钟`
  } else if (minutes > 0) {
    return `${minutes}分钟${seconds}秒`
  } else {
    return `${seconds}秒`
  }
}
</script>

<style scoped>
.detection-radar-content {
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

.detection-results-section {
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

.detection-results-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.detection-result-card {
  display: flex;
  flex-direction: column;
  padding: 1rem;
  background: white;
  border: 3px solid #000;
  border-radius: 8px;
  box-shadow: 3px 3px 0 #000;
}

.detection-result-card.highlight {
  background: linear-gradient(135deg, #fff3cd, #ffeeba);
  border-color: #ffc107;
}

.detection-result-card.frozen {
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

.result-content.time-display {
  font-size: 1.25rem;
  color: #856404;
}

@media (max-width: 768px) {
  .detection-results-grid {
    grid-template-columns: 1fr;
  }
}
</style>
