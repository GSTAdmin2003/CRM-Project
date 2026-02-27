import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import path from 'path';

export default defineConfig({
  plugins: [svelte()],
  root: path.resolve(__dirname, 'frontend'),
  build: {
    outDir: path.resolve(__dirname, 'static/dist'),
    emptyOutDir: true,
    manifest: true,
    rollupOptions: {
      input: {
        kanban: path.resolve(__dirname, 'frontend/src/entries/kanban.js'),
        lead_form: path.resolve(__dirname, 'frontend/src/entries/lead_form.js'),
      },
    },
  },
  server: { port: 5173, cors: true },
  resolve: { alias: { '@': path.resolve(__dirname, 'frontend/src') } },
});
