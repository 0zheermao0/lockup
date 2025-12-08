<template>
  <div class="duration-selector">
    <label v-if="label" class="duration-label">{{ label }}</label>

    <div class="duration-inputs">
      <!-- 天数选择 -->
      <div class="duration-unit">
        <label class="unit-label">天</label>
        <select
          v-model="days"
          @change="updateDuration"
          class="duration-select"
          :class="{ 'has-value': days > 0 }"
        >
          <option value="0">0</option>
          <option v-for="day in maxDays" :key="day" :value="day">{{ day }}</option>
        </select>
      </div>

      <!-- 小时选择 -->
      <div class="duration-unit">
        <label class="unit-label">小时</label>
        <select
          v-model="hours"
          @change="updateDuration"
          class="duration-select"
          :class="{ 'has-value': hours > 0 }"
        >
          <option value="0">0</option>
          <option v-for="hour in 23" :key="hour" :value="hour">{{ hour }}</option>
        </select>
      </div>

      <!-- 分钟选择 -->
      <div class="duration-unit">
        <label class="unit-label">分钟</label>
        <select
          v-model="minutes"
          @change="updateDuration"
          class="duration-select"
          :class="{ 'has-value': minutes > 0 }"
        >
          <option value="0">0</option>
          <option v-for="minute in [5, 10, 15, 20, 30, 45]" :key="minute" :value="minute">{{ minute }}</option>
          <option value="59">59</option>
        </select>
      </div>
    </div>

    <!-- 总时长显示 -->
    <div class="duration-display">
      <div class="total-display">
        总计: <span class="total-value">{{ formatTotalDuration() }}</span>
      </div>
      <div class="minutes-display">
        ({{ totalMinutes }} 分钟)
      </div>
    </div>

    <!-- 快捷选择按钮 -->
    <div class="quick-select">
      <span class="quick-label">快捷选择:</span>
      <div class="quick-buttons">
        <button
          type="button"
          v-for="preset in presets"
          :key="preset.label"
          @click="selectPreset(preset)"
          class="quick-btn"
          :class="{ 'active': totalMinutes === preset.minutes }"
        >
          {{ preset.label }}
        </button>
      </div>
    </div>

    <!-- 错误提示 -->
    <div v-if="error" class="error-message">
      {{ error }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'

interface Props {
  modelValue: number // 总分钟数
  label?: string
  minMinutes?: number // 最小分钟数
  maxMinutes?: number // 最大分钟数
  required?: boolean
}

interface Emits {
  (e: 'update:modelValue', value: number): void
}

interface Preset {
  label: string
  minutes: number
}

const props = withDefaults(defineProps<Props>(), {
  label: '',
  minMinutes: 1,
  maxMinutes: 10080, // 7天 = 7 * 24 * 60 = 10080分钟
  required: false
})

const emit = defineEmits<Emits>()

// 响应式数据
const days = ref(0)
const hours = ref(0)
const minutes = ref(0)
const error = ref('')

// 计算属性
const maxDays = computed(() => Math.floor(props.maxMinutes / (24 * 60)))

const totalMinutes = computed(() => {
  return days.value * 24 * 60 + hours.value * 60 + minutes.value
})

// 预设选项
const presets: Preset[] = [
  { label: '30分', minutes: 30 },
  { label: '1小时', minutes: 60 },
  { label: '2小时', minutes: 120 },
  { label: '3小时', minutes: 180 },
  { label: '6小时', minutes: 360 },
  { label: '12小时', minutes: 720 },
  { label: '1天', minutes: 1440 },
  { label: '3天', minutes: 4320 },
  { label: '1周', minutes: 10080 }
]

// 方法
const updateDuration = () => {
  const total = totalMinutes.value

  // 验证范围
  if (total < props.minMinutes) {
    error.value = `最短时间不能少于 ${props.minMinutes} 分钟`
    return
  }

  if (total > props.maxMinutes) {
    error.value = `最长时间不能超过 ${formatMinutesToText(props.maxMinutes)}`
    return
  }

  error.value = ''
  emit('update:modelValue', total)
}

const selectPreset = (preset: Preset) => {
  // 将预设时间转换为天/小时/分钟
  const totalMins = preset.minutes
  const d = Math.floor(totalMins / (24 * 60))
  const h = Math.floor((totalMins % (24 * 60)) / 60)
  const m = totalMins % 60

  days.value = d
  hours.value = h
  minutes.value = m

  updateDuration()
}

const formatTotalDuration = (): string => {
  return formatMinutesToText(totalMinutes.value)
}

const formatMinutesToText = (mins: number): string => {
  if (mins === 0) return '0分钟'

  const d = Math.floor(mins / (24 * 60))
  const h = Math.floor((mins % (24 * 60)) / 60)
  const m = mins % 60

  const parts = []
  if (d > 0) parts.push(`${d}天`)
  if (h > 0) parts.push(`${h}小时`)
  if (m > 0) parts.push(`${m}分钟`)

  return parts.join('')
}

const setFromMinutes = (totalMins: number) => {
  const d = Math.floor(totalMins / (24 * 60))
  const h = Math.floor((totalMins % (24 * 60)) / 60)
  const m = totalMins % 60

  days.value = d
  hours.value = h
  minutes.value = m
}

// 监听外部值变化
watch(() => props.modelValue, (newValue) => {
  if (newValue !== totalMinutes.value) {
    setFromMinutes(newValue)
  }
}, { immediate: true })

// 组件挂载时初始化
onMounted(() => {
  if (props.modelValue > 0) {
    setFromMinutes(props.modelValue)
  } else {
    // 默认设置为1小时
    selectPreset({ label: '1小时', minutes: 60 })
  }
})
</script>

<style scoped>
.duration-selector {
  width: 100%;
}

.duration-label {
  display: block;
  margin-bottom: 0.75rem;
  font-weight: 600;
  color: #333;
  font-size: 1rem;
}

.duration-inputs {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.duration-unit {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.unit-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: #666;
  margin-bottom: 0.5rem;
  text-align: center;
}

.duration-select {
  width: 100%;
  padding: 0.75rem;
  border: 2px solid #ddd;
  border-radius: 6px;
  font-size: 1rem;
  font-weight: 600;
  text-align: center;
  background: white;
  cursor: pointer;
  transition: all 0.2s ease;
}

.duration-select:focus {
  outline: none;
  border-color: #007bff;
  box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.1);
}

.duration-select.has-value {
  border-color: #28a745;
  background-color: #f8fff9;
  color: #155724;
}

.duration-display {
  background: #f8f9fa;
  border: 2px solid #e9ecef;
  border-radius: 6px;
  padding: 0.75rem;
  margin-bottom: 1rem;
  text-align: center;
}

.total-display {
  font-size: 1.1rem;
  font-weight: 700;
  color: #333;
  margin-bottom: 0.25rem;
}

.total-value {
  color: #007bff;
  font-weight: 900;
}

.minutes-display {
  font-size: 0.875rem;
  color: #666;
  font-style: italic;
}

.quick-select {
  margin-bottom: 1rem;
}

.quick-label {
  display: block;
  font-size: 0.875rem;
  font-weight: 600;
  color: #666;
  margin-bottom: 0.5rem;
}

.quick-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.quick-btn {
  padding: 0.5rem 0.75rem;
  border: 2px solid #ddd;
  border-radius: 4px;
  background: white;
  color: #666;
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.quick-btn:hover {
  border-color: #007bff;
  background-color: #f8f9fa;
  color: #007bff;
}

.quick-btn.active {
  border-color: #007bff;
  background-color: #007bff;
  color: white;
}

.error-message {
  background-color: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
  border-radius: 4px;
  padding: 0.75rem;
  font-size: 0.875rem;
  font-weight: 600;
  margin-top: 0.5rem;
}

/* Mobile responsive */
@media (max-width: 768px) {
  .duration-inputs {
    grid-template-columns: 1fr;
    gap: 0.5rem;
  }

  .duration-unit {
    flex-direction: row;
    justify-content: space-between;
    align-items: center;
  }

  .unit-label {
    margin-bottom: 0;
    margin-right: 1rem;
    flex-shrink: 0;
  }

  .duration-select {
    width: 120px;
    flex-shrink: 0;
  }

  .quick-buttons {
    justify-content: center;
  }

  .quick-btn {
    flex: 1;
    min-width: 60px;
    max-width: 80px;
  }
}
</style>