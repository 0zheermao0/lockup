<template>
  <div class="item-action-modals">
    <!-- Universal Key Modal -->
    <BaseItemModal
      v-if="activeModal === 'universal_key'"
      :is-visible="true"
      title="使用万能钥匙"
      icon="🗝️"
      size="large"
      :show-confirm-button="false"
      :show-cancel-button="false"
      @close="closeModal"
    >
      <template #body>
        <UniversalKeyContent
          :item="activeItem"
          :available-tasks="modalData.availableTasks || []"
          :selected-task-id="modalData.selectedTaskId || ''"
          :is-processing="modalData.isProcessing || false"
          @update:selected-task-id="updateModalData('selectedTaskId', $event)"
          @confirm="handleUniversalKeyConfirm"
        />
      </template>
    </BaseItemModal>

    <!-- Detection Radar Modal -->
    <BaseItemModal
      v-if="activeModal === 'detection_radar'"
      :is-visible="true"
      title="使用探测雷达"
      icon="🎯"
      :confirm-text="modalData.detectionResults ? '确定' : '开始探测'"
      :is-processing="modalData.isProcessing || false"
      :confirm-disabled="!modalData.detectionResults && !activeItem"
      @close="closeModal"
      @confirm="handleDetectionRadarConfirm"
    >
      <template #body>
        <DetectionRadarContent
          :detection-results="modalData.detectionResults"
        />
      </template>
    </BaseItemModal>

    <!-- Blizzard Bottle Modal -->
    <BaseItemModal
      v-if="activeModal === 'blizzard_bottle'"
      :is-visible="true"
      title="使用暴雪瓶"
      icon="🌨️"
      :confirm-text="modalData.blizzardResults ? '确定' : '释放暴雪'"
      :is-processing="modalData.isProcessing || false"
      :confirm-disabled="!modalData.blizzardResults && !activeItem"
      @close="closeModal"
      @confirm="handleBlizzardBottleConfirm"
    >
      <template #body>
        <BlizzardBottleContent
          :blizzard-results="modalData.blizzardResults"
        />
      </template>
    </BaseItemModal>

    <!-- Sun Bottle Modal -->
    <BaseItemModal
      v-if="activeModal === 'sun_bottle'"
      :is-visible="true"
      title="使用太阳瓶"
      icon="☀️"
      :confirm-text="modalData.sunBottleResults ? '确定' : '释放阳光'"
      :is-processing="modalData.isProcessing || false"
      :confirm-disabled="!modalData.sunBottleResults && !activeItem"
      @close="closeModal"
      @confirm="handleSunBottleConfirm"
    >
      <template #body>
        <SunBottleContent
          :sun-bottle-results="modalData.sunBottleResults"
        />
      </template>
    </BaseItemModal>

    <!-- Time Hourglass Modal -->
    <BaseItemModal
      v-if="activeModal === 'time_hourglass'"
      :is-visible="true"
      title="使用时间沙漏"
      icon="⏳"
      :confirm-text="modalData.hourglassResults ? '确定' : '使用时间沙漏'"
      :is-processing="modalData.isProcessing || false"
      :confirm-disabled="!modalData.hourglassResults && !activeItem"
      @close="closeModal"
      @confirm="handleTimeHourglassConfirm"
    >
      <template #body>
        <TimeHourglassContent
          :hourglass-results="modalData.hourglassResults"
        />
      </template>
    </BaseItemModal>

    <!-- Lucky Charm Modal -->
    <BaseItemModal
      v-if="activeModal === 'lucky_charm'"
      :is-visible="true"
      title="使用幸运符"
      icon="🍀"
      :is-processing="modalData.isProcessing || false"
      @close="closeModal"
      @confirm="handleLuckyCharmConfirm"
    >
      <template #body>
        <div class="item-info">
          <p><strong>效果：</strong>下一个带锁任务的小时奖励概率+20%</p>
          <p><strong>说明：</strong>使用后立即生效，持续到下一个任务完成</p>
          <p class="warning">⚠️ 确认要使用幸运符吗？使用后道具将消失</p>
        </div>
      </template>
    </BaseItemModal>

    <!-- Energy Potion Modal -->
    <BaseItemModal
      v-if="activeModal === 'energy_potion'"
      :is-visible="true"
      title="使用活力药水"
      icon="⚡"
      :is-processing="modalData.isProcessing || false"
      @close="closeModal"
      @confirm="handleEnergyPotionConfirm"
    >
      <template #body>
        <div class="item-info">
          <p><strong>效果：</strong>24小时内活跃度衰减减少50%</p>
          <p><strong>持续时间：</strong>24小时</p>
          <p class="warning">⚠️ 确认要使用活力药水吗？使用后道具将消失</p>
        </div>
      </template>
    </BaseItemModal>

    <!-- Time Anchor Modal -->
    <BaseItemModal
      v-if="activeModal === 'time_anchor'"
      :is-visible="true"
      title="使用时间锚点"
      icon="⚓"
      size="large"
      :show-confirm-button="false"
      :show-cancel-button="false"
      @close="closeModal"
    >
      <template #body>
        <TimeAnchorContent
          :item="activeItem"
          :tasks="modalData.timeAnchorTasks || []"
          :saved-task-info="modalData.savedTaskInfo"
          :is-processing="modalData.isProcessing || false"
          @confirm="handleTimeAnchorConfirm"
        />
      </template>
    </BaseItemModal>

    <!-- Exploration Compass Modal -->
    <BaseItemModal
      v-if="activeModal === 'exploration_compass'"
      :is-visible="true"
      title="使用探索指南针"
      icon="🧭"
      :is-processing="modalData.isProcessing || false"
      :confirm-disabled="!modalData.selectedCompassZone"
      @close="closeModal"
      @confirm="handleExplorationCompassConfirm"
    >
      <template #body>
        <ExplorationCompassContent
          :selected-zone="modalData.selectedCompassZone || ''"
          @update:selected-zone="updateModalData('selectedCompassZone', $event)"
        />
      </template>
    </BaseItemModal>

    <!-- Influence Crown Modal -->
    <BaseItemModal
      v-if="activeModal === 'influence_crown'"
      :is-visible="true"
      title="使用影响力皇冠"
      icon="👑"
      :is-processing="modalData.isProcessing || false"
      @close="closeModal"
      @confirm="handleInfluenceCrownConfirm"
    >
      <template #body>
        <div class="item-info">
          <p><strong>效果：</strong>48小时内，所有投票的权重变为3倍</p>
          <p><strong>持续时间：</strong>48小时</p>
          <p class="warning">⚠️ 确认要使用影响力皇冠吗？使用后道具将消失</p>
        </div>
      </template>
    </BaseItemModal>

    <!-- Small Campfire Modal -->
    <BaseItemModal
      v-if="activeModal === 'small_campfire'"
      :is-visible="true"
      title="使用小火堆"
      icon="🔥"
      size="large"
      :is-processing="modalData.isProcessing || false"
      :confirm-disabled="(modalData.frozenTasks || []).length === 0"
      @close="closeModal"
      @confirm="handleSmallCampfireConfirm"
    >
      <template #body>
        <SmallCampfireContent
          :frozen-tasks="modalData.frozenTasks || []"
          :item="activeItem"
        />
      </template>
    </BaseItemModal>

    <!-- Note Edit Modal -->
    <BaseItemModal
      v-if="activeModal === 'note_edit'"
      :is-visible="true"
      title="编辑纸条"
      icon="✏️"
      :show-confirm-button="false"
      :show-cancel-button="false"
      @close="closeModal"
    >
      <template #body>
        <NoteEditContent
          :initial-content="modalData.noteContent || ''"
          :is-processing="modalData.isProcessing || false"
          @confirm="handleNoteEditConfirm"
        />
      </template>
    </BaseItemModal>

    <!-- Bury Item Modal -->
    <BaseItemModal
      v-if="activeModal === 'bury'"
      :is-visible="true"
      title="掩埋物品"
      icon="⛏️"
      :show-confirm-button="false"
      :show-cancel-button="false"
      @close="closeModal"
    >
      <template #body>
        <BuryItemContent
          :item="activeItem"
          :is-processing="modalData.isProcessing || false"
          @confirm="handleBuryItemConfirm"
        />
      </template>
    </BaseItemModal>

    <!-- Discard Item Modal -->
    <BaseItemModal
      v-if="activeModal === 'discard'"
      :is-visible="true"
      title="丢弃物品"
      icon="🗑️"
      :is-processing="modalData.isProcessing || false"
      @close="closeModal"
      @confirm="handleDiscardItemConfirm"
    >
      <template #body>
        <DiscardItemContent
          :item="activeItem"
        />
      </template>
    </BaseItemModal>
  </div>
</template>

<script setup lang="ts">
import { reactive, watch } from 'vue'
import type { Item } from '@/types'
import BaseItemModal from './item-modals/BaseItemModal.vue'
import UniversalKeyContent from './item-modals/UniversalKeyContent.vue'
import DetectionRadarContent from './item-modals/DetectionRadarContent.vue'
import BlizzardBottleContent from './item-modals/BlizzardBottleContent.vue'
import SunBottleContent from './item-modals/SunBottleContent.vue'
import TimeHourglassContent from './item-modals/TimeHourglassContent.vue'
import TimeAnchorContent from './item-modals/TimeAnchorContent.vue'
import ExplorationCompassContent from './item-modals/ExplorationCompassContent.vue'
import SmallCampfireContent from './item-modals/SmallCampfireContent.vue'
import NoteEditContent from './item-modals/NoteEditContent.vue'
import BuryItemContent from './item-modals/BuryItemContent.vue'
import DiscardItemContent from './item-modals/DiscardItemContent.vue'

export type ItemActionModalType =
  | 'universal_key'
  | 'detection_radar'
  | 'blizzard_bottle'
  | 'sun_bottle'
  | 'time_hourglass'
  | 'lucky_charm'
  | 'energy_potion'
  | 'time_anchor'
  | 'exploration_compass'
  | 'influence_crown'
  | 'small_campfire'
  | 'note_edit'
  | 'bury'
  | 'discard'

interface Props {
  /** Currently active modal type */
  activeModal: ItemActionModalType | null
  /** The item being acted upon */
  activeItem: Item | null
  /** Initial data for the modal */
  initialData?: Record<string, any>
}

const props = withDefaults(defineProps<Props>(), {
  initialData: () => ({})
})

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'action', action: string, data: any): void
  (e: 'update:data', key: string, value: any): void
}>()

// Reactive modal data that can be updated by child components
const modalData = reactive<Record<string, any>>({})

// Watch for initialData changes
watch(() => props.initialData, (newData) => {
  Object.assign(modalData, newData)
}, { immediate: true, deep: true })

// Update modal data helper
const updateModalData = (key: string, value: any) => {
  modalData[key] = value
  emit('update:data', key, value)
}

// Close modal handler
const closeModal = () => {
  // Clear modal data
  Object.keys(modalData).forEach(key => delete modalData[key])
  emit('close')
}

// Action confirm handlers
const handleUniversalKeyConfirm = (data: any) => {
  emit('action', 'universal_key', data)
}

const handleDetectionRadarConfirm = () => {
  if (modalData.detectionResults) {
    closeModal()
  } else {
    emit('action', 'detection_radar', {})
  }
}

const handleBlizzardBottleConfirm = () => {
  if (modalData.blizzardResults) {
    closeModal()
  } else {
    emit('action', 'blizzard_bottle', {})
  }
}

const handleSunBottleConfirm = () => {
  if (modalData.sunBottleResults) {
    closeModal()
  } else {
    emit('action', 'sun_bottle', {})
  }
}

const handleTimeHourglassConfirm = () => {
  if (modalData.hourglassResults) {
    closeModal()
  } else {
    emit('action', 'time_hourglass', {})
  }
}

const handleLuckyCharmConfirm = () => {
  emit('action', 'lucky_charm', {})
}

const handleEnergyPotionConfirm = () => {
  emit('action', 'energy_potion', {})
}

const handleTimeAnchorConfirm = (data: any) => {
  emit('action', 'time_anchor', data)
}

const handleExplorationCompassConfirm = () => {
  emit('action', 'exploration_compass', {
    zone: modalData.selectedCompassZone
  })
}

const handleInfluenceCrownConfirm = () => {
  emit('action', 'influence_crown', {})
}

const handleSmallCampfireConfirm = () => {
  emit('action', 'small_campfire', {})
}

const handleNoteEditConfirm = (data: { content: string }) => {
  emit('action', 'note_edit', data)
}

const handleBuryItemConfirm = (data: any) => {
  emit('action', 'bury', data)
}

const handleDiscardItemConfirm = () => {
  emit('action', 'discard', {})
}

// Expose methods for parent
defineExpose({
  updateModalData,
  closeModal
})
</script>

<style scoped>
.item-action-modals {
  /* Container for all modals */
}

.item-info {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.item-info p {
  margin: 0;
  font-size: 1rem;
  line-height: 1.5;
}

.item-info .warning {
  color: #dc3545;
  font-weight: 600;
  padding: 0.75rem;
  background: rgba(220, 53, 69, 0.1);
  border-radius: 6px;
  border-left: 4px solid #dc3545;
}
</style>
