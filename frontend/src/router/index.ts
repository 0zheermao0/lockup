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

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
      meta: { requiresAuth: true }
    },
    {
      path: '/post/:id',
      name: 'post-detail',
      component: PostDetailView,
      meta: { requiresAuth: true }
    },
    {
      path: '/posts/:id',
      redirect: to => ({ name: 'post-detail', params: to.params })
    },
    {
      path: '/profile/:id?',
      name: 'profile',
      component: ProfileView,
      meta: { requiresAuth: true }
    },
    {
      path: '/tasks',
      name: 'tasks',
      component: TaskView,
      meta: { requiresAuth: true }
    },
    {
      path: '/tasks/:id',
      name: 'task-detail',
      component: TaskDetailView,
      meta: { requiresAuth: true }
    },
    {
      path: '/store',
      name: 'store',
      component: StoreView,
      meta: { requiresAuth: true }
    },
    {
      path: '/inventory',
      name: 'inventory',
      component: InventoryView,
      meta: { requiresAuth: true }
    },
    {
      path: '/games',
      name: 'games',
      component: GameView,
      meta: { requiresAuth: true }
    },
    {
      path: '/explore',
      name: 'explore',
      component: ExploreView,
      meta: { requiresAuth: true }
    },
    {
      path: '/claim/:token',
      name: 'claim',
      component: ClaimView,
      meta: { requiresAuth: true }
    },
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: { requiresGuest: true }
    },
    {
      path: '/register',
      name: 'register',
      component: RegisterView,
      meta: { requiresGuest: true }
    },
    {
      path: '/password-reset',
      name: 'password-reset',
      component: PasswordResetView,
      meta: { requiresGuest: true }
    },
    {
      path: '/about',
      name: 'about',
      component: () => import('../views/AboutView.vue'),
      meta: { requiresAuth: true }
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