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
  mode?: 'in-out' | 'out-in' | 'default'
  appear?: boolean
  duration?: 'fast' | 'normal' | 'slow'
}

const props = withDefaults(defineProps<Props>(), {
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

const transitionName = `fade-${props.duration}`
</script>

<style>
/* Fast fade */
.fade-fast-enter-active,
.fade-fast-leave-active {
  transition: opacity 150ms ease;
}

.fade-fast-enter-from,
.fade-fast-leave-to {
  opacity: 0;
}

/* Normal fade */
.fade-normal-enter-active,
.fade-normal-leave-active {
  transition: opacity 300ms ease;
}

.fade-normal-enter-from,
.fade-normal-leave-to {
  opacity: 0;
}

/* Slow fade */
.fade-slow-enter-active,
.fade-slow-leave-active {
  transition: opacity 500ms ease;
}

.fade-slow-enter-from,
.fade-slow-leave-to {
  opacity: 0;
}
</style>
