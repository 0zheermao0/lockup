import { defineStore } from 'pinia'
import { ref } from 'vue'

interface TaskViewState {
  activeTaskType: 'lock' | 'board'
  activeFilter: string
  sortBy: 'remaining_time' | 'created_time' | 'end_time' | 'user_activity' | 'difficulty'
  sortOrder: 'asc' | 'desc'
  scrollPosition?: number
}

interface TasksViewState {
  tasks: any[]
  currentPage: number
  totalCount: number
  hasMore: boolean
  scrollPosition: number
  lastFetchTime: number
  // Store filter context to ensure we restore the right data
  activeTaskType: 'lock' | 'board'
  activeFilter: string
  sortBy: 'remaining_time' | 'created_time' | 'end_time' | 'user_activity' | 'difficulty'
  sortOrder: 'asc' | 'desc'
}

interface PostsViewState {
  posts: any[] // Using any[] to match the Post type from the posts store
  currentPage: number
  totalCount: number
  hasMore: boolean
  scrollPosition: number
  lastFetchTime: number
}

export const useNavigationStore = defineStore('navigation', () => {
  // Store the previous task view state (for filter/sort restoration)
  const taskViewState = ref<TaskViewState | null>(null)

  // Store the previous tasks view state (for position/data restoration)
  const tasksViewState = ref<TasksViewState | null>(null)

  // Store the previous posts view state
  const postsViewState = ref<PostsViewState | null>(null)

  // Store the previous route for back navigation
  const previousRoute = ref<string | null>(null)

  const saveTaskViewState = (state: TaskViewState) => {
    console.log('🗂️ Saving task view state:', state)
    taskViewState.value = { ...state }
  }

  const getTaskViewState = (): TaskViewState | null => {
    console.log('🗂️ Getting saved task view state:', taskViewState.value)
    return taskViewState.value
  }

  const clearTaskViewState = () => {
    console.log('🗂️ Clearing task view state')
    taskViewState.value = null
  }

  const saveTasksViewState = (state: TasksViewState) => {
    console.log('📋 Saving tasks view state:', state)
    tasksViewState.value = { ...state }
  }

  const getTasksViewState = (): TasksViewState | null => {
    console.log('📋 Getting saved tasks view state:', tasksViewState.value)
    return tasksViewState.value
  }

  const clearTasksViewState = () => {
    console.log('📋 Clearing tasks view state')
    tasksViewState.value = null
  }

  const savePostsViewState = (state: PostsViewState) => {
    console.log('📱 Saving posts view state:', state)
    postsViewState.value = { ...state }
  }

  const getPostsViewState = (): PostsViewState | null => {
    console.log('📱 Getting saved posts view state:', postsViewState.value)
    return postsViewState.value
  }

  const clearPostsViewState = () => {
    console.log('📱 Clearing posts view state')
    postsViewState.value = null
  }

  const setPreviousRoute = (route: string) => {
    console.log('🔙 Setting previous route:', route)
    previousRoute.value = route
  }

  const getPreviousRoute = (): string | null => {
    console.log('🔙 Getting previous route:', previousRoute.value)
    return previousRoute.value
  }

  const clearPreviousRoute = () => {
    console.log('🔙 Clearing previous route')
    previousRoute.value = null
  }

  return {
    // State
    taskViewState,
    tasksViewState,
    postsViewState,
    previousRoute,

    // Actions
    saveTaskViewState,
    getTaskViewState,
    clearTaskViewState,
    saveTasksViewState,
    getTasksViewState,
    clearTasksViewState,
    savePostsViewState,
    getPostsViewState,
    clearPostsViewState,
    setPreviousRoute,
    getPreviousRoute,
    clearPreviousRoute
  }
})