<script>
  import { onMount } from 'svelte';
  import { apiGet } from '../../utils/api.js';
  import { getCsrfToken } from '../../utils/csrf.js';
  import { showToast } from '../shared/toastStore.js';
  import Toast from '../shared/Toast.svelte';

  export let apiUrls = {};

  let teams = [];
  let loading = true;
  let uploading = {}; // { `${teamId}_${lang}`: true }

  onMount(async () => {
    const res = await apiGet(apiUrls.teams);
    if (res.ok) {
      const data = await res.json();
      teams = Array.isArray(data) ? data : (data.results ?? data.teams ?? []);
    } else {
      showToast('error', 'Failed to load sales teams.');
    }
    loading = false;
  });

  function resolveTeamUrl(id) {
    return apiUrls.pitchTeam.replace('{id}', id);
  }

  async function uploadPitch(teamId, language, file) {
    const key = `${teamId}_${language}`;
    uploading = { ...uploading, [key]: true };
    try {
      const formData = new FormData();
      formData.append('pitch_pdf', file);
      formData.append('language', language);

      const res = await fetch(resolveTeamUrl(teamId), {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'X-CSRFToken': getCsrfToken() },
        body: formData,
      });

      if (res.ok) {
        showToast('success', `${language === 'ka' ? 'Georgian' : 'English'} PDF uploaded successfully.`);
        // Refresh teams list to show updated status
        const r = await apiGet(apiUrls.teams);
        if (r.ok) {
          const data = await r.json();
          teams = Array.isArray(data) ? data : (data.results ?? data.teams ?? []);
        }
      } else {
        const data = await res.json().catch(() => ({}));
        showToast('error', data.error || 'Upload failed.');
      }
    } catch (err) {
      showToast('error', 'Upload failed: ' + err.message);
    }
    uploading = { ...uploading, [key]: false };
  }

  async function uploadDefault(language, file) {
    const key = `default_${language}`;
    uploading = { ...uploading, [key]: true };
    try {
      const formData = new FormData();
      formData.append('pitch_pdf', file);
      formData.append('language', language);

      const res = await fetch(apiUrls.pitchDefault, {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'X-CSRFToken': getCsrfToken() },
        body: formData,
      });

      if (res.ok) {
        showToast('success', `Default ${language === 'ka' ? 'Georgian' : 'English'} PDF uploaded.`);
      } else {
        const data = await res.json().catch(() => ({}));
        showToast('error', data.error || 'Upload failed.');
      }
    } catch (err) {
      showToast('error', 'Upload failed: ' + err.message);
    }
    uploading = { ...uploading, [key]: false };
  }

  function handleFileInput(teamId, language) {
    return (e) => {
      const file = e.target.files?.[0];
      if (file) uploadPitch(teamId, language, file);
      e.target.value = '';
    };
  }

  function handleDefaultFileInput(language) {
    return (e) => {
      const file = e.target.files?.[0];
      if (file) uploadDefault(language, file);
      e.target.value = '';
    };
  }
</script>

<Toast />

{#if loading}
  <div class="flex items-center justify-center py-20">
    <svg class="w-6 h-6 animate-spin text-indigo-500" fill="none" viewBox="0 0 24 24">
      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
    </svg>
  </div>
{:else}
  <div class="space-y-6">
    <!-- Default Pitch -->
    <div class="bg-white border border-indigo-200 rounded-lg overflow-hidden">
      <div class="px-5 py-3 bg-indigo-50 border-b border-indigo-200">
        <h3 class="text-sm font-semibold text-indigo-900">Default Pitch PDF</h3>
        <p class="text-xs text-indigo-600 mt-0.5">Used when a team has no PDF set</p>
      </div>
      <div class="px-5 py-4 grid grid-cols-1 sm:grid-cols-2 gap-4">
        {#each ['en', 'ka'] as lang}
          <div class="flex items-center gap-3">
            <span class="inline-block px-1.5 py-0.5 rounded font-mono text-xs bg-gray-200 text-gray-600">{lang}</span>
            <label class="flex-1">
              <input
                type="file"
                accept=".pdf"
                class="sr-only"
                on:change={handleDefaultFileInput(lang)}
                disabled={uploading[`default_${lang}`]}
              />
              <span
                class="inline-flex items-center px-3 py-1.5 text-xs font-medium rounded-lg border cursor-pointer
                  {uploading[`default_${lang}`]
                    ? 'bg-gray-100 text-gray-400 border-gray-200 cursor-not-allowed'
                    : 'bg-indigo-50 text-indigo-700 border-indigo-200 hover:bg-indigo-100'}"
              >
                {uploading[`default_${lang}`] ? 'Uploading...' : 'Upload PDF'}
              </span>
            </label>
          </div>
        {/each}
      </div>
    </div>

    <!-- Teams Table -->
    {#if teams.length > 0}
      <div class="overflow-hidden border border-gray-200 rounded-lg">
        <table class="min-w-full divide-y divide-gray-200 text-sm">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-4 py-3 text-left font-medium text-gray-500 uppercase tracking-wide text-xs">Team</th>
              <th class="px-4 py-3 text-left font-medium text-gray-500 uppercase tracking-wide text-xs">
                <span class="inline-block px-1.5 py-0.5 rounded font-mono text-xs bg-gray-200 text-gray-600 mr-1">en</span> English PDF
              </th>
              <th class="px-4 py-3 text-left font-medium text-gray-500 uppercase tracking-wide text-xs">
                <span class="inline-block px-1.5 py-0.5 rounded font-mono text-xs bg-gray-200 text-gray-600 mr-1">ka</span> Georgian PDF
              </th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-100">
            {#each teams as team}
              <tr class="hover:bg-gray-50 align-middle">
                <td class="px-4 py-3 font-medium text-gray-900 whitespace-nowrap">{team.name}</td>
                {#each ['en', 'ka'] as lang}
                  <td class="px-4 py-3">
                    <label class="cursor-pointer">
                      <input
                        type="file"
                        accept=".pdf"
                        class="sr-only"
                        on:change={handleFileInput(team.id, lang)}
                        disabled={uploading[`${team.id}_${lang}`]}
                      />
                      <span
                        class="inline-flex items-center px-2.5 py-1 text-xs font-medium rounded border cursor-pointer
                          {uploading[`${team.id}_${lang}`]
                            ? 'bg-gray-50 text-gray-400 border-gray-200 cursor-not-allowed'
                            : 'bg-white text-indigo-700 border-indigo-200 hover:bg-indigo-50'}"
                      >
                        {uploading[`${team.id}_${lang}`] ? 'Uploading...' : 'Upload PDF'}
                      </span>
                    </label>
                  </td>
                {/each}
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {:else}
      <div class="py-16 text-center border border-dashed border-gray-300 rounded-lg">
        <p class="text-gray-500 font-medium">No active sales teams</p>
        <p class="text-gray-400 text-sm mt-1">Create a sales team in CRM &rarr; Teams first.</p>
      </div>
    {/if}

    <div class="pt-4 border-t border-gray-100">
      <a
        href="/settings/whatsapp/templates/"
        class="inline-flex items-center text-sm text-gray-500 hover:text-gray-700 font-medium"
      >
        &larr; Back to Templates
      </a>
    </div>
  </div>
{/if}
