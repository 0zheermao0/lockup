import type { LockTask, TaskCreateRequest } from '../types/index.js'
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

  return response.json();
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
  } = {}) => {
    const searchParams = new URLSearchParams()

    if (params.task_type) searchParams.append('task_type', params.task_type)
    if (params.status) searchParams.append('status', params.status)
    if (params.my_tasks) searchParams.append('my_tasks', 'true')
    if (params.my_taken) searchParams.append('my_taken', 'true')

    const queryString = searchParams.toString()
    const url = queryString ? `/tasks/?${queryString}` : '/tasks/'

    return apiRequest(url)
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

  // 投票
  voteTask: async (id: string, agree: boolean): Promise<any> => {
    return apiRequest(`/tasks/${id}/vote/`, {
      method: 'POST',
      body: JSON.stringify({ agree })
    })
  },

  // 审核通过任务板任务
  approveTask: async (id: string): Promise<LockTask> => {
    return apiRequest(`/tasks/${id}/approve/`, {
      method: 'POST'
    })
  },

  // 审核拒绝任务板任务
  rejectTask: async (id: string, rejectReason?: string): Promise<LockTask> => {
    return apiRequest(`/tasks/${id}/reject/`, {
      method: 'POST',
      body: JSON.stringify({
        reject_reason: rejectReason || ''
      })
    })
  },

  // 获取我的钥匙
  getMyKeys: async (): Promise<any[]> => {
    return apiRequest('/tasks/keys/my/')
  },

  // 为带锁任务随机加时
  addOvertime: async (id: string): Promise<any> => {
    return apiRequest(`/tasks/${id}/overtime/`, {
      method: 'POST'
    })
  }
}