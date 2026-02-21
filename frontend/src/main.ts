import './assets/main.css'
import './assets/transitions/index.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import vRipple from './directives/vRipple'

const app = createApp(App)

app.use(createPinia())
app.use(router)

// Register global directives
app.directive('ripple', vRipple)

app.mount('#app')
