<template>
  <div class="dsc">

    <!-- Header badge -->
    <div class="dsc__header">
      <span class="dsc__badge-detained">🔒 收押中</span>
    </div>

    <!-- Captor info -->
    <div class="dsc__captor">
      <span class="dsc__captor-label">拘押者:</span>
      <div class="dsc__captor-player">
        <div class="dsc__avatar">
          <img
            v-if="detention.captor.avatar"
            :src="detention.captor.avatar"
            :alt="detention.captor.username"
            class="dsc__avatar-img"
          />
          <span v-else class="dsc__avatar-fallback">
            {{ detention.captor.username.charAt(0).toUpperCase() }}
          </span>
        </div>
        <span class="dsc__captor-name">{{ detention.captor.username }}</span>
      </div>
    </div>

    <!-- Countdown -->
    <div class="dsc__countdown">
      <span class="dsc__countdown-label">剩余时间:</span>
      <span
        class="dsc__countdown-value"
        :class="{
          'dsc__countdown-value--orange': remainingSeconds < 3600 && remainingSeconds >= 600,
          'dsc__countdown-value--red': remainingSeconds < 600,
          'dsc__countdown-value--pulse': remainingSeconds < 600,
        }"
      >
        {{ formattedCountdown }}
      </span>
    </div>

    <!-- Seized crystals -->
    <div class="dsc__crystals">
      🔮 没收刀具: <strong>{{ detention.seized_crystals }}</strong>
    </div>

    <!-- Purity hint -->
    <p v-if="showPurityHint" class="dsc__purity-hint">
      需要光滑度 ≥ 70
    </p>

    <!-- Charm button -->
    <div class="dsc__charm-section">
      <button
        class="dsc__charm-btn"
        :disabled="charmDisabled"
        @click="handleCharmClick"
        :title="charmButtonTitle"
      >
        💫 哄骗看守
        <span v-if="charmAttemptsLeft <= 0" class="dsc__charm-meta">（已用尽）</span>
        <span v-else-if="charmCooldownText" class="dsc__charm-meta">{{ charmCooldownText }}</span>
        <span v-else class="dsc__charm-meta">{{ charmAttemptsLeft }}/3 次剩余</span>
      </button>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import type { DetentionRecord } from '../../lib/api-game'

const props = defineProps<{
  detention: DetentionRecord
}>()

const emit = defineEmits<{
  charmAttempted: []
}>()

// Live countdown state
const remainingSeconds = ref(Math.max(0, props.detention.time_remaining_seconds))
let countdownInterval: ReturnType<typeof setInterval> | null = null

// Cooldown state (re-evaluated every second)
const now = ref(Date.now())

onMounted(() => {
  countdownInterval = setInterval(() => {
    remainingSeconds.value = Math.max(0, remainingSeconds.value - 1)
    now.value = Date.now()
  }, 1000)
})

onUnmounted(() => {
  if (countdownInterval !== null) {
    clearInterval(countdownInterval)
    countdownInterval = null
  }
})

const formattedCountdown = computed(() => {
  const total = remainingSeconds.value
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = total % 60
  if (h > 0) {
    return `${h}h ${m}m ${s}s`
  }
  if (m > 0) {
    return `${m}m ${s}s`
  }
  return `${s}s`
})

const charmAttemptsLeft = computed(() => {
  return Math.max(0, 3 - props.detention.charm_attempts_used)
})

// Returns seconds remaining on 4-hour cooldown, or 0 if no cooldown
const cooldownSecondsRemaining = computed(() => {
  if (!props.detention.last_charm_at) return 0
  const lastCharm = new Date(props.detention.last_charm_at).getTime()
  const cooldownEnds = lastCharm + 4 * 60 * 60 * 1000
  const remaining = Math.ceil((cooldownEnds - now.value) / 1000)
  return Math.max(0, remaining)
})

const charmCooldownText = computed(() => {
  if (cooldownSecondsRemaining.value <= 0) return ''
  const secs = cooldownSecondsRemaining.value
  const h = Math.floor(secs / 3600)
  const m = Math.floor((secs % 3600) / 60)
  const s = secs % 60
  if (h > 0) return `冷却: ${h}h ${m}m`
  if (m > 0) return `冷却: ${m}m ${s}s`
  return `冷却: ${s}s`
})

const charmDisabled = computed(() => {
  return charmAttemptsLeft.value <= 0 || cooldownSecondsRemaining.value > 0
})

const charmButtonTitle = computed(() => {
  if (charmAttemptsLeft.value <= 0) return '哄骗机会已用尽'
  if (cooldownSecondsRemaining.value > 0) return '哄骗冷却中'
  return '尝试哄骗看守'
})

// Show purity hint when purity_score is relevant — we check if mimic's purity is potentially low.
// Since we only have DetentionRecord here, we show the hint as a reminder (always visible).
const showPurityHint = computed(() => true)

function handleCharmClick() {
  if (charmDisabled.value) return
  emit('charmAttempted')
}
</script>

<style scoped>
.dsc {
  background: #fff;
  border: 2px solid #dc3545;
  box-shadow: 4px 4px 0 #dc3545;
  font-family: 'Inter', sans-serif;
  padding: 0;
  overflow: hidden;
}

/* Header */
.dsc__header {
  padding: 10px 14px;
  background: #dc3545;
  display: flex;
  align-items: center;
}

.dsc__badge-detained {
  color: #fff;
  font-weight: 800;
  font-size: 0.95em;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

/* Captor */
.dsc__captor {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border-bottom: 2px solid #f0c0c0;
}

.dsc__captor-label {
  font-size: 0.8em;
  font-weight: 700;
  color: #888;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  flex-shrink: 0;
}

.dsc__captor-player {
  display: flex;
  align-items: center;
  gap: 8px;
}

.dsc__avatar {
  width: 32px;
  height: 32px;
  border: 2px solid #000;
  box-shadow: 2px 2px 0 #000;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #e8e8e8;
  flex-shrink: 0;
}

.dsc__avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.dsc__avatar-fallback {
  font-size: 0.9em;
  font-weight: 800;
}

.dsc__captor-name {
  font-weight: 700;
  font-size: 0.9em;
}

/* Countdown */
.dsc__countdown {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-bottom: 1px solid #f0c0c0;
}

.dsc__countdown-label {
  font-size: 0.8em;
  font-weight: 700;
  color: #888;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  flex-shrink: 0;
}

.dsc__countdown-value {
  font-size: 1.1em;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.04em;
}

.dsc__countdown-value--orange {
  color: #cc7700;
}

.dsc__countdown-value--red {
  color: #dc3545;
}

.dsc__countdown-value--pulse {
  animation: dsc-pulse 1s ease-in-out infinite;
}

/* Crystals */
.dsc__crystals {
  padding: 10px 14px;
  font-size: 0.9em;
  font-weight: 600;
  border-bottom: 1px solid #f0c0c0;
}

.dsc__crystals strong {
  font-weight: 800;
}

/* Purity hint */
.dsc__purity-hint {
  margin: 0;
  padding: 6px 14px;
  font-size: 0.78em;
  color: #cc7700;
  font-weight: 700;
  background: #fff8e8;
  border-bottom: 1px solid #f0c0c0;
}

/* Charm section */
.dsc__charm-section {
  padding: 12px 14px;
}

.dsc__charm-btn {
  width: 100%;
  background: #fff;
  border: 2px solid #000;
  box-shadow: 4px 4px 0 #000;
  font-family: inherit;
  font-size: 0.9em;
  font-weight: 800;
  padding: 10px 16px;
  cursor: pointer;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: transform 0.1s, box-shadow 0.1s;
}

.dsc__charm-btn:not(:disabled):hover {
  background: #000;
  color: #fff;
}

.dsc__charm-btn:not(:disabled):active {
  transform: translate(2px, 2px);
  box-shadow: 2px 2px 0 #000;
}

.dsc__charm-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  box-shadow: 2px 2px 0 #888;
  border-color: #888;
}

.dsc__charm-meta {
  font-size: 0.8em;
  font-weight: 600;
  color: #666;
  text-transform: none;
  letter-spacing: 0;
}

.dsc__charm-btn:not(:disabled):hover .dsc__charm-meta {
  color: #ccc;
}

@keyframes dsc-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
</style>
