<template>
  <div class="register-container">
    <div class="register-card">
      <h1>锁芯社区</h1>
      <h2>注册</h2>

      <form @submit.prevent="handleRegister">
        <div class="form-group">
          <label for="username">用户名</label>
          <input
            id="username"
            v-model="form.username"
            type="text"
            required
            :disabled="authStore.isLoading"
          />
        </div>

        <div class="form-group">
          <label for="email">邮箱</label>
          <input
            id="email"
            v-model="form.email"
            type="email"
            required
            :disabled="authStore.isLoading"
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

        <div class="form-group">
          <label for="password_confirm">确认密码</label>
          <input
            id="password_confirm"
            v-model="form.password_confirm"
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
          {{ authStore.isLoading ? '注册中...' : '注册' }}
        </button>
      </form>

      <div class="auth-links">
        <p>已有账号？ <router-link to="/login">立即登录</router-link></p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import type { RegisterRequest } from '../types/index'

const router = useRouter()
const authStore = useAuthStore()

const form = reactive<RegisterRequest>({
  username: '',
  email: '',
  password: '',
  password_confirm: ''
})

const error = ref('')

// Helper function to parse Django REST Framework validation errors
const parseRegistrationError = (err: any): string => {
  console.log('Registration error:', err)

  // Check if this is a DRF validation error with field-specific errors
  if (err.response?.data && typeof err.response.data === 'object') {
    const errorData = err.response.data

    // Handle password validation errors specifically
    if (errorData.password && Array.isArray(errorData.password)) {
      const passwordErrors = errorData.password as string[]
      // Join multiple password validation errors with line breaks
      return passwordErrors.join('\n')
    }

    // Handle username validation errors
    if (errorData.username && Array.isArray(errorData.username)) {
      const usernameErrors = errorData.username as string[]
      return `用户名错误：${usernameErrors.join('，')}`
    }

    // Handle email validation errors
    if (errorData.email && Array.isArray(errorData.email)) {
      const emailErrors = errorData.email as string[]
      return `邮箱错误：${emailErrors.join('，')}`
    }

    // Handle non-field errors (general validation errors)
    if (errorData.non_field_errors && Array.isArray(errorData.non_field_errors)) {
      const nonFieldErrors = errorData.non_field_errors as string[]
      return nonFieldErrors.join('\n')
    }

    // Handle Django's general error messages
    if (errorData.detail) {
      return errorData.detail
    }

    // Handle any other field errors by combining all error messages
    const allErrors: string[] = []
    for (const [field, fieldErrors] of Object.entries(errorData)) {
      if (Array.isArray(fieldErrors)) {
        allErrors.push(...(fieldErrors as string[]))
      }
    }

    if (allErrors.length > 0) {
      return allErrors.join('\n')
    }

    // Fall back to the old method if no structured errors found
    if (errorData.message) {
      return errorData.message
    }
  }

  // Final fallback for network errors or unexpected error formats
  return err.message || '注册失败，请检查网络连接后重试'
}

const handleRegister = async () => {
  error.value = ''

  if (form.password !== form.password_confirm) {
    error.value = '密码确认不匹配'
    return
  }

  try {
    await authStore.register(form)
    router.push('/')
  } catch (err: any) {
    error.value = parseRegistrationError(err)
  }
}
</script>

<style scoped>
.register-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #f5f5f5;
}

.register-card {
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
  background-color: #28a745;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  cursor: pointer;
  margin-top: 1rem;
}

button:hover:not(:disabled) {
  background-color: #218838;
}

button:disabled {
  background-color: #6c757d;
  cursor: not-allowed;
}

.error {
  color: #dc3545;
  margin: 1rem 0;
  padding: 0.5rem;
  background-color: #f8d7da;
  border: 1px solid #f5c6cb;
  border-radius: 4px;
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
</style>