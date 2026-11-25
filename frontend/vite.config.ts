import { defineConfig } from 'vite'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [tailwindcss()],
  server: { host: '127.0.0.1', fs: { strict: true, allow: [process.cwd()], deny: ['.env', '.env.*', '**/*.key', '**/*.aes256'] } },
  preview: { host: '127.0.0.1' },
})
