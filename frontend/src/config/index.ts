// 应用配置文件
export const config = {
  // API配置
  api: {
    // 从环境变量获取API基础URL
    baseURL: import.meta.env.VITE_API_BASE_URL || 'https://lock-down.z820.changhai0109.com/api',
    // 请求超时时间（毫秒）
    timeout: 10000,
  },

  // 应用信息
  app: {
    name: 'Lockup Community',
    version: '1.0.0',
  },

  // 调试模式
  debug: import.meta.env.DEV,
}

// 导出API基础URL以便其他文件使用
export const API_BASE_URL = config.api.baseURL

// 打印配置信息（仅在开发环境）
if (config.debug) {
  console.log('App Config:', config)
}