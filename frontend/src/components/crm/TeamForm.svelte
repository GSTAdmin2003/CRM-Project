<script>
  import { apiPost, apiPatch } from '../../utils/api.js';

  export let team = null;
  export let managers = [];
  export let apiUrls = {};

  let name = team?.name ?? '';
  let description = team?.description ?? '';
  let managerId = team?.managerId ? String(team.managerId) : '';
  let saving = false;
  let error = '';

  async function submit() {
    saving = true;
    error = '';
    const body = {
      name,
      description,
      manager: managerId || null,
    };
    const res = team
      ? await apiPatch(`${apiUrls.teams}${team.id}/`, body)
      : await apiPost(apiUrls.teams, body);
    saving = false;
    if (res.ok) {
      window.location.href = '/crm/teams/';
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
      <a href="/crm/teams/" class="hover:text-indigo-600">Teams</a>
      <span class="mx-2">/</span>
      <span>{team ? 'Edit Team' : 'Create Team'}</span>
    </nav>
    <h1 class="text-2xl font-bold text-gray-900">{team ? 'Edit Team' : 'Create Team'}</h1>
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
        Team Name <span class="text-red-500">*</span>
      </label>
      <input
        type="text"
        bind:value={name}
        required
        placeholder="e.g., Enterprise Sales, SMB Team"
        class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
      <p class="mt-1 text-xs text-gray-500">Choose a descriptive name for your sales team</p>
    </div>

    <!-- Description -->
    <div>
      <label class="block text-sm font-semibold text-gray-700 mb-1">Description</label>
      <textarea
        bind:value={description}
        rows="4"
        placeholder="Brief description of the team's focus or responsibilities"
        class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-vertical"
      ></textarea>
    </div>

    <!-- Manager -->
    <div>
      <label class="block text-sm font-semibold text-gray-700 mb-1">Team Manager</label>
      <select
        bind:value={managerId}
        class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        <option value="">Select a manager...</option>
        {#each managers as m}
          <option value={String(m.id)}>{m.name}</option>
        {/each}
      </select>
      <p class="mt-1 text-xs text-gray-500">Choose a team manager to oversee this sales team</p>
    </div>

    <!-- Actions -->
    <div class="flex items-center justify-between pt-2 border-t border-gray-100">
      <button
        type="button"
        class="px-4 py-2 text-sm font-medium text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-md transition-colors"
        on:click={() => history.back()}
      >
        Cancel
      </button>
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
        {team ? 'Update Team' : 'Create Team'}
      </button>
    </div>
  </form>
</div>
