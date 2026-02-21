<template>
  <router-view v-slot="{ Component, route }">
    <transition
      :name="getTransitionName(route)"
      mode="out-in"
      @before-leave="onBeforeLeave"
      @after-enter="onAfterEnter"
    >
      <component :is="Component" :key="route.path" />
    </transition>
  </router-view>
</template>

<script setup lang="ts">
import type { RouteLocationNormalized } from 'vue-router'

interface Props {
  defaultTransition?: string
}

const props = withDefaults(defineProps<Props>(), {
  defaultTransition: 'page-fade'
})

const getTransitionName = (route: RouteLocationNormalized): string => {
  // Use route meta transition if specified
  if (route.meta?.transition) {
    return route.meta.transition as string
  }

  // Auto-detect based on route patterns
  const path = route.path

  // Detail pages - use slide
  if (path.includes('/tasks/') || path.includes('/post/')) {
    return 'page-slide'
  }

  // Profile page - use scale
  if (path.includes('/profile')) {
    return 'page-scale'
  }

  // Default fade
  return props.defaultTransition
}

const onBeforeLeave = () => {
  // Optional: Add logic before route leave
  document.body.style.overflow = 'hidden'
}

const onAfterEnter = () => {
  // Restore body scroll after transition
  document.body.style.overflow = ''

  // Scroll to top on route change
  window.scrollTo({ top: 0, behavior: 'smooth' })
}
</script>

<style scoped>
/* Transition styles are defined in page-transitions.css */
</style>
