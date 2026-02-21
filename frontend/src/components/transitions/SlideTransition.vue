<template>
  <Transition
    :name="transitionName"
    :mode="mode"
    :appear="appear"
    @before-enter="$emit('beforeEnter')"
    @after-enter="$emit('afterEnter')"
    @before-leave="$emit('beforeLeave')"
    @after-leave="$emit('afterLeave')"
  >
    <slot />
  </Transition>
</template>

<script setup lang="ts">
interface Props {
  direction?: 'up' | 'down' | 'left' | 'right'
  mode?: 'in-out' | 'out-in' | 'default'
  appear?: boolean
  duration?: 'fast' | 'normal' | 'slow'
}

const props = withDefaults(defineProps<Props>(), {
  direction: 'up',
  mode: 'default',
  appear: false,
  duration: 'normal'
})

defineEmits<{
  beforeEnter: []
  afterEnter: []
  beforeLeave: []
  afterLeave: []
}>()

const transitionName = `slide-${props.direction}-${props.duration}`
</script>

<style>
/* Slide Up */
.slide-up-fast-enter-active,
.slide-up-fast-leave-active {
  transition: all 150ms cubic-bezier(0.4, 0, 0.2, 1);
}

.slide-up-fast-enter-from,
.slide-up-fast-leave-to {
  opacity: 0;
  transform: translateY(20px);
}

.slide-up-normal-enter-active,
.slide-up-normal-leave-active {
  transition: all 300ms cubic-bezier(0.4, 0, 0.2, 1);
}

.slide-up-normal-enter-from,
.slide-up-normal-leave-to {
  opacity: 0;
  transform: translateY(30px);
}

.slide-up-slow-enter-active,
.slide-up-slow-leave-active {
  transition: all 500ms cubic-bezier(0.4, 0, 0.2, 1);
}

.slide-up-slow-enter-from,
.slide-up-slow-leave-to {
  opacity: 0;
  transform: translateY(40px);
}

/* Slide Down */
.slide-down-fast-enter-active,
.slide-down-fast-leave-active {
  transition: all 150ms cubic-bezier(0.4, 0, 0.2, 1);
}

.slide-down-fast-enter-from,
.slide-down-fast-leave-to {
  opacity: 0;
  transform: translateY(-20px);
}

.slide-down-normal-enter-active,
.slide-down-normal-leave-active {
  transition: all 300ms cubic-bezier(0.4, 0, 0.2, 1);
}

.slide-down-normal-enter-from,
.slide-down-normal-leave-to {
  opacity: 0;
  transform: translateY(-30px);
}

.slide-down-slow-enter-active,
.slide-down-slow-leave-active {
  transition: all 500ms cubic-bezier(0.4, 0, 0.2, 1);
}

.slide-down-slow-enter-from,
.slide-down-slow-leave-to {
  opacity: 0;
  transform: translateY(-40px);
}

/* Slide Left */
.slide-left-fast-enter-active,
.slide-left-fast-leave-active {
  transition: all 150ms cubic-bezier(0.4, 0, 0.2, 1);
}

.slide-left-fast-enter-from,
.slide-left-fast-leave-to {
  opacity: 0;
  transform: translateX(20px);
}

.slide-left-normal-enter-active,
.slide-left-normal-leave-active {
  transition: all 300ms cubic-bezier(0.4, 0, 0.2, 1);
}

.slide-left-normal-enter-from,
.slide-left-normal-leave-to {
  opacity: 0;
  transform: translateX(30px);
}

.slide-left-slow-enter-active,
.slide-left-slow-leave-active {
  transition: all 500ms cubic-bezier(0.4, 0, 0.2, 1);
}

.slide-left-slow-enter-from,
.slide-left-slow-leave-to {
  opacity: 0;
  transform: translateX(40px);
}

/* Slide Right */
.slide-right-fast-enter-active,
.slide-right-fast-leave-active {
  transition: all 150ms cubic-bezier(0.4, 0, 0.2, 1);
}

.slide-right-fast-enter-from,
.slide-right-fast-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}

.slide-right-normal-enter-active,
.slide-right-normal-leave-active {
  transition: all 300ms cubic-bezier(0.4, 0, 0.2, 1);
}

.slide-right-normal-enter-from,
.slide-right-normal-leave-to {
  opacity: 0;
  transform: translateX(-30px);
}

.slide-right-slow-enter-active,
.slide-right-slow-leave-active {
  transition: all 500ms cubic-bezier(0.4, 0, 0.2, 1);
}

.slide-right-slow-enter-from,
.slide-right-slow-leave-to {
  opacity: 0;
  transform: translateX(-40px);
}
</style>
