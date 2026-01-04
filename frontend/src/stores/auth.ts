import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '../lib/api'
import type { User, LoginRequest, RegisterRequest } from '../types/index'

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref<User | null>(null)
  const token = ref<string | null>(null)
  const isLoading = ref(false)

  // Getters
  const isAuthenticated = computed(() => !!token.value && !!user.value)

  // Actions
  const initAuth = () => {
    const savedToken = localStorage.getItem('token')
    const savedUser = localStorage.getItem('user')

    if (savedToken && savedUser) {
      try {
        token.value = savedToken
        user.value = JSON.parse(savedUser)
      } catch (error) {
        console.error('Error parsing saved user data:', error)
        clearAuth()
      }
    }
  }

  const login = async (credentials: LoginRequest) => {
    isLoading.value = true
    try {
      const response = await authApi.login(credentials)
      token.value = response.token
      user.value = response.user

      localStorage.setItem('token', response.token)
      localStorage.setItem('user', JSON.stringify(response.user))

      return response
    } catch (error) {
      console.error('Login error:', error)
      throw error
    } finally {
      isLoading.value = false
    }
  }

  const register = async (userData: RegisterRequest) => {
    isLoading.value = true
    try {
      const response = await authApi.register(userData)
      token.value = response.token
      user.value = response.user

      localStorage.setItem('token', response.token)
      localStorage.setItem('user', JSON.stringify(response.user))

      return response
    } catch (error) {
      console.error('Register error:', error)
      throw error
    } finally {
      isLoading.value = false
    }
  }

  const logout = () => {
    clearAuth()
    // Call API logout if needed
    authApi.logout().catch(console.error)
  }

  const clearAuth = () => {
    user.value = null
    token.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  const updateUser = (newUser: User) => {
    user.value = newUser
    localStorage.setItem('user', JSON.stringify(newUser))
  }

  const refreshUser = async () => {
    if (!token.value) return

    try {
      const updatedUser = await authApi.getCurrentUser()
      updateUser(updatedUser)
      return updatedUser
    } catch (error) {
      console.error('Failed to refresh user data:', error)
      // If refresh fails, token might be invalid
      clearAuth()
      throw error
    }
  }

  // 统一积分管理方法
  const updateCoins = (newCoins: number) => {
    if (user.value) {
      user.value.coins = newCoins
      // 同步更新localStorage
      localStorage.setItem('user', JSON.stringify(user.value))
    }
  }

  const addCoins = (amount: number) => {
    if (user.value) {
      const newCoins = user.value.coins + amount
      updateCoins(newCoins)
    }
  }

  const subtractCoins = (amount: number) => {
    if (user.value) {
      const newCoins = Math.max(0, user.value.coins - amount)
      updateCoins(newCoins)
    }
  }

  // 锁定状态管理方法
  const updateActiveLockTask = (newLockTask: any) => {
    if (user.value) {
      user.value.active_lock_task = newLockTask
      // 同步更新localStorage
      localStorage.setItem('user', JSON.stringify(user.value))
    }
  }

  const clearActiveLockTask = () => {
    updateActiveLockTask(null)
  }

  const setActiveLockTask = (lockTask: any) => {
    updateActiveLockTask(lockTask)
  }

  return {
    // State
    user,
    token,
    isLoading,
    // Getters
    isAuthenticated,
    // Actions
    initAuth,
    login,
    register,
    logout,
    clearAuth,
    updateUser,
    refreshUser,
    // 积分管理方法
    updateCoins,
    addCoins,
    subtractCoins,
    // 锁定状态管理方法
    updateActiveLockTask,
    clearActiveLockTask,
    setActiveLockTask
  }
})