<template>
  <div id="app">
    <RouterView />
  </div>
</template>

<script setup lang="ts">
import { RouterView } from 'vue-router'
import { onMounted } from 'vue'
import { useAuthStore } from './stores/auth'
import { useNotificationStore } from './stores/notifications'

const authStore = useAuthStore()
const notificationStore = useNotificationStore()

onMounted(async () => {
  // Initialize auth state on app startup
  await authStore.initAuth()

  // Initialize notification system if user is authenticated
  if (authStore.isAuthenticated) {
    try {
      await notificationStore.initNotifications()
      notificationStore.startAutoRefresh()
    } catch (error) {
      console.error('Failed to initialize notifications:', error)
    }
  }
})
</script>

<style>
/* Global styles */
*,
*::before,
*::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  line-height: 1.6;
  color: #333;
}

#app {
  min-height: 100vh;
}

/* Remove default Vue styling */
a {
  color: inherit;
  text-decoration: none;
}

button {
  font-family: inherit;
}

input,
textarea {
  font-family: inherit;
}

/* Utility classes */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>