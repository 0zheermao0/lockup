import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
  build: {
    // 设置chunk大小警告阈值为1MB (1000KB)
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      output: {
        // 智能分块策略 - 只分离实际存在的大型依赖
        manualChunks(id) {
          if (id.includes('node_modules')) {
            // Vue生态系统 (vue, vue-router, pinia)
            if (id.includes('vue') || id.includes('pinia') || id.includes('vue-router')) {
              return 'vue-vendor';
            }
            // UI组件库 (naive-ui是最大的依赖)
            if (id.includes('naive-ui')) {
              return 'ui-vendor';
            }
            // 图标库
            if (id.includes('@vicons')) {
              return 'icons-vendor';
            }
            // 其他工具库 (axios, @vueuse/core等)
            if (id.includes('axios') || id.includes('@vueuse')) {
              return 'utils-vendor';
            }
          }
        },
        // 为chunk文件添加hash以支持长期缓存
        chunkFileNames: 'js/[name]-[hash].js',
        entryFileNames: 'js/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash].[ext]'
      }
    }
  },
  server: {
    // 配置开发服务器
    host: 'localhost',
    port: 5173,
    // 配置代理（可选）
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      '/media': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      }
    }
  }
})
