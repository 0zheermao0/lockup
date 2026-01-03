<template>
  <div class="password-reset-container">
    <div class="password-reset-card">
      <h1>锁芯社区</h1>
      <h2>密码重置</h2>

      <!-- Step 1: Email Input and Code Sending -->
      <div v-if="!isCodeSent" class="step-container">
        <h3>输入您的邮箱地址</h3>
        <p class="step-description">我们将向您的邮箱发送6位数字重置码</p>

        <form @submit.prevent="sendResetCode">
          <div class="form-group">
            <label for="email">邮箱地址</label>
            <input
              id="email"
              v-model="form.email"
              type="email"
              required
              :disabled="isLoading"
              :class="{ 'error-input': emailError }"
              placeholder="请输入您的邮箱地址"
            />
            <div v-if="emailError" class="field-error">
              {{ emailError }}
            </div>
          </div>

          <button
            type="submit"
            class="submit-button"
            :disabled="isLoading || !form.email"
          >
            {{ isLoading ? '发送中...' : '发送重置码' }}
          </button>
        </form>
      </div>

      <!-- Step 2: Code Verification and Password Reset -->
      <div v-else class="step-container">
        <h3>输入重置码并设置新密码</h3>
        <p class="step-description">
          重置码已发送至 <strong>{{ form.email }}</strong>
          <br>
          <small>有效期15分钟，剩余尝试次数：{{ remainingAttempts }}</small>
        </p>

        <form @submit.prevent="confirmPasswordReset">
          <div class="form-group">
            <label for="resetCode">6位重置码</label>
            <input
              id="resetCode"
              v-model="form.resetCode"
              type="text"
              maxlength="6"
              pattern="[0-9]{6}"
              required
              :disabled="isLoading"
              :class="{ 'error-input': codeError }"
              placeholder="请输入6位数字重置码"
            />
            <div v-if="codeError" class="field-error">
              {{ codeError }}
            </div>
          </div>

          <div class="form-group">
            <label for="newPassword">新密码</label>
            <div class="password-input-container">
              <input
                id="newPassword"
                v-model="form.newPassword"
                :type="showPassword ? 'text' : 'password'"
                required
                :disabled="isLoading"
                @input="validatePasswordStrength"
                :class="{ 'error-input': passwordError }"
                placeholder="请输入新密码"
              />
              <button
                type="button"
                class="password-toggle"
                @click="showPassword = !showPassword"
                :disabled="isLoading"
              >
                {{ showPassword ? '隐藏' : '显示' }}
              </button>
            </div>

            <!-- Password Requirements -->
            <div class="password-requirements" v-if="form.newPassword">
              <div class="requirement-title">密码要求：</div>
              <div class="requirements-list">
                <div
                  class="requirement-item"
                  :class="{
                    'valid': passwordValidation.length,
                    'invalid': !passwordValidation.length && form.newPassword
                  }"
                >
                  <span class="requirement-icon">{{ passwordValidation.length ? '✓' : '✗' }}</span>
                  至少8个字符
                </div>
                <div
                  class="requirement-item"
                  :class="{
                    'valid': passwordValidation.hasLetters,
                    'invalid': !passwordValidation.hasLetters && form.newPassword
                  }"
                >
                  <span class="requirement-icon">{{ passwordValidation.hasLetters ? '✓' : '✗' }}</span>
                  包含字母
                </div>
                <div
                  class="requirement-item"
                  :class="{
                    'valid': passwordValidation.notNumericOnly,
                    'invalid': !passwordValidation.notNumericOnly && form.newPassword
                  }"
                >
                  <span class="requirement-icon">{{ passwordValidation.notNumericOnly ? '✓' : '✗' }}</span>
                  不能只包含数字
                </div>
                <div
                  class="requirement-item"
                  :class="{
                    'valid': passwordValidation.notCommon,
                    'invalid': !passwordValidation.notCommon && form.newPassword
                  }"
                >
                  <span class="requirement-icon">{{ passwordValidation.notCommon ? '✓' : '✗' }}</span>
                  避免常见密码
                </div>
              </div>
            </div>

            <div v-if="passwordError" class="field-error">
              {{ passwordError }}
            </div>
          </div>

          <div class="form-group">
            <label for="confirmPassword">确认新密码</label>
            <input
              id="confirmPassword"
              v-model="form.confirmPassword"
              :type="showPassword ? 'text' : 'password'"
              required
              :disabled="isLoading"
              :class="{ 'error-input': confirmPasswordError }"
              placeholder="请再次输入新密码"
            />
            <div v-if="confirmPasswordError" class="field-error">
              {{ confirmPasswordError }}
            </div>
          </div>

          <div class="button-group">
            <button
              type="button"
              class="back-button"
              @click="goBack"
              :disabled="isLoading"
            >
              返回
            </button>
            <button
              type="submit"
              class="submit-button"
              :disabled="isLoading || !isFormValid"
            >
              {{ isLoading ? '重置中...' : '重置密码' }}
            </button>
          </div>
        </form>

        <!-- Resend Code -->
        <div class="resend-section" v-if="cooldownTime === 0">
          <button
            type="button"
            class="resend-button"
            @click="resendCode"
            :disabled="isLoading"
          >
            重新发送重置码
          </button>
        </div>
        <div v-else class="cooldown-info">
          {{ cooldownTime }}秒后可重新发送
        </div>
      </div>

      <!-- Success Message -->
      <div v-if="isResetSuccess" class="success-container">
        <div class="success-icon">✓</div>
        <h3>密码重置成功！</h3>
        <p>您的密码已成功重置，请使用新密码登录。</p>
        <router-link to="/login" class="login-link">
          前往登录
        </router-link>
      </div>

      <!-- General Error Message -->
      <div v-if="generalError" class="general-error">
        {{ generalError }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { authApi } from '@/lib/api'
import type {
  PasswordResetRequestRequest,
  PasswordResetConfirmRequest
} from '@/types/index'

// Router
const router = useRouter()

// Form data
const form = ref({
  email: '',
  resetCode: '',
  newPassword: '',
  confirmPassword: ''
})

// State
const isLoading = ref(false)
const isCodeSent = ref(false)
const isResetSuccess = ref(false)
const showPassword = ref(false)
const cooldownTime = ref(0)
const remainingAttempts = ref(5)

// Error states
const emailError = ref('')
const codeError = ref('')
const passwordError = ref('')
const confirmPasswordError = ref('')
const generalError = ref('')

// Password validation
const passwordValidation = computed(() => {
  const password = form.value.newPassword
  return {
    length: password.length >= 8,
    hasLetters: /[a-zA-Z]/.test(password),
    notNumericOnly: !/^\d+$/.test(password) || password === '',
    notCommon: !['123456', 'password', '12345678', 'qwerty', '123456789'].includes(password.toLowerCase())
  }
})

// Form validation
const isFormValid = computed(() => {
  return form.value.resetCode.length === 6 &&
         form.value.newPassword.length >= 8 &&
         form.value.newPassword === form.value.confirmPassword &&
         passwordValidation.value.length &&
         passwordValidation.value.hasLetters &&
         passwordValidation.value.notNumericOnly &&
         passwordValidation.value.notCommon
})

// Timer for cooldown
let cooldownTimer: number | null = null

// Methods
const clearErrors = () => {
  emailError.value = ''
  codeError.value = ''
  passwordError.value = ''
  confirmPasswordError.value = ''
  generalError.value = ''
}

const startCooldown = (seconds: number = 60) => {
  cooldownTime.value = seconds
  cooldownTimer = setInterval(() => {
    cooldownTime.value--
    if (cooldownTime.value <= 0) {
      if (cooldownTimer) {
        clearInterval(cooldownTimer)
        cooldownTimer = null
      }
    }
  }, 1000)
}

const validatePasswordStrength = () => {
  passwordError.value = ''
  confirmPasswordError.value = ''

  if (form.value.newPassword && form.value.confirmPassword) {
    if (form.value.newPassword !== form.value.confirmPassword) {
      confirmPasswordError.value = '两次输入的密码不一致'
    }
  }
}

const sendResetCode = async () => {
  clearErrors()

  if (!form.value.email) {
    emailError.value = '请输入邮箱地址'
    return
  }

  isLoading.value = true

  try {
    const requestData: PasswordResetRequestRequest = {
      email: form.value.email
    }

    const response = await authApi.requestPasswordReset(requestData)

    isCodeSent.value = true
    remainingAttempts.value = response.remaining_attempts
    startCooldown(60)

  } catch (error: any) {
    if (error.status === 400 && error.data) {
      if (error.data.error) {
        generalError.value = error.data.error
      } else if (error.data.email) {
        emailError.value = error.data.email[0]
      } else {
        generalError.value = '发送失败，请重试'
      }

      if (error.data.remaining_attempts !== undefined) {
        remainingAttempts.value = error.data.remaining_attempts
      }
    } else {
      generalError.value = '网络错误，请检查您的网络连接'
    }
  } finally {
    isLoading.value = false
  }
}

const confirmPasswordReset = async () => {
  clearErrors()

  // Validate form
  if (form.value.resetCode.length !== 6) {
    codeError.value = '请输入6位重置码'
    return
  }

  if (!isFormValid.value) {
    if (form.value.newPassword !== form.value.confirmPassword) {
      confirmPasswordError.value = '两次输入的密码不一致'
    }
    if (!passwordValidation.value.length) {
      passwordError.value = '密码至少需要8个字符'
    }
    return
  }

  isLoading.value = true

  try {
    const requestData: PasswordResetConfirmRequest = {
      email: form.value.email,
      reset_code: form.value.resetCode,
      new_password: form.value.newPassword,
      new_password_confirm: form.value.confirmPassword
    }

    await authApi.confirmPasswordReset(requestData)

    isResetSuccess.value = true

  } catch (error: any) {
    if (error.status === 400 && error.data) {
      if (error.data.error) {
        generalError.value = error.data.error
      } else {
        // Handle field-specific errors
        if (error.data.reset_code) {
          codeError.value = error.data.reset_code[0]
        }
        if (error.data.new_password) {
          passwordError.value = error.data.new_password[0]
        }
        if (error.data.new_password_confirm) {
          confirmPasswordError.value = error.data.new_password_confirm[0]
        }
        if (error.data.email) {
          emailError.value = error.data.email[0]
        }

        if (!error.data.reset_code && !error.data.new_password && !error.data.new_password_confirm && !error.data.email) {
          generalError.value = '重置失败，请检查输入信息'
        }
      }
    } else {
      generalError.value = '网络错误，请检查您的网络连接'
    }
  } finally {
    isLoading.value = false
  }
}

const resendCode = async () => {
  await sendResetCode()
}

const goBack = () => {
  isCodeSent.value = false
  form.value.resetCode = ''
  form.value.newPassword = ''
  form.value.confirmPassword = ''
  clearErrors()
}

// Cleanup
onUnmounted(() => {
  if (cooldownTimer) {
    clearInterval(cooldownTimer)
  }
})
</script>

<style scoped>
.password-reset-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.password-reset-card {
  background: white;
  padding: 40px;
  border-radius: 12px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
  width: 100%;
  max-width: 450px;
}

h1 {
  text-align: center;
  color: #333;
  margin-bottom: 8px;
  font-size: 28px;
  font-weight: bold;
}

h2 {
  text-align: center;
  color: #666;
  margin-bottom: 30px;
  font-size: 20px;
  font-weight: normal;
}

h3 {
  color: #333;
  margin-bottom: 15px;
  font-size: 18px;
}

.step-description {
  color: #666;
  margin-bottom: 25px;
  line-height: 1.5;
}

.form-group {
  margin-bottom: 20px;
}

label {
  display: block;
  margin-bottom: 8px;
  color: #333;
  font-weight: 500;
}

input {
  width: 100%;
  padding: 12px;
  border: 2px solid #e1e5e9;
  border-radius: 8px;
  font-size: 16px;
  transition: border-color 0.3s;
  box-sizing: border-box;
}

input:focus {
  outline: none;
  border-color: #667eea;
}

input.error-input {
  border-color: #dc3545;
}

.password-input-container {
  position: relative;
  display: flex;
}

.password-input-container input {
  flex: 1;
  padding-right: 80px;
}

.password-toggle {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  color: #667eea;
  cursor: pointer;
  font-size: 14px;
  padding: 4px 8px;
}

.password-toggle:hover {
  color: #5a6fd8;
}

.password-requirements {
  margin-top: 12px;
  padding: 12px;
  background: #f8f9fa;
  border-radius: 6px;
  border: 1px solid #e9ecef;
}

.requirement-title {
  font-size: 14px;
  font-weight: 500;
  color: #333;
  margin-bottom: 8px;
}

.requirements-list {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

.requirement-item {
  display: flex;
  align-items: center;
  font-size: 12px;
  color: #666;
}

.requirement-item.valid {
  color: #28a745;
}

.requirement-item.invalid {
  color: #dc3545;
}

.requirement-icon {
  margin-right: 6px;
  font-weight: bold;
}

.submit-button {
  width: 100%;
  padding: 14px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s;
}

.submit-button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
}

.submit-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.button-group {
  display: flex;
  gap: 12px;
}

.back-button {
  flex: 1;
  padding: 14px;
  background: #f8f9fa;
  color: #666;
  border: 2px solid #e1e5e9;
  border-radius: 8px;
  font-size: 16px;
  cursor: pointer;
  transition: all 0.3s;
}

.back-button:hover:not(:disabled) {
  background: #e9ecef;
  color: #333;
}

.submit-button {
  flex: 2;
}

.resend-section {
  margin-top: 20px;
  text-align: center;
}

.resend-button {
  background: none;
  border: none;
  color: #667eea;
  cursor: pointer;
  text-decoration: underline;
  font-size: 14px;
}

.resend-button:hover {
  color: #5a6fd8;
}

.cooldown-info {
  margin-top: 20px;
  text-align: center;
  color: #666;
  font-size: 14px;
}

.success-container {
  text-align: center;
  padding: 40px 20px;
}

.success-icon {
  font-size: 48px;
  color: #28a745;
  margin-bottom: 20px;
}

.success-container h3 {
  color: #28a745;
  margin-bottom: 15px;
}

.success-container p {
  color: #666;
  margin-bottom: 25px;
  line-height: 1.5;
}

.login-link {
  display: inline-block;
  padding: 12px 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  text-decoration: none;
  border-radius: 8px;
  font-weight: 500;
  transition: all 0.3s;
}

.login-link:hover {
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
}

.field-error {
  margin-top: 8px;
  color: #dc3545;
  font-size: 14px;
}

.general-error {
  margin-top: 20px;
  padding: 12px;
  background: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
  border-radius: 6px;
  text-align: center;
}

/* Responsive Design */
@media (max-width: 480px) {
  .password-reset-card {
    padding: 30px 20px;
    margin: 10px;
  }

  .requirements-list {
    grid-template-columns: 1fr;
  }

  .button-group {
    flex-direction: column;
  }

  .back-button,
  .submit-button {
    flex: none;
  }
}
</style>