import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    open: true,
    fs: {
      // Allow serving files from parent directory (for /data folder)
      allow: ['..']
    }
  },
  resolve: {
    alias: {
      '@': '/src'
    }
  },
  publicDir: 'public',
  // Optimize CSV file handling
  assetsInclude: ['**/*.csv']
})
