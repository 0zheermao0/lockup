<template>
  <Teleport to="body">
    <!-- Overlay Transition -->
    <Transition name="modal-overlay">
      <div
        v-if="isVisible"
        class="modal-overlay"
        :class="{ 'modal-backdrop-blur': backdropBlur }"
        @click="handleOverlayClick"
      >
        <!-- Content Transition -->
        <Transition
          name="modal-content"
          @after-leave="onAfterLeave"
        >
          <div
            v-if="isVisible"
            class="modal-container"
            :class="[sizeClass, modalClass]"
            @click.stop
          >
            <!-- Modal Header -->
            <div v-if="showHeader" class="modal-header">
              <slot name="header">
                <h3 class="modal-title">{{ title }}</h3>
              </slot>
              <button
                v-if="showCloseButton"
                class="modal-close-btn"
                @click="close"
                aria-label="关闭"
              >
                ×
              </button>
            </div>

            <!-- Modal Body -->
            <div class="modal-body">
              <Transition name="modal-body">
                <div v-if="isVisible">
                  <slot />
                </div>
              </Transition>
            </div>

            <!-- Modal Footer -->
            <div v-if="showFooter || $slots.footer" class="modal-footer">
              <slot name="footer">
                <button class="neo-button" @click="close">关闭</button>
              </slot>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, watch, onMounted, onUnmounted } from 'vue'

type ModalSize = 'sm' | 'md' | 'lg' | 'xl' | 'full'

interface Props {
  isVisible: boolean
  title?: string
  size?: ModalSize
  modalClass?: string
  showHeader?: boolean
  showFooter?: boolean
  showCloseButton?: boolean
  backdropBlur?: boolean
  closeOnOverlayClick?: boolean
  closeOnEsc?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  title: '',
  size: 'md',
  modalClass: '',
  showHeader: true,
  showFooter: false,
  showCloseButton: true,
  backdropBlur: true,
  closeOnOverlayClick: true,
  closeOnEsc: true
})

const emit = defineEmits<{
  close: []
  closed: []
}>()

const sizeClass = computed(() => {
  const sizes: Record<ModalSize, string> = {
    sm: 'modal-sm',
    md: 'modal-md',
    lg: 'modal-lg',
    xl: 'modal-xl',
    full: 'modal-full'
  }
  return sizes[props.size]
})

const close = () => {
  emit('close')
}

const handleOverlayClick = () => {
  if (props.closeOnOverlayClick) {
    close()
  }
}

const onAfterLeave = () => {
  emit('closed')
}

// Handle ESC key
const handleKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Escape' && props.isVisible && props.closeOnEsc) {
    close()
  }
}

// Lock body scroll when modal is open
watch(() => props.isVisible, (visible) => {
  if (visible) {
    document.body.style.overflow = 'hidden'
  } else {
    document.body.style.overflow = ''
  }
})

onMounted(() => {
  document.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
  document.body.style.overflow = ''
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
  overflow: auto;
}

.modal-container {
  background: white;
  border-radius: 8px;
  border: 3px solid #000;
  box-shadow: 8px 8px 0 #000;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  position: relative;
}

/* Size variants */
.modal-sm {
  width: 100%;
  max-width: 400px;
}

.modal-md {
  width: 100%;
  max-width: 600px;
}

.modal-lg {
  width: 100%;
  max-width: 800px;
}

.modal-xl {
  width: 100%;
  max-width: 1000px;
}

.modal-full {
  width: 95%;
  max-width: 1200px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 2px solid #e9ecef;
  flex-shrink: 0;
}

.modal-title {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.modal-close-btn {
  background: none;
  border: 2px solid #000;
  border-radius: 50%;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  cursor: pointer;
  transition: all 0.2s var(--ease-bounce);
  box-shadow: 2px 2px 0 #000;
}

.modal-close-btn:hover {
  background: #f8f9fa;
  transform: translate(-2px, -2px);
  box-shadow: 4px 4px 0 #000;
}

.modal-close-btn:active {
  transform: translate(1px, 1px);
  box-shadow: 1px 1px 0 #000;
}

.modal-body {
  padding: 1.5rem;
  overflow-y: auto;
  flex: 1;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  padding: 1rem 1.5rem;
  border-top: 2px solid #e9ecef;
  flex-shrink: 0;
}

/* Mobile responsive */
@media (max-width: 640px) {
  .modal-overlay {
    padding: 0.5rem;
    align-items: flex-end;
  }

  .modal-container {
    max-height: 95vh;
    width: 100%;
  }

  .modal-sm,
  .modal-md,
  .modal-lg,
  .modal-xl {
    max-width: 100%;
  }

  .modal-header,
  .modal-body,
  .modal-footer {
    padding: 1rem;
  }
}
</style>
