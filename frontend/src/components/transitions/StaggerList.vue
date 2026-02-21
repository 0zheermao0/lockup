<template>
  <TransitionGroup
    :name="transitionName"
    :tag="tag"
    :class="[listClass, { 'stagger-list': enableStagger }]"
    :style="staggerStyle"
    appear
  >
    <slot />
  </TransitionGroup>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  tag?: string
  listClass?: string
  staggerDelay?: number
  enableStagger?: boolean
  transitionName?: string
}

const props = withDefaults(defineProps<Props>(), {
  tag: 'div',
  listClass: '',
  staggerDelay: 60,
  enableStagger: true,
  transitionName: 'stagger-list'
})

const staggerStyle = computed(() => {
  if (!props.enableStagger) return {}
  return {
    '--stagger-delay': `${props.staggerDelay}ms`
  }
})
</script>

<style>
/* Base stagger list styles */
.stagger-list-move,
.stagger-list-enter-active,
.stagger-list-leave-active {
  transition: all 400ms cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

.stagger-list-enter-from,
.stagger-list-leave-to {
  opacity: 0;
  transform: translateY(30px) scale(0.95);
}

.stagger-list-leave-active {
  position: absolute;
}

/* Dynamic stagger delays using CSS custom properties */
.stagger-list > *:nth-child(1) { transition-delay: calc(var(--stagger-delay, 60ms) * 0); }
.stagger-list > *:nth-child(2) { transition-delay: calc(var(--stagger-delay, 60ms) * 1); }
.stagger-list > *:nth-child(3) { transition-delay: calc(var(--stagger-delay, 60ms) * 2); }
.stagger-list > *:nth-child(4) { transition-delay: calc(var(--stagger-delay, 60ms) * 3); }
.stagger-list > *:nth-child(5) { transition-delay: calc(var(--stagger-delay, 60ms) * 4); }
.stagger-list > *:nth-child(6) { transition-delay: calc(var(--stagger-delay, 60ms) * 5); }
.stagger-list > *:nth-child(7) { transition-delay: calc(var(--stagger-delay, 60ms) * 6); }
.stagger-list > *:nth-child(8) { transition-delay: calc(var(--stagger-delay, 60ms) * 7); }
.stagger-list > *:nth-child(9) { transition-delay: calc(var(--stagger-delay, 60ms) * 8); }
.stagger-list > *:nth-child(10) { transition-delay: calc(var(--stagger-delay, 60ms) * 9); }
.stagger-list > *:nth-child(11) { transition-delay: calc(var(--stagger-delay, 60ms) * 10); }
.stagger-list > *:nth-child(12) { transition-delay: calc(var(--stagger-delay, 60ms) * 11); }
.stagger-list > *:nth-child(13) { transition-delay: calc(var(--stagger-delay, 60ms) * 12); }
.stagger-list > *:nth-child(14) { transition-delay: calc(var(--stagger-delay, 60ms) * 13); }
.stagger-list > *:nth-child(15) { transition-delay: calc(var(--stagger-delay, 60ms) * 14); }
.stagger-list > *:nth-child(16) { transition-delay: calc(var(--stagger-delay, 60ms) * 15); }
.stagger-list > *:nth-child(17) { transition-delay: calc(var(--stagger-delay, 60ms) * 16); }
.stagger-list > *:nth-child(18) { transition-delay: calc(var(--stagger-delay, 60ms) * 17); }
.stagger-list > *:nth-child(19) { transition-delay: calc(var(--stagger-delay, 60ms) * 18); }
.stagger-list > *:nth-child(20) { transition-delay: calc(var(--stagger-delay, 60ms) * 19); }

/* Slide variant */
.stagger-slide-move,
.stagger-slide-enter-active,
.stagger-slide-leave-active {
  transition: all 400ms cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

.stagger-slide-enter-from,
.stagger-slide-leave-to {
  opacity: 0;
  transform: translateX(-30px);
}

.stagger-slide-leave-active {
  position: absolute;
}

/* Scale variant */
.stagger-scale-move,
.stagger-scale-enter-active,
.stagger-scale-leave-active {
  transition: all 400ms cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

.stagger-scale-enter-from,
.stagger-scale-leave-to {
  opacity: 0;
  transform: scale(0.8);
}

.stagger-scale-leave-active {
  position: absolute;
}

/* Fade variant */
.stagger-fade-move,
.stagger-fade-enter-active,
.stagger-fade-leave-active {
  transition: all 300ms ease;
}

.stagger-fade-enter-from,
.stagger-fade-leave-to {
  opacity: 0;
}

.stagger-fade-leave-active {
  position: absolute;
}

/* Flip variant */
.stagger-flip-move,
.stagger-flip-enter-active,
.stagger-flip-leave-active {
  transition: all 400ms cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

.stagger-flip-enter-from,
.stagger-flip-leave-to {
  opacity: 0;
  transform: perspective(400px) rotateX(-30deg);
}

.stagger-flip-leave-active {
  position: absolute;
}
</style>
