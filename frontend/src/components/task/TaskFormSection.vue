<template>
  <div class="task-form-section" :class="{ 'is-collapsible': collapsible, 'is-collapsed': isCollapsed }">
    <!-- Section Header -->
    <div
      class="task-form-section__header"
      :class="{ 'is-clickable': collapsible }"
      @click="toggleCollapse"
    >
      <div class="task-form-section__icon-wrapper" v-if="icon">
        <span class="task-form-section__icon">{{ icon }}</span>
      </div>
      <div class="task-form-section__title-wrapper">
        <h3 class="task-form-section__title">{{ title }}</h3>
        <p v-if="subtitle" class="task-form-section__subtitle">{{ subtitle }}</p>
      </div>
      <div v-if="collapsible" class="task-form-section__toggle">
        <span class="toggle-icon" :class="{ 'is-collapsed': isCollapsed }">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </span>
      </div>
    </div>

    <!-- Section Content -->
    <transition name="slide-fade">
      <div v-show="!isCollapsed" class="task-form-section__content">
        <slot />
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

interface Props {
  title: string
  subtitle?: string
  icon?: string
  collapsible?: boolean
  defaultCollapsed?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  collapsible: false,
  defaultCollapsed: false
})

const isCollapsed = ref(props.defaultCollapsed)

watch(() => props.defaultCollapsed, (newValue) => {
  isCollapsed.value = newValue
})

const toggleCollapse = () => {
  if (props.collapsible) {
    isCollapsed.value = !isCollapsed.value
  }
}
</script>

<style scoped>
.task-form-section {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 0.75rem;
  overflow: hidden;
  transition: all 0.3s ease;
}

.task-form-section:hover {
  border-color: #d1d5db;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
}

.task-form-section.is-collapsible {
  cursor: pointer;
}

.task-form-section.is-collapsed {
  border-color: #e5e7eb;
}

/* Header - 精简布局 */
.task-form-section__header {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0.75rem 1rem;
  transition: background-color 0.2s ease;
}

.task-form-section__header.is-clickable:hover {
  background-color: #f9fafb;
}

.task-form-section__icon-wrapper {
  width: 2rem;
  height: 2rem;
  background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%);
  border-radius: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.task-form-section__icon {
  font-size: 1rem;
  line-height: 1;
}

.task-form-section__title-wrapper {
  flex: 1;
  min-width: 0;
}

.task-form-section__title {
  font-size: 0.9375rem;
  font-weight: 600;
  color: #1f2937;
  margin: 0;
  line-height: 1.3;
}

.task-form-section__subtitle {
  font-size: 0.75rem;
  color: #6b7280;
  margin: 0.125rem 0 0 0;
  line-height: 1.3;
}

.task-form-section__toggle {
  flex-shrink: 0;
}

.toggle-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.25rem;
  height: 1.25rem;
  color: #6b7280;
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.toggle-icon svg {
  width: 100%;
  height: 100%;
}

.toggle-icon.is-collapsed {
  transform: rotate(-90deg);
}

/* Content - 精简内边距 */
.task-form-section__content {
  padding: 0 1rem 1rem;
}

/* Transitions */
.slide-fade-enter-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.slide-fade-leave-active {
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.slide-fade-enter-from,
.slide-fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

/* Variants */
.task-form-section--primary .task-form-section__icon-wrapper {
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
}

.task-form-section--success .task-form-section__icon-wrapper {
  background: linear-gradient(135deg, #10b981 0%, #34d399 100%);
}

.task-form-section--warning .task-form-section__icon-wrapper {
  background: linear-gradient(135deg, #f59e0b 0%, #fbbf24 100%);
}

.task-form-section--info .task-form-section__icon-wrapper {
  background: linear-gradient(135deg, #3b82f6 0%, #60a5fa 100%);
}

/* Mobile Responsive */
@media (max-width: 640px) {
  .task-form-section__header {
    padding: 0.625rem 0.875rem;
    gap: 0.5rem;
  }

  .task-form-section__icon-wrapper {
    width: 1.75rem;
    height: 1.75rem;
    border-radius: 0.375rem;
  }

  .task-form-section__icon {
    font-size: 0.875rem;
  }

  .task-form-section__title {
    font-size: 0.875rem;
  }

  .task-form-section__subtitle {
    font-size: 0.6875rem;
  }

  .task-form-section__content {
    padding: 0 0.875rem 0.875rem;
  }

  .toggle-icon {
    width: 1.125rem;
    height: 1.125rem;
  }
}
</style>
