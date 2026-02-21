<template>
  <div class="calendar-card">
    <div class="calendar-header">
      <div class="streak-display">
        <span class="streak-icon">🔥</span>
        <span class="streak-count">{{ currentStreak }}</span>
        <span class="streak-label">连续签到</span>
      </div>
      <button
        v-if="canCheckIn"
        @click="checkIn"
        :disabled="checkingIn"
        class="checkin-btn"
        :class="{ 'checking': checkingIn }"
      >
        <span v-if="checkingIn">...</span>
        <span v-else>签到</span>
      </button>
      <div v-else class="checked-badge">✓ 已签到</div>
    </div>

    <div class="calendar-weekdays">
      <span v-for="day in weekdays" :key="day">{{ day }}</span>
    </div>

    <div class="calendar-days">
      <div
        v-for="(day, index) in calendarDays"
        :key="index"
        class="day-cell"
        :class="{
          'other-month': !day.isCurrentMonth,
          'today': day.isToday,
          'checked': day.isCheckedIn,
          'checkable': day.isToday && !day.isCheckedIn && canCheckIn
        }"
        @click="handleDayClick(day)"
      >
        <span class="day-number">{{ day.dayOfMonth }}</span>
        <div v-if="day.isCheckedIn" class="check-icon">✓</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { authApi } from '../lib/api'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()

const currentDate = ref(new Date())
const checkinData = ref<any[]>([])
const canCheckIn = ref(true)
const currentStreak = ref(0)
const checkingIn = ref(false)

const weekdays = ['日', '一', '二', '三', '四', '五', '六']

const currentYear = computed(() => currentDate.value.getFullYear())
const currentMonth = computed(() => currentDate.value.getMonth() + 1)

// Helper function to format date as YYYY-MM-DD using local time
function formatDateLocal(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const calendarDays = computed(() => {
  const year = currentYear.value
  const month = currentMonth.value - 1

  const firstDay = new Date(year, month, 1)
  const lastDay = new Date(year, month + 1, 0)
  const daysInMonth = lastDay.getDate()
  const startDayOfWeek = firstDay.getDay()

  const days = []
  const today = new Date()

  // Previous month days
  const prevMonthLastDay = new Date(year, month, 0).getDate()
  for (let i = startDayOfWeek - 1; i >= 0; i--) {
    days.push({
      date: new Date(year, month - 1, prevMonthLastDay - i),
      dayOfMonth: prevMonthLastDay - i,
      isCurrentMonth: false,
      isToday: false,
      isCheckedIn: false
    })
  }

  // Current month days
  for (let i = 1; i <= daysInMonth; i++) {
    const date = new Date(year, month, i)
    const dateStr = formatDateLocal(date)
    const checkin = checkinData.value.find(c => c.date === dateStr)

    days.push({
      date,
      dayOfMonth: i,
      isCurrentMonth: true,
      isToday: formatDateLocal(date) === formatDateLocal(today),
      isCheckedIn: !!checkin,
      coinsEarned: checkin?.coins_earned || 0,
      consecutiveDays: checkin?.consecutive_days || 0
    })
  }

  // Next month days - only fill to 35 days (5 rows) instead of 42
  const remainingCells = 35 - days.length
  for (let i = 1; i <= remainingCells && i <= 7; i++) {
    days.push({
      date: new Date(year, month + 1, i),
      dayOfMonth: i,
      isCurrentMonth: false,
      isToday: false,
      isCheckedIn: false
    })
  }

  return days
})

const loadCalendarData = async () => {
  try {
    const data = await authApi.getCheckinCalendar(currentYear.value, currentMonth.value)
    checkinData.value = data.checkins
    canCheckIn.value = data.can_checkin
    currentStreak.value = data.current_streak
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

      // Show success notification
      alert(result.message)
    }
  } catch (error: any) {
    alert(error.message || '签到失败')
  } finally {
    checkingIn.value = false
  }
}

const handleDayClick = (day: any) => {
  if (day.isToday && !day.isCheckedIn && canCheckIn.value) {
    checkIn()
  }
}

onMounted(() => {
  loadCalendarData()
})
</script>

<style scoped>
.calendar-card {
  background: white;
  padding: 0.5rem;
  border-radius: 8px;
  border: 2px solid #000;
  box-shadow: 4px 4px 0 #000;
}

.calendar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.streak-display {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.streak-icon {
  font-size: 1rem;
}

.streak-count {
  font-size: 1.25rem;
  font-weight: 900;
  color: #fd7e14;
}

.streak-label {
  font-size: 0.75rem;
  color: #666;
}

.checkin-btn {
  background: linear-gradient(135deg, #28a745, #20c997);
  color: white;
  border: 2px solid #000;
  padding: 0.25rem 0.75rem;
  border-radius: 6px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 2px 2px 0 #000;
  transition: all 0.2s;
  font-size: 0.8rem;
}

.checkin-btn:hover:not(:disabled) {
  transform: translate(-1px, -1px);
  box-shadow: 3px 3px 0 #000;
}

.checkin-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.checked-badge {
  color: #28a745;
  font-weight: 700;
  font-size: 0.8rem;
}

.calendar-weekdays {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 2px;
  margin-bottom: 4px;
}

.calendar-weekdays span {
  text-align: center;
  font-size: 0.7rem;
  font-weight: 600;
  color: #666;
}

.calendar-days {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 2px;
}

.day-cell {
  aspect-ratio: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border: 1px solid #e9ecef;
  border-radius: 3px;
  cursor: default;
  position: relative;
  transition: all 0.2s;
  min-height: 28px;
}

.day-cell.other-month {
  color: #adb5bd;
  background: #f8f9fa;
}

.day-cell.today {
  border-color: #007bff;
  border-width: 2px;
}

.day-cell.checked {
  background: linear-gradient(135deg, #28a745, #20c997);
  border-color: #28a745;
}

.day-cell.checked .day-number {
  color: white;
  font-weight: 700;
}

.day-cell.checkable {
  cursor: pointer;
  background: linear-gradient(135deg, #ffd700, #ffed4e);
  border-color: #000;
  animation: pulse 2s infinite;
}

.day-cell.checkable:hover {
  transform: scale(1.05);
  box-shadow: 0 2px 8px rgba(0,0,0,0.2);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.8; }
}

.day-number {
  font-size: 0.7rem;
  font-weight: 500;
}

.check-icon {
  position: absolute;
  bottom: 1px;
  font-size: 0.55rem;
  color: white;
}
</style>
