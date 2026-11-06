import { fileURLToPath, URL } from 'node:url'

import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

/**
 * 构建产物由 Flask 挂在 /app/ 下，所以 base 必须是 '/app/'。
 *
 * 若 base 保持默认 '/'，构建后的 index.html 会去请求 /assets/xxx.js，
 * 而 Flask 那边 /assets/ 不存在（404），表现为"页面一片空白、控制台没有报错"——
 * 这是前后端分离最容易踩且最难查的一个坑，因为 dev 模式完全正常。
 */
const API_TARGET = process.env.VITE_API_TARGET || 'http://127.0.0.1:5000'

export default defineConfig({
  base: '/app/',
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    // 显式绑 127.0.0.1。
    // 不写的话 Vite 默认 host 是 'localhost'，而 Node 18+ 的 localhost
    // 会优先解析到 IPv6 的 ::1 —— 结果只有 http://localhost:5173 能开，
    // http://127.0.0.1:5173 直接连接被拒。本项目其他地方一律用 127.0.0.1，
    // 这个差异会让人以为"前端起不来"。
    host: '127.0.0.1',
    port: 5173,
    // 开发期走代理，浏览器里同源，不需要后端开 CORS。
    // 生产由 Flask 同端口提供 /api 与 /app/*，同样没有跨域。
    proxy: {
      '/api': {
        target: API_TARGET,
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    // 生产保留 sourcemap：这个项目要长期维护，出问题时能对到源码行。
    // 体积代价约 +30%，可接受（首屏资源总量仍在几百 KB 级）。
    sourcemap: true,
    chunkSizeWarningLimit: 700,
  },
})
