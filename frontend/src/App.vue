<template>
  <div id="app">
    <RouterView />
    <!-- Global Chat Modal -->
    <ChatModal
      :is-visible="messagingStore.isChatModalVisible"
      @close="messagingStore.closeChatModal"
    />
  </div>
</template>

<script setup lang="ts">
import { RouterView } from 'vue-router'
import { onMounted, watch } from 'vue'
import { useAuthStore } from './stores/auth'
import { useNotificationStore } from './stores/notifications'
import { useThemeStore } from './stores/theme'
import { useMessagingStore } from './stores/messaging'
import ChatModal from './components/ChatModal.vue'

const authStore = useAuthStore()
const notificationStore = useNotificationStore()
const themeStore = useThemeStore()
const messagingStore = useMessagingStore()

onMounted(async () => {
  // Initialize theme system first
  const themeCleanup = themeStore.initTheme()
  console.log('🎨 Theme system initialized:', themeStore.currentTheme)

  // Initialize auth state on app startup
  await authStore.initAuth()

  // Initialize notification and messaging systems if user is authenticated
  if (authStore.isAuthenticated) {
    try {
      await notificationStore.initNotifications()
      notificationStore.startAutoRefresh()
      // Fetch conversations for unread count
      await messagingStore.fetchConversations()
    } catch (error) {
      console.error('Failed to initialize notifications:', error)
    }
  }

  // Cleanup theme listeners on app unmount
  if (themeCleanup) {
    // Store cleanup function for potential future use
    // In Vue 3, we don't have onUnmounted at the app level easily accessible
  }
})

// Watch for theme changes and apply to document root
watch(
  () => themeStore.currentThemeClass,
  (newThemeClass, oldThemeClass) => {
    const html = document.documentElement

    // Remove old theme class
    if (oldThemeClass) {
      html.classList.remove(oldThemeClass)
    }

    // Add new theme class
    html.classList.add(newThemeClass)

    console.log('🎨 Theme applied to document:', newThemeClass)
  },
  { immediate: true }
)
</script>

<style>
/* Theme system imports */
@import './assets/themes/shared-variables.css';
@import './assets/themes/neo-brutalism.css';
@import './assets/themes/liquid-glass.css';
@import './assets/themes/liquid-glass-components.css';
@import './assets/themes/theme-transitions.css';

/* Global styles */
*,
*::before,
*::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: var(--theme-font-family-primary, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif);
  line-height: 1.6;
  color: var(--theme-text-primary, #333);
  background-color: var(--theme-primary-bg, #ffffff);
  transition: background-color var(--theme-transition-normal, 0.3s ease), color var(--theme-transition-normal, 0.3s ease);
}

#app {
  min-height: 100vh;
  background: var(--theme-primary-bg, #ffffff);
  transition: background var(--theme-transition-normal, 0.3s ease);
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