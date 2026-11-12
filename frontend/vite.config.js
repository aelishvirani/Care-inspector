import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],

  server: {
    port: 5173,

    proxy: {
      // Local Mac demo scanner; never routed through the cloud backend.
      '/local-ble': {
        target: 'http://127.0.0.1:8765',
        changeOrigin: true,
        rewrite: path => path.replace(/^\\/local-ble/, ''),
      },
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
