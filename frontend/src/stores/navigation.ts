import { defineStore } from 'pinia'
import { ref } from 'vue'

interface TaskViewState {
  activeTaskType: 'lock' | 'board'
  activeFilter: string
  sortBy: 'remaining_time' | 'created_time' | 'end_time' | 'user_activity' | 'difficulty'
  sortOrder: 'asc' | 'desc'
  scrollPosition?: number
}

export const useNavigationStore = defineStore('navigation', () => {
  // Store the previous task view state
  const taskViewState = ref<TaskViewState | null>(null)

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
    previousRoute,

    // Actions
    saveTaskViewState,
    getTaskViewState,
    clearTaskViewState,
    setPreviousRoute,
    getPreviousRoute,
    clearPreviousRoute
  }
})