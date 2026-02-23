<template>
  <label
    class="toggle-switch"
    :class="{
      'toggle-switch--checked': modelValue,
      'toggle-switch--disabled': disabled,
      'toggle-switch--loading': loading,
      [`toggle-switch--${size}`]: size
    }"
  >
    <input
      type="checkbox"
      :checked="modelValue"
      :disabled="disabled || loading"
      @change="handleChange"
      class="toggle-switch__input"
    />
    <span class="toggle-switch__track">
      <span class="toggle-switch__thumb">
        <span v-if="loading" class="toggle-switch__spinner"></span>
      </span>
    </span>
    <span v-if="label || $slots.label" class="toggle-switch__label">
      <slot name="label">{{ label }}</slot>
    </span>
  </label>
</template>

<script setup lang="ts">
interface Props {
  modelValue: boolean | undefined
  label?: string
  disabled?: boolean
  loading?: boolean
  size?: 'small' | 'medium' | 'large'
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
  (e: 'change', value: boolean): void
}

const props = withDefaults(defineProps<Props>(), {
  size: 'medium',
  disabled: false,
  loading: false
})

const emit = defineEmits<Emits>()

const handleChange = (event: Event) => {
  const target = event.target as HTMLInputElement
  const newValue = target.checked
  emit('update:modelValue', newValue)
  emit('change', newValue)
}
</script>

<style scoped>
.toggle-switch {
  display: inline-flex;
  align-items: center;
  gap: 0.75rem;
  cursor: pointer;
  user-select: none;
  position: relative;
  /* Size variables will be set by size modifier classes */
  --track-width: 48px;
  --track-height: 28px;
  --thumb-size: 22px;
  --thumb-offset: 3px;
}

.toggle-switch::before,
.toggle-switch::after {
  display: none;
  content: none;
}

.toggle-switch--disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.toggle-switch--loading {
  cursor: wait;
}

/* Size variants */
.toggle-switch--small {
  --track-width: 36px;
  --track-height: 20px;
  --thumb-size: 16px;
  --thumb-offset: 2px;
}

.toggle-switch--medium {
  --track-width: 48px;
  --track-height: 28px;
  --thumb-size: 22px;
  --thumb-offset: 3px;
}

.toggle-switch--large {
  --track-width: 60px;
  --track-height: 34px;
  --thumb-size: 28px;
  --thumb-offset: 3px;
}

.toggle-switch__input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
  margin: 0;
  padding: 0;
  border: none;
  pointer-events: none;
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;
  visibility: hidden;
}

.toggle-switch__track {
  position: relative;
  width: var(--track-width);
  height: var(--track-height);
  background-color: #e5e7eb;
  border-radius: 9999px;
  transition: background-color 0.3s ease-in-out;
  flex-shrink: 0;
  overflow: hidden;
}

.toggle-switch__track::before,
.toggle-switch__track::after {
  display: none;
  content: none;
}

.toggle-switch--checked .toggle-switch__track {
  background-color: #6366f1;
}

.toggle-switch__thumb {
  position: absolute;
  top: var(--thumb-offset);
  left: var(--thumb-offset);
  width: var(--thumb-size);
  height: var(--thumb-size);
  background-color: white;
  border-radius: 50%;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  align-items: center;
  justify-content: center;
  will-change: transform;
  backface-visibility: hidden;
  -webkit-backface-visibility: hidden;
}

.toggle-switch__thumb::before,
.toggle-switch__thumb::after {
  display: none;
  content: none;
}

.toggle-switch--checked .toggle-switch__thumb {
  transform: translateX(calc(var(--track-width) - var(--thumb-size) - var(--thumb-offset) * 2));
}

/* Ensure thumb is properly positioned when not checked */
.toggle-switch:not(.toggle-switch--checked) .toggle-switch__thumb {
  transform: translateX(0);
}

.toggle-switch__label {
  font-size: 0.875rem;
  font-weight: 500;
  color: #374151;
  line-height: 1.4;
  flex-shrink: 0;
}

/* Loading spinner */
.toggle-switch__spinner {
  width: 60%;
  height: 60%;
  border: 2px solid #e5e7eb;
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* Hover effects */
.toggle-switch:not(.toggle-switch--disabled):not(.toggle-switch--loading):hover .toggle-switch__track {
  background-color: #d1d5db;
}

.toggle-switch--checked:not(.toggle-switch--disabled):not(.toggle-switch--loading):hover .toggle-switch__track {
  background-color: #4f46e5;
}

/* Focus styles */
.toggle-switch__input:focus-visible + .toggle-switch__track {
  outline: 2px solid #6366f1;
  outline-offset: 2px;
}

/* Active state */
.toggle-switch:not(.toggle-switch--disabled):active .toggle-switch__thumb {
  transform: scale(0.95);
}

.toggle-switch--checked:not(.toggle-switch--disabled):active .toggle-switch__thumb {
  transform: translateX(calc(var(--track-width) - var(--thumb-size) - var(--thumb-offset) * 2)) scale(0.95);
}
</style>
