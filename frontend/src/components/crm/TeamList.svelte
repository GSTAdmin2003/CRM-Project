<script>
  import { apiDelete, apiPost, apiPatch } from '../../utils/api.js';
  import ConfirmModal from '../shared/ConfirmModal.svelte';

  export let teams = [];
  export let canCreate = false;
  export let canManageStages = false;
  export let globalStages = [];
  export let apiUrls = {};

  let deleteTarget = null;
  let deleting = false;

  // Stage management state
  let showStageForm = false;
  let editingStage = null;
  let stageForm = { name: '', color: '#6B7280', probability: 0, description: '' };
  let stageSaving = false;
  let stageError = '';
  let deleteStageTarget = null;
  let deletingStage = false;

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

  function openNewStageForm() {
    editingStage = null;
    stageForm = { name: '', color: '#6B7280', probability: 0, description: '' };
    stageError = '';
    showStageForm = true;
  }

  function openEditStageForm(stage) {
    editingStage = stage;
    stageForm = {
      name: stage.name,
      color: stage.color,
      probability: stage.probability,
      description: stage.description,
    };
    stageError = '';
    showStageForm = true;
  }

  function cancelStageForm() {
    showStageForm = false;
    editingStage = null;
    stageError = '';
  }

  async function saveStage() {
    if (!stageForm.name.trim()) { stageError = 'Stage name is required.'; return; }
    const prob = parseInt(stageForm.probability);
    if (isNaN(prob) || prob < 0 || prob > 100) { stageError = 'Probability must be 0–100.'; return; }

    stageSaving = true;
    stageError = '';

    const payload = {
      name: stageForm.name.trim(),
      color: stageForm.color,
      probability: prob,
      description: stageForm.description,
      sales_team: null,
    };

    let res;
    if (editingStage) {
      res = await apiPatch(`${apiUrls.stages}${editingStage.id}/`, payload);
    } else {
      res = await apiPost(apiUrls.stages, payload);
    }

    if (res.ok) {
      const data = await res.json();
      if (editingStage) {
        globalStages = globalStages.map(s => s.id === editingStage.id ? {
          id: data.id,
          name: data.name,
          order: data.order,
          color: data.color,
          probability: data.probability,
          isClosedStage: data.is_closed_stage,
          description: data.description || '',
        } : s);
      } else {
        globalStages = [...globalStages, {
          id: data.id,
          name: data.name,
          order: data.order,
          color: data.color,
          probability: data.probability,
          isClosedStage: data.is_closed_stage,
          description: data.description || '',
        }];
      }
      showStageForm = false;
      editingStage = null;
    } else {
      const err = await res.json().catch(() => ({}));
      stageError = err.detail || err.name?.[0] || 'Failed to save stage.';
    }
    stageSaving = false;
  }

  async function confirmDeleteStage() {
    deletingStage = true;
    const res = await apiDelete(`${apiUrls.stages}${deleteStageTarget.id}/`);
    if (res.ok) {
      globalStages = globalStages.filter(s => s.id !== deleteStageTarget.id);
    } else {
      const err = await res.json().catch(() => ({}));
      alert(err.detail || 'Cannot delete this stage.');
    }
    deletingStage = false;
    deleteStageTarget = null;
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
        <a
          href="/crm/teams/{team.id}/"
          class="bg-white border border-gray-200 rounded-lg shadow hover:shadow-md transition-shadow px-6 py-5 block"
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
        </a>
      {/each}
    </div>
  {/if}

  <!-- Global Pipeline Stages (Sales Director / Owner only) -->
  {#if canManageStages}
    <div class="mt-12">
      <div class="flex items-center justify-between mb-4">
        <div>
          <h2 class="text-xl font-semibold text-gray-900">Global Pipeline Stages</h2>
          <p class="mt-1 text-sm text-gray-500">Default stages available to all teams</p>
        </div>
        <button
          type="button"
          on:click={openNewStageForm}
          class="inline-flex items-center px-3 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition-colors"
        >
          Add Stage
        </button>
      </div>

      {#if globalStages.length === 0}
        <div class="text-center py-10 bg-white border border-gray-200 rounded-lg">
          <p class="text-sm text-gray-500">No global stages defined yet.</p>
        </div>
      {:else}
        <div class="bg-white border border-gray-200 rounded-lg divide-y divide-gray-100">
          {#each globalStages as stage (stage.id)}
            <div class="flex items-center justify-between px-5 py-3">
              <div class="flex items-center gap-3">
                <span class="w-3 h-3 rounded-full flex-shrink-0" style="background-color: {stage.color}"></span>
                <div>
                  <span class="text-sm font-medium text-gray-900">{stage.name}</span>
                  {#if stage.isClosedStage}
                    <span class="ml-2 inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600">Closed</span>
                  {/if}
                </div>
                <span class="text-xs text-gray-400">{stage.probability}%</span>
              </div>
              <div class="flex items-center gap-3">
                <button
                  type="button"
                  on:click={() => openEditStageForm(stage)}
                  class="text-sm text-indigo-600 hover:text-indigo-500"
                >Edit</button>
                <button
                  type="button"
                  on:click={() => (deleteStageTarget = stage)}
                  class="text-sm text-red-600 hover:text-red-500"
                >Delete</button>
              </div>
            </div>
          {/each}
        </div>
      {/if}
    </div>
  {/if}
</div>

<!-- Stage Form Modal -->
{#if showStageForm}
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
    <div class="bg-white rounded-xl shadow-xl w-full max-w-md mx-4 p-6">
      <h3 class="text-lg font-semibold text-gray-900 mb-4">
        {editingStage ? 'Edit Stage' : 'New Global Stage'}
      </h3>

      {#if stageError}
        <p class="mb-3 text-sm text-red-600">{stageError}</p>
      {/if}

      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Name *</label>
          <input
            type="text"
            bind:value={stageForm.name}
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            placeholder="e.g. Qualified"
          />
        </div>
        <div class="flex gap-4">
          <div class="flex-1">
            <label class="block text-sm font-medium text-gray-700 mb-1">Color</label>
            <input type="color" bind:value={stageForm.color} class="h-9 w-full border border-gray-300 rounded-lg cursor-pointer" />
          </div>
          <div class="flex-1">
            <label class="block text-sm font-medium text-gray-700 mb-1">Probability %</label>
            <input
              type="number"
              bind:value={stageForm.probability}
              min="0" max="100"
              class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Description</label>
          <textarea
            bind:value={stageForm.description}
            rows="2"
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          ></textarea>
        </div>
      </div>

      <div class="mt-5 flex justify-end gap-3">
        <button type="button" on:click={cancelStageForm} class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50">
          Cancel
        </button>
        <button
          type="button"
          on:click={saveStage}
          disabled={stageSaving}
          class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg disabled:opacity-50"
        >
          {stageSaving ? 'Saving…' : 'Save'}
        </button>
      </div>
    </div>
  </div>
{/if}

<!-- Delete Team Modal -->
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

<!-- Delete Stage Modal -->
{#if deleteStageTarget}
  <ConfirmModal
    title="Delete Stage"
    message="Are you sure you want to delete the stage '{deleteStageTarget.name}'?"
    confirmLabel="Delete"
    loading={deletingStage}
    danger={true}
    onConfirm={confirmDeleteStage}
    onCancel={() => { if (!deletingStage) deleteStageTarget = null; }}
  />
{/if}
