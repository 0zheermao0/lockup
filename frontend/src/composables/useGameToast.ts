import { ref } from 'vue'

interface ToastState {
  isVisible: boolean
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  message: string
}

// Global toast state (singleton)
const _toastState = ref<ToastState>({
  isVisible: false,
  type: 'info',
  title: '',
  message: ''
})

let toastTimeout: number | null = null

const _closeToast = () => {
  _toastState.value.isVisible = false
  if (toastTimeout) {
    clearTimeout(toastTimeout)
    toastTimeout = null
  }
}

const _showToast = (type: ToastState['type'], title: string, message: string, duration = 3000) => {
  // Clear any existing timeout
  if (toastTimeout) {
    clearTimeout(toastTimeout)
  }

  _toastState.value = {
    isVisible: true,
    type,
    title,
    message
  }

  // Auto close after duration
  if (duration > 0) {
    toastTimeout = window.setTimeout(() => {
      _closeToast()
    }, duration)
  }
}

export function useGameToast() {
  const showToast = (type: ToastState['type'], title: string, message: string, duration = 3000) => {
    _showToast(type, title, message, duration)
  }

  const showSuccess = (title: string, message: string, duration?: number) => {
    _showToast('success', title, message, duration)
  }

  const showError = (title: string, message: string, duration?: number) => {
    _showToast('error', title, message, duration)
  }

  const showWarning = (title: string, message: string, duration?: number) => {
    _showToast('warning', title, message, duration)
  }

  const showInfo = (title: string, message: string, duration?: number) => {
    _showToast('info', title, message, duration)
  }

  const closeToast = () => {
    _closeToast()
  }

  return {
    toastState: _toastState,
    showToast,
    showSuccess,
    showError,
    showWarning,
    showInfo,
    closeToast
  }
}

// Export global state and functions for convenience
export const toastState = _toastState
export const showToast = (type: ToastState['type'], title: string, message: string, duration = 3000) => _showToast(type, title, message, duration)
export const showSuccess = (title: string, message: string, duration?: number) => _showToast('success', title, message, duration)
export const showError = (title: string, message: string, duration?: number) => _showToast('error', title, message, duration)
export const showWarning = (title: string, message: string, duration?: number) => _showToast('warning', title, message, duration)
export const showInfo = (title: string, message: string, duration?: number) => _showToast('info', title, message, duration)
export const closeToast = _closeToast
