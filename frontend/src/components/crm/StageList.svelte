<script>
  import { apiDelete } from '../../utils/api.js';
  import ConfirmModal from '../shared/ConfirmModal.svelte';

  export let stages = [];
  export let apiUrls = {};

  let deleteTarget = null;
  let deleting = false;

  async function confirmDelete() {
    deleting = true;
    const res = await apiDelete(`${apiUrls.stages}${deleteTarget.id}/`);
    if (res.ok) {
      stages = stages.filter(s => s.id !== deleteTarget.id);
    }
    deleting = false;
    deleteTarget = null;
  }

  function cancelDelete() {
    if (!deleting) deleteTarget = null;
  }
</script>

<div class="max-w-6xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
  <!-- Header -->
  <div class="flex items-center justify-between mb-6">
    <div>
      <h1 class="text-3xl font-bold tracking-tight text-gray-900">Pipeline Stages</h1>
      <p class="mt-1 text-sm text-gray-600">Configure your sales pipeline stages</p>
    </div>
    <a
      href="/crm/stages/create/"
      class="inline-flex items-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors"
    >
      Add Stage
    </a>
  </div>

  <!-- Table -->
  <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
    {#if stages.length === 0}
      <p class="text-center py-16 text-gray-400 text-sm">No stages configured yet.</p>
    {:else}
      <table class="w-full">
        <thead>
          <tr class="bg-gray-50 border-b border-gray-200 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
            <th class="px-4 py-3">Color</th>
            <th class="px-4 py-3">Name</th>
            <th class="px-4 py-3">Team</th>
            <th class="px-4 py-3">Probability</th>
            <th class="px-4 py-3">Closed</th>
            <th class="px-4 py-3 text-right">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          {#each stages as stage (stage.id)}
            <tr class="hover:bg-gray-50">
              <td class="px-4 py-3">
                <span
                  class="inline-block w-5 h-5 rounded-full border border-gray-200"
                  style="background-color: {stage.color};"
                ></span>
              </td>
              <td class="px-4 py-3 font-medium text-gray-900">{stage.name}</td>
              <td class="px-4 py-3 text-gray-600">
                {#if stage.teamName}
                  {stage.teamName}
                {:else}
                  <span class="text-gray-400 italic">Global</span>
                {/if}
              </td>
              <td class="px-4 py-3 text-gray-600">{stage.probability}%</td>
              <td class="px-4 py-3">
                {#if stage.isClosedStage}
                  <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
                    Closed
                  </span>
                {:else}
                  <span class="text-gray-400">—</span>
                {/if}
              </td>
              <td class="px-4 py-3 text-right">
                <div class="flex items-center justify-end gap-2">
                  <a
                    href="/crm/stages/{stage.id}/edit/"
                    class="px-3 py-1 text-xs font-medium text-gray-600 border border-gray-200 rounded hover:bg-gray-50 transition-colors"
                  >
                    Edit
                  </a>
                  <button
                    type="button"
                    class="px-3 py-1 text-xs font-medium text-red-600 border border-red-200 rounded hover:bg-red-50 transition-colors"
                    on:click={() => (deleteTarget = stage)}
                  >
                    Delete
                  </button>
                </div>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </div>
</div>

{#if deleteTarget}
  <ConfirmModal
    title="Delete Stage"
    message="Are you sure you want to delete the stage '{deleteTarget.name}'? This cannot be undone."
    confirmLabel="Delete"
    loading={deleting}
    danger={true}
    onConfirm={confirmDelete}
    onCancel={cancelDelete}
  />
{/if}
