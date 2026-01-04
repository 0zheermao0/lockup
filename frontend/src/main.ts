import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.mount('#app')


// DEBUG
import { useAuthStore } from './stores/auth'
export function printAuthDebug() {
    const authStore = useAuthStore()
    console.log('Auth Store Debug Info:')
    console.log('Is Authenticated:', authStore.isAuthenticated)
    console.log('User:', authStore.user)
    console.log('Token:', authStore.token)
    console.log('Last Fetched At:', authStore.lastFetchedAt?.toISOString() ?? null)
}
export function forceUpdateUser() {
    const authStore = useAuthStore()
    authStore.refreshUser()
}

if (import.meta.env.DEV) {
    ; (window as any).printAuthDebug = printAuthDebug
        ; (window as any).forceUpdateUser = forceUpdateUser
}

