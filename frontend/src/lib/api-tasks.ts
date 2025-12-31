import type { LockTask, TaskCreateRequest, PinningQueueStatus, PinningCarouselData, SunBottleResponse } from '../types/index'
import { API_BASE_URL } from '../config/index.js';

class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public data?: any
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new ApiError(
      errorData.message || `HTTP ${response.status}: ${response.statusText}`,
      response.status,
      errorData
    );
  }

  // Handle responses with no content (like DELETE requests)
  if (response.status === 204 || response.headers.get('content-length') === '0') {
    return null as T;
  }

  // Check if response has content to parse
  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    return response.json();
  }

  // For non-JSON responses, return text
  const text = await response.text();
  return (text ? text : null) as T;
}

async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = localStorage.getItem('token');

  const config: RequestInit = {
    headers: {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Token ${token}` }),
      ...options.headers,
    },
    ...options,
  };

  const response = await fetch(`${API_BASE_URL}${endpoint}`, config);
  return handleResponse<T>(response);
}

// Tasks API
export const tasksApi = {
  // 获取任务列表
  getTasks: async (params: {
    task_type?: 'lock' | 'board'
    status?: string
    my_tasks?: boolean
    my_taken?: boolean
    can_overtime?: boolean
    page?: number
    page_size?: number
    sort_by?: string
    sort_order?: 'asc' | 'desc'
  } = {}) => {
    const searchParams = new URLSearchParams()

    if (params.task_type) searchParams.append('task_type', params.task_type)
    if (params.status) searchParams.append('status', params.status)
    if (params.my_tasks) searchParams.append('my_tasks', 'true')
    if (params.my_taken) searchParams.append('my_taken', 'true')
    if (params.can_overtime) searchParams.append('can_overtime', 'true')
    if (params.page) searchParams.append('page', params.page.toString())
    if (params.page_size) searchParams.append('page_size', params.page_size.toString())
    if (params.sort_by) searchParams.append('sort_by', params.sort_by)
    if (params.sort_order) searchParams.append('sort_order', params.sort_order)

    const queryString = searchParams.toString()
    const url = queryString ? `/tasks/?${queryString}` : '/tasks/'

    return apiRequest(url)
  },

  // 获取任务列表（返回数组）
  getTasksList: async (params: {
    task_type?: 'lock' | 'board'
    status?: string
    my_tasks?: boolean
    my_taken?: boolean
    can_overtime?: boolean
    page_size?: number
    sort_by?: string
    sort_order?: 'asc' | 'desc'
  } = {}) => {
    const searchParams = new URLSearchParams()

    if (params.task_type) searchParams.append('task_type', params.task_type)
    if (params.status) searchParams.append('status', params.status)
    if (params.my_tasks) searchParams.append('my_tasks', 'true')
    if (params.my_taken) searchParams.append('my_taken', 'true')
    if (params.can_overtime) searchParams.append('can_overtime', 'true')
    if (params.page_size) searchParams.append('page_size', params.page_size.toString())
    if (params.sort_by) searchParams.append('sort_by', params.sort_by)
    if (params.sort_order) searchParams.append('sort_order', params.sort_order)

    const queryString = searchParams.toString()
    const url = queryString ? `/tasks/?${queryString}` : '/tasks/'

    const response = await apiRequest<any>(url)
    return response.results || response
  },

  // 获取单个任务详情
  getTask: async (id: string): Promise<LockTask> => {
    return apiRequest(`/tasks/${id}/`)
  },

  // 创建任务
  createTask: async (data: TaskCreateRequest): Promise<LockTask> => {
    return apiRequest('/tasks/', {
      method: 'POST',
      body: JSON.stringify(data)
    })
  },

  // 更新任务
  updateTask: async (id: string, data: Partial<LockTask>): Promise<LockTask> => {
    return apiRequest(`/tasks/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(data)
    })
  },

  // 删除任务
  deleteTask: async (id: string): Promise<void> => {
    return apiRequest(`/tasks/${id}/`, {
      method: 'DELETE'
    })
  },

  // 开始任务
  startTask: async (id: string): Promise<LockTask> => {
    return apiRequest(`/tasks/${id}/start/`, {
      method: 'POST'
    })
  },

  // 完成任务
  completeTask: async (id: string): Promise<LockTask> => {
    return apiRequest(`/tasks/${id}/complete/`, {
      method: 'POST'
    })
  },

  // 停止任务
  stopTask: async (id: string): Promise<LockTask> => {
    return apiRequest(`/tasks/${id}/stop/`, {
      method: 'POST'
    })
  },

  // 接取任务板任务
  takeTask: async (id: string): Promise<LockTask> => {
    return apiRequest(`/tasks/${id}/take/`, {
      method: 'POST'
    })
  },

  // 提交任务板完成证明
  submitTask: async (id: string, completionProof: string): Promise<LockTask> => {
    return apiRequest(`/tasks/${id}/submit/`, {
      method: 'POST',
      body: JSON.stringify({
        completion_proof: completionProof
      })
    })
  },

  // 提交任务板完成证明（包含文件）- 支持多人任务
  submitTaskWithFiles: async (id: string, formData: FormData): Promise<LockTask> => {
    const token = localStorage.getItem('token');

    const response = await fetch(`${API_BASE_URL}/tasks/${id}/submit/`, {
      method: 'POST',
      headers: {
        ...(token && { Authorization: `Token ${token}` }),
        // Don't set Content-Type header, let browser set it with boundary for multipart/form-data
      },
      body: formData
    });

    return handleResponse<LockTask>(response);
  },


  // 发起投票
  startVoting: async (id: string): Promise<LockTask> => {
    return apiRequest(`/tasks/${id}/start-voting/`, {
      method: 'POST'
    })
  },

  // 投票
  voteTask: async (id: string, agree: boolean): Promise<any> => {
    return apiRequest(`/tasks/${id}/vote/`, {
      method: 'POST',
      body: JSON.stringify({ agree })
    })
  },

  // 审核通过任务板任务 - 支持多人任务
  approveTask: async (id: string, participantId?: string, reviewComment?: string): Promise<LockTask> => {
    return apiRequest(`/tasks/${id}/approve/`, {
      method: 'POST',
      body: JSON.stringify({
        participant_id: participantId,
        review_comment: reviewComment || ''
      })
    })
  },

  // 审核拒绝任务板任务 - 支持多人任务
  rejectTask: async (id: string, rejectReason?: string, participantId?: string): Promise<LockTask> => {
    return apiRequest(`/tasks/${id}/reject/`, {
      method: 'POST',
      body: JSON.stringify({
        reject_reason: rejectReason || '',
        participant_id: participantId
      })
    })
  },

  // 审核通过单个参与者（多人任务专用）
  approveParticipant: async (id: string, participantId: string, reviewComment?: string): Promise<any> => {
    return apiRequest(`/tasks/${id}/approve/`, {
      method: 'POST',
      body: JSON.stringify({
        participant_id: participantId,
        review_comment: reviewComment || ''
      })
    })
  },

  // 审核拒绝单个参与者（多人任务专用）
  rejectParticipant: async (id: string, participantId: string, reviewComment?: string): Promise<any> => {
    return apiRequest(`/tasks/${id}/reject/`, {
      method: 'POST',
      body: JSON.stringify({
        participant_id: participantId,
        review_comment: reviewComment || ''
      })
    })
  },

  // 结束任务板任务
  endTask: async (id: string, endReason?: string): Promise<LockTask> => {
    return apiRequest(`/tasks/${id}/end/`, {
      method: 'POST',
      body: JSON.stringify({
        end_reason: endReason || '发布者手动结束任务'
      })
    })
  },

  // 获取我的钥匙
  getMyKeys: async (): Promise<any[]> => {
    return apiRequest('/tasks/keys/my/')
  },

  // 为带锁任务随机加时
  addOvertime: async (id: string): Promise<{
    message: string
    overtime_minutes: number
    new_end_time: string
    is_frozen: boolean
    frozen_end_time: string | null
  }> => {
    return apiRequest(`/tasks/${id}/overtime/`, {
      method: 'POST'
    })
  },

  // 冻结任务倒计时
  freezeTask: async (id: string): Promise<any> => {
    return apiRequest(`/tasks/${id}/freeze/`, {
      method: 'POST'
    })
  },

  // 解冻任务倒计时
  unfreezeTask: async (id: string): Promise<any> => {
    return apiRequest(`/tasks/${id}/unfreeze/`, {
      method: 'POST'
    })
  },

  // 检查并完成过期任务
  checkAndCompleteExpiredTasks: async (): Promise<any> => {
    return apiRequest('/tasks/check-expired/', {
      method: 'GET'
    })
  },

  // 处理小时奖励
  processHourlyRewards: async (): Promise<any> => {
    return apiRequest('/tasks/process-hourly-rewards/', {
      method: 'POST'
    })
  },

  // 处理投票结果
  processVotingResults: async (): Promise<any> => {
    return apiRequest('/tasks/process-voting/', {
      method: 'POST'
    })
  },

  // 获取任务时间线
  getTaskTimeline: async (id: string): Promise<any> => {
    return apiRequest(`/tasks/${id}/timeline/`, {
      method: 'GET'
    })
  },

  // 获取当前活跃的带锁任务
  getActiveLockTask: async (): Promise<LockTask | null> => {
    try {
      const response = await apiRequest<any>('/tasks/?task_type=lock&status=active&my_tasks=true')
      const tasks = response.results || response
      return tasks.length > 0 ? tasks[0] : null
    } catch (error) {
      console.error('Error getting active lock task:', error)
      return null
    }
  },

  // 获取任务数量统计
  getTaskCounts: async (): Promise<{
    lock_tasks: {
      all: number
      active: number
      voting: number
      completed: number
      my_tasks: number
    }
    board_tasks: {
      all: number
      open: number
      taken: number
      submitted: number
      completed: number
      my_published: number
      my_taken: number
    }
  }> => {
    return apiRequest('/tasks/counts/')
  },

  // 手动时间调整（钥匙玩法）
  manualTimeAdjustment: async (id: string, type: 'increase' | 'decrease'): Promise<{
    message: string
    adjustment_minutes: number
    new_end_time: string
    is_frozen: boolean
    frozen_end_time: string | null
    cost: number
    remaining_coins: number
  }> => {
    return apiRequest(`/tasks/${id}/manual-time-adjustment/`, {
      method: 'POST',
      body: JSON.stringify({ type })
    })
  },

  // 切换时间显示/隐藏（钥匙玩法）
  toggleTimeDisplay: async (id: string): Promise<{
    message: string
    time_display_hidden: boolean
    cost: number
    remaining_coins: number
  }> => {
    return apiRequest(`/tasks/${id}/toggle-time-display/`, {
      method: 'POST'
    })
  },

  // 置顶任务创建者（钥匙持有者专属）
  pinTaskOwner: async (id: string, coinsSpent: number = 60, durationMinutes: number = 30): Promise<{
    message: string
    position?: number
    queue_status?: any
    coins_remaining: number
  }> => {
    return apiRequest(`/tasks/${id}/pin/`, {
      method: 'POST',
      body: JSON.stringify({
        coins_spent: coinsSpent,
        duration_minutes: durationMinutes
      })
    })
  },

  // 取消置顶任务创建者（管理员专用）
  unpinTaskOwner: async (id: string): Promise<{
    message: string
    queue_status?: any
  }> => {
    return apiRequest(`/tasks/${id}/unpin/`, {
      method: 'DELETE'
    })
  },

  // 获取置顶状态和队列信息
  getPinningStatus: async (): Promise<PinningQueueStatus> => {
    return apiRequest('/tasks/pinning-status/')
  },

  // 获取置顶任务轮播数据
  getPinnedTasksForCarousel: async (): Promise<{
    pinned_tasks: PinningCarouselData[]
    count: number
  }> => {
    return apiRequest('/tasks/pinned-carousel/')
  },

  // 钥匙持有者创建专属任务
  createExclusiveTask: async (taskId: string, taskData: {
    title: string
    description: string
    max_duration?: string
    deadline?: string
  }): Promise<{
    message: string
    task_id: string
    assigned_to: string
    coins_remaining: number
  }> => {
    return apiRequest(`/tasks/${taskId}/create-exclusive-task/`, {
      method: 'POST',
      body: JSON.stringify(taskData)
    })
  },

  // 使用探测雷达
  useDetectionRadar: async (id: string): Promise<{
    message: string
    revealed_data: {
      actual_end_time: string
      time_remaining_ms: number
      is_frozen: boolean
      frozen_end_time: string | null
      status_text: string
      task_title: string
    }
    item_destroyed: boolean
  }> => {
    return apiRequest(`/tasks/${id}/use-detection-radar/`, {
      method: 'POST'
    })
  },

  // 使用暴雪瓶
  useBlizzardBottle: async (): Promise<{
    message: string
    frozen_tasks_count: number
    affected_users_count: number
    frozen_tasks: Array<{
      task_id: string
      task_title: string
      owner: string
    }>
    item_destroyed: boolean
  }> => {
    return apiRequest('/tasks/use-blizzard-bottle/', {
      method: 'POST'
    })
  },

  // 使用太阳瓶
  useSunBottle: async (): Promise<SunBottleResponse> => {
    return apiRequest('/tasks/use-sun-bottle/', {
      method: 'POST'
    })
  },

  // 使用时间沙漏
  useTimeHourglass: async (id: string): Promise<{
    message: string
    rollback_data: {
      reverted_events_count: number
      new_end_time: string | null
      is_frozen: boolean
      rollback_id: string
    }
    item_destroyed: boolean
  }> => {
    return apiRequest(`/tasks/${id}/use-time-hourglass/`, {
      method: 'POST'
    })
  }
}