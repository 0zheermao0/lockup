import type { Router } from 'vue-router'

/**
 * 智能返回导航函数
 * 分析用户来源并智能返回到合适的页面
 *
 * @param router Vue Router 实例
 * @param options 配置选项
 */
export function smartGoBack(
  router: Router,
  options: {
    defaultRoute?: string
    checkReferrer?: boolean
  } = {}
) {
  const { defaultRoute = 'home', checkReferrer = true } = options

  // 检查是否有有效的历史记录
  const hasValidHistory = window.history.length > 1
  const referrer = document.referrer

  console.log('🔙 smartGoBack debug:', {
    hasValidHistory,
    historyLength: window.history.length,
    referrer,
    currentUrl: window.location.href
  })

  // 如果启用了引用页检查，分析用户来源
  if (checkReferrer && referrer) {
    const referrerUrl = new URL(referrer)
    const currentUrl = new URL(window.location.href)

    // 检查是否来自同一个应用（相同的origin）
    if (referrerUrl.origin === currentUrl.origin) {
      // 分析具体的来源页面并决定返回路由
      const referrerPath = referrerUrl.pathname

      console.log('🔙 Analyzing referrer path:', referrerPath)

      // 根据来源页面决定返回的目标
      let targetRoute = defaultRoute

      if (referrerPath === '/' || referrerPath === '/home') {
        targetRoute = 'home'
      } else if (referrerPath.startsWith('/tasks') && !referrerPath.includes('/tasks/')) {
        // 来自任务列表页面，但不是任务详情页面
        targetRoute = 'tasks'
      } else if (referrerPath.startsWith('/profile')) {
        targetRoute = 'profile'
      } else if (referrerPath.startsWith('/inventory')) {
        targetRoute = 'inventory'
      } else if (referrerPath.startsWith('/store')) {
        targetRoute = 'store'
      } else if (referrerPath.startsWith('/games')) {
        targetRoute = 'games'
      } else if (referrerPath.startsWith('/explore')) {
        targetRoute = 'explore'
      } else if (referrerPath.startsWith('/post')) {
        // 来自动态相关页面，返回首页（动态流）
        targetRoute = 'home'
      }

      console.log('🔙 Determined target route from referrer:', targetRoute)

      // 如果有有效历史记录，优先使用浏览器返回
      if (hasValidHistory) {
        try {
          router.back()
          return
        } catch (error) {
          console.warn('router.back() failed, using determined route:', error)
          router.push({ name: targetRoute })
          return
        }
      } else {
        // 没有有效历史记录，直接跳转到分析出的目标页面
        console.log('🔙 No valid history, navigating to determined route:', targetRoute)
        router.push({ name: targetRoute })
        return
      }
    }
  }

  // 如果有有效历史记录但不是从应用内跳转，或者没有启用引用页检查
  if (hasValidHistory) {
    try {
      console.log('🔙 Using browser back with valid history')
      router.back()
    } catch (error) {
      console.warn('router.back() failed, falling back to default route:', error)
      router.push({ name: defaultRoute })
    }
  } else {
    // 没有有效历史记录，返回到默认页面
    console.log('🔙 No valid history, using default route:', defaultRoute)
    router.push({ name: defaultRoute })
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