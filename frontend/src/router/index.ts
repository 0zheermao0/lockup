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
    },
    // 男娘幻城
    {
      path: '/phantom-city',
      name: 'phantom-city',
      component: () => import('../views/PhantomCityView.vue'),
      meta: { requiresAuth: true, title: '男娘幻城', transition: 'page-fade' }
    },
    {
      path: '/phantom-city/checkpoint',
      name: 'phantom-city-checkpoint',
      component: () => import('../views/CheckpointView.vue'),
      meta: { requiresAuth: true, title: '安检口', transition: 'page-slide' }
    },
    {
      path: '/phantom-city/ruins',
      name: 'phantom-city-ruins',
      component: () => import('../views/RuinsView.vue'),
      meta: { requiresAuth: true, title: '备皮间', transition: 'page-slide' }
    },
    {
      path: '/phantom-city/salon',
      name: 'phantom-city-salon',
      component: () => import('../views/SalonView.vue'),
      meta: { requiresAuth: true, title: '闺房', transition: 'page-slide' }
    },
    {
      path: '/phantom-city/profile',
      name: 'phantom-city-profile',
      component: () => import('../views/GameProfileView.vue'),
      meta: { requiresAuth: true, title: '游戏档案', transition: 'page-scale' }
    },
    {
      path: '/phantom-city/black-market',
      name: 'phantom-city-black-market',
      component: () => import('../views/BlackMarketView.vue'),
      meta: { requiresAuth: true, title: '黑市', transition: 'page-slide' }
    },
    {
      path: '/phantom-city/abandoned-camp',
      name: 'phantom-city-abandoned-camp',
      component: () => import('../views/AbandonedCampView.vue'),
      meta: { requiresAuth: true, title: '更衣室', transition: 'page-slide' }
    },
    {
      path: '/phantom-city/ruins-deep',
      name: 'phantom-city-ruins-deep',
      component: () => import('../views/RuinsDeepView.vue'),
      meta: { requiresAuth: true, title: '深处备皮间', transition: 'page-slide' }
    },
    {
      path: '/phantom-city/armory',
      name: 'phantom-city-armory',
      component: () => import('../views/ArmoryView.vue'),
      meta: { requiresAuth: true, title: '储物柜', transition: 'page-slide' }
    },
    {
      path: '/phantom-city/sewer',
      name: 'phantom-city-sewer',
      component: () => import('../views/SewerView.vue'),
      meta: { requiresAuth: true, title: '下水道', transition: 'page-slide' }
    },
    {
      path: '/phantom-city/ruins-outer',
      name: 'phantom-city-ruins-outer',
      component: () => import('../views/RuinsOuterView.vue'),
      meta: { requiresAuth: true, title: '外围备皮间', transition: 'page-slide' }
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