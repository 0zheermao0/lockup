<template>
  <div class="exploration-compass-content">
    <div class="item-info">
      <p><strong>效果：</strong>显示指定区域内所有已埋藏宝物的相关信息（物品类型、难度、埋藏者），但不显示具体位置</p>
      <div class="modal-form">
        <label>选择探索区域：</label>
        <select
          :value="selectedZone"
          class="form-select"
          @change="handleZoneChange"
        >
          <option value="">请选择区域</option>
          <option value="beach">🏖️ 月光海滩 (简单)</option>
          <option value="forest">🌲 神秘森林 (普通)</option>
          <option value="mountain">🏔️ 雾山 (困难)</option>
          <option value="desert">🏜️ 沙漠绿洲 (普通)</option>
          <option value="cave">🕳️ 深邃洞穴 (困难)</option>
        </select>
      </div>
      <p class="warning">⚠️ 确认要使用探索指南针吗？使用后道具将消失</p>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  selectedZone: string
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'update:selectedZone', zone: string): void
}>()

const handleZoneChange = (event: Event) => {
  const target = event.target as HTMLSelectElement
  emit('update:selectedZone', target.value)
}
</script>

<style scoped>
.exploration-compass-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.item-info {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.item-info p {
  margin: 0;
  font-size: 1rem;
  line-height: 1.5;
}

.modal-form {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.modal-form label {
  font-weight: 600;
  font-size: 0.95rem;
  color: #333;
}

.form-select {
  padding: 0.75rem;
  font-size: 1rem;
  border: 3px solid #000;
  border-radius: 8px;
  background: white;
  cursor: pointer;
  box-shadow: 3px 3px 0 #000;
  transition: all 0.2s ease;
}

.form-select:focus {
  outline: none;
  transform: translate(-1px, -1px);
  box-shadow: 4px 4px 0 #000;
}

.warning {
  color: #dc3545;
  font-weight: 600;
  padding: 0.75rem;
  background: rgba(220, 53, 69, 0.1);
  border-radius: 6px;
  border-left: 4px solid #dc3545;
}
</style>
