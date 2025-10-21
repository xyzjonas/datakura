import { defineConfig } from '@hey-api/openapi-ts'

export default defineConfig({
  input: 'http://localhost:8000/api/v1/openapi.json',
  output: 'src/client',
  plugins: ['@hey-api/sdk', '@hey-api/client-fetch', '@hey-api/typescript'],
})
