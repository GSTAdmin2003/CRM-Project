<script>
  import { apiPost, apiPatch } from '../../utils/api.js';

  export let stage = null;
  export let teams = [];
  export let teamId = null;
  export let apiUrls = {};

  let name = stage?.name ?? '';
  let color = stage?.color ?? '#6B7280';
  let probability = stage?.probability ?? 0;
  let isClosedStage = stage?.isClosedStage ?? false;
  let salesTeamId = stage?.salesTeamId ?? teamId ?? '';
  let saving = false;
  let error = '';

  async function submit() {
    saving = true;
    error = '';
    const body = {
      name,
      color,
      probability,
      is_closed_stage: isClosedStage,
      sales_team: salesTeamId || null,
    };
    const res = stage
      ? await apiPatch(`${apiUrls.stages}${stage.id}/`, body)
      : await apiPost(apiUrls.stages, body);
    saving = false;
    if (res.ok) {
      window.location.href = '/crm/stages/';
    } else {
      const d = await res.json().catch(() => ({}));
      error = d.detail || JSON.stringify(d);
    }
  }
</script>

<div class="max-w-2xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
  <!-- Header -->
  <div class="mb-6">
    <nav class="text-sm text-gray-500 mb-2">
      <a href="/crm/" class="hover:text-indigo-600">CRM</a>
      <span class="mx-2">/</span>
      <a href="/crm/stages/" class="hover:text-indigo-600">Stages</a>
      <span class="mx-2">/</span>
      <span>{stage ? 'Edit Stage' : 'Create Stage'}</span>
    </nav>
    <h1 class="text-2xl font-bold text-gray-900">{stage ? 'Edit Stage' : 'Create Stage'}</h1>
  </div>

  {#if error}
    <div class="mb-4 rounded-md bg-red-50 px-4 py-3 text-sm text-red-700 border border-red-200">
      {error}
    </div>
  {/if}

  <form on:submit|preventDefault={submit} class="space-y-6 bg-white rounded-xl border border-gray-200 p-6">
    <!-- Name -->
    <div>
      <label class="block text-sm font-semibold text-gray-700 mb-1">
        Stage Name <span class="text-red-500">*</span>
      </label>
      <input
        type="text"
        bind:value={name}
        required
        placeholder="e.g., Prospecting, Negotiation, Closed Won"
        class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
      <p class="mt-1 text-xs text-gray-500">A descriptive name for this stage in your sales pipeline</p>
    </div>

    <!-- Color -->
    <div>
      <label class="block text-sm font-semibold text-gray-700 mb-1">Stage Color</label>
      <div class="flex items-center gap-3">
        <input
          type="color"
          bind:value={color}
          class="w-14 h-10 p-0 border border-gray-300 rounded cursor-pointer"
        />
        <span class="text-sm text-gray-500">{color}</span>
      </div>
      <p class="mt-1 text-xs text-gray-500">Color used to represent this stage in the pipeline</p>
    </div>

    <!-- Probability -->
    <div>
      <label class="block text-sm font-semibold text-gray-700 mb-1">Default Probability (%)</label>
      <input
        type="number"
        bind:value={probability}
        min="0"
        max="100"
        class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
      <p class="mt-1 text-xs text-gray-500">Default win probability for opportunities in this stage (0–100)</p>
    </div>

    <!-- Is Closed Stage -->
    <div>
      <label class="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          bind:checked={isClosedStage}
          class="h-4 w-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
        />
        <span class="text-sm font-semibold text-gray-700">This is a closed stage</span>
      </label>
      <p class="mt-1 ml-6 text-xs text-gray-500">Mark this stage as closed (e.g., "Closed Won" or "Closed Lost")</p>
    </div>

    <!-- Team -->
    {#if teams.length > 0}
      <div>
        <label class="block text-sm font-semibold text-gray-700 mb-1">Sales Team (optional)</label>
        <select
          bind:value={salesTeamId}
          class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Global Stage (no team)</option>
          {#each teams as t}
            <option value={String(t.id)}>{t.name}</option>
          {/each}
        </select>
        <p class="mt-1 text-xs text-gray-500">Leave blank to create a global stage available to all teams</p>
      </div>
    {/if}

    <!-- Actions -->
    <div class="flex items-center justify-between pt-2 border-t border-gray-100">
      <a
        href="/crm/stages/"
        class="px-4 py-2 text-sm font-medium text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-md transition-colors"
      >
        Cancel
      </a>
      <button
        type="submit"
        disabled={saving}
        class="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium rounded-md transition-colors"
      >
        {#if saving}
          <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
          </svg>
        {/if}
        {stage ? 'Update Stage' : 'Create Stage'}
      </button>
    </div>
  </form>
</div>
