import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { notificationsApi } from '../lib/api'
import type { NotificationItem } from '../types/index'

export const useNotificationStore = defineStore('notifications', () => {
  // State
  const notifications = ref<NotificationItem[]>([])
  const unreadCount = ref(0)
  const stats = ref<{
    total_notifications: number
    unread_notifications: number
    unread_by_type: Record<string, { display_name: string; count: number }>
    unread_by_priority: Record<string, { display_name: string; count: number }>
  }>({
    total_notifications: 0,
    unread_notifications: 0,
    unread_by_type: {},
    unread_by_priority: {}
  })
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // 新增分页状态
  const currentPage = ref(1)
  const hasMore = ref(true)
  const isLoadingMore = ref(false)
  const pageSize = ref(10)
  const totalCount = ref(0)

  // Getters
  const hasUnreadNotifications = computed(() => unreadCount.value > 0)
  const unreadNotifications = computed(() =>
    notifications.value.filter(n => !n.is_read)
  )
  const readNotifications = computed(() =>
    notifications.value.filter(n => n.is_read)
  )
  const urgentNotifications = computed(() =>
    notifications.value.filter(n => !n.is_read && n.priority === 'urgent')
  )
  const highPriorityNotifications = computed(() =>
    notifications.value.filter(n => !n.is_read && n.priority === 'high')
  )

  // Actions
  const fetchNotifications = async (params?: {
    is_read?: string
    type?: string
    limit?: number
  }) => {
    isLoading.value = true
    error.value = null

    try {
      const response = await notificationsApi.getNotifications(params)
      notifications.value = response.results || []
      return response.results || []
    } catch (err) {
      error.value = err instanceof Error ? err.message : '获取通知失败'
      console.error('Failed to fetch notifications:', err)
      throw err
    } finally {
      isLoading.value = false
    }
  }

  // 新增分页方法
  const fetchNotificationsPage = async (params?: {
    is_read?: string
    type?: string
    page?: number
    reset?: boolean  // 是否重置列表
  }) => {
    if (isLoadingMore.value && !params?.reset) return

    isLoadingMore.value = true
    error.value = null

    try {
      const page = params?.page || currentPage.value
      const response = await notificationsApi.getNotifications({
        ...params,
        page,
        limit: pageSize.value
      })

      if (params?.reset) {
        notifications.value = response.results || []
        currentPage.value = 1
      } else {
        notifications.value.push(...(response.results || []))
      }

      hasMore.value = response.next !== null
      currentPage.value = page + 1
      totalCount.value = response.count || 0

      return response.results || []
    } catch (err) {
      error.value = err instanceof Error ? err.message : '获取通知失败'
      throw err
    } finally {
      isLoadingMore.value = false
    }
  }

  const loadMoreNotifications = async (params?: {
    is_read?: string
    type?: string
  }) => {
    if (!hasMore.value || isLoadingMore.value) return
    return fetchNotificationsPage({ ...params, page: currentPage.value })
  }

  // 重置分页状态
  const resetPagination = () => {
    currentPage.value = 1
    hasMore.value = true
    isLoadingMore.value = false
    notifications.value = []
    totalCount.value = 0
  }

  const fetchNotificationStats = async () => {
    try {
      const fetchedStats = await notificationsApi.getNotificationStats()
      stats.value = fetchedStats
      unreadCount.value = fetchedStats.unread_notifications
      return fetchedStats
    } catch (err) {
      console.error('Failed to fetch notification stats:', err)
      throw err
    }
  }

  const markAsRead = async (notificationId: string) => {
    try {
      await notificationsApi.markAsRead(notificationId)

      // Update local state
      const notification = notifications.value.find(n => n.id === notificationId)
      if (notification) {
        notification.is_read = true
        notification.read_at = new Date().toISOString()
      }

      // Update unread count
      if (unreadCount.value > 0) {
        unreadCount.value--
      }
    } catch (err) {
      console.error('Failed to mark notification as read:', err)
      throw err
    }
  }

  const markAllAsRead = async () => {
    try {
      const result = await notificationsApi.markAllAsRead()

      // Update local state
      notifications.value.forEach(notification => {
        if (!notification.is_read) {
          notification.is_read = true
          notification.read_at = new Date().toISOString()
        }
      })

      // Update unread count
      unreadCount.value = 0
    } catch (err) {
      console.error('Failed to mark all notifications as read:', err)
      throw err
    }
  }

  const deleteNotification = async (notificationId: string) => {
    try {
      await notificationsApi.deleteNotification(notificationId)

      // Update local state
      const index = notifications.value.findIndex(n => n.id === notificationId)
      if (index > -1) {
        const deletedNotification = notifications.value[index]
        notifications.value.splice(index, 1)

        // Update unread count
        if (deletedNotification && !deletedNotification.is_read && unreadCount.value > 0) {
          unreadCount.value--
        }
      }
    } catch (err) {
      console.error('Failed to delete notification:', err)
      throw err
    }
  }

  const clearReadNotifications = async () => {
    try {
      const result = await notificationsApi.clearReadNotifications()

      // Update local state - only keep unread notifications
      const readNotificationsCount = notifications.value.filter(n => n.is_read).length
      notifications.value = notifications.value.filter(n => !n.is_read)

      // Clear error if any
      error.value = null
    } catch (err) {
      console.error('Failed to clear read notifications:', err)
      throw err
    }
  }

  const createNotification = async (data: {
    recipient_id: number
    notification_type: string
    title?: string
    message?: string
    priority?: string
    related_object_type?: string
    related_object_id?: string
    extra_data?: Record<string, any>
  }) => {
    try {
      const result = await notificationsApi.createNotification(data)

      // Add to local state if it's for current user
      // (This would need the current user's ID, but we'll handle that in the component)
      notifications.value.unshift(result.notification)

      if (!result.notification.is_read) {
        unreadCount.value++
      }

      return result
    } catch (err) {
      console.error('Failed to create notification:', err)
      throw err
    }
  }

  const refreshNotifications = async () => {
    await fetchNotificationStats()
    if (hasUnreadNotifications.value) {
      // Fetch recent notifications
      await fetchNotifications({
        limit: 20,
        is_read: 'false'
      })
    }
  }

  const addNotification = (notification: NotificationItem) => {
    notifications.value.unshift(notification)
    if (!notification.is_read) {
      unreadCount.value++
    }
  }

  const clearNotifications = () => {
    notifications.value = []
    unreadCount.value = 0
    error.value = null
  }

  // Initialize store
  const initNotifications = async () => {
    try {
      await fetchNotificationStats()
      // Don't fetch notifications immediately, let components request them as needed
    } catch (err) {
      console.error('Failed to initialize notifications:', err)
    }
  }

  // Auto-refresh interval
  let refreshInterval: number | null = null

  const startAutoRefresh = () => {
    if (refreshInterval) return

    refreshInterval = setInterval(async () => {
      try {
        await refreshNotifications()
      } catch (err) {
        console.error('Auto-refresh notifications failed:', err)
      }
    }, 60000) // Refresh every minute
  }

  const stopAutoRefresh = () => {
    if (refreshInterval) {
      clearInterval(refreshInterval)
      refreshInterval = null
    }
  }

  return {
    // State
    notifications,
    unreadCount,
    stats,
    isLoading,
    error,

    // 分页状态
    currentPage,
    hasMore,
    isLoadingMore,
    pageSize,
    totalCount,

    // Getters
    hasUnreadNotifications,
    unreadNotifications,
    readNotifications,
    urgentNotifications,
    highPriorityNotifications,

    // Actions
    fetchNotifications,
    fetchNotificationStats,
    markAsRead,
    markAllAsRead,
    deleteNotification,
    clearReadNotifications,
    createNotification,
    refreshNotifications,
    addNotification,
    clearNotifications,
    initNotifications,
    startAutoRefresh,
    stopAutoRefresh,

    // 分页方法
    fetchNotificationsPage,
    loadMoreNotifications,
    resetPagination
  }
})