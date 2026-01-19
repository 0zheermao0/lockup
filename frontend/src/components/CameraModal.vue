<template>
  <div v-if="isVisible" class="camera-overlay">
    <div class="camera-modal">
      <!-- Header -->
      <div class="camera-header">
        <h3>📷 拍照</h3>
        <button class="close-btn" @click="emit('close')">×</button>
      </div>

      <!-- Camera Viewport -->
      <div class="viewport-wrapper">
        <div class="polaroid"
          :style="{ transform: `rotate(${rotation}deg)` }">
          <div class="viewport">
            <!-- Camera -->
            <div v-if="mode === 'camera'" class="viewport-panel">
              <video ref="video" autoplay playsinline muted />
              <div v-if="countdown > 0" class="overlay">{{ countdown }}</div>
            </div>

            <!-- Preview -->
            <div v-else-if="mode === 'preview'" class="viewport-panel">
              <div class="preview-image" :style="{ transform: previewTransform }">
                <img :src="previewUrl" />
              </div>
            </div>

            <!-- Error -->
            <div v-else-if="mode === 'error'" class="viewport-panel error-panel">
              <div class="error-icon">📷</div>
              <div class="error-text">{{ errorMessage }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Controls -->
      <div class="controls">
        <template v-if="mode === 'camera'">
          <button class="secondary-btn" @click="switchCamera">🔄 切摄像头</button>
          <button class="primary-btn" @click="capture">📸 拍照</button>
        </template>

        <template v-else-if="mode === 'preview'">
          <div class="controls grid-2x2">
            <button class="secondary-btn" @click="rotatePreview">↻ 旋转</button>
            <button class="secondary-btn" @click="mirrorPreview">↔️ 镜像</button>
            <button class="secondary-btn" @click="retake">🔁 重拍</button>
            <button class="primary-btn" @click="confirm">✅ 使用这张</button>
          </div>
        </template>

        <template v-else="mode === 'error'">
          <button class="primary-btn" @click="emit('close')">🔁 关闭</button>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, onBeforeUnmount, computed } from "vue";

/* =======================
 * Props / Emits
 * ======================= */

interface Props {
  isVisible: boolean;
  strictCode?: string | null;
}

interface Emits {
  (e: "close"): void;
  (e: "success", payload: Blob): void;
}

const emit = defineEmits<Emits>();

const props = withDefaults(defineProps<Props>(), {
  isVisible: false,
  strictCode: null,
});

/* =======================
 * Refs & State
 * ======================= */

const video = ref<HTMLVideoElement | null>(null);
const rawBlob = ref<Blob | null>(null);
// preview 用
const previewCanvas = ref<HTMLCanvasElement | null>(null);
const previewUrl = ref<string | null>(null);

const mode = ref<"camera" | "preview">("camera");
const countdown = ref<number>(0);
const facingMode = ref<"environment" | "user">("user");
const errorMessage = ref<string>("");
const rotation = ref<0|90|180|270>(0);
const mirroredHorizontal = ref<boolean>(false);
const mirroredVertical = ref<boolean>(false);

let stream: MediaStream | null = null;

const MAX_IMAGE_SIZE = 2.5 * 1024 * 1024; // 2.5MB

/* =======================
 * Camera Control
 * ======================= */

const stopCamera = (): void => {
  stream?.getTracks().forEach((t) => t.stop());
  stream = null;
};

const pickBestBackCamera = async (): Promise<string | null> => {
  const devices = await navigator.mediaDevices.enumerateDevices();
  const videoDevices = devices.filter((d) => d.kind === "videoinput");

  let bestDeviceId: string | null = null;
  let bestPixels = 0;

  for (const device of videoDevices) {
    try {
      const testStream = await navigator.mediaDevices.getUserMedia({
        video: { deviceId: { exact: device.deviceId } },
      });

      const track = testStream.getVideoTracks()[0];
      const caps = track.getCapabilities?.() ?? {};

      const pixels = (caps.width?.max ?? 0) * (caps.height?.max ?? 0);

      testStream.getTracks().forEach((t) => t.stop());

      if (pixels > bestPixels) {
        bestPixels = pixels;
        bestDeviceId = device.deviceId;
      }
    } catch {
      /* ignore */
    }
  }

  return bestDeviceId;
};

const startCamera = async (): Promise<void> => {
  console.log("Starting camera with facingMode:", facingMode.value);
  stopCamera();

  try {
    if (facingMode.value === "environment") {
      const bestDeviceId = await pickBestBackCamera();

      stream = await navigator.mediaDevices.getUserMedia({
        video: bestDeviceId
          ? {
              deviceId: { exact: bestDeviceId },
              width: { ideal: 1920 },
              height: { ideal: 1080 },
            }
          : { facingMode: "environment" },
      });
    } else {
      stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user" },
      });
    }
  } catch (error) {
    console.error("Error accessing camera:", error);
    errorMessage.value = "无法访问摄像头，请检查权限设置，或者摄像头是否可用。";
    mode.value = "error";
    return;
  }

  if (video.value) {
    video.value.srcObject = stream;
  }
};

const switchCamera = async (): Promise<void> => {
  facingMode.value = facingMode.value === "environment" ? "user" : "environment";
  await startCamera();
};

/* =======================
 * Image Capture & Compress
 * ======================= */

const previewTransform = computed(() => {
  const transforms: string[] = [];

  if (mirroredHorizontal.value) transforms.push("scaleX(-1)");
  if (mirroredVertical.value) transforms.push("scaleY(-1)");

  return transforms.join(" ");
});

async function renderPreview(): Promise<void> {
  if (!rawBlob.value) return;

  const img = await createImageBitmap(rawBlob.value);

  const angle = rotation.value;
  const rad = (angle * Math.PI) / 180;
  const swap = Math.abs(angle) % 180 === 90;

  const canvas = previewCanvas.value ?? document.createElement("canvas");
  previewCanvas.value = canvas;

  canvas.width = swap ? img.height : img.width;
  canvas.height = swap ? img.width : img.height;

  const ctx = canvas.getContext("2d")!;
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  ctx.translate(canvas.width / 2, canvas.height / 2);
  ctx.scale(
    mirroredHorizontal.value ? -1 : 1,
    mirroredVertical.value ? -1 : 1,
  );

  // 照片
  ctx.drawImage(img, -img.width / 2, -img.height / 2);

  // 水印（跟着旋转）
  ctx.save();
  ctx.rotate(-rad);
  drawWatermark(ctx, img.width, img.height);
  ctx.restore();

  // 更新预览 URL（只用于 UI）
  previewUrl.value && URL.revokeObjectURL(previewUrl.value);
  const blob = await new Promise<Blob>((resolve) =>
    canvas.toBlob((b) => resolve(b!), "image/jpeg", 0.8),
  );

  previewUrl.value && URL.revokeObjectURL(previewUrl.value);
  previewUrl.value = URL.createObjectURL(blob);
}

function drawWatermark(
  ctx: CanvasRenderingContext2D,
  imgW: number,
  imgH: number,
) {
  const text = "Lockup-Test";   // TODO:
  const fontSize = 28;

  ctx.save();
  ctx.font = `600 ${fontSize}px system-ui, sans-serif`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";

  ctx.shadowColor = "rgba(0,0,0,0.4)";
  ctx.shadowBlur = 6;
  ctx.fillStyle = "rgba(255,255,255,0.35)";

  // ⭐ 图像中心永远是 (0, 0)
  ctx.fillText(text, 0, 0);

  ctx.restore();
}


async function exportFinalImage(
  maxBytes = 2.5 * 1024 * 1024,
): Promise<Blob> {
  if (!rawBlob.value) {
    throw new Error("No source image");
  }

  const img = await createImageBitmap(rawBlob.value);

  const angle = rotation.value;
  const rad = (angle * Math.PI) / 180;
  const swap = Math.abs(angle) % 180 === 90;

  const canvas = document.createElement("canvas");
  canvas.width = swap ? img.height : img.width;
  canvas.height = swap ? img.width : img.height;

  const ctx = canvas.getContext("2d")!;
  ctx.translate(canvas.width / 2, canvas.height / 2);
  ctx.rotate(rad);
  ctx.scale(
    mirroredHorizontal.value ? -1 : 1,
    mirroredVertical.value ? -1 : 1,
  );

  ctx.drawImage(img, -img.width / 2, -img.height / 2);
  ctx.save();
  ctx.rotate(-rad);
  drawWatermark(ctx, img.width, img.height);
  ctx.restore();

  // === 压缩 ===
  let quality = 0.9;
  while (quality >= 0.5) {
    const blob = await new Promise<Blob>((resolve) =>
      canvas.toBlob((b) => resolve(b!), "image/jpeg", quality),
    );
    if (blob.size <= maxBytes) return blob;
    quality -= 0.05;
  }

  throw new Error("Image too large even after compression");
}


/* =======================
 * Actions
 * ======================= */

const capture = async (): Promise<void> => {
  if (!video.value) return;

  countdown.value = 3;

  const timer = setInterval(() => {
    countdown.value--;
    if (countdown.value === 0) clearInterval(timer);
  }, 1000);

  await new Promise((resolve) => setTimeout(resolve, 3000));

  // === 1. 截一帧，生成 raw ===
  const canvas = document.createElement("canvas");
  canvas.width = video.value.videoWidth;
  canvas.height = video.value.videoHeight;

  const ctx = canvas.getContext("2d")!;
  ctx.drawImage(video.value, 0, 0);

  const raw = await new Promise<Blob>((resolve) =>
    canvas.toBlob((b) => resolve(b!), "image/jpeg", 0.95),
  );

  // === 2. 保存 raw ===
  rawBlob.value = raw;

  // === 3. 初始化编辑状态 ===
  rotation.value = 0;
  mirroredHorizontal.value = false;
  mirroredVertical.value = false;

  // === 4. 生成 preview（canvas / url）===
  await renderPreview();

  stopCamera();
  mode.value = "preview";
};


const retake = async (): Promise<void> => {
  previewUrl.value && URL.revokeObjectURL(previewUrl.value);

  previewUrl.value = null;
  rawBlob.value = null;

  mirroredHorizontal.value = false;
  mirroredVertical.value = false;
  rotation.value = 0;

  mode.value = "camera";
  await startCamera();
};



const confirm = async (): Promise<void> => {
  if (!rawBlob.value) return;

  try {
    const blob = await exportFinalImage(MAX_IMAGE_SIZE);
    emit("success", blob); 
  } catch (e) {
    errorMessage.value = "图片生成失败，请重试";
    mode.value = "error";
  }
};


const mirrorPreview = async (): Promise<void> => {
  if (rotation.value === 0) {         // ↑
    mirroredHorizontal.value = !mirroredHorizontal.value;
  } else if (rotation.value === 90) {  // →
    mirroredVertical.value = !mirroredVertical.value;
  } else if (rotation.value === 180) { // ↓
    mirroredHorizontal.value = !mirroredHorizontal.value;
  }  else if (rotation.value === 270) { // ←
    mirroredVertical.value = !mirroredVertical.value;
  }
  await renderPreview();
};

const rotatePreview = async (): Promise<void> => {
  rotation.value = (rotation.value + 90) % 360;
  await renderPreview();
};

/* =======================
 * Lifecycle
 * ======================= */

// onMounted(startCamera);

watch(
  () => props.isVisible,
  async (visible) => {
    if (visible) {
      await startCamera();
    } else {
      stopCamera();
    }
  },
  { immediate: false },
);


onBeforeUnmount(() => {
  stopCamera();
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value);
  }
});
</script>

<style scoped>
.camera-modal {
  background: white;
  border-radius: 8px;
  border: 2px solid #000;
  box-shadow: 4px 4px 0 #000;
  max-width: 420px;
  margin: 0 auto;
  padding: 0;
}

.camera-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 2px solid #e9ecef;
}

.camera-header h3 {
  margin: 0;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.viewport-wrapper {
  padding: 1rem;
}

.polaroid {
  background: #fff;
  padding: 16px 16px 48px;
  /* 下边更厚 */
  border-radius: 4px;
  box-shadow:
    0 8px 20px rgba(0, 0, 0, 0.15),
    0 1px 2px rgba(0, 0, 0, 0.1);

  width: fit-content;
  margin: 0 auto;
}

.viewport-panel {
  width: 100%;
  height: 100%;
  position: relative;

  display: flex;
  align-items: center;
  justify-content: center;
}

.viewport-panel video,
.viewport-panel img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.error-panel {
  background: #111;
  color: #fff;
  flex-direction: column;
  gap: 12px;
  text-align: center;
  padding: 16px;
}

.error-icon {
  font-size: 32px;
}

.error-text {
  font-size: 14px;
  opacity: 0.85;
}

.viewport {
  width: 260px;
  aspect-ratio: 3 / 4;
  overflow: hidden;
  background: #000;
}

.overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 72px;
  font-weight: 900;
  color: white;
  background: rgba(0, 0, 0, 0.4);
}

.controls {
  display: flex;
  gap: 0.75rem;
  padding: 1rem;
  border-top: 2px solid #e9ecef;
}

.primary-btn,
.secondary-btn {
  flex: 1;
  padding: 0.75rem;
  border-radius: 4px;
  font-weight: 600;
  cursor: pointer;
  border: 2px solid #000;
}

.primary-btn {
  background-color: #007bff;
  color: white;
}

.primary-btn:hover {
  background-color: #0056b3;
}

.secondary-btn {
  background: white;
}

.secondary-btn:hover {
  background: #f8f9fa;
}

.camera-overlay {
  position: fixed;
  inset: 0;
  z-index: 99999;

  display: flex;
  align-items: center;
  justify-content: center;

  background: rgba(0, 0, 0, 0.5);
}

.preview-image {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.2s ease;
}

.preview-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.controls.grid-2x2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
  width: 100%;
}



</style>
