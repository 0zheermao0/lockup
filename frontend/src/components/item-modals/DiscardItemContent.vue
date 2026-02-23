<template>
  <div class="discard-item-content">
    <div class="warning-section">
      <div class="warning-icon">⚠️</div>
      <div class="warning-content">
        <h4 class="warning-title">确认丢弃</h4>
        <p class="warning-message">
          你确定要丢弃 <strong>{{ item?.item_type?.display_name }}</strong> 吗？
        </p>
        <p class="warning-note">
          此操作不可撤销，物品将永久消失！
        </p>
      </div>
    </div>

    <div v-if="item?.properties && Object.keys(item.properties).length > 0" class="item-details">
      <h4 class="details-title">物品详情</h4>
      <div class="details-content">
        <pre class="details-json">{{ JSON.stringify(item.properties, null, 2) }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  item: any
}

defineProps<Props>()
</script>

<style scoped>
.discard-item-content {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.warning-section {
  display: flex;
  gap: 1rem;
  padding: 1rem;
  background: linear-gradient(135deg, #f8d7da, #f5c6cb);
  border: 2px solid #dc3545;
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
  color: #721c24;
}

.warning-message,
.warning-note {
  margin: 0;
  font-size: 0.9rem;
  color: #721c24;
  line-height: 1.5;
}

.warning-message strong {
  font-weight: 800;
}

.warning-note {
  margin-top: 0.5rem;
  font-weight: 600;
}

.item-details {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.details-title {
  font-size: 0.95rem;
  font-weight: 700;
  margin: 0;
  color: #333;
}

.details-content {
  padding: 1rem;
  background: #f8f9fa;
  border: 2px solid #dee2e6;
  border-radius: 8px;
  overflow-x: auto;
}

.details-json {
  margin: 0;
  font-family: 'Courier New', monospace;
  font-size: 0.85rem;
  color: #333;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
