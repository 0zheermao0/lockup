import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useScrollPositionPreservation } from './useScrollPositionPreservation'

export interface InfiniteScrollOptions {
  threshold?: number // Distance from bottom to trigger load (in pixels)
  initialPageSize?: number // Number of items per page
  loadDelay?: number // Delay before loading next page (in ms)
  routeKey: string // Unique key for position preservation
  enablePositionPreservation?: boolean // Enable/disable position preservation
}

export interface PaginatedData<T> {
  results: T[]
  count: number
  next: string | null
  previous: string | null
}

export function useInfiniteScrollWithPosition<T>(
  fetchFunction: (page: number, pageSize: number, extraFilters?: any) => Promise<PaginatedData<T>>,
  options: InfiniteScrollOptions
) {
  const {
    threshold = 200,
    initialPageSize = 10,
    loadDelay = 300,
    routeKey,
    enablePositionPreservation = true
  } = options

  // State
  const items = ref<T[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const hasMore = ref(true)
  const currentPage = ref(1)
  const totalCount = ref(0)
  const initialized = ref(false)
  const isRestoringFromCache = ref(false)

  // Position preservation
  const scrollPreservation = enablePositionPreservation
    ? useScrollPositionPreservation({ routeKey })
    : null

  // Computed
  const isEmpty = computed(() => !loading.value && items.value.length === 0)
  const isLoadingMore = computed(() => loading.value && items.value.length > 0)
  const isInitialLoading = computed(() => loading.value && items.value.length === 0)

  // Loading timeout for better UX
  let loadTimeout: ReturnType<typeof setTimeout> | null = null
  let extraFilters: any = null

  // Save current state to position preservation
  const saveCurrentState = (immediate: boolean = false) => {
    if (!scrollPreservation) return

    scrollPreservation.saveScrollPosition(items.value, {
      hasMore: hasMore.value,
      currentPage: currentPage.value,
      totalPages: Math.ceil(totalCount.value / initialPageSize),
      isInitialized: initialized.value
    }, immediate)
  }

  // Restore state from position preservation
  const restoreStateIfAvailable = () => {
    if (!scrollPreservation) return false

    const { scrollTop, savedData, savedState } = scrollPreservation.restoreScrollPosition()

    if (savedData && savedState && savedData.length > 0) {
      console.log(`[InfiniteScroll] Restoring ${savedData.length} items for ${routeKey}`)

      // Restore data and state
      items.value = savedData
      hasMore.value = savedState.hasMore ?? true
      currentPage.value = savedState.currentPage ?? 1
      initialized.value = savedState.isInitialized ?? true
      totalCount.value = savedData.length // Approximate, will be corrected on next fetch

      isRestoringFromCache.value = true

      // Restore scroll position after DOM updates
      if (scrollTop !== null) {
        // Wait longer for DOM to fully render before restoring scroll
        setTimeout(() => {
          scrollPreservation.scrollToPosition(scrollTop)

          // Reset restoring flag after scroll restoration
          setTimeout(() => {
            isRestoringFromCache.value = false
          }, 500)
        }, 100) // Give DOM more time to render
      }

      return true
    }

    return false
  }

  // Fetch data
  const fetchData = async (page: number = 1, append: boolean = false, skipPositionSave: boolean = false) => {
    if (loading.value) return

    loading.value = true
    error.value = null

    try {
      // Add delay for loading more (not for initial load or restoration)
      if (append && loadDelay > 0 && !isRestoringFromCache.value) {
        await new Promise(resolve => setTimeout(resolve, loadDelay))
      }

      const response = await fetchFunction(page, initialPageSize, extraFilters)

      totalCount.value = response.count

      if (append) {
        items.value = [...(items.value as T[]), ...response.results]
      } else {
        items.value = response.results
      }

      hasMore.value = !!response.next
      currentPage.value = page

      if (!initialized.value) {
        initialized.value = true
      }

      // Save position after successful load (unless explicitly skipped)
      if (!skipPositionSave) {
        saveCurrentState()
      }
    } catch (err: any) {
      error.value = err.message || '加载失败，请重试'
      console.error('Error loading data:', err)
    } finally {
      loading.value = false
    }
  }

  // Load next page
  const loadMore = async () => {
    if (!hasMore.value || loading.value || isRestoringFromCache.value) return

    await fetchData(currentPage.value + 1, true)
  }

  // Refresh data (reset to first page) - clears cache
  const refresh = async () => {
    console.log(`[InfiniteScroll] Refreshing data for ${routeKey}`)

    // Clear saved position when refreshing
    if (scrollPreservation) {
      scrollPreservation.clearSavedPosition()
    }

    currentPage.value = 1
    hasMore.value = true
    items.value = []
    isRestoringFromCache.value = false

    await fetchData(1, false)
  }

  // Reset all state
  const reset = () => {
    items.value = []
    loading.value = false
    error.value = null
    hasMore.value = true
    currentPage.value = 1
    totalCount.value = 0
    initialized.value = false
    isRestoringFromCache.value = false

    if (scrollPreservation) {
      scrollPreservation.clearSavedPosition()
    }
  }

  // Set extra filters for API calls
  const setFilters = (filters: any) => {
    extraFilters = filters
  }

  // Scroll event handler
  const handleScroll = () => {
    if (loading.value || !hasMore.value || isRestoringFromCache.value) return

    const scrollHeight = document.documentElement.scrollHeight
    const scrollTop = document.documentElement.scrollTop || document.body.scrollTop
    const clientHeight = document.documentElement.clientHeight

    // Check if user has scrolled near the bottom
    if (scrollHeight - scrollTop - clientHeight < threshold) {
      // Clear any existing timeout to prevent rapid firing
      if (loadTimeout) {
        clearTimeout(loadTimeout)
      }

      // Debounce the load more action
      loadTimeout = setTimeout(() => {
        loadMore()
      }, 100)
    }
  }

  // Initialize with position preservation support
  const initialize = async () => {
    if (initialized.value) return

    console.log(`[InfiniteScroll] Initializing for ${routeKey}`)

    // Try to restore from cache first
    const restored = restoreStateIfAvailable()

    if (!restored) {
      // No cached data, fetch fresh data
      console.log(`[InfiniteScroll] No cached data, fetching fresh for ${routeKey}`)
      await fetchData(1, false)
    } else {
      console.log(`[InfiniteScroll] Restored from cache for ${routeKey}`)
    }
  }

  // Enhanced navigation methods for position preservation
  const prepareForNavigation = () => {
    // Save current state immediately before navigating away
    console.log(`[InfiniteScroll] Preparing for navigation from ${routeKey}`)

    // Capture scroll position immediately
    const currentScrollTop = window.pageYOffset || document.documentElement.scrollTop
    console.log(`[InfiniteScroll] Current scroll position: ${currentScrollTop}`)

    // Save state with immediate flag to bypass throttling
    saveCurrentState(true)

    // Also save scroll position directly to ensure it's captured
    if (scrollPreservation) {
      scrollPreservation.saveScrollPosition(items.value, {
        hasMore: hasMore.value,
        currentPage: currentPage.value,
        totalPages: Math.ceil(totalCount.value / initialPageSize),
        isInitialized: initialized.value
      }, true) // Use immediate flag
    }
  }

  // Watch for items changes and save position (debounced)
  let saveTimeout: number | null = null
  watch(
    () => items.value.length,
    () => {
      if (saveTimeout) clearTimeout(saveTimeout)
      saveTimeout = setTimeout(() => {
        if (!isRestoringFromCache.value) {
          saveCurrentState()
        }
      }, 1000) // Save position 1 second after items change
    }
  )

  // Setup scroll listener
  onMounted(() => {
    window.addEventListener('scroll', handleScroll, { passive: true })
  })

  onUnmounted(() => {
    window.removeEventListener('scroll', handleScroll)
    if (loadTimeout) {
      clearTimeout(loadTimeout)
    }
    if (saveTimeout) {
      clearTimeout(saveTimeout)
    }

    // Save final state before component unmounts
    if (!isRestoringFromCache.value) {
      saveCurrentState()
    }
  })

  return {
    // State
    items,
    loading,
    error,
    hasMore,
    currentPage,
    totalCount,
    initialized,
    isRestoringFromCache,

    // Computed
    isEmpty,
    isLoadingMore,
    isInitialLoading,

    // Methods
    initialize,
    loadMore,
    refresh,
    reset,
    fetchData,
    setFilters,
    prepareForNavigation,

    // Position preservation
    isRestoring: scrollPreservation?.isRestoring || ref(false),
    isComingFromDetail: scrollPreservation?.isComingFromDetail || (() => false)
  }
}