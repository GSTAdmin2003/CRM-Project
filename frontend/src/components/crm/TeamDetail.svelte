<script>
  import { apiGet, apiPatch, apiPost } from '../../utils/api.js';
  import { onMount } from 'svelte';

  export let team = {};
  export let members = [];
  export let allUsers = [];
  export let canEdit = false;
  export let apiUrls = {};

  // Edit team state
  let editing = false;
  let saving = false;
  let editError = '';
  let editName = '';
  let editDescription = '';
  let editManagerId = '';

  // Displayed values (updated optimistically on save)
  let displayName = team.name;
  let displayDescription = team.description;
  let displayManagerName = team.managerName;

  // Member management state
  let currentMembers = [...members];
  let addMemberId = '';
  let addingMember = false;
  let memberError = '';

  $: availableToAdd = allUsers.filter(u => !currentMembers.find(m => m.id === u.id));

  // Stages
  let teamStages = [];
  let stagesLoading = true;
  let stagesError = '';

  onMount(async () => {
    try {
      const res = await apiGet(`${apiUrls.stages}?sales_team=${team.id}`);
      if (res.ok) {
        const data = await res.json();
        teamStages = data.results || data;
      } else {
        stagesError = 'Failed to load stages';
      }
    } catch {
      stagesError = 'Failed to load stages';
    } finally {
      stagesLoading = false;
    }
  });

  // ---- Team edit ----
  function startEdit() {
    editName = displayName;
    editDescription = displayDescription;
    editManagerId = team.managerId ? String(team.managerId) : '';
    editError = '';
    editing = true;
  }

  function cancelEdit() {
    editing = false;
    editError = '';
  }

  async function saveEdit() {
    if (!editName.trim()) { editError = 'Team name is required.'; return; }
    saving = true;
    editError = '';
    const res = await apiPatch(`${apiUrls.teams}${team.id}/`, {
      name: editName.trim(),
      description: editDescription,
      manager: editManagerId || null,
    });
    saving = false;
    if (res.ok) {
      const data = await res.json();
      displayName = data.name ?? editName.trim();
      displayDescription = data.description ?? editDescription;
      const mgr = allUsers.find(u => String(u.id) === editManagerId);
      displayManagerName = mgr ? mgr.name : null;
      team = { ...team, managerId: editManagerId ? parseInt(editManagerId) : null };
      editing = false;
    } else {
      const d = await res.json().catch(() => ({}));
      editError = d.detail || d.name?.[0] || 'Failed to save.';
    }
  }

  // ---- Member management ----
  async function addMember() {
    if (!addMemberId) return;
    addingMember = true;
    memberError = '';
    const res = await apiPost(`${apiUrls.teams}${team.id}/add_member/`, { user_id: parseInt(addMemberId) });
    addingMember = false;
    if (res.ok) {
      currentMembers = await res.json();
      addMemberId = '';
    } else {
      const d = await res.json().catch(() => ({}));
      memberError = d.detail || 'Failed to add member.';
    }
  }

  async function removeMember(userId) {
    memberError = '';
    const res = await apiPost(`${apiUrls.teams}${team.id}/remove_member/`, { user_id: userId });
    if (res.ok) {
      currentMembers = await res.json();
    } else {
      const d = await res.json().catch(() => ({}));
      memberError = d.detail || 'Failed to remove member.';
    }
  }
</script>

<div class="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
  <!-- Header -->
  <div class="mb-8 bg-white rounded-xl border border-gray-200 p-6">
    {#if editing}
      {#if editError}
        <div class="mb-4 rounded-md bg-red-50 px-4 py-3 text-sm text-red-700 border border-red-200">{editError}</div>
      {/if}
      <div class="space-y-4">
        <div>
          <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Team Name</label>
          <input
            type="text"
            bind:value={editName}
            class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
        <div>
          <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Description</label>
          <textarea
            bind:value={editDescription}
            rows="2"
            class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
          ></textarea>
        </div>
        <div>
          <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Manager</label>
          <select
            bind:value={editManagerId}
            class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">No manager</option>
            {#each allUsers as u}
              <option value={String(u.id)}>{u.name}</option>
            {/each}
          </select>
        </div>
      </div>
      <div class="flex items-center gap-3 mt-5">
        <button
          type="button"
          on:click={saveEdit}
          disabled={saving}
          class="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-medium rounded-md transition-colors"
        >
          {#if saving}
            <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
            </svg>
          {/if}
          Save
        </button>
        <button type="button" on:click={cancelEdit} disabled={saving}
          class="px-4 py-2 text-sm font-medium text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-md transition-colors">
          Cancel
        </button>
      </div>
    {:else}
      <div class="flex items-start justify-between">
        <div>
          <h1 class="text-3xl font-bold tracking-tight text-gray-900">{displayName}</h1>
          {#if displayDescription}
            <p class="mt-2 text-sm text-gray-600">{displayDescription}</p>
          {/if}
          {#if displayManagerName}
            <p class="mt-1 text-sm text-gray-500">Manager: {displayManagerName}</p>
          {/if}
        </div>
        <div class="flex gap-3 flex-shrink-0 ml-6">
          <a href="/crm/teams/"
            class="px-4 py-2 text-sm font-medium text-white bg-gray-600 hover:bg-gray-700 rounded-md transition-colors">
            Back
          </a>
          {#if canEdit}
            <button type="button" on:click={startEdit}
              class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-md transition-colors">
              Edit
            </button>
          {/if}
        </div>
      </div>
    {/if}
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
    <!-- Members -->
    <div class="bg-white shadow rounded-lg">
      <div class="px-6 py-4 border-b border-gray-200">
        <h3 class="text-lg font-medium text-gray-900">Team Members ({currentMembers.length})</h3>
      </div>
      <div class="px-6 py-4">
        {#if memberError}
          <p class="mb-3 text-sm text-red-600">{memberError}</p>
        {/if}

        {#if currentMembers.length === 0}
          <p class="text-sm text-gray-500 text-center py-6">No team members assigned yet.</p>
        {:else}
          <table class="w-full text-sm mb-4">
            <thead>
              <tr class="text-left text-xs font-medium text-gray-500 uppercase tracking-wide border-b border-gray-200">
                <th class="pb-2 pr-4">Name</th>
                <th class="pb-2">Email</th>
                {#if canEdit}<th class="pb-2"></th>{/if}
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
              {#each currentMembers as member (member.id)}
                <tr class="hover:bg-gray-50">
                  <td class="py-3 pr-4">
                    <div class="flex items-center gap-3">
                      <div class="w-8 h-8 rounded-full bg-indigo-500 flex items-center justify-center text-white text-xs font-semibold flex-shrink-0">
                        {(member.name || '?').charAt(0).toUpperCase()}
                      </div>
                      <span class="font-medium text-gray-900">{member.name}</span>
                    </div>
                  </td>
                  <td class="py-3 text-gray-600">{member.email}</td>
                  {#if canEdit}
                    <td class="py-3 text-right">
                      <button
                        type="button"
                        on:click={() => removeMember(member.id)}
                        class="text-xs text-red-500 hover:text-red-700"
                      >Remove</button>
                    </td>
                  {/if}
                </tr>
              {/each}
            </tbody>
          </table>
        {/if}

        {#if canEdit && availableToAdd.length > 0}
          <div class="flex items-center gap-2 pt-3 border-t border-gray-100">
            <select
              bind:value={addMemberId}
              class="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">Select user to add…</option>
              {#each availableToAdd as u}
                <option value={String(u.id)}>{u.name}</option>
              {/each}
            </select>
            <button
              type="button"
              on:click={addMember}
              disabled={!addMemberId || addingMember}
              class="px-3 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-medium rounded-md transition-colors"
            >
              {addingMember ? '…' : 'Add'}
            </button>
          </div>
        {/if}
      </div>
    </div>

    <!-- Team Stages -->
    <div class="bg-white shadow rounded-lg">
      <div class="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
        <h3 class="text-lg font-medium text-gray-900">Team Stages</h3>
        {#if canEdit}
          <a href="/crm/teams/{team.id}/stages/create/"
            class="text-sm text-indigo-600 hover:text-indigo-500 font-medium">+ Add Stage</a>
        {/if}
      </div>
      <div class="px-6 py-4">
        {#if stagesLoading}
          <div class="flex items-center justify-center py-8 text-gray-400">
            <svg class="w-5 h-5 animate-spin mr-2" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
            </svg>
            Loading stages...
          </div>
        {:else if stagesError}
          <p class="text-sm text-red-500 text-center py-8">{stagesError}</p>
        {:else if teamStages.length === 0}
          <p class="text-sm text-gray-500 text-center py-8">
            This team is using the global default pipeline stages.
          </p>
        {:else}
          <div class="space-y-2">
            {#each teamStages as stage (stage.id)}
              <div class="flex items-center justify-between p-3 border border-gray-100 rounded-lg">
                <div class="flex items-center gap-3">
                  <span class="w-4 h-4 rounded-full flex-shrink-0" style="background-color: {stage.color};"></span>
                  <span class="text-sm font-medium text-gray-900">{stage.name}</span>
                </div>
                <div class="flex items-center gap-3 text-xs text-gray-500">
                  <span>{stage.probability}%</span>
                  {#if canEdit}
                    <a href="/crm/teams/{team.id}/stages/{stage.id}/edit/" class="text-indigo-600 hover:text-indigo-500">Edit</a>
                    <a href="/crm/teams/{team.id}/stages/{stage.id}/delete/" class="text-red-500 hover:text-red-600">Delete</a>
                  {/if}
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    </div>
  </div>
</div>
