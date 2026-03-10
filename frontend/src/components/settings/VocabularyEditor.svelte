<script>
  import { onMount } from 'svelte';
  import { apiGet, apiPatch, apiFetch } from '../../utils/api.js';
  import { showToast } from '../shared/toastStore.js';
  import Toast from '../shared/Toast.svelte';

  export let apiUrls = {};

  let enKeywords = '';
  let kaKeywords = '';
  let teams = [];
  let loading = true;
  let savingGlobal = false;
  let savingTeam = {};

  onMount(async () => {
    const [vocabRes] = await Promise.all([
      apiGet(apiUrls.vocabulary),
    ]);
    if (vocabRes.ok) {
      const data = await vocabRes.json();
      enKeywords = data.en_keywords || '';
      kaKeywords = data.ka_keywords || '';
      teams = (data.teams || []).map(t => ({
        ...t,
        keywords_en_local: t.keywords_en || '',
        keywords_ka_local: t.keywords_ka || '',
      }));
    } else {
      showToast('error', 'Failed to load vocabulary settings.');
    }
    loading = false;
  });

  async function saveGlobal() {
    savingGlobal = true;
    const res = await apiPatch(apiUrls.vocabulary, {
      en_keywords: enKeywords,
      ka_keywords: kaKeywords,
    });
    if (res.ok) {
      showToast('success', 'Default keywords saved.');
    } else {
      showToast('error', 'Failed to save keywords.');
    }
    savingGlobal = false;
  }

  async function saveTeamKeywords(team) {
    savingTeam = { ...savingTeam, [team.id]: true };
    const res = await apiFetch(apiUrls.vocabulary, {
      method: 'PATCH',
      body: JSON.stringify({
        team_id: team.id,
        keywords_en: team.keywords_en_local,
        keywords_ka: team.keywords_ka_local,
      }),
    });
    if (res.ok) {
      showToast('success', `Keywords saved for "${team.name}".`);
    } else {
      showToast('error', 'Failed to save team keywords.');
    }
    savingTeam = { ...savingTeam, [team.id]: false };
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
  <div class="space-y-8">
    <!-- Default Keywords -->
    <div>
      <h2 class="text-base font-semibold text-gray-900 mb-1">Default Keywords</h2>
      <p class="text-sm text-gray-500 mb-4">
        Applied to every transcription regardless of team. One per line or comma-separated.
      </p>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
        <div>
          <label class="block text-xs font-semibold text-blue-700 uppercase tracking-wide mb-1">
            English (EN)
          </label>
          <textarea
            bind:value={enKeywords}
            rows="6"
            class="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500"
            placeholder="e.g. TBC Bank, BGBank, Rustavi2"
          ></textarea>
        </div>
        <div>
          <label class="block text-xs font-semibold text-yellow-700 uppercase tracking-wide mb-1">
            Georgian (KA)
          </label>
          <textarea
            bind:value={kaKeywords}
            rows="6"
            class="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500"
            placeholder="e.g. საქართველო, თბილისი, რუსთავი"
          ></textarea>
        </div>
      </div>
      <div class="flex justify-end">
        <button
          type="button"
          on:click={saveGlobal}
          disabled={savingGlobal}
          class="inline-flex items-center px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
        >
          {#if savingGlobal}
            <svg class="w-4 h-4 animate-spin mr-2" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
            </svg>
          {/if}
          Save keywords
        </button>
      </div>
    </div>

    <hr class="border-gray-200" />

    <!-- Per-team Keywords -->
    <div>
      <h2 class="text-base font-semibold text-gray-900 mb-1">Team-Specific Keywords</h2>
      <p class="text-sm text-gray-500 mb-4">
        Additional keywords per team, added on top of the defaults above when a call's
        opportunity belongs to that team. One per line or comma-separated.
      </p>

      {#if teams.length > 0}
        <div class="space-y-4">
          {#each teams as team}
            <div class="p-4 border border-gray-200 rounded-lg">
              <h3 class="text-sm font-medium text-gray-800 mb-3">{team.name}</h3>
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">
                <div>
                  <label class="block text-xs font-semibold text-blue-700 uppercase tracking-wide mb-1">English (EN)</label>
                  <textarea
                    bind:value={team.keywords_en_local}
                    rows="3"
                    class="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500"
                    placeholder="Team-specific English terms..."
                  ></textarea>
                </div>
                <div>
                  <label class="block text-xs font-semibold text-yellow-700 uppercase tracking-wide mb-1">Georgian (KA)</label>
                  <textarea
                    bind:value={team.keywords_ka_local}
                    rows="3"
                    class="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500"
                    placeholder="გუნდის სპეციფიკური სიტყვები..."
                  ></textarea>
                </div>
              </div>
              <div class="flex justify-end">
                <button
                  type="button"
                  on:click={() => saveTeamKeywords(team)}
                  disabled={savingTeam[team.id]}
                  class="inline-flex items-center px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
                >
                  {savingTeam[team.id] ? 'Saving...' : 'Save'}
                </button>
              </div>
            </div>
          {/each}
        </div>
      {:else}
        <p class="text-sm text-gray-400 italic">No active sales teams found.</p>
      {/if}
    </div>
  </div>
{/if}
