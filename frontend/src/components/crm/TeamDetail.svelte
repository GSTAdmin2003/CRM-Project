<script>
  import { apiGet } from '../../utils/api.js';
  import { onMount } from 'svelte';

  export let team = {};
  export let members = [];
  export let apiUrls = {};

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
</script>

<div class="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
  <!-- Header -->
  <div class="mb-8 flex items-center justify-between">
    <div>
      <h1 class="text-3xl font-bold tracking-tight text-gray-900">{team.name}</h1>
      {#if team.description}
        <p class="mt-2 text-sm text-gray-600">{team.description}</p>
      {/if}
      {#if team.managerName}
        <p class="mt-1 text-sm text-gray-500">Manager: {team.managerName}</p>
      {/if}
    </div>
    <div class="flex gap-3">
      <a
        href="/crm/teams/"
        class="px-4 py-2 text-sm font-medium text-white bg-gray-600 hover:bg-gray-700 rounded-md transition-colors"
      >
        Back to Teams
      </a>
      <a
        href="/crm/teams/{team.id}/edit/"
        class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-md transition-colors"
      >
        Edit Team
      </a>
    </div>
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
    <!-- Members -->
    <div class="bg-white shadow rounded-lg">
      <div class="px-6 py-4 border-b border-gray-200">
        <h3 class="text-lg font-medium text-gray-900">Team Members ({members.length})</h3>
      </div>
      <div class="px-6 py-4">
        {#if members.length === 0}
          <p class="text-sm text-gray-500 text-center py-8">No team members assigned yet.</p>
        {:else}
          <table class="w-full text-sm">
            <thead>
              <tr class="text-left text-xs font-medium text-gray-500 uppercase tracking-wide border-b border-gray-200">
                <th class="pb-2 pr-4">Name</th>
                <th class="pb-2">Email</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
              {#each members as member (member.id)}
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
                </tr>
              {/each}
            </tbody>
          </table>
        {/if}
      </div>
    </div>

    <!-- Team Stages -->
    <div class="bg-white shadow rounded-lg">
      <div class="px-6 py-4 border-b border-gray-200">
        <h3 class="text-lg font-medium text-gray-900">Team Stages</h3>
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
                  <span
                    class="w-4 h-4 rounded-full flex-shrink-0"
                    style="background-color: {stage.color};"
                  ></span>
                  <span class="text-sm font-medium text-gray-900">{stage.name}</span>
                </div>
                <div class="text-right text-xs text-gray-500">
                  <span>{stage.probability}%</span>
                  {#if stage.is_closed_stage}
                    <span class="ml-2 inline-flex items-center px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-600">
                      Closed
                    </span>
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
