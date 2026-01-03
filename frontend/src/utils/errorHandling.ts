/**
 * 错误处理工具函数
 * 将后端API错误映射为用户友好的错误消息
 */


export interface ApiError {
  message: string
  code?: string
  details?: any
}

export interface UserFriendlyError {
  title: string
  message: string
  actionSuggestion?: string
  severity: 'error' | 'warning' | 'info'
}

/**
 * 任务创建相关错误映射
 */
const TASK_CREATION_ERROR_MAP: Record<string, UserFriendlyError> = {
  // 验证错误
  'TITLE_REQUIRED': {
    title: '标题不能为空',
    message: '请输入任务标题',
    actionSuggestion: '请填写一个描述性的任务标题',
    severity: 'error'
  },
  'DURATION_TOO_SHORT': {
    title: '持续时间过短',
    message: '带锁任务持续时间至少为1分钟',
    actionSuggestion: '请增加任务的持续时间',
    severity: 'error'
  },
  'DURATION_VALUE_REQUIRED': {
    title: '持续时间必填',
    message: '带锁任务必须设置持续时间',
    actionSuggestion: '请选择任务的持续时间',
    severity: 'error'
  },
  'RANDOM_DURATION_MAX_REQUIRED': {
    title: '最大时间必填',
    message: '随机时间类型必须设置最大持续时间',
    actionSuggestion: '请设置最大持续时间，且必须大于最短时间',
    severity: 'error'
  },
  'VOTE_AGREEMENT_RATIO_REQUIRED': {
    title: '投票比例必填',
    message: '投票解锁必须设置同意比例',
    actionSuggestion: '请设置投票通过所需的同意比例',
    severity: 'error'
  },
  'REWARD_REQUIRED': {
    title: '奖励积分必填',
    message: '任务板必须设置奖励积分',
    actionSuggestion: '请设置合理的奖励积分数量',
    severity: 'error'
  },
  'MAX_DURATION_REQUIRED': {
    title: '最大完成时间必填',
    message: '任务板必须设置最大完成时间',
    actionSuggestion: '请设置任务的最大完成时间',
    severity: 'error'
  },
  'REWARD_TOO_HIGH': {
    title: '奖励积分过高',
    message: '奖励积分不能超过10000',
    actionSuggestion: '请降低奖励积分数量',
    severity: 'error'
  },
  'REWARD_TOO_LOW': {
    title: '奖励积分过低',
    message: '奖励积分至少为1',
    actionSuggestion: '请增加奖励积分数量',
    severity: 'error'
  },

  // 权限和状态错误
  'ACTIVE_LOCK_TASK_EXISTS': {
    title: '已有进行中的任务',
    message: '您已经有一个正在进行的带锁任务，一次只能进行一个带锁任务',
    actionSuggestion: '请先完成当前任务或等待任务结束',
    severity: 'error'
  },
  'INSUFFICIENT_COINS': {
    title: '积分不足',
    message: '您的积分不足以创建此任务',
    actionSuggestion: '请完成其他任务获取更多积分',
    severity: 'error'
  },
  'INVENTORY_FULL': {
    title: '背包已满',
    message: '您的背包空间不足，无法获得钥匙',
    actionSuggestion: '请先清理背包空间或使用一些道具',
    severity: 'error'
  },
  'AUTHENTICATION_REQUIRED': {
    title: '需要登录',
    message: '请先登录后再创建任务',
    actionSuggestion: '请登录您的账户',
    severity: 'error'
  },

  // 网络和服务器错误
  'NETWORK_ERROR': {
    title: '网络连接失败',
    message: '网络连接出现问题，请检查您的网络连接',
    actionSuggestion: '请检查网络连接后重试',
    severity: 'error'
  },
  'SERVER_ERROR': {
    title: '服务器错误',
    message: '服务器暂时出现问题，请稍后重试',
    actionSuggestion: '请稍后重试，如果问题持续存在请联系管理员',
    severity: 'error'
  },
  'TIMEOUT_ERROR': {
    title: '请求超时',
    message: '请求处理时间过长，请稍后重试',
    actionSuggestion: '请稍后重试',
    severity: 'warning'
  }
}

/**
 * 动态创建相关错误映射
 */
const POST_CREATION_ERROR_MAP: Record<string, UserFriendlyError> = {
  // 内容验证错误
  'CONTENT_REQUIRED': {
    title: '内容不能为空',
    message: '请输入动态内容',
    actionSuggestion: '请填写动态的具体内容',
    severity: 'error'
  },
  'CONTENT_TOO_LONG': {
    title: '内容过长',
    message: '动态内容超过了最大长度限制',
    actionSuggestion: '请缩短动态内容',
    severity: 'error'
  },
  'INVALID_POST_TYPE': {
    title: '动态类型无效',
    message: '选择的动态类型不正确',
    actionSuggestion: '请选择正确的动态类型',
    severity: 'error'
  },

  // 打卡相关错误
  'NO_ACTIVE_STRICT_TASK': {
    title: '无活跃的严格模式任务',
    message: '当前没有活跃的严格模式带锁任务',
    actionSuggestion: '请先创建并启动一个严格模式的带锁任务',
    severity: 'error'
  },
  'CHECKIN_ALREADY_EXISTS': {
    title: '今日已打卡',
    message: '您今天已经发布过打卡动态',
    actionSuggestion: '每天只能发布一次打卡动态',
    severity: 'warning'
  },
  'INVALID_VERIFICATION_CODE': {
    title: '验证码错误',
    message: '输入的验证码不正确',
    actionSuggestion: '请输入正确的4位数字验证码',
    severity: 'error'
  },

  // 文件上传错误
  'FILE_TOO_LARGE': {
    title: '文件过大',
    message: '上传的文件超过了大小限制',
    actionSuggestion: '请压缩文件或选择较小的文件',
    severity: 'error'
  },
  'INVALID_FILE_TYPE': {
    title: '文件类型不支持',
    message: '不支持此文件类型',
    actionSuggestion: '请上传支持的文件格式（图片、视频等）',
    severity: 'error'
  },
  'UPLOAD_FAILED': {
    title: '文件上传失败',
    message: '文件上传过程中出现错误',
    actionSuggestion: '请重试文件上传',
    severity: 'error'
  },

  // 权限错误
  'AUTHENTICATION_REQUIRED': {
    title: '需要登录',
    message: '请先登录后再发布动态',
    actionSuggestion: '请登录您的账户',
    severity: 'error'
  },
  'PERMISSION_DENIED': {
    title: '权限不足',
    message: '您没有权限执行此操作',
    actionSuggestion: '请检查您的账户权限',
    severity: 'error'
  },

  // 频率限制
  'RATE_LIMIT_EXCEEDED': {
    title: '操作过于频繁',
    message: '您的操作过于频繁，请稍后重试',
    actionSuggestion: '请等待一段时间后再试',
    severity: 'warning'
  }
}

/**
 * @deprecated 解析后端API错误响应
 */
export function parseApiError(error: any): ApiError {
  console.log("debugddddddd", error, error.data, error.response);
  let status: number | undefined
  let data: any


  // TODO: better routing?
  // 处理ApiError错误格式
  if (error.data) {
    console.log("debuginsideapieror");
    status = error.status
    data = error.data
  }
  // 处理axios错误格式
  else if (error.response) {
    console.log("debuginsideaxioserror");
    status = error.response.status
    data = error.response.data
  }
  else {
    console.log("debuginsideunknownerror");
    status = undefined
    data = error
  }

  console.log("debugparsedata", { status, data });

  if (data && typeof data === 'object') {
    // Django REST framework 标准错误格式
    if (data.detail) {
      return {
        message: data.detail,
        code: data.code || `HTTP_${status}`,
        details: data
      }
    }

    // 字段验证错误
    if (data.non_field_errors) {
      return {
        message: Array.isArray(data.non_field_errors)
          ? data.non_field_errors[0]
          : data.non_field_errors,
        code: 'VALIDATION_ERROR',
        details: data
      }
    }

    // 特定字段错误
    const fieldErrors = Object.keys(data).filter(key =>
      key !== 'detail' && key !== 'code' && Array.isArray(data[key])
    )

    if (fieldErrors.length > 0) {
      const firstField = fieldErrors[0]
      if (firstField) {
        const fieldErrorArray = data[firstField]
        if (Array.isArray(fieldErrorArray) && fieldErrorArray.length > 0) {
          const firstError = fieldErrorArray[0]
          console.log("debugreturn", `${firstField}: ${firstError}`, `FIELD_ERROR_${firstField.toUpperCase()}`, data);
          return {
            message: `${firstField}: ${firstError}`,
            code: `FIELD_ERROR_${firstField.toUpperCase()}`,
            details: data
          }
        }
      }
    }

    // 通用错误消息
    if (data.error) {
      return {
        message: data.error,
        code: data.code || `HTTP_${status}`,
        details: data
      }
    }
  }

  // HTTP状态码错误
  if (status) {

    return {
      message: `HTTP ${status} Error`,
      code: `HTTP_${status}`,
      details: { status, data }
    }
  }


  // 网络错误
  if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
    return {
      message: 'Request timeout',
      code: 'TIMEOUT_ERROR',
      details: error
    }
  }

  if (error.code === 'NETWORK_ERROR' || !error.response) {
    return {
      message: 'Network connection failed',
      code: 'NETWORK_ERROR',
      details: error
    }
  }

  // 未知错误
  return {
    message: error.message || 'Unknown error occurred',
    code: 'UNKNOWN_ERROR',
    details: error
  }
}

/**
 * 获取默认错误信息
 */
function getDefaultError(apiError: ApiError): UserFriendlyError {
  return {
    title: '操作失败',
    message: apiError.message,
    actionSuggestion: '请重试，如果问题持续存在请联系管理员',
    severity: 'error'
  }
}

/**
 * 将API错误映射为用户友好的错误消息
 */
export function mapToUserFriendlyError(
  apiError: ApiError,
  context: 'task' | 'post' = 'task'
): UserFriendlyError {
  const errorMap = context === 'task' ? TASK_CREATION_ERROR_MAP : POST_CREATION_ERROR_MAP


  // 尝试根据错误消息匹配
  const detailedMessage = apiError?.message?.toLowerCase?.() ?? ''
  console.log("debugmappingerror", detailedMessage);

  // 任务创建相关错误匹配
  if (context === 'task') {
    if (detailedMessage.includes('title') && detailedMessage.includes('required')) {
      return errorMap['TITLE_REQUIRED'] ?? getDefaultError(apiError)
    }
    if (detailedMessage.includes('持续时间') && detailedMessage.includes('至少')) {
      return errorMap['DURATION_TOO_SHORT'] ?? getDefaultError(apiError)
    }
    if (detailedMessage.includes('已经有一个正在进行的带锁任务')) {
      return errorMap['ACTIVE_LOCK_TASK_EXISTS'] ?? getDefaultError(apiError)
    }
    if (detailedMessage.includes('积分不足') || detailedMessage.includes('insufficient')) {
      return errorMap['INSUFFICIENT_COINS'] ?? getDefaultError(apiError)
    }
    if (detailedMessage.includes('背包') || detailedMessage.includes('inventory')) {
      return errorMap['INVENTORY_FULL'] ?? getDefaultError(apiError)
    }
    if (detailedMessage.includes('随机时间') && detailedMessage.includes('最大')) {
      return errorMap['RANDOM_DURATION_MAX_REQUIRED'] ?? getDefaultError(apiError)
    }
    if (detailedMessage.includes('投票') && detailedMessage.includes('比例')) {
      return errorMap['VOTE_AGREEMENT_RATIO_REQUIRED'] ?? getDefaultError(apiError)
    }
    if (detailedMessage.includes('奖励') && detailedMessage.includes('必须')) {
      return errorMap['REWARD_REQUIRED'] ?? getDefaultError(apiError)
    }
    if (detailedMessage.includes('奖励') && detailedMessage.includes('10000')) {
      return errorMap['REWARD_TOO_HIGH'] ?? getDefaultError(apiError)
    }
  }

  // 动态创建相关错误匹配
  if (context === 'post') {
    if (detailedMessage.includes('content') && detailedMessage.includes('required')) {
      return errorMap['CONTENT_REQUIRED'] ?? getDefaultError(apiError)
    }
    if (detailedMessage.includes('没有活跃的严格模式')) {
      return errorMap['NO_ACTIVE_STRICT_TASK'] ?? getDefaultError(apiError)
    }
    if (detailedMessage.includes('已经发布过打卡')) {
      return errorMap['CHECKIN_ALREADY_EXISTS'] ?? getDefaultError(apiError)
    }
    if (detailedMessage.includes('验证码') || detailedMessage.includes('verification')) {
      return errorMap['INVALID_VERIFICATION_CODE'] ?? getDefaultError(apiError)
    }
    if (detailedMessage.includes('file') && detailedMessage.includes('large')) {
      return errorMap['FILE_TOO_LARGE'] ?? getDefaultError(apiError)
    }
    if (detailedMessage.includes('file') && detailedMessage.includes('type')) {
      return errorMap['INVALID_FILE_TYPE'] ?? getDefaultError(apiError)
    }
  }

  // 通用错误匹配
  const commonErrorMap = context === 'task' ? TASK_CREATION_ERROR_MAP : POST_CREATION_ERROR_MAP

  if (detailedMessage.includes('authentication') || detailedMessage.includes('登录')) {
    return commonErrorMap['AUTHENTICATION_REQUIRED'] ?? getDefaultError(apiError)
  }
  if (detailedMessage.includes('network') || detailedMessage.includes('网络')) {
    return commonErrorMap['NETWORK_ERROR'] ?? getDefaultError(apiError)
  }
  if (detailedMessage.includes('timeout') || detailedMessage.includes('超时')) {
    return commonErrorMap['TIMEOUT_ERROR'] ?? getDefaultError(apiError)
  }
  if (detailedMessage.includes('server') || detailedMessage.includes('500')) {
    return commonErrorMap['SERVER_ERROR'] ?? getDefaultError(apiError)
  }

  // 最后匹配错误代码
  if (apiError.code) {
    const mappedError = errorMap[apiError.code]
    if (mappedError) {
      return mappedError
    }
  }

  // 默认错误
  return getDefaultError(apiError)
}

/**
 * 处理API错误的主要函数
 * @param error - 原始错误对象
 * @param context - 错误上下文（任务或动态）
 * @returns 用户友好的错误信息
 */
export function handleApiError(error: any, context: 'task' | 'post' = 'task'): UserFriendlyError {
  // const apiError = parseApiError(error)
  const apiError = error
  return mapToUserFriendlyError(apiError, context)
}

/**
 * 格式化错误消息用于通知显示
 */
export function formatErrorForNotification(userFriendlyError: UserFriendlyError): {
  title: string
  message: string
  secondaryMessage: string
  type: 'error' | 'warning' | 'info'
  details: Record<string, any>
} {
  return {
    title: userFriendlyError.title,
    message: userFriendlyError.message,
    secondaryMessage: userFriendlyError.actionSuggestion || '',
    type: userFriendlyError.severity,
    details: {}
  }
}