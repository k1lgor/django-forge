import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

// https://vite.dev/config/
export default defineConfig({
  plugins: [svelte()],
  // GitHub Pages project site: the repo is served under /django-forge/, so
  // asset URLs must be prefixed with that base. CI builds (GitHub Actions)
  // get the prefixed base; local dev keeps the root base.
  base: process.env.GITHUB_ACTIONS === 'true' ? '/django-forge/' : '/',
})
