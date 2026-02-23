<template>
  <div class="daily-task-config" :class="{ 'is-expanded': isEnabled }">
    <!-- Header with Toggle -->
    <div class="daily-task-config__header" @click="toggleEnabled">
      <div class="daily-task-config__icon-wrapper">
        <span class="daily-task-config__icon">🔄</span>
      </div>
      <div class="daily-task-config__title-wrapper">
        <h4 class="daily-task-config__title">设为日常任务</h4>
        <p class="daily-task-config__subtitle">每天自动发布相同任务到任务板</p>
      </div>
      <ToggleSwitch
        v-model="localEnabled"
        size="medium"
        @change="onToggleChange"
        @click.stop
      />
    </div>

    <!-- Expanded Configuration -->
    <transition name="slide-fade">
      <div v-if="isEnabled" class="daily-task-config__content">
        <div class="daily-task-config__divider"></div>

        <div class="daily-task-config__form">
          <!-- Duration Days -->
          <div class="form-field">
            <label class="form-field__label">
              <span class="form-field__icon">📅</span>
              持续天数
            </label>
            <div class="duration-selector">
              <button
                type="button"
                v-for="day in [3, 7, 14, 30]"
                :key="day"
                class="duration-btn"
                :class="{ active: localDuration === day }"
                @click="setDuration(day)"
              >
                {{ day }}天
              </button>
              <input
                type="number"
                v-model.number="localDuration"
                min="1"
                max="30"
                class="duration-input"
                placeholder="自定义"
                @change="validateDuration"
              />
            </div>
          </div>

          <!-- Publish Time -->
          <div class="form-field">
            <label class="form-field__label">
              <span class="form-field__icon">⏰</span>
              每日发布时间
            </label>
            <TimePicker
              v-model="localPublishTime"
              :show-hint="true"
              hint="任务将在每天此时自动发布"
              @change="onTimeChange"
            />
          </div>

          <!-- Cost Preview -->
          <div class="cost-preview" :class="{ 'insufficient': !hasSufficientCoins }">
            <div class="cost-preview__header">
              <span class="cost-preview__icon">💰</span>
              <span class="cost-preview__title">积分预扣明细</span>
            </div>
            <div class="cost-preview__calculation">
              <div class="calc-row">
                <span class="calc-label">每日奖励</span>
                <span class="calc-value">{{ reward }} 积分</span>
              </div>
              <div class="calc-row">
                <span class="calc-label">持续天数</span>
                <span class="calc-value">× {{ localDuration }} 天</span>
              </div>
              <div class="calc-divider"></div>
              <div class="calc-row calc-row--total">
                <span class="calc-label">总预扣积分</span>
                <span class="calc-value calc-value--total">{{ totalCost }} 积分</span>
              </div>
            </div>

            <!-- Balance Status -->
            <div class="balance-status" :class="{ 'balance-ok': hasSufficientCoins, 'balance-low': !hasSufficientCoins }">
              <template v-if="hasSufficientCoins">
                <span class="status-icon">✅</span>
                <span class="status-text">
                  您的余额充足 ({{ userCoins }} 积分)
                </span>
              </template>
              <template v-else>
                <span class="status-icon">⚠️</span>
                <span class="status-text">
                  余额不足，还需 {{ coinsNeeded }} 积分
                </span>
              </template>
            </div>
          </div>

          <!-- Info Tips -->
          <div class="info-tips">
            <div class="info-tip">
              <span class="info-tip__icon">ℹ️</span>
              <span class="info-tip__text">创建时将一次性扣除总积分</span>
            </div>
            <div class="info-tip">
              <span class="info-tip__icon">🔄</span>
              <span class="info-tip__text">可随时取消未发布的日常任务</span>
            </div>
            <div class="info-tip">
              <span class="info-tip__icon">⏰</span>
              <span class="info-tip__text">发布时间基于服务器时区</span>
            </div>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import ToggleSwitch from '../ui/ToggleSwitch.vue'
import TimePicker from '../ui/TimePicker.vue'

interface Props {
  modelValue: {
    isEnabled: boolean
    duration: number
    publishTime: string
  }
  reward: number
  userCoins: number
}

interface Emits {
  (e: 'update:modelValue', value: { isEnabled: boolean; duration: number; publishTime: string }): void
  (e: 'validation-change', isValid: boolean): void
}

const props = withDefaults(defineProps<Props>(), {
  reward: 0,
  userCoins: 0
})

const emit = defineEmits<Emits>()

// Local state
const localEnabled = ref(props.modelValue.isEnabled)
const localDuration = ref(props.modelValue.duration || 7)
const localPublishTime = ref(props.modelValue.publishTime || '08:00')

// Computed
const isEnabled = computed(() => localEnabled.value)

const totalCost = computed(() => {
  return props.reward * localDuration.value
})

const hasSufficientCoins = computed(() => {
  if (!isEnabled.value) return true
  return props.userCoins >= totalCost.value
})

const coinsNeeded = computed(() => {
  return Math.max(0, totalCost.value - props.userCoins)
})

// Watch for external changes
watch(() => props.modelValue, (newValue) => {
  localEnabled.value = newValue.isEnabled
  localDuration.value = newValue.duration
  localPublishTime.value = newValue.publishTime
}, { deep: true })

// Emit changes
watch([localEnabled, localDuration, localPublishTime], () => {
  emit('update:modelValue', {
    isEnabled: localEnabled.value,
    duration: localDuration.value,
    publishTime: localPublishTime.value
  })
  emit('validation-change', !localEnabled.value || hasSufficientCoins.value)
}, { deep: true })

// Methods
const toggleEnabled = () => {
  localEnabled.value = !localEnabled.value
}

const onToggleChange = (value: boolean) => {
  localEnabled.value = value
}

const setDuration = (days: number) => {
  localDuration.value = days
}

const validateDuration = () => {
  if (localDuration.value < 1) {
    localDuration.value = 1
  } else if (localDuration.value > 30) {
    localDuration.value = 30
  }
}

const onTimeChange = (time: string) => {
  localPublishTime.value = time
}
</script>

<style scoped>
.daily-task-config {
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border: 2px solid #e2e8f0;
  border-radius: 1rem;
  overflow: hidden;
  transition: all 0.3s ease;
}

.daily-task-config.is-expanded {
  border-color: #6366f1;
  box-shadow: 0 4px 6px -1px rgba(99, 102, 241, 0.1), 0 2px 4px -1px rgba(99, 102, 241, 0.06);
}

/* Ensure ToggleSwitch aligns correctly in header */
.daily-task-config__header .toggle-switch {
  margin-left: auto;
  flex-shrink: 0;
}

.daily-task-config__header {
  display: flex;
  align-items: center;
  gap: 0.875rem;
  padding: 1rem 1.25rem;
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.daily-task-config__header:hover {
  background-color: rgba(99, 102, 241, 0.05);
}

.daily-task-config__icon-wrapper {
  width: 2.5rem;
  height: 2.5rem;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  border-radius: 0.75rem;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.daily-task-config__icon {
  font-size: 1.25rem;
}

.daily-task-config__title-wrapper {
  flex: 1;
  min-width: 0;
}

.daily-task-config__title {
  font-size: 1rem;
  font-weight: 600;
  color: #1e293b;
  margin: 0 0 0.25rem 0;
}

.daily-task-config__subtitle {
  font-size: 0.8125rem;
  color: #64748b;
  margin: 0;
}

.daily-task-config__content {
  padding: 0 1.25rem 1.25rem;
}

.daily-task-config__divider {
  height: 1px;
  background: linear-gradient(90deg, transparent 0%, #e2e8f0 50%, transparent 100%);
  margin-bottom: 1.25rem;
}

.daily-task-config__form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

/* Form Fields */
.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-field__label {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: #374151;
}

.form-field__icon {
  font-size: 1rem;
}

/* Duration Selector */
.duration-selector {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  align-items: center;
}

.duration-btn {
  padding: 0.5rem 0.875rem;
  font-size: 0.8125rem;
  font-weight: 500;
  color: #4b5563;
  background: white;
  border: 2px solid #e5e7eb;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.duration-btn:hover {
  border-color: #6366f1;
  color: #6366f1;
}

.duration-btn.active {
  background: #6366f1;
  border-color: #6366f1;
  color: white;
}

.duration-input {
  width: 5rem;
  padding: 0.5rem 0.625rem;
  font-size: 0.8125rem;
  font-weight: 500;
  color: #374151;
  background: white;
  border: 2px solid #e5e7eb;
  border-radius: 0.5rem;
  text-align: center;
}

.duration-input:focus {
  outline: none;
  border-color: #6366f1;
}

/* Cost Preview */
.cost-preview {
  background: white;
  border: 2px solid #e2e8f0;
  border-radius: 0.75rem;
  padding: 1rem;
  transition: all 0.2s ease;
}

.cost-preview.insufficient {
  border-color: #f59e0b;
  background: linear-gradient(135deg, #fffbeb 0%, white 100%);
}

.cost-preview__header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.cost-preview__icon {
  font-size: 1.125rem;
}

.cost-preview__title {
  font-size: 0.875rem;
  font-weight: 600;
  color: #374151;
}

.cost-preview__calculation {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.calc-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.8125rem;
}

.calc-label {
  color: #6b7280;
}

.calc-value {
  font-weight: 500;
  color: #374151;
}

.calc-divider {
  height: 1px;
  background: #e5e7eb;
  margin: 0.25rem 0;
}

.calc-row--total {
  font-size: 0.9375rem;
}

.calc-value--total {
  font-weight: 700;
  color: #6366f1;
  font-size: 1.125rem;
}

.cost-preview.insufficient .calc-value--total {
  color: #dc2626;
}

/* Balance Status */
.balance-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.75rem;
  padding: 0.625rem 0.875rem;
  border-radius: 0.5rem;
  font-size: 0.8125rem;
  font-weight: 500;
}

.balance-ok {
  background: #d1fae5;
  color: #065f46;
}

.balance-low {
  background: #fef3c7;
  color: #92400e;
}

.status-icon {
  font-size: 1rem;
}

/* Info Tips */
.info-tips {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.info-tip {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.75rem;
  color: #6b7280;
}

.info-tip__icon {
  font-size: 0.875rem;
}

/* Transitions */
.slide-fade-enter-active {
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.slide-fade-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.slide-fade-enter-from,
.slide-fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* Mobile Responsive */
@media (max-width: 640px) {
  .daily-task-config__header {
    padding: 0.875rem 1rem;
  }

  .daily-task-config__icon-wrapper {
    width: 2.25rem;
    height: 2.25rem;
  }

  .daily-task-config__icon {
    font-size: 1.125rem;
  }

  .daily-task-config__title {
    font-size: 0.9375rem;
  }

  .daily-task-config__subtitle {
    font-size: 0.75rem;
  }

  .daily-task-config__content {
    padding: 0 1rem 1rem;
  }

  .duration-selector {
    gap: 0.375rem;
  }

  .duration-btn {
    padding: 0.4375rem 0.75rem;
    font-size: 0.75rem;
  }

  .duration-input {
    width: 4.5rem;
  }

  .cost-preview {
    padding: 0.875rem;
  }

  .calc-value--total {
    font-size: 1rem;
  }
}
</style>
