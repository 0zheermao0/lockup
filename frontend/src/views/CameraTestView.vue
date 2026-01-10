<template>
    <div>
        <h1>Camera Test View</h1>
        <p>This is a test view for the CameraModal component.</p>
        <button @click="showCamera = true">Open Camera Modal</button>
    </div>
    <CameraModal
    :isVisible="showCamera"
    @success="handleCameraSuccess"
    @close="showCamera = false"
  />
</template>

<script setup lang="ts">
import CameraModal from '@/components/CameraModal.vue'
import { ref, onMounted } from 'vue';

onMounted(() => {
  console.error("Only for debug use");
  console.error("Only for debug use");
  console.error("Only for debug use");
});

const showCamera = ref(false);
const handleCameraSuccess = (photoData: string) => {
  console.log("Photo captured:", photoData);
  showCamera.value = false;
};

</script>
