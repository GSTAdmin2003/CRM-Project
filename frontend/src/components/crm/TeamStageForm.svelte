<script>
  import { apiPost, apiPatch } from '../../utils/api.js';

  export let team = {};
  export let stage = null;
  export let apiUrls = {};

  let name = stage?.name ?? '';
  let color = stage?.color ?? '#6B7280';
  let probability = stage?.probability ?? 0;
  let saving = false;
  let error = '';

  const cancelUrl = `/crm/teams/${team.id}/`;

  async function submit() {
    saving = true;
    error = '';
    const body = {
      name,
      color,
      probability,
      sales_team: team.id,
    };
    const res = stage
      ? await apiPatch(`${apiUrls.stages}${stage.id}/`, body)
      : await apiPost(apiUrls.stages, body);
    saving = false;
    if (res.ok) {
      window.location.href = cancelUrl;
    } else {
      const d = await res.json().catch(() => ({}));
      error = d.detail || JSON.stringify(d);
    }
  }
</script>

<div class="max-w-2xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
  <nav class="text-sm text-gray-500 mb-4">
    <a href="/crm/" class="hover:text-indigo-600">CRM</a>
    <span class="mx-2">/</span>
    <a href="/crm/teams/" class="hover:text-indigo-600">Teams</a>
    <span class="mx-2">/</span>
    <a href={cancelUrl} class="hover:text-indigo-600">{team.name}</a>
    <span class="mx-2">/</span>
    <span>{stage ? 'Edit Stage' : 'Create Stage'}</span>
  </nav>

  <div class="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-800">
    Team: <span class="font-semibold">{team.name}</span> — this stage is specific to this team.
  </div>

  {#if error}
    <div class="mb-4 rounded-md bg-red-50 px-4 py-3 text-sm text-red-700 border border-red-200">{error}</div>
  {/if}

  <form on:submit|preventDefault={submit} class="space-y-6 bg-white rounded-xl border border-gray-200 p-6">
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
    </div>

    <div>
      <label class="block text-sm font-semibold text-gray-700 mb-1">Stage Color</label>
      <div class="flex items-center gap-3">
        <input type="color" bind:value={color} class="w-14 h-10 p-0 border border-gray-300 rounded cursor-pointer" />
        <span class="text-sm text-gray-500">{color}</span>
      </div>
    </div>

    <div>
      <label class="block text-sm font-semibold text-gray-700 mb-1">Default Probability (%)</label>
      <input
        type="number"
        bind:value={probability}
        min="0"
        max="100"
        class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
    </div>

    <div class="flex items-center justify-between pt-2 border-t border-gray-100">
      <a href={cancelUrl} class="px-4 py-2 text-sm font-medium text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-md transition-colors">
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
