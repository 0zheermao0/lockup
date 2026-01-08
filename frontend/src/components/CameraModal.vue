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
        <div class="frame polaroid">
          <div class="viewport">
            <video v-show="mode === 'camera'" ref="video" autoplay playsinline />
            <img v-show="mode === 'preview'" :src="photo" />
            <div v-if="countdown > 0" class="overlay">{{ countdown }}</div>
          </div>
        </div>
      </div>

      <!-- Controls -->
      <div class="controls">
        <template v-if="mode === 'camera'">
          <button class="secondary-btn" @click="switchCamera">🔄 切摄像头</button>
          <button class="primary-btn" @click="capture">📸 拍照</button>
        </template>

        <template v-else>
          <button class="secondary-btn" @click="retake">🔁 重拍</button>
          <button class="primary-btn" @click="confirm">✅ 使用这张</button>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, onBeforeUnmount } from "vue";

/* =======================
 * Props / Emits
 * ======================= */

interface Props {
  isVisible: boolean;
  strictCode?: string | null;
}

interface Emits {
  (e: "close"): void;
  (e: "success", payload: string): void;
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
const photo = ref<string | null>(null);

const mode = ref<"camera" | "preview">("camera");
const countdown = ref<number>(0);
const facingMode = ref<"environment" | "user">("environment");

let stream: MediaStream | null = null;

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

    if (video.value) {
      video.value.srcObject = stream;
    }
  } catch (e) {
    console.error("Error starting camera:", e);
    emit("close");
  }
};

const switchCamera = async (): Promise<void> => {
  facingMode.value = facingMode.value === "environment" ? "user" : "environment";
  await startCamera();
};

/* =======================
 * Image Capture & Compress
 * ======================= */

async function captureCompressedImage(
  videoEl: HTMLVideoElement,
  {
    maxEdge = 1600,
    quality = 0.8,
  }: {
    maxEdge?: number;
    quality?: number;
  } = {},
): Promise<Blob> {
  const vw = videoEl.videoWidth;
  const vh = videoEl.videoHeight;

  const scale = Math.min(1, maxEdge / Math.max(vw, vh));
  const cw = Math.round(vw * scale);
  const ch = Math.round(vh * scale);

  const canvas = document.createElement("canvas");
  canvas.width = cw;
  canvas.height = ch;

  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Canvas context unavailable");

  ctx.drawImage(videoEl, 0, 0, cw, ch);

  return new Promise<Blob>((resolve, reject) => {
    canvas.toBlob(
      (blob) => (blob ? resolve(blob) : reject(new Error("toBlob failed"))),
      "image/jpeg",
      quality,
    );
  });
}

async function compressUntilFit(videoEl: HTMLVideoElement, maxBytes: number): Promise<Blob> {
  let quality = 0.85;

  while (quality >= 0.5) {
    const blob = await captureCompressedImage(videoEl, {
      maxEdge: 1600,
      quality,
    });

    if (blob.size <= maxBytes) {
      return blob;
    }

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

  let blob = await captureCompressedImage(video.value);

  if (blob.size > 2.5 * 1024 * 1024) {
    try {
      blob = await compressUntilFit(video.value, 2.5 * 1024 * 1024);
    } catch {
      emit("error", "Captured image is too large even after compression.");
      return;
    }
  }

  if (photo.value) {
    URL.revokeObjectURL(photo.value);
  }

  photo.value = URL.createObjectURL(blob);

  stopCamera();
  mode.value = "preview";
};

const retake = async (): Promise<void> => {
  if (photo.value) {
    URL.revokeObjectURL(photo.value);
  }

  photo.value = null;
  mode.value = "camera";
  await startCamera();
};

const confirm = (): void => {
  if (photo.value) {
    emit("success", photo.value);
  }
};

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

/* =======================
 * Lifecycle
 * ======================= */

// onMounted(startCamera);

onBeforeUnmount(() => {
  stopCamera();
  if (photo.value) {
    URL.revokeObjectURL(photo.value);
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
  z-index: 99999;
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
  padding: 16px 16px 36px;
  /* 下边更厚 */
  border-radius: 4px;
  box-shadow:
    0 8px 20px rgba(0, 0, 0, 0.15),
    0 1px 2px rgba(0, 0, 0, 0.1);

  width: fit-content;
  margin: 0 auto;

  /* 微微歪一点，更像随手拍 */
  transform: rotate(-1.5deg);
}

.polaroid:hover {
  transform: rotate(0deg) scale(1.02);
  transition: 0.2s ease;
}

.viewport {
  width: 280px;
  aspect-ratio: 3 / 4;
  /* 拍立得照片是正方形 */
  overflow: hidden;
  background: #000;
  position: relative;
}

.viewport video,
.viewport img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
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
</style>
