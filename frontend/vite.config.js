import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // Needed for Docker mapping
    watch: {
      usePolling: true, // Fix for Windows/Docker file events
    }
  }
})
