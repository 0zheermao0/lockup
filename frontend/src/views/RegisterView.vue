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
            :class="{ 'error-input': usernameFieldErrors.length > 0 }"
          />
          <!-- Field-specific username errors -->
          <div v-if="usernameFieldErrors.length > 0" class="field-error">
            <div v-for="(error, index) in usernameFieldErrors" :key="index" class="field-error-item">
              {{ error }}
            </div>
          </div>
        </div>

        <div class="form-group">
          <label for="email">邮箱</label>
          <input
            id="email"
            v-model="form.email"
            type="email"
            required
            :disabled="authStore.isLoading"
            :class="{ 'error-input': emailFieldErrors.length > 0 }"
          />
          <!-- Field-specific email errors -->
          <div v-if="emailFieldErrors.length > 0" class="field-error">
            <div v-for="(error, index) in emailFieldErrors" :key="index" class="field-error-item">
              {{ error }}
            </div>
          </div>
        </div>

        <div class="form-group">
          <label for="password">密码</label>
          <div class="password-input-container">
            <input
              id="password"
              v-model="form.password"
              :type="showPassword ? 'text' : 'password'"
              required
              :disabled="authStore.isLoading"
              @input="validatePasswordStrength"
              :class="{ 'error-input': passwordFieldErrors.length > 0 }"
            />
            <button
              type="button"
              class="password-toggle"
              @click="showPassword = !showPassword"
              :disabled="authStore.isLoading"
            >
              {{ showPassword ? '隐藏' : '显示' }}
            </button>
          </div>

          <!-- Password Requirements -->
          <div class="password-requirements" v-if="form.password || passwordFieldErrors.length > 0">
            <div class="requirement-title">密码要求：</div>
            <div class="requirements-list">
              <div
                class="requirement-item"
                :class="{
                  'valid': passwordValidation.length,
                  'invalid': !passwordValidation.length && form.password
                }"
              >
                <span class="requirement-icon">{{ passwordValidation.length ? '✓' : '✗' }}</span>
                至少8个字符
              </div>
              <div
                class="requirement-item"
                :class="{
                  'valid': passwordValidation.hasLetters,
                  'invalid': !passwordValidation.hasLetters && form.password
                }"
              >
                <span class="requirement-icon">{{ passwordValidation.hasLetters ? '✓' : '✗' }}</span>
                包含字母
              </div>
              <div
                class="requirement-item"
                :class="{
                  'valid': passwordValidation.notNumericOnly,
                  'invalid': !passwordValidation.notNumericOnly && form.password
                }"
              >
                <span class="requirement-icon">{{ passwordValidation.notNumericOnly ? '✓' : '✗' }}</span>
                不能只包含数字
              </div>
              <div
                class="requirement-item"
                :class="{
                  'valid': passwordValidation.notCommon,
                  'invalid': !passwordValidation.notCommon && form.password
                }"
              >
                <span class="requirement-icon">{{ passwordValidation.notCommon ? '✓' : '✗' }}</span>
                避免常见密码
              </div>
            </div>
          </div>

          <!-- Field-specific password errors -->
          <div v-if="passwordFieldErrors.length > 0" class="field-error">
            <div v-for="(error, index) in passwordFieldErrors" :key="index" class="field-error-item">
              {{ error }}
            </div>
          </div>
        </div>

        <div class="form-group">
          <label for="password_confirm">确认密码</label>
          <div class="password-input-container">
            <input
              id="password_confirm"
              v-model="form.password_confirm"
              :type="showPasswordConfirm ? 'text' : 'password'"
              required
              :disabled="authStore.isLoading"
              @input="checkPasswordMatch"
              :class="{ 'error-input': passwordConfirmFieldErrors.length > 0 || (form.password_confirm && !passwordsMatch) }"
            />
            <button
              type="button"
              class="password-toggle"
              @click="showPasswordConfirm = !showPasswordConfirm"
              :disabled="authStore.isLoading"
            >
              {{ showPasswordConfirm ? '隐藏' : '显示' }}
            </button>
          </div>

          <!-- Password match indicator -->
          <div v-if="form.password_confirm" class="password-match-indicator">
            <div
              class="requirement-item"
              :class="{ 'valid': passwordsMatch, 'invalid': !passwordsMatch }"
            >
              <span class="requirement-icon">{{ passwordsMatch ? '✓' : '✗' }}</span>
              {{ passwordsMatch ? '密码匹配' : '密码不匹配' }}
            </div>
          </div>

          <!-- Field-specific password confirm errors -->
          <div v-if="passwordConfirmFieldErrors.length > 0" class="field-error">
            <div v-for="(error, index) in passwordConfirmFieldErrors" :key="index" class="field-error-item">
              {{ error }}
            </div>
          </div>
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
import { ref, reactive, computed, watch } from 'vue'
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
const showPassword = ref(false)
const showPasswordConfirm = ref(false)

// Field-specific error tracking
const passwordFieldErrors = ref<string[]>([])
const passwordConfirmFieldErrors = ref<string[]>([])
const usernameFieldErrors = ref<string[]>([])
const emailFieldErrors = ref<string[]>([])

// Password validation state
const passwordValidation = reactive({
  length: false,
  hasLetters: false,
  notNumericOnly: false,
  notCommon: false
})

// Common passwords list (simplified)
const commonPasswords = [
  'password', '123456', '123456789', 'qwerty', 'abc123', 'password123',
  '111111', '123123', 'admin', 'root', '000000', '888888', '666666'
]

// Computed property for password match
const passwordsMatch = computed(() => {
  if (!form.password_confirm) return true
  return form.password === form.password_confirm
})

// Password strength validation function
const validatePasswordStrength = () => {
  const password = form.password

  // Check length (at least 8 characters)
  passwordValidation.length = password.length >= 8

  // Check if contains letters
  passwordValidation.hasLetters = /[a-zA-Z]/.test(password)

  // Check if not numeric only
  passwordValidation.notNumericOnly = !/^\d+$/.test(password)

  // Check if not common password
  passwordValidation.notCommon = !commonPasswords.includes(password.toLowerCase())
}

// Password confirmation check
const checkPasswordMatch = () => {
  // This will trigger the computed property update
}

// Clear field-specific errors
const clearFieldErrors = () => {
  passwordFieldErrors.value = []
  passwordConfirmFieldErrors.value = []
  usernameFieldErrors.value = []
  emailFieldErrors.value = []
}

// Enhanced error parsing with field-specific error handling
const parseRegistrationError = (err: any): string => {
  console.log('Registration error:', err)

  // Clear previous field errors
  clearFieldErrors()

  // Check if this is a DRF validation error with field-specific errors
  if (err.response?.data && typeof err.response.data === 'object') {
    const errorData = err.response.data

    // Handle field-specific errors and store them separately
    if (errorData.password && Array.isArray(errorData.password)) {
      passwordFieldErrors.value = errorData.password as string[]
    }

    if (errorData.username && Array.isArray(errorData.username)) {
      usernameFieldErrors.value = errorData.username as string[]
    }

    if (errorData.email && Array.isArray(errorData.email)) {
      emailFieldErrors.value = errorData.email as string[]
    }

    if (errorData.password_confirm && Array.isArray(errorData.password_confirm)) {
      passwordConfirmFieldErrors.value = errorData.password_confirm as string[]
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

    // Handle specific error field
    if (errorData.error) {
      return errorData.error
    }

    // Handle message field
    if (errorData.message) {
      return errorData.message
    }

    // If we have field-specific errors, show a general message
    // The specific errors will be displayed next to their respective fields
    if (passwordFieldErrors.value.length > 0 ||
        usernameFieldErrors.value.length > 0 ||
        emailFieldErrors.value.length > 0 ||
        passwordConfirmFieldErrors.value.length > 0) {
      return '请修正下方标注的错误信息'
    }

    // Handle any other field errors by combining all error messages with field labels
    const allErrors: string[] = []
    for (const [field, fieldErrors] of Object.entries(errorData)) {
      if (Array.isArray(fieldErrors)) {
        const fieldErrorMessages = fieldErrors as string[]
        if (field === 'username') {
          allErrors.push(`用户名：${fieldErrorMessages.join('，')}`)
        } else if (field === 'email') {
          allErrors.push(`邮箱：${fieldErrorMessages.join('，')}`)
        } else if (field === 'password') {
          allErrors.push(`密码：${fieldErrorMessages.join('，')}`)
        } else if (field === 'password_confirm') {
          allErrors.push(`确认密码：${fieldErrorMessages.join('，')}`)
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
  if (err.response?.status === 400) {
    return '提交的信息有误，请检查后重试'
  } else if (err.response?.status === 409) {
    return '用户名或邮箱已被注册，请使用其他信息'
  } else if (err.response?.status === 429) {
    return '注册尝试过于频繁，请稍后再试'
  } else if (err.response?.status >= 500) {
    return '服务器内部错误，请稍后重试'
  } else if (!navigator.onLine) {
    return '网络连接已断开，请检查网络设置'
  }

  // Final fallback for network errors or unexpected error formats
  return err.message || '注册失败，请检查网络连接后重试'
}

const handleRegister = async () => {
  error.value = ''
  clearFieldErrors()

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

/* Enhanced Password Input Styles */
.password-input-container {
  position: relative;
  display: flex;
  align-items: center;
}

.password-input-container input {
  padding-right: 60px; /* Make room for the toggle button */
}

.password-toggle {
  position: absolute;
  right: 8px;
  background: none;
  border: none;
  color: #007bff;
  cursor: pointer;
  font-size: 0.8rem;
  padding: 4px 8px;
  border-radius: 4px;
  white-space: nowrap;
  margin: 0;
  width: auto;
}

.password-toggle:hover:not(:disabled) {
  background-color: #e7f3ff;
  color: #0056b3;
}

.password-toggle:disabled {
  color: #6c757d;
  cursor: not-allowed;
}

/* Error Input Styling */
.error-input {
  border-color: #dc3545 !important;
  background-color: #fff5f5;
}

.error-input:focus {
  border-color: #dc3545 !important;
  box-shadow: 0 0 0 0.2rem rgba(220, 53, 69, 0.25);
}

/* Password Requirements */
.password-requirements {
  margin-top: 8px;
  padding: 12px;
  background-color: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 6px;
  font-size: 0.85rem;
}

.requirement-title {
  font-weight: 600;
  margin-bottom: 8px;
  color: #495057;
}

.requirements-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.requirement-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 2px 0;
  transition: all 0.2s ease;
}

.requirement-item.valid {
  color: #28a745;
}

.requirement-item.invalid {
  color: #dc3545;
}

.requirement-icon {
  font-weight: bold;
  font-size: 0.9rem;
  width: 16px;
  text-align: center;
}

/* Password Match Indicator */
.password-match-indicator {
  margin-top: 8px;
}

/* Field-Specific Error Messages */
.field-error {
  margin-top: 8px;
  padding: 8px 12px;
  background-color: #f8d7da;
  border: 1px solid #f5c6cb;
  border-radius: 6px;
  font-size: 0.85rem;
}

.field-error-item {
  color: #721c24;
  margin-bottom: 4px;
  line-height: 1.3;
}

.field-error-item:last-child {
  margin-bottom: 0;
}

/* Enhanced General Error Styling */
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

/* Responsive Design */
@media (max-width: 480px) {
  .password-input-container {
    flex-direction: column;
    align-items: stretch;
  }

  .password-input-container input {
    padding-right: 0.75rem;
    margin-bottom: 8px;
  }

  .password-toggle {
    position: static;
    align-self: flex-end;
    width: auto;
  }

  .requirements-list {
    font-size: 0.8rem;
  }
}

/* Accessibility Improvements */
@media (prefers-reduced-motion: reduce) {
  .requirement-item {
    transition: none;
  }
}

/* High contrast mode support */
@media (prefers-contrast: high) {
  .requirement-item.valid {
    color: #0f5132;
    font-weight: 600;
  }

  .requirement-item.invalid {
    color: #842029;
    font-weight: 600;
  }

  .password-requirements {
    border-width: 2px;
  }

  .field-error {
    border-width: 2px;
  }
}
</style>