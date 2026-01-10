import type { Router } from 'vue-router'
import { useNavigationStore } from '../stores/navigation'

/**
 * 智能返回导航函数 - 应用内安全返回
 * 分析用户在应用内的导航路径，确保返回时不离开应用
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
  const navigationStore = useNavigationStore()

  const referrer = document.referrer
  const currentUrl = window.location.href
  const currentPath = window.location.pathname

  console.log('🔙 smartGoBack debug:', {
    currentPath,
    referrer,
    defaultRoute
  })

  // 确定目标返回路由
  let targetRoute = defaultRoute

  // 特殊处理：如果当前在任务详情页面，应该返回任务列表并恢复状态
  if (currentPath.startsWith('/tasks/')) {
    console.log('🔙 Current page is task detail, returning to tasks list with state restoration')
    targetRoute = 'tasks'

    // 检查是否有保存的任务视图状态
    const savedTasksState = navigationStore.getTasksViewState()
    if (savedTasksState) {
      console.log('🔙 Found saved tasks view state, navigating to tasks')

      // 直接导航到任务路由，状态将在TaskView组件中恢复
      try {
        router.push({ name: 'tasks' })
        return
      } catch (error) {
        console.error('🔙 Failed to navigate with saved tasks state:', error)
        // 失败时继续执行常规导航
      }
    }
  }
  // 如果当前在动态详情页面，返回首页并恢复状态
  else if (currentPath.startsWith('/post/') || currentPath.startsWith('/posts/')) {
    console.log('🔙 Current page is post detail, returning to home with state restoration')
    targetRoute = 'home'

    // 检查是否有保存的动态视图状态
    const savedPostsState = navigationStore.getPostsViewState()
    if (savedPostsState) {
      console.log('🔙 Found saved posts view state, navigating to home')

      try {
        router.push({ name: 'home' })
        // Note: State restoration will happen in HomeView onMounted
        return
      } catch (error) {
        console.error('🔙 Failed to navigate with saved posts state:', error)
        // 失败时继续执行常规导航
      }
    }
  }
  // 如果启用了引用页检查且有引用页，分析来源
  else if (checkReferrer && referrer) {
    try {
      const referrerUrl = new URL(referrer)
      const currentUrlObj = new URL(currentUrl)

      // 检查是否来自同一个应用（相同的origin）
      if (referrerUrl.origin === currentUrlObj.origin) {
        const referrerPath = referrerUrl.pathname

        // 根据来源页面决定返回的目标（仅限应用内页面）
        if (referrerPath === '/' || referrerPath === '/home') {
          targetRoute = 'home'
        } else if (referrerPath === '/tasks' || referrerPath === '/tasks/') {
          // 来自任务列表页面
          targetRoute = 'tasks'
        } else if (referrerPath.startsWith('/tasks/') && referrerPath !== currentUrlObj.pathname) {
          // 来自其他任务详情页面，返回任务列表
          targetRoute = 'tasks'
        } else if (referrerPath.startsWith('/post/') || referrerPath.startsWith('/posts/')) {
          // 来自动态详情页面，返回首页（动态流）
          targetRoute = 'home'
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
        } else {
          // 其他应用内页面，返回首页
          targetRoute = 'home'
        }

        console.log('🔙 Using referrer-based route:', targetRoute)
      } else {
        // 来自外部网站，使用默认路由
        console.log('🔙 Referrer is external, using default route:', defaultRoute)
        targetRoute = defaultRoute
      }
    } catch (error) {
      console.warn('🔙 Error parsing referrer URL:', error)
      targetRoute = defaultRoute
    }
  }


  const currentRoute = router.currentRoute.value

  if (currentRoute.name === targetRoute) {
    console.warn('🔙 Target route is current route, falling back to default')
    targetRoute = defaultRoute
  }

  // 执行应用内导航 - 永远不使用 router.back()
  console.log('🔙 Final decision - Navigating to target route:', targetRoute)
  router.push({ name: targetRoute })
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
    smartGoBack(router, { defaultRoute: fallbackRoute })
  }
}