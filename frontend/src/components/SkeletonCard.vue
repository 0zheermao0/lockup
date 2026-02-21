<template>
  <div class="skeleton-card" :class="{ 'animated': animated }">
    <div class="skeleton-header">
      <div class="skeleton-avatar"></div>
      <div class="skeleton-info">
        <div class="skeleton-title"></div>
        <div class="skeleton-meta"></div>
      </div>
    </div>
    <div class="skeleton-content">
      <div class="skeleton-line"></div>
      <div class="skeleton-line short"></div>
    </div>
    <div v-if="showImage" class="skeleton-image"></div>
    <div class="skeleton-actions">
      <div class="skeleton-btn"></div>
      <div class="skeleton-btn"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  animated?: boolean
  showImage?: boolean
}

withDefaults(defineProps<Props>(), {
  animated: true,
  showImage: false
})
</script>

<style scoped>
.skeleton-card {
  background: white;
  border: 3px solid #000;
  border-radius: 8px;
  box-shadow: 4px 4px 0 #000;
  padding: 1.5rem;
  margin-bottom: 1rem;
}

.skeleton-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
}

.skeleton-avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  border: 2px solid #000;
}

.skeleton-info {
  flex: 1;
}

.skeleton-title {
  height: 1.2rem;
  width: 60%;
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  border-radius: 4px;
  margin-bottom: 0.5rem;
}

.skeleton-meta {
  height: 0.875rem;
  width: 40%;
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  border-radius: 4px;
}

.skeleton-content {
  margin-bottom: 1rem;
}

.skeleton-line {
  height: 1rem;
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  border-radius: 4px;
  margin-bottom: 0.5rem;
}

.skeleton-line.short {
  width: 70%;
}

.skeleton-image {
  aspect-ratio: 16/9;
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  border-radius: 8px;
  margin-bottom: 1rem;
  border: 2px solid #000;
}

.skeleton-actions {
  display: flex;
  gap: 1rem;
}

.skeleton-btn {
  height: 2rem;
  width: 80px;
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  border-radius: 4px;
}

.animated .skeleton-avatar,
.animated .skeleton-title,
.animated .skeleton-meta,
.animated .skeleton-line,
.animated .skeleton-image,
.animated .skeleton-btn {
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% {
    background-position: -200% 0;
  }
  100% {
    background-position: 200% 0;
  }
}

/* Stagger delays for multiple skeleton cards */
.skeleton-card:nth-child(1) .skeleton-avatar,
.skeleton-card:nth-child(1) .skeleton-title,
.skeleton-card:nth-child(1) .skeleton-meta,
.skeleton-card:nth-child(1) .skeleton-line,
.skeleton-card:nth-child(1) .skeleton-image,
.skeleton-card:nth-child(1) .skeleton-btn {
  animation-delay: 0ms;
}

.skeleton-card:nth-child(2) .skeleton-avatar,
.skeleton-card:nth-child(2) .skeleton-title,
.skeleton-card:nth-child(2) .skeleton-meta,
.skeleton-card:nth-child(2) .skeleton-line,
.skeleton-card:nth-child(2) .skeleton-image,
.skeleton-card:nth-child(2) .skeleton-btn {
  animation-delay: 100ms;
}

.skeleton-card:nth-child(3) .skeleton-avatar,
.skeleton-card:nth-child(3) .skeleton-title,
.skeleton-card:nth-child(3) .skeleton-meta,
.skeleton-card:nth-child(3) .skeleton-line,
.skeleton-card:nth-child(3) .skeleton-image,
.skeleton-card:nth-child(3) .skeleton-btn {
  animation-delay: 200ms;
}

.skeleton-card:nth-child(4) .skeleton-avatar,
.skeleton-card:nth-child(4) .skeleton-title,
.skeleton-card:nth-child(4) .skeleton-meta,
.skeleton-card:nth-child(4) .skeleton-line,
.skeleton-card:nth-child(4) .skeleton-image,
.skeleton-card:nth-child(4) .skeleton-btn {
  animation-delay: 300ms;
}

.skeleton-card:nth-child(5) .skeleton-avatar,
.skeleton-card:nth-child(5) .skeleton-title,
.skeleton-card:nth-child(5) .skeleton-meta,
.skeleton-card:nth-child(5) .skeleton-line,
.skeleton-card:nth-child(5) .skeleton-image,
.skeleton-card:nth-child(5) .skeleton-btn {
  animation-delay: 400ms;
}
</style>
