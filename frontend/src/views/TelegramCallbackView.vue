<template>
  <div class="telegram-callback">
    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <p>正在通过Telegram登录...</p>
    </div>
    <div v-else-if="error" class="error">
      <h3>登录失败</h3>
      <p>{{ error }}</p>
      <router-link to="/login" class="back-link">返回登录页</router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { authApi } from '../lib/api'
import type { TelegramLoginRequest } from '../types/index'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const loading = ref(true)
const error = ref('')

onMounted(async () => {
  try {
    // 从URL查询参数中获取Telegram登录数据
    const query = route.query

    // 检查必需参数
    const id = query.id as string
    const hash = query.hash as string
    const authDate = query.auth_date as string

    if (!id || !hash || !authDate) {
      error.value = '登录信息不完整，请重新尝试Telegram登录'
      loading.value = false
      return
    }

    // 构建Telegram登录请求数据
    const telegramData: TelegramLoginRequest = {
      id: parseInt(id),
      first_name: (query.first_name as string) || '',
      last_name: (query.last_name as string) || '',
      username: (query.username as string) || '',
      photo_url: (query.photo_url as string) || '',
      auth_date: parseInt(authDate),
      hash: hash
    }

    // 调用后端API进行验证和登录
    const response = await authApi.telegramLogin(telegramData)

    // 保存登录状态
    authStore.token = response.token
    authStore.user = response.user
    localStorage.setItem('token', response.token)
    localStorage.setItem('user', JSON.stringify(response.user))

    // 登录成功，跳转到首页
    router.push('/')
  } catch (err: any) {
    console.error('Telegram login error:', err)

    // 解析错误信息
    if (err.response?.data?.error) {
      error.value = err.response.data.error
    } else if (err.message) {
      error.value = err.message
    } else {
      error.value = 'Telegram登录失败，请稍后重试'
    }

    loading.value = false
  }
})
</script>

<style scoped>
.telegram-callback {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #f5f5f5;
}

.loading {
  text-align: center;
  padding: 2rem;
}

.spinner {
  width: 50px;
  height: 50px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #007bff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 1rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error {
  text-align: center;
  padding: 2rem;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  max-width: 400px;
}

.error h3 {
  color: #dc3545;
  margin-bottom: 1rem;
}

.error p {
  color: #666;
  margin-bottom: 1.5rem;
}

.back-link {
  display: inline-block;
  padding: 0.75rem 1.5rem;
  background-color: #007bff;
  color: white;
  text-decoration: none;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.back-link:hover {
  background-color: #0056b3;
}
</style>
