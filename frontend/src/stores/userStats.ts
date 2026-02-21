import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { ActivityLog, CoinsLog, LevelProgress } from '@/types'
import { userStatsApi } from '@/lib/api'

export const useUserStatsStore = defineStore('userStats', () => {
  // State
  const activityLogs = ref<ActivityLog[]>([])
  const activityLogsLoading = ref(false)
  const activityLogsError = ref<string | null>(null)
  const activityLogsPagination = ref({
    count: 0,
    next: null as string | null,
    previous: null as string | null,
    page: 1
  })

  const coinsLogs = ref<CoinsLog[]>([])
  const coinsLogsLoading = ref(false)
  const coinsLogsError = ref<string | null>(null)
  const coinsLogsPagination = ref({
    count: 0,
    next: null as string | null,
    previous: null as string | null,
    page: 1
  })

  const levelProgress = ref<LevelProgress | null>(null)
  const levelProgressLoading = ref(false)
  const levelProgressError = ref<string | null>(null)

  // Getters
  const hasMoreActivityLogs = computed(() => !!activityLogsPagination.value.next)
  const hasMoreCoinsLogs = computed(() => !!coinsLogsPagination.value.next)

  const incomeLogs = computed(() => coinsLogs.value.filter(log => log.amount > 0))
  const expenseLogs = computed(() => coinsLogs.value.filter(log => log.amount < 0))

  // Actions
  async function fetchActivityLogs(page = 1, append = false) {
    activityLogsLoading.value = true
    activityLogsError.value = null

    try {
      const response = await userStatsApi.getActivityLogs({ page, page_size: 20 })

      if (append) {
        activityLogs.value.push(...response.results)
      } else {
        activityLogs.value = response.results
      }

      activityLogsPagination.value = {
        count: response.count,
        next: response.next,
        previous: response.previous,
        page
      }
    } catch (error: any) {
      activityLogsError.value = error.message || '获取活跃度记录失败'
      console.error('Failed to fetch activity logs:', error)
    } finally {
      activityLogsLoading.value = false
    }
  }

  async function loadMoreActivityLogs() {
    if (!hasMoreActivityLogs.value || activityLogsLoading.value) return
    await fetchActivityLogs(activityLogsPagination.value.page + 1, true)
  }

  async function fetchCoinsLogs(page = 1, type?: string, append = false) {
    coinsLogsLoading.value = true
    coinsLogsError.value = null

    try {
      const response = await userStatsApi.getCoinsLogs({ page, page_size: 20, type })

      if (append) {
        coinsLogs.value.push(...response.results)
      } else {
        coinsLogs.value = response.results
      }

      coinsLogsPagination.value = {
        count: response.count,
        next: response.next,
        previous: response.previous,
        page
      }
    } catch (error: any) {
      coinsLogsError.value = error.message || '获取积分记录失败'
      console.error('Failed to fetch coins logs:', error)
    } finally {
      coinsLogsLoading.value = false
    }
  }

  async function loadMoreCoinsLogs(type?: string) {
    if (!hasMoreCoinsLogs.value || coinsLogsLoading.value) return
    await fetchCoinsLogs(coinsLogsPagination.value.page + 1, type, true)
  }

  async function fetchLevelProgress() {
    levelProgressLoading.value = true
    levelProgressError.value = null

    try {
      const response = await userStatsApi.getLevelProgress()
      levelProgress.value = response
    } catch (error: any) {
      levelProgressError.value = error.message || '获取等级进度失败'
      console.error('Failed to fetch level progress:', error)
    } finally {
      levelProgressLoading.value = false
    }
  }

  function resetActivityLogs() {
    activityLogs.value = []
    activityLogsPagination.value = { count: 0, next: null, previous: null, page: 1 }
    activityLogsError.value = null
  }

  function resetCoinsLogs() {
    coinsLogs.value = []
    coinsLogsPagination.value = { count: 0, next: null, previous: null, page: 1 }
    coinsLogsError.value = null
  }

  function resetLevelProgress() {
    levelProgress.value = null
    levelProgressError.value = null
  }

  function resetAll() {
    resetActivityLogs()
    resetCoinsLogs()
    resetLevelProgress()
  }

  return {
    // State
    activityLogs,
    activityLogsLoading,
    activityLogsError,
    activityLogsPagination,
    coinsLogs,
    coinsLogsLoading,
    coinsLogsError,
    coinsLogsPagination,
    levelProgress,
    levelProgressLoading,
    levelProgressError,

    // Getters
    hasMoreActivityLogs,
    hasMoreCoinsLogs,
    incomeLogs,
    expenseLogs,

    // Actions
    fetchActivityLogs,
    loadMoreActivityLogs,
    fetchCoinsLogs,
    loadMoreCoinsLogs,
    fetchLevelProgress,
    resetActivityLogs,
    resetCoinsLogs,
    resetLevelProgress,
    resetAll
  }
})
