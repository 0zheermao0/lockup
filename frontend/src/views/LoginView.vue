<template>
  <div class="login-container">
    <div class="login-card">
      <h1>锁芯社区</h1>
      <h2>登录</h2>

      <!-- 普通登录表单 -->
      <form @submit.prevent="handleLogin">
        <div class="form-group">
          <label for="account">用户名或邮箱</label>
          <input
            id="account"
            v-model="form.account"
            type="text"
            required
            :disabled="authStore.isLoading"
            placeholder="输入用户名或邮箱"
          />
        </div>

        <div class="form-group">
          <label for="password">密码</label>
          <input
            id="password"
            v-model="form.password"
            type="password"
            required
            :disabled="authStore.isLoading"
          />
        </div>

        <div v-if="error" class="error">
          <div v-for="(line, index) in error.split('\n')" :key="index">
            {{ line }}
          </div>
        </div>

        <button type="submit" :disabled="authStore.isLoading">
          {{ authStore.isLoading ? '登录中...' : '登录' }}
        </button>
      </form>

      <!-- 分隔线 -->
      <div class="divider">
        <span>或</span>
      </div>

      <!-- Telegram登录按钮 -->
      <div class="telegram-login-section">
        <div v-if="telegramLoading" class="telegram-loading">
          <span class="loading-spinner"></span>
          加载中...
        </div>
        <div v-else-if="telegramError" class="telegram-error">
          <span>{{ telegramError }}</span>
          <button @click="loadTelegramWidget" class="retry-btn">重试</button>
        </div>
        <div v-else id="telegram-login-container"></div>
      </div>

      <div class="auth-links">
        <p>还没有账号？ <router-link to="/register">立即注册</router-link></p>
        <p>忘记密码？ <router-link to="/password-reset">重置密码</router-link></p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { authApi } from '../lib/api'
import type { LoginRequest } from '../types/index'

const router = useRouter()
const authStore = useAuthStore()

const form = reactive<LoginRequest>({
  account: '',
  password: ''
})

const error = ref('')
const telegramLoading = ref(true)
const telegramError = ref('')
let telegramScript: HTMLScriptElement | null = null

// Helper function to parse Django REST Framework validation errors for login
const parseLoginError = (err: any): string => {
  console.log('Login error:', err)

  // Check if this is a DRF validation error with field-specific errors
  if (err.response?.data && typeof err.response.data === 'object') {
    const errorData = err.response.data

    // Handle username validation errors
    if (errorData.username && Array.isArray(errorData.username)) {
      const usernameErrors = errorData.username as string[]
      return `用户名错误：${usernameErrors.join('，')}`
    }

    // Handle password validation errors
    if (errorData.password && Array.isArray(errorData.password)) {
      const passwordErrors = errorData.password as string[]
      return `密码错误：${passwordErrors.join('，')}`
    }

    // Handle non-field errors (authentication errors)
    if (errorData.non_field_errors && Array.isArray(errorData.non_field_errors)) {
      const nonFieldErrors = errorData.non_field_errors as string[]
      return nonFieldErrors.join('\n')
    }

    // Handle Django's general error messages
    if (errorData.detail) {
      return errorData.detail
    }

    // Handle specific authentication errors
    if (errorData.error) {
      return errorData.error
    }

    // Handle message field
    if (errorData.message) {
      return errorData.message
    }

    // Handle any other field errors by combining all error messages
    const allErrors: string[] = []
    for (const [field, fieldErrors] of Object.entries(errorData)) {
      if (Array.isArray(fieldErrors)) {
        const fieldErrorMessages = fieldErrors as string[]
        if (field === 'username') {
          allErrors.push(`用户名：${fieldErrorMessages.join('，')}`)
        } else if (field === 'password') {
          allErrors.push(`密码：${fieldErrorMessages.join('，')}`)
        } else {
          allErrors.push(...fieldErrorMessages)
        }
      } else if (typeof fieldErrors === 'string') {
        allErrors.push(fieldErrors)
      }
    }

    if (allErrors.length > 0) {
      return allErrors.join('\n')
    }
  }

  // Handle HTTP status codes with meaningful messages
  if (err.response?.status === 401) {
    return '用户名或密码错误，请检查后重试'
  } else if (err.response?.status === 403) {
    return '账户已被禁用或暂停，请联系管理员'
  } else if (err.response?.status === 429) {
    return '登录尝试过于频繁，请稍后再试'
  } else if (err.response?.status >= 500) {
    return '服务器内部错误，请稍后重试'
  } else if (!navigator.onLine) {
    return '网络连接已断开，请检查网络设置'
  }

  // Final fallback for network errors or unexpected error formats
  return err.message || '登录失败，请检查网络连接后重试'
}

const handleLogin = async () => {
  error.value = ''

  try {
    await authStore.login(form)
    router.push('/')
  } catch (err: any) {
    error.value = parseLoginError(err)
  }
}

// 加载Telegram Login Widget
const loadTelegramWidget = async () => {
  try {
    telegramLoading.value = true
    telegramError.value = ''

    // 获取Telegram配置
    const config = await authApi.getTelegramLoginConfig()

    // 检查配置是否有效
    if (!config.bot_name) {
      telegramError.value = 'Telegram登录未配置'
      telegramLoading.value = false
      return
    }

    // 动态加载Telegram Login Widget脚本
    telegramScript = document.createElement('script')
    telegramScript.src = 'https://telegram.org/js/telegram-widget.js?22'
    telegramScript.setAttribute('data-telegram-login', config.bot_name)
    telegramScript.setAttribute('data-size', 'large')
    telegramScript.setAttribute('data-auth-url', config.auth_url)
    telegramScript.setAttribute('data-request-access', 'write')
    telegramScript.async = true

    // 设置加载超时（最多等待3秒）
    const loadTimeout = setTimeout(() => {
      telegramLoading.value = false
    }, 3000)

    // 脚本加载完成后的处理
    telegramScript.onload = () => {
      clearTimeout(loadTimeout)
      // 给Telegram Widget一些时间来渲染
      setTimeout(() => {
        telegramLoading.value = false
      }, 500)
    }

    telegramScript.onerror = () => {
      clearTimeout(loadTimeout)
      telegramError.value = '加载Telegram登录失败，请刷新页面重试'
      telegramLoading.value = false
    }

    document.getElementById('telegram-login-container')?.appendChild(telegramScript)
  } catch (err: any) {
    // 提供更详细的错误信息
    if (err.response?.status === 500) {
      telegramError.value = '服务器配置错误，请联系管理员'
    } else if (err.response?.data?.error) {
      telegramError.value = err.response.data.error
    } else if (!navigator.onLine) {
      telegramError.value = '网络连接已断开'
    } else {
      telegramError.value = '加载Telegram登录失败，请稍后重试'
    }
    telegramLoading.value = false
    console.error('Failed to load Telegram widget:', err)
  }
}

onMounted(() => {
  loadTelegramWidget()
})

onUnmounted(() => {
  // 清理Telegram脚本
  if (telegramScript && telegramScript.parentNode) {
    telegramScript.parentNode.removeChild(telegramScript)
  }
})
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #f5f5f5;
}

.login-card {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  width: 100%;
  max-width: 400px;
}

h1 {
  text-align: center;
  color: #333;
  margin-bottom: 0.5rem;
  font-size: 1.8rem;
}

h2 {
  text-align: center;
  color: #666;
  margin-bottom: 2rem;
  font-size: 1.2rem;
}

.form-group {
  margin-bottom: 1rem;
}

label {
  display: block;
  margin-bottom: 0.5rem;
  color: #333;
  font-weight: 500;
}

input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
  box-sizing: border-box;
}

input:focus {
  outline: none;
  border-color: #007bff;
}

input:disabled {
  background-color: #f8f9fa;
  opacity: 0.7;
}

button {
  width: 100%;
  padding: 0.75rem;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  cursor: pointer;
  margin-top: 1rem;
}

button:hover:not(:disabled) {
  background-color: #0056b3;
}

button:disabled {
  background-color: #6c757d;
  cursor: not-allowed;
}

.error {
  color: #721c24;
  margin: 1rem 0;
  padding: 0.75rem;
  background-color: #f8d7da;
  border: 1px solid #f5c6cb;
  border-radius: 6px;
  font-size: 0.9rem;
  line-height: 1.4;
}

.error div {
  margin-bottom: 0.25rem;
}

.error div:last-child {
  margin-bottom: 0;
}

.auth-links {
  text-align: center;
  margin-top: 2rem;
}

.auth-links a {
  color: #007bff;
  text-decoration: none;
}

.auth-links a:hover {
  text-decoration: underline;
}

/* Telegram登录区域样式 */
.divider {
  display: flex;
  align-items: center;
  margin: 1.5rem 0;
  color: #666;
}

.divider::before,
.divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background-color: #ddd;
}

.divider span {
  padding: 0 1rem;
  font-size: 0.9rem;
}

.telegram-login-section {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 40px;
}

.telegram-loading {
  color: #666;
  font-size: 0.9rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid #ddd;
  border-top-color: #007bff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.telegram-error {
  color: #dc3545;
  font-size: 0.9rem;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

.retry-btn {
  padding: 0.25rem 0.75rem;
  background-color: #6c757d;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 0.8rem;
  cursor: pointer;
  margin-top: 0;
}

.retry-btn:hover {
  background-color: #5a6268;
}
</style>