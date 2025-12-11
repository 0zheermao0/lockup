import type { Router } from 'vue-router'

/**
 * 智能返回导航函数
 * 优先使用浏览器历史记录，如果不可用则使用指定的备用路由
 *
 * @param router Vue Router 实例
 * @param fallbackRoute 备用路由名称，默认为 'home'
 * @param options 额外配置选项
 */
export function smartGoBack(
  router: Router,
  fallbackRoute: string = 'home',
  options: {
    fallbackParams?: Record<string, any>
    checkReferrer?: boolean
  } = {}
) {
  const { fallbackParams = {}, checkReferrer = true } = options

  // 检查是否有有效的历史记录
  const hasValidHistory = window.history.length > 1

  // 检查是否从应用内页面跳转而来（如果启用了检查）
  let isFromAppPage = true
  if (checkReferrer) {
    const referrer = document.referrer
    isFromAppPage = referrer && (
      referrer.includes('/tasks') ||
      referrer.includes('/home') ||
      referrer.includes('/profile') ||
      referrer.includes('/inventory') ||
      referrer.includes('/store') ||
      referrer.includes('/games') ||
      referrer.includes('/explore') ||
      referrer.includes('/posts') ||
      referrer.includes('/post')
    )
  }

  console.log('🔙 smartGoBack debug:', {
    hasValidHistory,
    historyLength: window.history.length,
    referrer: document.referrer,
    isFromAppPage,
    fallbackRoute,
    checkReferrer
  })

  // 如果有有效历史记录且来源是应用内页面，使用浏览器返回
  if (hasValidHistory && isFromAppPage) {
    try {
      router.back()
    } catch (error) {
      console.warn('router.back() failed, falling back to specified route:', error)
      router.push({ name: fallbackRoute, params: fallbackParams })
    }
  } else {
    // 否则返回到指定的备用页面
    console.log('🔙 Using fallback navigation to', fallbackRoute)
    router.push({ name: fallbackRoute, params: fallbackParams })
  }
}

/**
 * 创建智能返回函数的快捷方式
 *
 * @param router Vue Router 实例
 * @param fallbackRoute 备用路由名称
 * @returns 返回函数
 */
export function createSmartGoBack(router: Router, fallbackRoute: string = 'home') {
  return (fallbackParams?: Record<string, any>) => {
    smartGoBack(router, fallbackRoute, { fallbackParams })
  }
}