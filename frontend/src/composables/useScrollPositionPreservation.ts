import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter, type RouteLocationNormalized } from 'vue-router'

interface ScrollState {
  scrollTop: number
  timestamp: number
  data?: any[]
  hasMore?: boolean
  currentPage?: number
  totalPages?: number
  isInitialized?: boolean
}

interface ScrollPositionStore {
  [key: string]: ScrollState
}

// Global store for scroll positions
const scrollPositionStore: ScrollPositionStore = {}

// Maximum age for stored scroll positions (5 minutes)
const MAX_POSITION_AGE = 5 * 60 * 1000

export function useScrollPositionPreservation(options: {
  routeKey: string // Unique key for this route (e.g., 'home', 'tasks')
  restoreDelay?: number // Delay before restoring position (ms)
  saveThrottleMs?: number // Throttle saving to avoid too frequent updates
}) {
  const route = useRoute()
  const router = useRouter()

  const { routeKey, restoreDelay = 100, saveThrottleMs = 500 } = options

  const isRestoring = ref(false)
  let saveTimeout: number | null = null
  let restoreTimeout: number | null = null

  // Clean up old scroll positions
  const cleanupOldPositions = () => {
    const now = Date.now()
    Object.keys(scrollPositionStore).forEach(key => {
      const state = scrollPositionStore[key]
      if (state && (now - state.timestamp) > MAX_POSITION_AGE) {
        delete scrollPositionStore[key]
      }
    })
  }

  // Save current scroll position and data
  const saveScrollPosition = (data?: any[], additionalState?: Partial<ScrollState>, immediate: boolean = false) => {
    const doSave = () => {
      const scrollTop = window.pageYOffset || document.documentElement.scrollTop

      scrollPositionStore[routeKey] = {
        scrollTop,
        timestamp: Date.now(),
        data: data ? [...data] : undefined, // Deep copy to avoid reference issues
        ...additionalState
      }

      console.log(`[ScrollPreservation] Saved position for ${routeKey}:`, {
        scrollTop,
        dataLength: data?.length,
        additionalState,
        immediate
      })
    }

    if (immediate) {
      // For navigation, save immediately without throttling
      doSave()
    } else {
      // Throttle saving to avoid excessive updates for regular saves
      if (saveTimeout) {
        clearTimeout(saveTimeout)
      }

      saveTimeout = setTimeout(doSave, saveThrottleMs)
    }
  }

  // Restore scroll position and return saved data
  const restoreScrollPosition = (): {
    scrollTop: number | null
    savedData: any[] | null
    savedState: Partial<ScrollState> | null
  } => {
    cleanupOldPositions()

    const savedState = scrollPositionStore[routeKey]

    if (!savedState) {
      console.log(`[ScrollPreservation] No saved state for ${routeKey}`)
      return { scrollTop: null, savedData: null, savedState: null }
    }

    // Check if the saved state is not too old
    const age = Date.now() - savedState.timestamp
    if (age > MAX_POSITION_AGE) {
      console.log(`[ScrollPreservation] Saved state too old for ${routeKey}:`, age)
      delete scrollPositionStore[routeKey]
      return { scrollTop: null, savedData: null, savedState: null }
    }

    console.log(`[ScrollPreservation] Restoring position for ${routeKey}:`, {
      scrollTop: savedState.scrollTop,
      dataLength: savedState.data?.length,
      age
    })

    return {
      scrollTop: savedState.scrollTop,
      savedData: savedState.data || null,
      savedState: {
        hasMore: savedState.hasMore,
        currentPage: savedState.currentPage,
        totalPages: savedState.totalPages,
        isInitialized: savedState.isInitialized
      }
    }
  }

  // Actually scroll to the saved position
  const scrollToPosition = (scrollTop: number) => {
    if (restoreTimeout) {
      clearTimeout(restoreTimeout)
    }

    isRestoring.value = true
    console.log(`[ScrollPreservation] Starting scroll restoration to position ${scrollTop} for ${routeKey}`)

    restoreTimeout = setTimeout(async () => {
      await nextTick()

      // Wait for DOM to be fully ready
      await new Promise(resolve => setTimeout(resolve, 100))

      // Check if document is scrollable before attempting
      const maxScrollTop = Math.max(
        document.body.scrollHeight - window.innerHeight,
        document.documentElement.scrollHeight - window.innerHeight
      )

      console.log(`[ScrollPreservation] Document scroll info - height: ${document.documentElement.scrollHeight}, viewport: ${window.innerHeight}, maxScroll: ${maxScrollTop}`)

      if (maxScrollTop <= 0) {
        console.log(`[ScrollPreservation] Document not scrollable yet, retrying...`)
        // If not scrollable, retry after more time
        setTimeout(() => scrollToPosition(scrollTop), 200)
        return
      }

      const targetScrollTop = Math.min(scrollTop, maxScrollTop)

      // Multiple attempts to ensure scroll restoration works
      const attempts = [0, 100, 200, 400, 600, 1000]

      for (let i = 0; i < attempts.length; i++) {
        const delay = attempts[i]
        setTimeout(() => {
          // Re-check scroll limits for each attempt
          const currentMaxScroll = Math.max(
            document.body.scrollHeight - window.innerHeight,
            document.documentElement.scrollHeight - window.innerHeight
          )

          const currentTarget = Math.min(scrollTop, currentMaxScroll)

          // Try multiple scroll methods
          window.scrollTo({
            top: currentTarget,
            left: 0,
            behavior: 'auto'
          })

          // Fallback scroll methods
          document.documentElement.scrollTop = currentTarget
          document.body.scrollTop = currentTarget

          console.log(`[ScrollPreservation] Scrolled to position ${currentTarget}/${scrollTop} (attempt ${i + 1} with ${delay}ms delay, currentMaxScroll: ${currentMaxScroll})`)

          // Verify scroll position on final attempt
          if (i === attempts.length - 1) {
            setTimeout(() => {
              const finalScrollTop = window.pageYOffset || document.documentElement.scrollTop
              console.log(`[ScrollPreservation] Final scroll position: ${finalScrollTop}, target was: ${currentTarget}`)

              // If still not at target, try one more time
              if (Math.abs(finalScrollTop - currentTarget) > 10 && currentTarget > 0) {
                console.log(`[ScrollPreservation] Final attempt to reach target position`)
                window.scrollTo({ top: currentTarget, left: 0, behavior: 'auto' })
                document.documentElement.scrollTop = currentTarget
                document.body.scrollTop = currentTarget
              }
            }, 200)
          }
        }, delay)
      }

      // Reset restoring flag after the last attempt
      setTimeout(() => {
        isRestoring.value = false
        console.log(`[ScrollPreservation] Position restoration complete for ${routeKey}`)
      }, (attempts[attempts.length - 1] || 1000) + 300)

    }, restoreDelay)
  }

  // Clear saved position (useful when user manually refreshes or navigates away)
  const clearSavedPosition = () => {
    if (scrollPositionStore[routeKey]) {
      delete scrollPositionStore[routeKey]
      console.log(`[ScrollPreservation] Cleared saved position for ${routeKey}`)
    }
  }

  // Check if we're coming back from a detail page
  const isComingFromDetail = () => {
    // Check if the previous route was a detail page
    const history = router.options.history
    if (history && 'state' in history && history.state) {
      const state = history.state as any
      if (state.back) {
        return true
      }
    }

    // Alternative check: if we have saved data, we're likely coming back
    return !!scrollPositionStore[routeKey]
  }

  // Save scroll position before navigating away
  const handleBeforeUnload = () => {
    // This will be called by the component when navigating to detail
  }

  // Auto-save scroll position periodically when user is scrolling
  const handleScroll = () => {
    if (!isRestoring.value) {
      // Only save basic scroll position during scroll, not the full data
      const scrollTop = window.pageYOffset || document.documentElement.scrollTop

      if (scrollPositionStore[routeKey]) {
        scrollPositionStore[routeKey].scrollTop = scrollTop
        scrollPositionStore[routeKey].timestamp = Date.now()
      }
    }
  }

  // Setup scroll listener
  onMounted(() => {
    window.addEventListener('scroll', handleScroll, { passive: true })
  })

  onUnmounted(() => {
    window.removeEventListener('scroll', handleScroll)

    // Clear timeouts
    if (saveTimeout) {
      clearTimeout(saveTimeout)
    }
    if (restoreTimeout) {
      clearTimeout(restoreTimeout)
    }
  })

  return {
    isRestoring,
    saveScrollPosition,
    restoreScrollPosition,
    scrollToPosition,
    clearSavedPosition,
    isComingFromDetail,
    handleBeforeUnload
  }
}