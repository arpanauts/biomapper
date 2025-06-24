import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { nodePolyfills } from 'vite-plugin-node-polyfills'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    nodePolyfills({
      include: ['crypto'], // Explicitly polyfill crypto
      globals: {
        Buffer: true
      }
    })
  ],
  define: {
    global: 'globalThis'
  },
  // Handle server specific settings
  server: {
    host: true,
    port: 3000,
    // Proxy API requests to the backend server
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  }
})
