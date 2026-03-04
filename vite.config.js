import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import path from 'path';

export default defineConfig({
  plugins: [svelte()],
  // django-vite 3.x builds dev URLs as: localhost:5173 + STATIC_URL + static_url_prefix + path
  // = localhost:5173/static/dist/<path>  — so Vite must serve at that base.
  base: '/static/dist/',
  root: path.resolve(__dirname, 'frontend'),
  build: {
    outDir: path.resolve(__dirname, 'static/dist'),
    emptyOutDir: true,
    manifest: true,
    rollupOptions: {
      input: {
        kanban: path.resolve(__dirname, 'frontend/src/entries/kanban.js'),
        lead_form: path.resolve(__dirname, 'frontend/src/entries/lead_form.js'),
        opportunity_list: path.resolve(__dirname, 'frontend/src/entries/opportunity_list.js'),
        lead_incoming: path.resolve(__dirname, 'frontend/src/entries/lead_incoming.js'),
        activities: path.resolve(__dirname, 'frontend/src/entries/activities.js'),
        messaging: path.resolve(__dirname, 'frontend/src/entries/messaging.js'),
        calls: path.resolve(__dirname, 'frontend/src/entries/calls.js'),
      },
    },
  },
  server: { port: 5173, cors: true },
  resolve: { alias: { '@': path.resolve(__dirname, 'frontend/src') } },
});
