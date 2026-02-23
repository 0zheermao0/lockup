<template>
  <div class="time-wheel-container">
    <div class="wheel-overlay" v-if="showWheel">
      <div class="overlay-content">
        <div class="spinning-wheel">
          <svg class="wheel-svg" viewBox="0 0 300 300" @click="spinWheel" :class="{ spinning: isSpinning, disabled: isSpinning }">
            <!-- 外圈：增加/减少区域 -->
            <g class="outer-ring">
              <!-- 增加时间区域 (52%) -->
              <path
                d="M 150,150 L 150,30 A 120,120 0 0,1 269.28,90 z"
                class="increase-section"
                fill="#28a745"
              />
              <path
                d="M 150,150 L 269.28,90 A 120,120 0 0,1 269.28,210 z"
                class="increase-section"
                fill="#34ce57"
              />
              <path
                d="M 150,150 L 269.28,210 A 120,120 0 0,1 150,270 z"
                class="increase-section"
                fill="#28a745"
              />

              <!-- 减少时间区域 (48%) -->
              <path
                d="M 150,150 L 150,270 A 120,120 0 0,1 30.72,210 z"
                class="decrease-section"
                fill="#dc3545"
              />
              <path
                d="M 150,150 L 30.72,210 A 120,120 0 0,1 30.72,90 z"
                class="decrease-section"
                fill="#e85368"
              />
              <path
                d="M 150,150 L 30.72,90 A 120,120 0 0,1 150,30 z"
                class="decrease-section"
                fill="#dc3545"
              />
            </g>

            <!-- 内圈：时间档位 -->
            <g class="inner-ring">
              <!-- 5分钟 -->
              <path
                d="M 150,150 L 150,60 A 90,90 0 0,1 213.64,86.36 z"
                class="time-section time-5"
                fill="#ffc107"
              />
              <!-- 15分钟 -->
              <path
                d="M 150,150 L 213.64,86.36 A 90,90 0 0,1 213.64,213.64 z"
                class="time-section time-15"
                fill="#17a2b8"
              />
              <!-- 30分钟 -->
              <path
                d="M 150,150 L 213.64,213.64 A 90,90 0 0,1 86.36,213.64 z"
                class="time-section time-30"
                fill="#6f42c1"
              />
              <!-- 60分钟 -->
              <path
                d="M 150,150 L 86.36,213.64 A 90,90 0 0,1 86.36,86.36 z"
                class="time-section time-60"
                fill="#fd7e14"
              />
              <path
                d="M 150,150 L 86.36,86.36 A 90,90 0 0,1 150,60 z"
                class="time-section time-5-alt"
                fill="#ffc107"
              />
            </g>

            <!-- 指针 -->
            <g class="pointer" :style="{ transform: `rotate(${rotation}deg)`, transformOrigin: '150px 150px' }">
              <polygon points="150,70 155,150 145,150" fill="#000" stroke="#fff" stroke-width="2"/>
              <circle cx="150" cy="150" r="8" fill="#000" stroke="#fff" stroke-width="2"/>
            </g>

            <!-- 标签文字 -->
            <g class="labels">
              <text x="150" y="50" text-anchor="middle" class="time-label">5分</text>
              <text x="230" y="100" text-anchor="middle" class="time-label">15分</text>
              <text x="230" y="220" text-anchor="middle" class="time-label">30分</text>
              <text x="70" y="220" text-anchor="middle" class="time-label">60分</text>
              <text x="70" y="100" text-anchor="middle" class="time-label">5分</text>

              <text x="210" y="65" text-anchor="middle" class="action-label increase">+</text>
              <text x="235" y="150" text-anchor="middle" class="action-label increase">+</text>
              <text x="210" y="235" text-anchor="middle" class="action-label increase">+</text>
              <text x="90" y="235" text-anchor="middle" class="action-label decrease">-</text>
              <text x="65" y="150" text-anchor="middle" class="action-label decrease">-</text>
              <text x="90" y="65" text-anchor="middle" class="action-label decrease">-</text>
            </g>
          </svg>
        </div>

        <div class="wheel-controls">
          <div class="bet-section">
            <label>投入积分：</label>
            <input
              v-model.number="betAmount"
              type="number"
              min="1"
              :disabled="isSpinning"
              class="bet-input"
            />
          </div>

          <button
            @click="spinWheel"
            :disabled="isSpinning || !canSpin"
            class="spin-btn"
          >
            {{ isSpinning ? '转动中...' : '开始转动' }}
          </button>

          <button @click="closeWheel" class="close-btn">关闭</button>
        </div>

        <div v-if="result" class="result-display">
          <div class="result-text" :class="result.isIncrease ? 'increase' : 'decrease'">
            {{ result.isIncrease ? '增加' : '减少' }} {{ result.totalMinutes }} 分钟！
          </div>
          <div class="result-details">
            基础时间：{{ result.baseTime }}分钟 × {{ betAmount }}倍 = {{ result.totalMinutes }}分钟
          </div>
        </div>
      </div>
    </div>

    <!-- 触发按钮 -->
    <button
      v-if="!showWheel"
      @click="openWheel"
      class="time-wheel-trigger"
      :disabled="!canSpin"
    >
      🎰 时间转盘
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { storeApi } from '../lib/api'

interface Props {
  taskId: string
  userCoins: number
}

interface Result {
  isIncrease: boolean
  baseTime: number
  totalMinutes: number
  newEndTime?: string
}

const props = defineProps<Props>()
const emit = defineEmits<{
  timeChanged: [change: { isIncrease: boolean, minutes: number, taskId: string, newEndTime?: string }]
  coinsChanged: [newCoins: number]
  close: []
  error: [message: string]
}>()

// 状态
const showWheel = ref(false)
const isSpinning = ref(false)
const rotation = ref(0)
const betAmount = ref(1)
const result = ref<Result | null>(null)

// 计算属性
const canSpin = computed(() => {
  return props.userCoins >= betAmount.value && !isSpinning.value
})

// 转盘配置
const timeOptions = [5, 15, 30, 60] // 时间档位
const increaseWeight = 0.52 // 增加时间的概率

// 方法
const openWheel = () => {
  result.value = null
  showWheel.value = true
}

const spinWheel = async () => {
  if (!canSpin.value) return

  isSpinning.value = true
  result.value = null

  try {
    // 计算转盘结果
    const spinResult = calculateSpinResult()

    // 模拟转盘动画
    await animateWheel(spinResult)

    // 调用后端API实现时间变更
    const apiResult = await storeApi.playTimeWheel({
      task_id: props.taskId,
      bet_amount: betAmount.value,
      is_increase: spinResult.isIncrease,
      time_change_minutes: spinResult.totalMinutes,
      base_time: spinResult.baseTime
    })

    // 显示结果
    result.value = {
      isIncrease: spinResult.isIncrease,
      baseTime: spinResult.baseTime,
      totalMinutes: spinResult.totalMinutes,
      newEndTime: apiResult.new_end_time || undefined
    }

    // 通知父组件时间变更
    emit('timeChanged', {
      isIncrease: spinResult.isIncrease,
      minutes: spinResult.totalMinutes,
      taskId: props.taskId,
      newEndTime: apiResult.new_end_time || undefined
    })

    // 通知父组件积分变更
    emit('coinsChanged', apiResult.remaining_coins)

  } catch (error: any) {
    console.error('Time wheel API error:', error)
    emit('error', error.response?.data?.error || '时间转盘游戏失败，请重试')
  }

  // 延迟一段时间后重置状态
  setTimeout(() => {
    isSpinning.value = false
  }, 2000)
}

const closeWheel = () => {
  showWheel.value = false
  isSpinning.value = false
  result.value = null
  emit('close')
}

const calculateSpinResult = () => {
  // 1. 确定增加还是减少（52% vs 48%）
  const isIncrease = Math.random() < increaseWeight

  // 2. 随机选择时间档位
  const baseTime = timeOptions[Math.floor(Math.random() * timeOptions.length)] || 5

  // 3. 计算最终时间变化
  const totalMinutes = baseTime * betAmount.value

  return {
    isIncrease,
    baseTime,
    totalMinutes
  }
}

const animateWheel = async (spinResult: { isIncrease: boolean, baseTime: number }) => {
  // 计算目标角度
  let targetAngle = 0

  // 根据结果确定指针应该停在哪个区域
  if (spinResult.isIncrease) {
    // 增加时间区域：0-187.2度（52%）
    targetAngle = Math.random() * 187.2
  } else {
    // 减少时间区域：187.2-360度（48%）
    targetAngle = 187.2 + Math.random() * 172.8
  }

  // 根据时间档位微调角度
  const timeIndex = timeOptions.indexOf(spinResult.baseTime)
  const sectionAngle = 360 / timeOptions.length
  const timeSectionStart = timeIndex * sectionAngle
  const timeSectionEnd = (timeIndex + 1) * sectionAngle

  // 确保指针停在正确的时间档位区域内
  targetAngle = targetAngle % 360
  const currentTimeSection = Math.floor(targetAngle / sectionAngle)
  if (currentTimeSection !== timeIndex) {
    // 调整到正确的时间区域
    targetAngle = timeSectionStart + (targetAngle % sectionAngle)
  }

  // 添加多圈旋转使动画更自然
  const totalRotation = 360 * 3 + targetAngle // 转3圈加目标角度

  return new Promise<void>((resolve) => {
    const startRotation = rotation.value
    const duration = 3000 // 3秒动画
    const startTime = Date.now()

    const animate = () => {
      const elapsed = Date.now() - startTime
      const progress = Math.min(elapsed / duration, 1)

      // 使用缓动函数
      const easeOut = 1 - Math.pow(1 - progress, 3)
      rotation.value = startRotation + (totalRotation - startRotation) * easeOut

      if (progress < 1) {
        requestAnimationFrame(animate)
      } else {
        resolve()
      }
    }

    requestAnimationFrame(animate)
  })
}
</script>

<style scoped>
.time-wheel-container {
  position: relative;
}

.time-wheel-trigger {
  background: #ffc107;
  border: 3px solid #000;
  border-radius: 0;
  padding: 1rem 2rem;
  cursor: pointer;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: #000;
  box-shadow: 4px 4px 0 #000;
  transition: all 0.2s ease;
  min-height: 48px;
}

.time-wheel-trigger:hover:not(:disabled) {
  transform: translate(2px, 2px);
  box-shadow: 2px 2px 0 #000;
}

.time-wheel-trigger:disabled {
  background: #6c757d;
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
  box-shadow: 2px 2px 0 #000;
}

.wheel-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.overlay-content {
  background: white;
  border: 4px solid #000;
  border-radius: 0;
  padding: 2rem;
  max-width: 90vw;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1.5rem;
  box-shadow: 12px 12px 0 #000;
}

.spinning-wheel {
  position: relative;
}

.wheel-svg {
  width: 300px;
  height: 300px;
  cursor: pointer;
  transition: opacity 0.3s ease;
}

.wheel-svg.disabled {
  cursor: not-allowed;
  opacity: 0.8;
}

.wheel-svg.spinning {
  pointer-events: none;
}

.outer-ring, .inner-ring {
  transition: all 0.3s ease;
}

.increase-section:hover {
  filter: brightness(1.1);
}

.decrease-section:hover {
  filter: brightness(1.1);
}

.time-section:hover {
  filter: brightness(1.1);
}

.time-label {
  font-size: 14px;
  font-weight: bold;
  fill: #000;
  pointer-events: none;
}

.action-label {
  font-size: 18px;
  font-weight: bold;
  pointer-events: none;
}

.action-label.increase {
  fill: #fff;
}

.action-label.decrease {
  fill: #fff;
}

.wheel-controls {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  width: 100%;
}

.bet-section {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: bold;
}

.bet-section select,
.bet-input {
  padding: 0.75rem;
  border: 3px solid #000;
  border-radius: 0;
  font-weight: 900;
  background: white;
  min-width: 100px;
}

.spin-btn {
  background: #28a745;
  border: 3px solid #000;
  border-radius: 0;
  padding: 1rem 2rem;
  cursor: pointer;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: white;
  font-size: 1.1rem;
  box-shadow: 4px 4px 0 #000;
  transition: all 0.2s ease;
  min-height: 48px;
}

.spin-btn:hover:not(:disabled) {
  transform: translate(2px, 2px);
  box-shadow: 2px 2px 0 #000;
}

.spin-btn:disabled {
  background: #6c757d;
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
  box-shadow: 2px 2px 0 #000;
}

.close-btn {
  background: #dc3545;
  border: 3px solid #000;
  border-radius: 0;
  padding: 0.75rem 1.5rem;
  cursor: pointer;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: white;
  box-shadow: 3px 3px 0 #000;
  transition: all 0.2s ease;
  min-height: 48px;
}

.close-btn:hover {
  background: #c82333;
  transform: translate(1px, 1px);
  box-shadow: 2px 2px 0 #000;
}

.result-display {
  text-align: center;
  padding: 1rem;
  border: 2px solid #000;
  border-radius: 8px;
  background: #f8f9fa;
  width: 100%;
}

.result-text {
  font-size: 1.5rem;
  font-weight: bold;
  margin-bottom: 0.5rem;
}

.result-text.increase {
  color: #28a745;
}

.result-text.decrease {
  color: #dc3545;
}

.result-details {
  color: #666;
  font-size: 0.9rem;
}

/* 动画 */
@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.pointer {
  transition: transform 3s cubic-bezier(0.25, 0.1, 0.25, 1);
}

/* 移动端适配 */
@media (max-width: 768px) {
  .overlay-content {
    padding: 1rem;
    margin: 1rem;
  }

  .wheel-svg {
    width: 250px;
    height: 250px;
  }

  .time-label {
    font-size: 12px;
  }

  .action-label {
    font-size: 16px;
  }
}
</style>