import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api': {
        target: `http://localhost:${process.env.VITE_API_PORT || 8006}`,
        changeOrigin: true,
      },
    },
  },
})
