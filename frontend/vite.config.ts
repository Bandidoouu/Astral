import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  // GitHub Pages serves the site under /Astral/; local dev and the API build use '/'.
  base: process.env.VITE_BASE ?? '/',
  cacheDir: path.resolve(__dirname, 'node_modules/.vite'),
});
