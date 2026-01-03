import { ref } from 'vue'

export interface Notification {
  id: string
  message: string
  type: 'success' | 'error' | 'warning' | 'info'
  duration?: number
}

export function useNotificationToast() {
  const notifications = ref<Notification[]>([])

  const showNotification = (message: string, type: 'success' | 'error' | 'warning' | 'info' = 'info', duration: number = 3000) => {
    console.log('showNotification called:', { message, type })

    const id = Date.now().toString()
    const notification: Notification = {
      id,
      message,
      type,
      duration
    }

    notifications.value.push(notification)

    // Auto remove notification after duration
    setTimeout(() => {
      removeNotification(id)
    }, duration)

    // Show browser notification if permission granted
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification(message, {
        body: message,
        icon: type === 'success' ? '/success-icon.png' : '/error-icon.png'
      })
    }
  }

  const removeNotification = (id: string) => {
    const index = notifications.value.findIndex(n => n.id === id)
    if (index > -1) {
      notifications.value.splice(index, 1)
    }
  }

  const clearNotifications = () => {
    notifications.value = []
  }

  return {
    notifications,
    showNotification,
    removeNotification,
    clearNotifications
  }
}