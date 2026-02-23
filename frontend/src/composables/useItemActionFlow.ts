import { ref, nextTick } from 'vue'
import type { Item } from '@/types'

export type FlowState = 'idle' | 'closing' | 'opening' | 'active'

export interface UseItemActionFlowOptions {
  /** Toast close animation duration in ms (default: 300) */
  toastCloseDuration?: number
  /** Maximum wait time for toast close in ms (default: 500) */
  maxWaitTime?: number
}

/**
 * Simple composable for managing the item action flow on mobile.
 * Handles the coordination between closing the Toast notification
 * and opening the item action modal.
 */
export function useItemActionFlow(options: UseItemActionFlowOptions = {}) {
  const {
    toastCloseDuration = 300,
    maxWaitTime = 500
  } = options

  // Flow state tracking
  const flowState = ref<FlowState>('idle')

  /**
   * Wait for the Toast to be fully removed from DOM
   */
  const waitForToastClose = (): Promise<void> => {
    return new Promise((resolve) => {
      const startTime = Date.now()

      const checkInterval = setInterval(() => {
        // Check if toast overlay is removed from DOM
        const toastOverlay = document.querySelector('.toast-overlay')
        const toastWrapper = document.querySelector('.notification-toast-wrapper')

        // If toast is gone from DOM
        if (!toastOverlay && !toastWrapper) {
          clearInterval(checkInterval)
          resolve()
          return
        }

        // Timeout protection
        if (Date.now() - startTime >= maxWaitTime) {
          clearInterval(checkInterval)
          resolve()
        }
      }, 50)

      // Absolute timeout fallback
      setTimeout(() => {
        clearInterval(checkInterval)
        resolve()
      }, maxWaitTime)
    })
  }

  /**
   * Start the item action flow
   * 1. Close the Toast
   * 2. Wait for Toast animation to complete
   * 3. Execute the callback to open modal
   */
  const startActionFlow = async (
    closeToast: () => void
  ): Promise<void> => {
    flowState.value = 'closing'

    // Step 1: Close the Toast
    closeToast()

    // Step 2: Wait for nextTick to ensure Vue has processed the state change
    await nextTick()

    // Step 3: Wait for Toast animation to complete
    await waitForToastClose()

    flowState.value = 'opening'
  }

  /**
   * Reset the flow state
   */
  const resetFlow = () => {
    flowState.value = 'idle'
  }

  return {
    flowState,
    startActionFlow,
    resetFlow,
    waitForToastClose
  }
}

export default useItemActionFlow
