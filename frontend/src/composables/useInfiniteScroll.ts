import { ref, computed, onMounted, onUnmounted } from 'vue'

export interface InfiniteScrollOptions {
  threshold?: number // Distance from bottom to trigger load (in pixels)
  initialPageSize?: number // Number of items per page
  loadDelay?: number // Delay before loading next page (in ms)
}

export interface PaginatedData<T> {
  results: T[]
  count: number
  next: string | null
  previous: string | null
}

export function useInfiniteScroll<T>(
  fetchFunction: (page: number, pageSize: number) => Promise<PaginatedData<T>>,
  options: InfiniteScrollOptions = {}
) {
  const {
    threshold = 200,
    initialPageSize = 10,
    loadDelay = 300
  } = options

  // State
  const items = ref<T[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const hasMore = ref(true)
  const currentPage = ref(1)
  const totalCount = ref(0)
  const initialized = ref(false)

  // Computed
  const isEmpty = computed(() => !loading.value && items.value.length === 0)
  const isLoadingMore = computed(() => loading.value && items.value.length > 0)
  const isInitialLoading = computed(() => loading.value && items.value.length === 0)

  // Loading timeout for better UX
  let loadTimeout: ReturnType<typeof setTimeout> | null = null

  // Fetch data
  const fetchData = async (page: number = 1, append: boolean = false) => {
    if (loading.value) return

    loading.value = true
    error.value = null

    try {
      // Add delay for loading more (not for initial load)
      if (append && loadDelay > 0) {
        await new Promise(resolve => setTimeout(resolve, loadDelay))
      }

      const response = await fetchFunction(page, initialPageSize)

      totalCount.value = response.count

      if (append) {
        items.value.push(...response.results)
      } else {
        items.value = response.results
      }

      hasMore.value = !!response.next
      currentPage.value = page

      if (!initialized.value) {
        initialized.value = true
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
    if (!hasMore.value || loading.value) return

    await fetchData(currentPage.value + 1, true)
  }

  // Refresh data (reset to first page)
  const refresh = async () => {
    currentPage.value = 1
    hasMore.value = true
    items.value = []
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
  }

  // Scroll event handler
  const handleScroll = () => {
    if (loading.value || !hasMore.value) return

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

  // Initialize
  const initialize = async () => {
    if (!initialized.value) {
      await fetchData(1, false)
    }
  }

  // Setup scroll listener
  onMounted(() => {
    window.addEventListener('scroll', handleScroll, { passive: true })
  })

  onUnmounted(() => {
    window.removeEventListener('scroll', handleScroll)
    if (loadTimeout) {
      clearTimeout(loadTimeout)
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

    // Computed
    isEmpty,
    isLoadingMore,
    isInitialLoading,

    // Methods
    initialize,
    loadMore,
    refresh,
    reset,
    fetchData
  }
}