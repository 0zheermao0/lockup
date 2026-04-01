<template>
  <div v-if="tells.length > 0" class="tell-text-renderer">
    <div
      v-for="(tell, index) in tells"
      :key="index"
      class="tell-text-renderer__item"
    >
      {{ tell.tell_text ?? tell.text }}
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  tells: Array<{ type: string; text: string; tell_text?: string }>
}>()
</script>

<style scoped>
.tell-text-renderer {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.tell-text-renderer__item {
  font-style: italic;
  font-size: 0.85em;
  color: #555;
  border-left: 2px solid #888;
  padding-left: 8px;
  margin-top: 4px;
  text-decoration: underline dotted #888;
  line-height: 1.4;
}
</style>
