<template>
  <div class="time-picker" :class="{ 'time-picker--disabled': disabled }">
    <div class="time-picker__input-wrapper">
      <input
        type="time"
        :value="modelValue"
        :disabled="disabled"
        :required="required"
        @input="handleInput"
        @change="handleChange"
        class="time-picker__input"
      />
      <span class="time-picker__icon">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"></circle>
          <polyline points="12 6 12 12 16 14"></polyline>
        </svg>
      </span>
    </div>
    <div v-if="showHint" class="time-picker__hint">
      <slot name="hint">{{ hint }}</slot>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  modelValue: string
  disabled?: boolean
  required?: boolean
  hint?: string
  showHint?: boolean
}

interface Emits {
  (e: 'update:modelValue', value: string): void
  (e: 'change', value: string): void
}

const props = withDefaults(defineProps<Props>(), {
  disabled: false,
  required: false,
  showHint: false,
  hint: ''
})

const emit = defineEmits<Emits>()

const handleInput = (event: Event) => {
  const target = event.target as HTMLInputElement
  emit('update:modelValue', target.value)
}

const handleChange = (event: Event) => {
  const target = event.target as HTMLInputElement
  emit('change', target.value)
}
</script>

<style scoped>
.time-picker {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.time-picker--disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.time-picker__input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.time-picker__input {
  width: 100%;
  padding: 0.625rem 2.5rem 0.625rem 0.875rem;
  font-size: 0.9375rem;
  font-weight: 500;
  color: #1f2937;
  background-color: white;
  border: 2px solid #e5e7eb;
  border-radius: 0.5rem;
  transition: all 0.2s ease;
  cursor: pointer;
}

.time-picker__input:hover:not(:disabled) {
  border-color: #d1d5db;
}

.time-picker__input:focus {
  outline: none;
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
}

.time-picker__input:disabled {
  background-color: #f3f4f6;
  cursor: not-allowed;
}

/* Custom time picker icon styling */
.time-picker__input::-webkit-calendar-picker-indicator {
  position: absolute;
  right: 0.5rem;
  width: 1.25rem;
  height: 1.25rem;
  opacity: 0;
  cursor: pointer;
  z-index: 2;
}

.time-picker__icon {
  position: absolute;
  right: 0.75rem;
  width: 1.25rem;
  height: 1.25rem;
  color: #6b7280;
  pointer-events: none;
  transition: color 0.2s ease;
}

.time-picker__input:focus ~ .time-picker__icon {
  color: #6366f1;
}

.time-picker__icon svg {
  width: 100%;
  height: 100%;
}

.time-picker__hint {
  font-size: 0.75rem;
  color: #6b7280;
  line-height: 1.4;
}

/* Size variants could be added here if needed */
</style>
