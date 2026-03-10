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
        // Existing entries
        kanban: path.resolve(__dirname, 'frontend/src/entries/kanban.js'),
        lead_form: path.resolve(__dirname, 'frontend/src/entries/lead_form.js'),
        opportunity_list: path.resolve(__dirname, 'frontend/src/entries/opportunity_list.js'),
        lead_incoming: path.resolve(__dirname, 'frontend/src/entries/lead_incoming.js'),
        activities: path.resolve(__dirname, 'frontend/src/entries/activities.js'),
        messaging: path.resolve(__dirname, 'frontend/src/entries/messaging.js'),
        calls: path.resolve(__dirname, 'frontend/src/entries/calls.js'),
        // Phase 1 — CRM management pages
        crm_dashboard: path.resolve(__dirname, 'frontend/src/entries/crm_dashboard.js'),
        lead_detail: path.resolve(__dirname, 'frontend/src/entries/lead_detail.js'),
        stage_list: path.resolve(__dirname, 'frontend/src/entries/stage_list.js'),
        stage_form: path.resolve(__dirname, 'frontend/src/entries/stage_form.js'),
        team_list: path.resolve(__dirname, 'frontend/src/entries/team_list.js'),
        team_form: path.resolve(__dirname, 'frontend/src/entries/team_form.js'),
        team_detail: path.resolve(__dirname, 'frontend/src/entries/team_detail.js'),
        // Phase 2 — Lead import + activity pages
        lead_import: path.resolve(__dirname, 'frontend/src/entries/lead_import.js'),
        activity_form: path.resolve(__dirname, 'frontend/src/entries/activity_form.js'),
        activity_detail: path.resolve(__dirname, 'frontend/src/entries/activity_detail.js'),
        // Phase 3 — Call detail
        call_detail: path.resolve(__dirname, 'frontend/src/entries/call_detail.js'),
        // Phase 4 — VoIP/SIP settings
        sip_settings: path.resolve(__dirname, 'frontend/src/entries/sip_settings.js'),
        voip_config: path.resolve(__dirname, 'frontend/src/entries/voip_config.js'),
        voip_sounds: path.resolve(__dirname, 'frontend/src/entries/voip_sounds.js'),
        voip_working_hours: path.resolve(__dirname, 'frontend/src/entries/voip_working_hours.js'),
        // Phase 5 — Profile + user management settings
        settings_dashboard: path.resolve(__dirname, 'frontend/src/entries/settings_dashboard.js'),
        profile_overview: path.resolve(__dirname, 'frontend/src/entries/profile_overview.js'),
        profile_personal_info: path.resolve(__dirname, 'frontend/src/entries/profile_personal_info.js'),
        profile_security: path.resolve(__dirname, 'frontend/src/entries/profile_security.js'),
        profile_preferences: path.resolve(__dirname, 'frontend/src/entries/profile_preferences.js'),
        general_overview: path.resolve(__dirname, 'frontend/src/entries/general_overview.js'),
        general_language: path.resolve(__dirname, 'frontend/src/entries/general_language.js'),
        user_list: path.resolve(__dirname, 'frontend/src/entries/user_list.js'),
        user_form: path.resolve(__dirname, 'frontend/src/entries/user_form.js'),
        // Phase 6 — WhatsApp + transcription settings
        whatsapp_config: path.resolve(__dirname, 'frontend/src/entries/whatsapp_config.js'),
        whatsapp_templates_list: path.resolve(__dirname, 'frontend/src/entries/whatsapp_templates_list.js'),
        whatsapp_template_form: path.resolve(__dirname, 'frontend/src/entries/whatsapp_template_form.js'),
        pitch_manager: path.resolve(__dirname, 'frontend/src/entries/pitch_manager.js'),
        elevenlabs_config: path.resolve(__dirname, 'frontend/src/entries/elevenlabs_config.js'),
        vocabulary_editor: path.resolve(__dirname, 'frontend/src/entries/vocabulary_editor.js'),
        ai_config: path.resolve(__dirname, 'frontend/src/entries/ai_config.js'),
        team_products: path.resolve(__dirname, 'frontend/src/entries/team_products.js'),
        // Phase 7 — Global stages
        global_stages: path.resolve(__dirname, 'frontend/src/entries/global_stages.js'),
        // Phase 8 — Remaining CRM pages
        team_stage_form: path.resolve(__dirname, 'frontend/src/entries/team_stage_form.js'),
        team_stage_confirm_delete: path.resolve(__dirname, 'frontend/src/entries/team_stage_confirm_delete.js'),
        incoming_lead_confirm_delete: path.resolve(__dirname, 'frontend/src/entries/incoming_lead_confirm_delete.js'),
        incoming_lead_confirm_convert: path.resolve(__dirname, 'frontend/src/entries/incoming_lead_confirm_convert.js'),
      },
    },
  },
  server: {
    port: 5173,
    cors: true,
    // ─────────────────────────────────────────────────────────────────────────
    // Dev proxy — access the app at http://localhost:5173 (NOT :8000).
    // Used when VITE_DEV_MODE=true (frontend development with HMR).
    //
    // Exclusions in the catch-all regex:
    //   @vite, @svelte, @id, @fs  — Vite internal HMR/transform paths
    //   static/dist/              — Vite-served built assets (base: '/static/dist/')
    // ─────────────────────────────────────────────────────────────────────────
    proxy: {
      '/ws': { target: 'ws://localhost:8000', ws: true, changeOrigin: true },
      '^/(?!@|static/dist/)': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        configure: (proxy) => {
          proxy.on('proxyRes', (proxyRes, req) => {
            if (proxyRes.statusCode >= 300 && proxyRes.statusCode < 400) {
              console.log(
                `[proxy] ${req.method} ${req.url} → ${proxyRes.statusCode} ${proxyRes.headers.location}`
              );
            }
          });
        },
      },
    },
  },
  resolve: { alias: { '@': path.resolve(__dirname, 'frontend/src') } },
  // No `preview` block — `vite preview` is not used in this project.
  // Built app is served directly by Django at http://localhost:8000.
  // Port 5173 is reserved exclusively for `make dev` (Vite HMR).
});
