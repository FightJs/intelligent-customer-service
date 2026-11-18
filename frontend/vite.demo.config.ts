import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'node:path'

export default defineConfig({
  root: resolve(__dirname, 'demo'),
  base: '/intelligent-customer-service/',
  plugins: [react()],
  mode: 'pages-demo',
  publicDir: resolve(__dirname, 'demo/public'),
  build: { outDir: resolve(__dirname, 'dist-demo'), emptyOutDir: true },
})
