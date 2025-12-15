import { defineStore } from 'pinia'
import { ref } from 'vue'
import { tasksApi } from '../lib/api-tasks'
import type { PaginatedResponse, LockTask, BoardTask, Task } from '../types/index'

export const useTasksStore = defineStore('tasks', () => {
  // State
  const tasks = ref<Task[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const currentPage = ref(1)
  const totalCount = ref(0)
  const hasMore = ref(true)

  // Filter state
  const filters = ref({
    task_type: '',
    status: '',
    my_tasks: false
  })

  // Actions
  const fetchTasks = async (params?: {
    task_type?: string;
    status?: string;
    my_tasks?: boolean;
    page?: number;
    page_size?: number;
  }) => {
    loading.value = true
    error.value = null

    try {
      // Filter out page and page_size since the API doesn't support them yet
      const { page, page_size, ...apiParams } = params || {}

      const response = await tasksApi.getTasks({
        task_type: apiParams.task_type as 'lock' | 'board' | undefined,
        status: apiParams.status,
        my_tasks: apiParams.my_tasks
      }) as any

      if (page === 1 || !page) {
        // First page or reset - replace all tasks
        tasks.value = (response.results || response || []) as Task[]
        currentPage.value = 1
      } else {
        // Subsequent pages - append to existing tasks
        tasks.value.push(...((response.results || response || []) as Task[]))
        currentPage.value = page
      }

      totalCount.value = response.count || (response.results?.length || response?.length || 0)
      hasMore.value = !!response.next
    } catch (err: any) {
      error.value = '加载任务失败'
      console.error('Error fetching tasks:', err)
    } finally {
      loading.value = false
    }
  }

  // Get paginated tasks for infinite scroll
  const getPaginatedTasks = async (
    page: number,
    pageSize: number = 10,
    extraFilters: {
      task_type?: 'lock' | 'board'
      status?: string
      my_tasks?: boolean
      my_taken?: boolean
      can_overtime?: boolean
      sort_by?: string
      sort_order?: 'asc' | 'desc'
    } = {}
  ): Promise<PaginatedResponse<Task>> => {
    const response = await tasksApi.getTasks({
      task_type: extraFilters.task_type || filters.value.task_type as 'lock' | 'board' | undefined,
      status: extraFilters.status || filters.value.status,
      my_tasks: extraFilters.my_tasks !== undefined ? extraFilters.my_tasks : filters.value.my_tasks,
      my_taken: extraFilters.my_taken,
      can_overtime: extraFilters.can_overtime,
      page: page,
      page_size: pageSize,
      sort_by: extraFilters.sort_by,
      sort_order: extraFilters.sort_order
    }) as any
    return response as PaginatedResponse<Task>
  }

  // Task actions
  const startTask = async (taskId: string) => {
    try {
      const result = await tasksApi.startTask(taskId)

      // Update local state
      const taskIndex = tasks.value.findIndex(task => task.id === taskId)
      if (taskIndex !== -1) {
        tasks.value[taskIndex] = { ...tasks.value[taskIndex], ...result } as Task
      }

      return result as Task
    } catch (err) {
      console.error('Error starting task:', err)
      throw err
    }
  }

  const completeTask = async (taskId: string) => {
    try {
      const result = await tasksApi.completeTask(taskId)

      // Update local state
      const taskIndex = tasks.value.findIndex(task => task.id === taskId)
      if (taskIndex !== -1) {
        tasks.value[taskIndex] = { ...tasks.value[taskIndex], ...result } as Task
      }

      return result as Task
    } catch (err) {
      console.error('Error completing task:', err)
      throw err
    }
  }

  const stopTask = async (taskId: string) => {
    try {
      const result = await tasksApi.stopTask(taskId)

      // Update local state
      const taskIndex = tasks.value.findIndex(task => task.id === taskId)
      if (taskIndex !== -1) {
        tasks.value[taskIndex] = { ...tasks.value[taskIndex], ...result } as Task
      }

      return result as Task
    } catch (err) {
      console.error('Error stopping task:', err)
      throw err
    }
  }

  const takeTask = async (taskId: string) => {
    try {
      const result = await tasksApi.takeTask(taskId)

      // Update local state
      const taskIndex = tasks.value.findIndex(task => task.id === taskId)
      if (taskIndex !== -1) {
        tasks.value[taskIndex] = { ...tasks.value[taskIndex], ...result } as Task
      }

      return result as Task
    } catch (err) {
      console.error('Error taking task:', err)
      throw err
    }
  }

  const submitTask = async (taskId: string, completionProof: string) => {
    try {
      const result = await tasksApi.submitTask(taskId, completionProof)

      // Update local state
      const taskIndex = tasks.value.findIndex(task => task.id === taskId)
      if (taskIndex !== -1) {
        tasks.value[taskIndex] = { ...tasks.value[taskIndex], ...result } as Task
      }

      return result as Task
    } catch (err) {
      console.error('Error submitting task:', err)
      throw err
    }
  }

  const approveTask = async (taskId: string) => {
    try {
      const result = await tasksApi.approveTask(taskId)

      // Update local state
      const taskIndex = tasks.value.findIndex(task => task.id === taskId)
      if (taskIndex !== -1) {
        tasks.value[taskIndex] = { ...tasks.value[taskIndex], ...result } as Task
      }

      return result as Task
    } catch (err) {
      console.error('Error approving task:', err)
      throw err
    }
  }

  const rejectTask = async (taskId: string, rejectReason?: string) => {
    try {
      const result = await tasksApi.rejectTask(taskId, rejectReason)

      // Update local state
      const taskIndex = tasks.value.findIndex(task => task.id === taskId)
      if (taskIndex !== -1) {
        tasks.value[taskIndex] = { ...tasks.value[taskIndex], ...result } as Task
      }

      return result as Task
    } catch (err) {
      console.error('Error rejecting task:', err)
      throw err
    }
  }

  const voteTask = async (taskId: string, agree: boolean) => {
    try {
      const result = await tasksApi.voteTask(taskId, agree)

      // Update local state - voteTask returns different format, handle carefully
      const taskIndex = tasks.value.findIndex(task => task.id === taskId)
      if (taskIndex !== -1 && result && typeof result === 'object') {
        tasks.value[taskIndex] = { ...tasks.value[taskIndex], ...result } as Task
      }

      return result
    } catch (err) {
      console.error('Error voting on task:', err)
      throw err
    }
  }

  const deleteTask = async (taskId: string) => {
    try {
      await tasksApi.deleteTask(taskId)

      // Remove from local state
      const taskIndex = tasks.value.findIndex(task => task.id === taskId)
      if (taskIndex !== -1) {
        tasks.value.splice(taskIndex, 1)
        totalCount.value = Math.max(0, totalCount.value - 1)
      }
    } catch (err) {
      console.error('Error deleting task:', err)
      throw err
    }
  }

  // Remove task from local state without API call (for overtime scenarios)
  const removeTaskFromList = (taskId: string) => {
    const taskIndex = tasks.value.findIndex(task => task.id === taskId)
    if (taskIndex !== -1) {
      tasks.value.splice(taskIndex, 1)
      totalCount.value = Math.max(0, totalCount.value - 1)
    }
  }

  // Utility functions
  const getActiveLockTask = async (): Promise<LockTask | null> => {
    try {
      return await tasksApi.getActiveLockTask()
    } catch (err) {
      console.error('Error getting active lock task:', err)
      return null
    }
  }

  const checkAndCompleteExpiredTasks = async () => {
    try {
      return await tasksApi.checkAndCompleteExpiredTasks()
    } catch (err) {
      console.error('Error checking expired tasks:', err)
      throw err
    }
  }

  const getTaskTimeline = async (taskId: string) => {
    try {
      return await tasksApi.getTaskTimeline(taskId)
    } catch (err) {
      console.error('Error getting task timeline:', err)
      throw err
    }
  }

  // Filter management
  const setFilters = (newFilters: Partial<typeof filters.value>) => {
    filters.value = { ...filters.value, ...newFilters }
  }

  const clearFilters = () => {
    filters.value = {
      task_type: '',
      status: '',
      my_tasks: false
    }
  }

  // Reset state
  const reset = () => {
    tasks.value = []
    loading.value = false
    error.value = null
    currentPage.value = 1
    totalCount.value = 0
    hasMore.value = true
    clearFilters()
  }

  return {
    // State
    tasks,
    loading,
    error,
    currentPage,
    totalCount,
    hasMore,
    filters,

    // Actions
    fetchTasks,
    getPaginatedTasks,
    startTask,
    completeTask,
    stopTask,
    takeTask,
    submitTask,
    approveTask,
    rejectTask,
    voteTask,
    deleteTask,
    removeTaskFromList,
    getActiveLockTask,
    checkAndCompleteExpiredTasks,
    processVotingResults: async () => {
      try {
        return await tasksApi.processVotingResults()
      } catch (err) {
        console.error('Error processing voting results:', err)
        throw err
      }
    },
    getTaskTimeline,

    // Utilities
    setFilters,
    clearFilters,
    reset
  }
})