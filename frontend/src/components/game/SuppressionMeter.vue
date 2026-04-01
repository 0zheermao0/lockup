<template>
  <div class="suppression-meter">
    <div class="suppression-meter__header">
      <span class="suppression-meter__label">压抑值</span>
      <div class="suppression-meter__right">
        <span
          v-if="value > 85"
          class="suppression-meter__badge suppression-meter__badge--critical"
        >
          ⚠️ 压抑临界
        </span>
        <span class="suppression-meter__value">{{ value }}</span>
      </div>
    </div>

    <div class="suppression-meter__track">
      <div
        class="suppression-meter__fill"
        :class="{
          'suppression-meter__fill--pulse': value > 70,
        }"
        :style="{
          width: `${Math.min(value, 100)}%`,
          backgroundColor: fillColor,
        }"
      />
    </div>

    <p v-if="value >= 100" class="suppression-meter__glitch">
      🔴 文字故障激活
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  value: number
}>()

const fillColor = computed(() => {
  if (props.value <= 50) return '#00cc44'
  if (props.value <= 70) return '#ffaa00'
  return '#ff3300'
})
</script>

<style scoped>
.suppression-meter {
  font-family: 'Inter', sans-serif;
  font-weight: 700;
  user-select: none;
}

.suppression-meter__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.suppression-meter__label {
  font-size: 0.85em;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.suppression-meter__right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.suppression-meter__value {
  font-size: 0.85em;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  min-width: 2.5ch;
  text-align: right;
}

.suppression-meter__badge {
  font-size: 0.75em;
  font-weight: 700;
  padding: 1px 6px;
  border: 2px solid #000;
  box-shadow: 2px 2px 0 #000;
}

.suppression-meter__badge--critical {
  background-color: #ff3300;
  color: #fff;
}

.suppression-meter__track {
  height: 12px;
  background-color: #e0e0e0;
  border: 2px solid #000;
  box-shadow: 4px 4px 0 #000;
  overflow: hidden;
  position: relative;
}

.suppression-meter__fill {
  height: 100%;
  transition: width 0.4s ease, background-color 0.4s ease;
}

.suppression-meter__fill--pulse {
  animation: suppression-pulse 2s ease-in-out infinite;
}

.suppression-meter__glitch {
  margin-top: 6px;
  font-size: 0.8em;
  font-weight: 700;
  color: #ff3300;
  border: 2px solid #ff3300;
  box-shadow: 4px 4px 0 #ff3300;
  padding: 4px 8px;
  background-color: #fff0ee;
  display: inline-block;
}

@keyframes suppression-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
</style>
