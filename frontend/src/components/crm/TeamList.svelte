<script>
  import { apiDelete } from '../../utils/api.js';
  import ConfirmModal from '../shared/ConfirmModal.svelte';

  export let teams = [];
  export let canCreate = false;
  export let apiUrls = {};

  let deleteTarget = null;
  let deleting = false;

  async function confirmDelete() {
    deleting = true;
    const res = await apiDelete(`${apiUrls.teams}${deleteTarget.id}/`);
    if (res.ok) {
      teams = teams.filter(t => t.id !== deleteTarget.id);
    }
    deleting = false;
    deleteTarget = null;
  }

  function cancelDelete() {
    if (!deleting) deleteTarget = null;
  }
</script>

<div class="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
  <!-- Header -->
  <div class="flex items-center justify-between mb-8">
    <div>
      <h1 class="text-3xl font-bold tracking-tight text-gray-900">Sales Teams</h1>
      <p class="mt-2 text-sm text-gray-600">Manage sales teams and team members</p>
    </div>
    {#if canCreate}
      <a
        href="/crm/teams/create/"
        class="inline-flex items-center px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition-colors"
      >
        Create Team
      </a>
    {/if}
  </div>

  {#if teams.length === 0}
    <div class="text-center py-16">
      <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
          d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/>
      </svg>
      <h3 class="mt-4 text-lg font-medium text-gray-900">No sales teams</h3>
      <p class="mt-2 text-sm text-gray-500">Get started by creating your first sales team.</p>
      {#if canCreate}
        <a
          href="/crm/teams/create/"
          class="mt-6 inline-flex items-center px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg"
        >
          Create Team
        </a>
      {/if}
    </div>
  {:else}
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
      {#each teams as team (team.id)}
        <div class="bg-white border border-gray-200 rounded-lg shadow hover:shadow-md transition-shadow flex flex-col">
          <button
            type="button"
            class="flex-1 px-6 py-5 text-left"
            on:click={() => window.location.href = `/crm/teams/${team.id}/`}
          >
            <h3 class="text-lg font-semibold text-gray-900 hover:text-indigo-600 transition-colors">
              {team.name}
            </h3>
            {#if team.managerName}
              <p class="mt-2 text-sm text-gray-600 flex items-center gap-1">
                <svg class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
                </svg>
                Manager: {team.managerName}
              </p>
            {/if}
            <p class="mt-1 text-sm text-gray-600 flex items-center gap-1">
              <svg class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/>
              </svg>
              Members: {team.memberCount}
            </p>
          </button>

          <div class="px-6 py-3 bg-gray-50 border-t border-gray-100 flex items-center justify-between">
            <a
              href="/crm/teams/{team.id}/"
              class="text-sm font-medium text-indigo-600 hover:text-indigo-500"
            >
              View
            </a>
            <div class="flex items-center gap-3">
              <a
                href="/crm/teams/{team.id}/edit/"
                class="text-sm font-medium text-indigo-600 hover:text-indigo-500"
              >
                Edit
              </a>
              <button
                type="button"
                class="text-sm font-medium text-red-600 hover:text-red-500"
                on:click={() => (deleteTarget = team)}
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

{#if deleteTarget}
  <ConfirmModal
    title="Delete Team"
    message="Are you sure you want to delete the team '{deleteTarget.name}'? This cannot be undone."
    confirmLabel="Delete"
    loading={deleting}
    danger={true}
    onConfirm={confirmDelete}
    onCancel={cancelDelete}
  />
{/if}
