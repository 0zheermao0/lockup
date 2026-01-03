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

        <!-- 邮箱验证组件 -->
        <EmailVerification
          v-model="form.email"
          v-model:verification-code="form.email_verification_code"
          :disabled="authStore.isLoading"
          @verified="handleEmailVerified"
          @error="handleEmailVerificationError"
        />

        <!-- 邮箱验证码字段级错误 -->
        <div v-if="emailVerificationFieldErrors.length > 0" class="field-error">
          <div v-for="(error, index) in emailVerificationFieldErrors" :key="index" class="field-error-item">
            {{ error }}
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

        <button type="submit" :disabled="authStore.isLoading || !isEmailVerified">
          <span v-if="authStore.isLoading">注册中...</span>
          <span v-else-if="!isEmailVerified">请先完成邮箱验证</span>
          <span v-else>注册</span>
        </button>
      </form>

      <div class="auth-links">
        <p>已有账号？ <router-link to="/login">立即登录</router-link></p>
      </div>
    </div>

    <!-- Notification Toast -->
    <NotificationToast
      :is-visible="showToast"
      :type="toastData.type"
      :title="toastData.title"
      :message="toastData.message"
      :secondary-message="toastData.secondaryMessage"
      :details="toastData.details"
      @close="showToast = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import NotificationToast from '../components/NotificationToast.vue'
import EmailVerification from '../components/EmailVerification.vue'
import type { RegisterRequest } from '../types/index'

const router = useRouter()
const authStore = useAuthStore()

const form = reactive<RegisterRequest>({
  username: '',
  email: '',
  password: '',
  password_confirm: '',
  email_verification_code: ''
})

const error = ref('')
const showPassword = ref(false)
const showPasswordConfirm = ref(false)

// Field-specific error tracking
const passwordFieldErrors = ref<string[]>([])
const passwordConfirmFieldErrors = ref<string[]>([])
const usernameFieldErrors = ref<string[]>([])
const emailFieldErrors = ref<string[]>([])
const emailVerificationFieldErrors = ref<string[]>([])

// Email verification state
const isEmailVerified = ref(false)

// Toast notification state
const showToast = ref(false)
const toastData = ref<{
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  message: string
  secondaryMessage?: string
  details?: Record<string, any>
}>({
  type: 'info',
  title: '',
  message: ''
})

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

// Email verification handlers
const handleEmailVerified = (email: string, code: string) => {
  form.email = email
  form.email_verification_code = code
  isEmailVerified.value = true
  emailFieldErrors.value = []
  emailVerificationFieldErrors.value = []

  console.log('邮箱验证成功:', { email, code })
}

const handleEmailVerificationError = (error: string) => {
  console.error('邮箱验证错误:', error)
}

// Clear field-specific errors
const clearFieldErrors = () => {
  passwordFieldErrors.value = []
  passwordConfirmFieldErrors.value = []
  usernameFieldErrors.value = []
  emailFieldErrors.value = []
  emailVerificationFieldErrors.value = []
}

// Enhanced error parsing with field-specific error handling and NotificationToast data
const parseRegistrationError = (err: any): {
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  message: string
  secondaryMessage?: string
  details?: Record<string, any>
} => {
  console.log('Registration error:', err)
  console.log('Error data:', err.data)
  console.log('Error response:', err.response?.data)

  // Clear previous field errors
  clearFieldErrors()

  // Default error response structure
  let errorResult = {
    type: 'error' as const,
    title: '注册失败',
    message: '注册过程中发生错误',
    secondaryMessage: '请检查输入信息后重试',
    details: {} as Record<string, any>
  }

  // The ApiError structure: err.data contains the actual response data
  const errorData = err.data || err.response?.data || {}

  console.log('Parsed error data:', errorData)

  if (errorData && typeof errorData === 'object') {
    const fieldErrorsFound: string[] = []

    // Handle field-specific errors and store them separately
    if (errorData.password && Array.isArray(errorData.password)) {
      passwordFieldErrors.value = errorData.password as string[]
      fieldErrorsFound.push('密码')
      errorResult.details['密码错误'] = (errorData.password as string[]).join('，')
    }

    if (errorData.username && Array.isArray(errorData.username)) {
      usernameFieldErrors.value = errorData.username as string[]
      fieldErrorsFound.push('用户名')
      errorResult.details['用户名错误'] = (errorData.username as string[]).join('，')

      // Check for specific username uniqueness error
      const usernameErrors = errorData.username as string[]
      if (usernameErrors.some((error: string) => error.toLowerCase().includes('already exists') || error.includes('已存在'))) {
        errorResult.title = '用户名已存在'
        errorResult.message = '该用户名已被其他用户注册'
        errorResult.secondaryMessage = '请选择其他用户名'
        errorResult.details['解决方案'] = '尝试在用户名后添加数字或使用其他用户名'
        return errorResult
      }
    }

    if (errorData.email && Array.isArray(errorData.email)) {
      emailFieldErrors.value = errorData.email as string[]
      fieldErrorsFound.push('邮箱')
      errorResult.details['邮箱错误'] = (errorData.email as string[]).join('，')

      // Check for specific email uniqueness error
      const emailErrors = errorData.email as string[]
      if (emailErrors.some((error: string) => error.toLowerCase().includes('already exists') || error.includes('已存在'))) {
        errorResult.title = '邮箱已被注册'
        errorResult.message = '该邮箱地址已被其他用户使用'
        errorResult.secondaryMessage = '请使用其他邮箱地址或尝试找回密码'
        errorResult.details['解决方案'] = '使用其他邮箱地址注册，或前往登录页面找回密码'
        return errorResult
      }
    }

    if (errorData.password_confirm && Array.isArray(errorData.password_confirm)) {
      passwordConfirmFieldErrors.value = errorData.password_confirm as string[]
      fieldErrorsFound.push('确认密码')
      errorResult.details['确认密码错误'] = (errorData.password_confirm as string[]).join('，')
    }

    if (errorData.email_verification_code && Array.isArray(errorData.email_verification_code)) {
      emailVerificationFieldErrors.value = errorData.email_verification_code as string[]
      fieldErrorsFound.push('邮箱验证码')
      errorResult.details['邮箱验证码错误'] = (errorData.email_verification_code as string[]).join('，')
    }

    // Handle non-field errors (general validation errors)
    if (errorData.non_field_errors && Array.isArray(errorData.non_field_errors)) {
      const nonFieldErrors = errorData.non_field_errors as string[]
      errorResult.message = nonFieldErrors[0] || '表单验证失败'
      errorResult.secondaryMessage = nonFieldErrors.length > 1 ? nonFieldErrors.slice(1).join('，') : '请检查输入信息'
      errorResult.details['验证错误'] = nonFieldErrors.join('，')
      return errorResult
    }

    // Handle Django's general error messages
    if (errorData.detail) {
      errorResult.message = errorData.detail
      errorResult.secondaryMessage = '请联系管理员或稍后重试'
      return errorResult
    }

    // Handle specific error field
    if (errorData.error) {
      errorResult.message = errorData.error
      return errorResult
    }

    // Handle message field
    if (errorData.message) {
      errorResult.message = errorData.message
      return errorResult
    }

    // If we have field-specific errors, show a summary message
    if (fieldErrorsFound.length > 0) {
      errorResult.title = '表单验证失败'
      errorResult.message = `以下字段存在错误：${fieldErrorsFound.join('、')}`
      errorResult.secondaryMessage = '请查看表单中红色标注的错误信息并修正'
      return errorResult
    }

    // Handle any other field errors
    const allErrors: string[] = []
    for (const [field, fieldErrors] of Object.entries(errorData)) {
      if (Array.isArray(fieldErrors)) {
        const fieldErrorMessages = fieldErrors as string[]
        if (field === 'username') {
          usernameFieldErrors.value = fieldErrorMessages
          allErrors.push(`用户名：${fieldErrorMessages.join('，')}`)
        } else if (field === 'email') {
          emailFieldErrors.value = fieldErrorMessages
          allErrors.push(`邮箱：${fieldErrorMessages.join('，')}`)
        } else if (field === 'password') {
          passwordFieldErrors.value = fieldErrorMessages
          allErrors.push(`密码：${fieldErrorMessages.join('，')}`)
        } else if (field === 'password_confirm') {
          passwordConfirmFieldErrors.value = fieldErrorMessages
          allErrors.push(`确认密码：${fieldErrorMessages.join('，')}`)
        } else if (field === 'email_verification_code') {
          emailVerificationFieldErrors.value = fieldErrorMessages
          allErrors.push(`邮箱验证码：${fieldErrorMessages.join('，')}`)
        } else {
          allErrors.push(...fieldErrorMessages)
        }
      } else if (typeof fieldErrors === 'string') {
        allErrors.push(fieldErrors)
      }
    }

    if (allErrors.length > 0) {
      errorResult.message = allErrors[0]!
      if (allErrors.length > 1) {
        errorResult.secondaryMessage = allErrors.slice(1).join('，')
      }
      errorResult.details['详细错误'] = allErrors.join('；')
      return errorResult
    }
  }

  // Handle HTTP status codes with meaningful messages
  if (err.status === 400) {
    errorResult.title = '请求格式错误'
    errorResult.message = '提交的信息格式有误'
    errorResult.secondaryMessage = '请检查所有字段是否正确填写'
    errorResult.details['状态码'] = '400'
    errorResult.details['错误类型'] = '客户端请求错误'
  } else if (err.status === 409) {
    errorResult.title = '注册信息冲突'
    errorResult.message = '用户名或邮箱已被注册'
    errorResult.secondaryMessage = '请使用其他用户名或邮箱地址'
    errorResult.details['状态码'] = '409'
    errorResult.details['错误类型'] = '资源冲突'
  } else if (err.status === 429) {
    errorResult.title = '请求过于频繁'
    errorResult.message = '注册尝试次数过多'
    errorResult.secondaryMessage = '请稍等片刻后再试'
    errorResult.details['状态码'] = '429'
    errorResult.details['错误类型'] = '频率限制'
  } else if (err.status >= 500) {
    errorResult.title = '服务器错误'
    errorResult.message = '服务器内部发生错误'
    errorResult.secondaryMessage = '请稍后重试或联系管理员'
    errorResult.details['状态码'] = err.status?.toString() || '未知'
    errorResult.details['错误类型'] = '服务器内部错误'
  } else if (!navigator.onLine) {
    errorResult.title = '网络连接错误'
    errorResult.message = '网络连接已断开'
    errorResult.secondaryMessage = '请检查网络设置后重试'
    errorResult.details['错误类型'] = '网络连接问题'
  } else {
    // Final fallback for network errors or unexpected error formats
    // Check if err.message contains useful information
    if (err.message && !err.message.startsWith('HTTP ')) {
      errorResult.message = err.message
    } else {
      errorResult.message = '注册失败，请重试'
    }
    errorResult.secondaryMessage = '请检查网络连接或稍后重试'
    errorResult.details['原始错误'] = err.message || '未知错误'
    errorResult.details['错误对象'] = JSON.stringify(err, null, 2)
  }

  return errorResult
}

const handleRegister = async () => {
  error.value = ''
  clearFieldErrors()
  showToast.value = false

  // Client-side validation for email verification
  if (!isEmailVerified.value) {
    toastData.value = {
      type: 'warning',
      title: '邮箱验证未完成',
      message: '请先完成邮箱验证',
      secondaryMessage: '需要验证邮箱后才能注册账号',
      details: {
        '问题': '未完成邮箱验证',
        '解决方法': '请按照提示完成邮箱验证'
      }
    }
    showToast.value = true
    return
  }

  // Client-side validation for password match
  if (form.password !== form.password_confirm) {
    toastData.value = {
      type: 'warning',
      title: '密码确认错误',
      message: '两次输入的密码不一致',
      secondaryMessage: '请确保确认密码与密码字段完全相同',
      details: {
        '问题': '密码确认不匹配',
        '解决方法': '重新输入确认密码'
      }
    }
    showToast.value = true
    return
  }

  try {
    await authStore.register(form)

    // Success notification
    toastData.value = {
      type: 'success',
      title: '注册成功',
      message: '欢迎加入锁芯社区！',
      secondaryMessage: '正在为您跳转到首页...',
      details: {
        '用户名': form.username,
        '邮箱': form.email,
        '注册时间': new Date().toLocaleString('zh-CN')
      }
    }
    showToast.value = true

    // Delay navigation to show success message
    setTimeout(() => {
      router.push('/')
    }, 2000)

  } catch (err: any) {
    const errorData = parseRegistrationError(err)
    toastData.value = errorData
    showToast.value = true
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