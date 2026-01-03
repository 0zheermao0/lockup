<template>
  <div class="email-verification-container">
    <!-- 邮箱输入和验证码发送 -->
    <div class="form-group">
      <label for="email">邮箱地址</label>
      <div class="email-input-container">
        <input
          id="email"
          v-model="email"
          type="email"
          required
          :disabled="isLoading || isEmailVerified"
          :class="{
            'error-input': emailError,
            'success-input': isEmailVerified
          }"
          placeholder="请输入常用邮箱地址"
          @input="handleEmailChange"
        />
        <button
          type="button"
          class="send-code-btn"
          :disabled="!canSendCode || isLoading"
          @click="sendVerificationCode"
        >
          <span v-if="cooldownTime > 0">{{ cooldownTime }}s</span>
          <span v-else-if="isLoading">发送中...</span>
          <span v-else-if="codeSent">重新发送</span>
          <span v-else>发送验证码</span>
        </button>
      </div>

      <!-- 邮箱错误信息 -->
      <div v-if="emailError" class="field-error">
        <div class="field-error-item">{{ emailError }}</div>
      </div>

      <!-- 发送成功提示 -->
      <div v-if="sendSuccessMessage" class="success-message">
        <div class="success-item">
          <span class="success-icon">✓</span>
          {{ sendSuccessMessage }}
        </div>
      </div>
    </div>

    <!-- 验证码输入 -->
    <div v-if="codeSent" class="form-group">
      <label for="verification-code">验证码</label>
      <div class="verification-input-container">
        <input
          id="verification-code"
          v-model="verificationCode"
          type="text"
          maxlength="6"
          required
          :disabled="isLoading || isEmailVerified"
          :class="{
            'error-input': verificationError,
            'success-input': isEmailVerified
          }"
          placeholder="请输入6位验证码"
          @input="handleCodeChange"
        />
        <button
          v-if="verificationCode.length === 6 && !isEmailVerified"
          type="button"
          class="verify-btn"
          :disabled="isLoading"
          @click="verifyCode"
        >
          <span v-if="isLoading">验证中...</span>
          <span v-else>验证</span>
        </button>
      </div>

      <!-- 验证码错误信息 -->
      <div v-if="verificationError" class="field-error">
        <div class="field-error-item">{{ verificationError }}</div>
      </div>

      <!-- 验证成功提示 -->
      <div v-if="isEmailVerified" class="success-message">
        <div class="success-item">
          <span class="success-icon">✓</span>
          邮箱验证成功！可以继续注册
        </div>
      </div>

      <!-- 验证码提示信息 -->
      <div v-if="!isEmailVerified" class="verification-hints">
        <div class="hint-item">
          <span class="hint-icon">💡</span>
          验证码有效期为15分钟
        </div>
        <div class="hint-item">
          <span class="hint-icon">📧</span>
          请检查邮箱收件箱和垃圾邮件文件夹
        </div>
        <div v-if="remainingAttempts < 5" class="hint-item warning">
          <span class="hint-icon">⚠️</span>
          剩余发送次数：{{ remainingAttempts }} 次
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from 'vue'
import { authApi } from '../lib/api'
import type { EmailVerificationSendRequest, EmailVerificationVerifyRequest } from '../types/index'

// Props
interface Props {
  modelValue: string // 邮箱地址
  verificationCode?: string // 验证码
  disabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  verificationCode: '',
  disabled: false
})

// Emits
const emit = defineEmits<{
  'update:modelValue': [value: string]
  'update:verificationCode': [value: string]
  'verified': [email: string, code: string]
  'error': [error: string]
}>()

// Reactive data
const email = ref(props.modelValue)
const verificationCode = ref(props.verificationCode)
const isLoading = ref(false)
const codeSent = ref(false)
const isEmailVerified = ref(false)
const cooldownTime = ref(0)
const remainingAttempts = ref(5)

// Error states
const emailError = ref('')
const verificationError = ref('')
const sendSuccessMessage = ref('')

// Cooldown timer
let cooldownTimer: number | null = null

// Computed properties
const canSendCode = computed(() => {
  return email.value &&
         isValidEmail(email.value) &&
         cooldownTime.value === 0 &&
         !isEmailVerified.value &&
         !props.disabled
})

// Email validation
const isValidEmail = (emailValue: string): boolean => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRegex.test(emailValue)
}

// Handle email input change
const handleEmailChange = () => {
  emailError.value = ''
  sendSuccessMessage.value = ''

  // Reset verification state when email changes
  if (codeSent.value || isEmailVerified.value) {
    codeSent.value = false
    isEmailVerified.value = false
    verificationCode.value = ''
    verificationError.value = ''
  }

  emit('update:modelValue', email.value)
}

// Handle verification code input change
const handleCodeChange = () => {
  verificationError.value = ''
  emit('update:verificationCode', verificationCode.value)
}

// Start cooldown timer
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

// Send verification code
const sendVerificationCode = async () => {
  if (!canSendCode.value) return

  // Validate email
  if (!email.value) {
    emailError.value = '请输入邮箱地址'
    return
  }

  if (!isValidEmail(email.value)) {
    emailError.value = '请输入有效的邮箱地址'
    return
  }

  isLoading.value = true
  emailError.value = ''
  sendSuccessMessage.value = ''

  try {
    const response = await authApi.sendEmailVerification({ email: email.value })

    // Success
    codeSent.value = true
    sendSuccessMessage.value = response.message
    remainingAttempts.value = response.remaining_attempts
    startCooldown(60) // 60 seconds cooldown

    console.log('验证码发送成功:', response)

  } catch (error: any) {
    console.error('发送验证码失败:', error)

    // Handle different error types
    if (error.data?.error) {
      emailError.value = error.data.error
    } else if (error.data?.message) {
      emailError.value = error.data.message
    } else if (error.message) {
      emailError.value = error.message
    } else {
      emailError.value = '发送验证码失败，请重试'
    }

    // Update remaining attempts if available
    if (error.data?.remaining_attempts !== undefined) {
      remainingAttempts.value = error.data.remaining_attempts
    }

    emit('error', emailError.value)
  } finally {
    isLoading.value = false
  }
}

// Verify email code
const verifyCode = async () => {
  if (!verificationCode.value || verificationCode.value.length !== 6) {
    verificationError.value = '请输入6位验证码'
    return
  }

  isLoading.value = true
  verificationError.value = ''

  try {
    const response = await authApi.verifyEmail({
      email: email.value,
      code: verificationCode.value
    })

    if (response.verified) {
      isEmailVerified.value = true
      emit('verified', email.value, verificationCode.value)
      console.log('邮箱验证成功:', response)
    } else {
      verificationError.value = response.message || '验证失败'
      emit('error', verificationError.value)
    }

  } catch (error: any) {
    console.error('验证失败:', error)

    if (error.data?.error) {
      verificationError.value = error.data.error
    } else if (error.data?.message) {
      verificationError.value = error.data.message
    } else if (error.message) {
      verificationError.value = error.message
    } else {
      verificationError.value = '验证失败，请重试'
    }

    emit('error', verificationError.value)
  } finally {
    isLoading.value = false
  }
}

// Watch for prop changes
watch(() => props.modelValue, (newValue) => {
  email.value = newValue
})

watch(() => props.verificationCode, (newValue) => {
  verificationCode.value = newValue
})

// Cleanup on unmount
onUnmounted(() => {
  if (cooldownTimer) {
    clearInterval(cooldownTimer)
  }
})

// Expose methods for parent component
defineExpose({
  sendVerificationCode,
  verifyCode,
  isEmailVerified: computed(() => isEmailVerified.value),
  canSendCode
})
</script>

<style scoped>
.email-verification-container {
  width: 100%;
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

/* Email input container */
.email-input-container {
  display: flex;
  gap: 8px;
  align-items: stretch;
}

.email-input-container input {
  flex: 1;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
  box-sizing: border-box;
}

.send-code-btn {
  padding: 0.75rem 1rem;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 0.9rem;
  cursor: pointer;
  white-space: nowrap;
  min-width: 100px;
  transition: background-color 0.2s;
}

.send-code-btn:hover:not(:disabled) {
  background-color: #0056b3;
}

.send-code-btn:disabled {
  background-color: #6c757d;
  cursor: not-allowed;
}

/* Verification code input container */
.verification-input-container {
  display: flex;
  gap: 8px;
  align-items: stretch;
}

.verification-input-container input {
  flex: 1;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
  box-sizing: border-box;
  text-align: center;
  letter-spacing: 2px;
  font-family: 'Courier New', monospace;
}

.verify-btn {
  padding: 0.75rem 1rem;
  background-color: #28a745;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 0.9rem;
  cursor: pointer;
  white-space: nowrap;
  min-width: 80px;
  transition: background-color 0.2s;
}

.verify-btn:hover:not(:disabled) {
  background-color: #218838;
}

.verify-btn:disabled {
  background-color: #6c757d;
  cursor: not-allowed;
}

/* Input states */
input:focus {
  outline: none;
  border-color: #007bff;
  box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25);
}

input:disabled {
  background-color: #f8f9fa;
  opacity: 0.7;
}

.error-input {
  border-color: #dc3545 !important;
  background-color: #fff5f5;
}

.error-input:focus {
  border-color: #dc3545 !important;
  box-shadow: 0 0 0 0.2rem rgba(220, 53, 69, 0.25);
}

.success-input {
  border-color: #28a745 !important;
  background-color: #f8fff8;
}

.success-input:focus {
  border-color: #28a745 !important;
  box-shadow: 0 0 0 0.2rem rgba(40, 167, 69, 0.25);
}

/* Error messages */
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
  line-height: 1.3;
}

/* Success messages */
.success-message {
  margin-top: 8px;
  padding: 8px 12px;
  background-color: #d4edda;
  border: 1px solid #c3e6cb;
  border-radius: 6px;
  font-size: 0.85rem;
}

.success-item {
  color: #155724;
  display: flex;
  align-items: center;
  gap: 6px;
  line-height: 1.3;
}

.success-icon {
  color: #28a745;
  font-weight: bold;
}

/* Verification hints */
.verification-hints {
  margin-top: 12px;
  padding: 12px;
  background-color: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 6px;
  font-size: 0.85rem;
}

.hint-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  color: #6c757d;
  line-height: 1.3;
}

.hint-item:last-child {
  margin-bottom: 0;
}

.hint-item.warning {
  color: #856404;
}

.hint-icon {
  font-size: 0.9rem;
  flex-shrink: 0;
}

/* Responsive design */
@media (max-width: 480px) {
  .email-input-container,
  .verification-input-container {
    flex-direction: column;
    gap: 8px;
  }

  .send-code-btn,
  .verify-btn {
    width: 100%;
    min-width: auto;
  }

  .verification-input-container input {
    text-align: left;
  }
}

/* Accessibility improvements */
@media (prefers-reduced-motion: reduce) {
  .send-code-btn,
  .verify-btn {
    transition: none;
  }
}

/* High contrast mode support */
@media (prefers-contrast: high) {
  .success-item {
    color: #0f5132;
    font-weight: 600;
  }

  .field-error-item {
    color: #842029;
    font-weight: 600;
  }

  .success-message,
  .field-error,
  .verification-hints {
    border-width: 2px;
  }
}
</style>