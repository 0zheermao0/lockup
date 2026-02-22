<template>
  <div class="calendar-mini">
    <div class="streak-badge">
      <span class="streak-icon">🔥</span>
      <span class="streak-count">{{ currentStreak }}</span>
    </div>

    <div class="three-day-row">
      <div
        v-for="(day, index) in threeDays"
        :key="index"
        class="day-cell"
        :class="{
          'checked': day.isCheckedIn,
          'today': day.isToday,
          'checkable': day.isToday && !day.isCheckedIn && canCheckIn
        }"
        @click="day.isToday && !day.isCheckedIn && canCheckIn && checkIn()"
      >
        <span class="day-label">{{ day.label }}</span>
        <span v-if="day.isCheckedIn" class="check-mark">✓</span>
        <span v-else class="day-num">{{ day.dayOfMonth }}</span>
      </div>
    </div>

    <!-- 签到按钮已移除，点击日期单元格即可签到 -->
    <div v-if="!canCheckIn" class="checked-indicator">✓</div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { authApi } from '../lib/api'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()

const emit = defineEmits<{
  checkedIn: []
  loaded: [canCheckIn: boolean]
}>()

const checkinData = ref<any[]>([])
const canCheckIn = ref(true)
const currentStreak = ref(0)
const checkingIn = ref(false)

// Helper function to format date as YYYY-MM-DD using local time
function formatDateLocal(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const threeDays = computed(() => {
  const today = new Date()
  const yesterday = new Date(today)
  yesterday.setDate(yesterday.getDate() - 1)
  const tomorrow = new Date(today)
  tomorrow.setDate(tomorrow.getDate() + 1)

  const days = [
    { date: yesterday, label: '昨', isToday: false },
    { date: today, label: '今', isToday: true },
    { date: tomorrow, label: '明', isToday: false }
  ]

  return days.map(day => {
    const dateStr = formatDateLocal(day.date)
    const checkin = checkinData.value.find(c => c.date === dateStr)
    return {
      ...day,
      dayOfMonth: day.date.getDate(),
      isCheckedIn: !!checkin
    }
  })
})

const loadCalendarData = async () => {
  try {
    const today = new Date()
    const data = await authApi.getCheckinCalendar(today.getFullYear(), today.getMonth() + 1)
    checkinData.value = data.checkins
    canCheckIn.value = data.can_checkin
    currentStreak.value = data.current_streak
    // 通知父组件今天的签到状态：false 表示今日已签到，true 表示今日未签到
    emit('loaded', data.can_checkin)
  } catch (error) {
    console.error('Failed to load calendar:', error)
  }
}

const checkIn = async () => {
  if (checkingIn.value) return

  checkingIn.value = true
  try {
    const result = await authApi.checkIn()
    if (result.success) {
      checkinData.value.push({
        date: formatDateLocal(new Date()),
        coins_earned: result.coins_earned,
        consecutive_days: result.consecutive_days
      })
      canCheckIn.value = false
      currentStreak.value = result.consecutive_days

      // Update user's coins in auth store
      authStore.refreshUser()

      // Notify parent component that check-in was successful
      emit('checkedIn')

      // Show success notification
      alert(result.message)
    }
  } catch (error: any) {
    alert(error.message || '签到失败')
  } finally {
    checkingIn.value = false
  }
}

onMounted(() => {
  loadCalendarData()
})
</script>

<style scoped>
.calendar-mini {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  height: 36px;
  padding: 0 0.5rem;
  background: linear-gradient(135deg, #f8f9fa, #e9ecef);
  border: 2px solid #000;
  border-radius: 6px;
  min-width: 0;
  flex: 1;
}

.streak-badge {
  display: flex;
  align-items: center;
  gap: 0.125rem;
  font-size: 0.875rem;
  flex-shrink: 0;
}

.streak-icon {
  font-size: 0.875rem;
}

.streak-count {
  font-weight: 700;
  color: #fd7e14;
}

.three-day-row {
  display: flex;
  align-items: center;
  gap: 4px;
  flex: 1;
  justify-content: center;
}

.day-cell {
  width: 28px;
  height: 28px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  font-size: 0.65rem;
  border-radius: 4px;
  position: relative;
  background: white;
  border: 1px solid #dee2e6;
  color: #666;
}

.day-cell.today {
  border-color: #007bff;
  border-width: 2px;
  font-weight: 700;
}

.day-cell.checked {
  background: linear-gradient(135deg, #28a745, #20c997);
  border-color: #28a745;
  color: white;
}

.day-cell.checkable {
  cursor: pointer;
  background: linear-gradient(135deg, #ffd700, #ffed4e);
  border-color: #000;
  animation: pulse 2s infinite;
}

.day-cell.checkable:hover {
  transform: scale(1.05);
}

.day-label {
  font-size: 0.55rem;
  line-height: 1;
  opacity: 0.7;
}

.day-num {
  font-size: 0.7rem;
  line-height: 1;
}

.check-mark {
  font-size: 0.75rem;
  font-weight: 700;
  line-height: 1;
}

/* 签到按钮已移除，点击日期单元格即可签到 */

.checked-indicator {
  color: #28a745;
  font-weight: 700;
  font-size: 1rem;
  flex-shrink: 0;
  width: 40px;
  text-align: center;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}
</style>
