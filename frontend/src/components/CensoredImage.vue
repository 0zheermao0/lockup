<template>
  <div class="censored-image-container" :class="$props.class">
    <img
      :src="src"
      :alt="alt"
      class="censored-image"
      @click="handleClick"
    />
    <div
      v-if="needsCensor"
      class="censor-overlay"
      @click="handleClick"
    >
      <div class="censor-content">
        <div class="censor-icon">🔒</div>
        <div class="censor-text">还需 {{ likesNeeded }} 个赞解锁</div>
        <div class="censor-hint">点击查看原图</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  src: string
  alt: string
  likesCount: number
  class?: string
}

const props = defineProps<Props>()

const emit = defineEmits<{
  click: []
}>()

const needsCensor = computed(() => props.likesCount < 5)
const likesNeeded = computed(() => Math.max(0, 5 - props.likesCount))

const handleClick = () => {
  emit('click')
}
</script>

<style scoped>
.censored-image-container {
  position: relative;
  display: inline-block;
  overflow: hidden;
}

.censored-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.censor-overlay {
  position: absolute;
  inset: 0;
  backdrop-filter: blur(24px);
  background:
    url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E") repeat,
    rgba(0, 0, 0, 0.4);
  background-size: 8px 8px, auto;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: opacity 0.3s ease;
}

.censor-overlay:hover {
  opacity: 0.95;
}

.censor-content {
  background: rgba(255, 255, 255, 0.95);
  padding: 0.75rem 1rem;
  border: 3px solid #000;
  box-shadow: 4px 4px 0 #000;
  text-align: center;
  transition: transform 0.2s ease;
}

.censor-overlay:hover .censor-content {
  transform: scale(1.02);
}

.censor-icon {
  font-size: 1.5rem;
  margin-bottom: 0.25rem;
}

.censor-text {
  font-weight: 900;
  font-size: 0.875rem;
  color: #000;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.censor-hint {
  font-size: 0.75rem;
  color: #666;
  margin-top: 0.25rem;
}
</style>
