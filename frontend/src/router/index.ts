import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import HomeView from '../views/HomeView.vue'
import LoginView from '../views/LoginView.vue'
import RegisterView from '../views/RegisterView.vue'
import PasswordResetView from '../views/PasswordResetView.vue'
import PostDetailView from '../views/PostDetailView.vue'
import ProfileView from '../views/ProfileView.vue'
import TaskView from '../views/TaskView.vue'
import TaskDetailView from '../views/TaskDetailView.vue'
import StoreView from '../views/StoreView.vue'
import InventoryView from '../views/InventoryView.vue'
import GameView from '../views/GameView.vue'
import ExploreView from '../views/ExploreView.vue'
import ClaimView from '../views/ClaimView.vue'
import TelegramCallbackView from '../views/TelegramCallbackView.vue'
import CommunityStatsView from '../views/CommunityStatsView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
      meta: { requiresAuth: true, transition: 'page-fade' }
    },
    {
      path: '/post/:id',
      name: 'post-detail',
      component: PostDetailView,
      meta: { requiresAuth: true, transition: 'page-slide' }
    },
    {
      path: '/posts/:id',
      redirect: to => ({ name: 'post-detail', params: to.params })
    },
    {
      path: '/profile/:id?',
      name: 'profile',
      component: ProfileView,
      meta: { requiresAuth: true, transition: 'page-scale' }
    },
    {
      path: '/tasks',
      name: 'tasks',
      component: TaskView,
      meta: { requiresAuth: true, transition: 'page-fade' }
    },
    {
      path: '/tasks/:id',
      name: 'task-detail',
      component: TaskDetailView,
      meta: { requiresAuth: true, transition: 'page-slide' }
    },
    {
      path: '/store',
      name: 'store',
      component: StoreView,
      meta: { requiresAuth: true, transition: 'page-fade' }
    },
    {
      path: '/inventory',
      name: 'inventory',
      component: InventoryView,
      meta: { requiresAuth: true, transition: 'page-fade' }
    },
    {
      path: '/games',
      name: 'games',
      component: GameView,
      meta: { requiresAuth: true, transition: 'page-fade' }
    },
    {
      path: '/explore',
      name: 'explore',
      component: ExploreView,
      meta: { requiresAuth: true, transition: 'page-fade' }
    },
    {
      path: '/claim/:token',
      name: 'claim',
      component: ClaimView,
      meta: { requiresAuth: true, transition: 'page-scale' }
    },
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: { requiresGuest: true, transition: 'page-fade' }
    },
    {
      path: '/register',
      name: 'register',
      component: RegisterView,
      meta: { requiresGuest: true, transition: 'page-fade' }
    },
    {
      path: '/password-reset',
      name: 'password-reset',
      component: PasswordResetView,
      meta: { requiresGuest: true, transition: 'page-fade' }
    },
    {
      path: '/auth/telegram-callback',
      name: 'telegram-callback',
      component: TelegramCallbackView,
      meta: { requiresGuest: true, transition: 'page-fade' }
    },
    {
      path: '/about',
      name: 'about',
      component: () => import('../views/AboutView.vue'),
      meta: { requiresAuth: true, transition: 'page-fade' }
    },
    {
      path: '/level-detail',
      name: 'level-detail',
      component: () => import('../views/LevelDetailView.vue'),
      meta: { requiresAuth: true, title: '等级详情', transition: 'page-slide' }
    },
    {
      path: '/coins-detail',
      name: 'coins-detail',
      component: () => import('../views/CoinsDetailView.vue'),
      meta: { requiresAuth: true, title: '积分详情', transition: 'page-slide' }
    },
    {
      path: '/community-stats',
      name: 'community-stats',
      component: CommunityStatsView,
      meta: { requiresAuth: true, title: '社区排行榜', transition: 'page-fade' }
    }
  ]
})

// Navigation guards
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()

  // Initialize auth state if not already done
  if (!authStore.user && !authStore.token) {
    authStore.initAuth()
  }

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    // Redirect to login if route requires authentication
    next({ name: 'login' })
  } else if (to.meta.requiresGuest && authStore.isAuthenticated) {
    // Redirect to home if route requires guest and user is authenticated
    next({ name: 'home' })
  } else {
    next()
  }
})

export default router