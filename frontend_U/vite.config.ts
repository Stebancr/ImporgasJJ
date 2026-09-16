import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': '/src',
    },
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    watch: {
      usePolling: true,
      interval: 1000,
      ignored: ['**/dist/**', '**/.git/**', '**/*.tsbuildinfo'],
    },
    warmup: { clientFiles: ['./src/admin/pages/{Dashboard,Products,Users,Orders,Categories,Brands,Locations}Page.tsx'] },
  },
})
