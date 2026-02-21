<template>
  <div class="skeleton-loader" :class="{ 'stagger': stagger }">
    <SkeletonCard
      v-for="n in count"
      :key="n"
      :animated="animated"
      :show-image="showImage"
    />
  </div>
</template>

<script setup lang="ts">
import SkeletonCard from './SkeletonCard.vue'

interface Props {
  count?: number
  animated?: boolean
  showImage?: boolean
  stagger?: boolean
}

withDefaults(defineProps<Props>(), {
  count: 3,
  animated: true,
  showImage: false,
  stagger: true
})
</script>

<style scoped>
.skeleton-loader {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
</style>
