import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
    VitePWA({
      registerType: 'autoUpdate',
      manifest: {
        name: '锁芯社区',
        short_name: '锁芯',
        description: '锁芯社区 - 任务管理与社交平台',
        theme_color: '#ffffff',
        background_color: '#ffffff',
        display: 'standalone',
        scope: '/',
        start_url: '/',
        icons: [
          { src: '/icons/icon-192x192.png', sizes: '192x192', type: 'image/png' },
          { src: '/icons/icon-512x512.png', sizes: '512x512', type: 'image/png' }
        ]
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,jpg,jpeg}'],
        runtimeCaching: [
          {
            urlPattern: /^https:\/\/.*\/api\//,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-cache',
              expiration: {
                maxEntries: 100,
                maxAgeSeconds: 86400
              },
              cacheableResponse: {
                statuses: [0, 200]
              }
            }
          },
          {
            urlPattern: /\.(?:png|jpg|jpeg|svg|gif|webp)$/,
            handler: 'CacheFirst',
            options: {
              cacheName: 'image-cache',
              expiration: {
                maxEntries: 200,
                maxAgeSeconds: 2592000
              }
            }
          }
        ]
      }
    }),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
  // 修复部署时CSS丢失问题 - 使用绝对路径确保SPA路由正常工作
  base: '/',
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
        // 修复CSS部署问题 - 使用更简单的资源命名策略
        assetFileNames: (assetInfo) => {
          // CSS文件使用简单命名避免路径问题
          if (assetInfo.name?.endsWith('.css')) {
            return 'css/[name]-[hash].css';
          }
          // 其他资源文件
          return 'assets/[name]-[hash].[ext]';
        }
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
