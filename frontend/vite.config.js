import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8006',
        changeOrigin: true,
      },
    },
    maxHttpBufferSize: 50 * 1024 * 1024, // 50MB — allow large agent payloads
  },
})
