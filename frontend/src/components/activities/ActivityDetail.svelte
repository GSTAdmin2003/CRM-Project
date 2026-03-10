<script>
  import { apiPost, apiDelete } from '../../utils/api.js';
  import StatusBadge from '../shared/StatusBadge.svelte';
  import ConfirmModal from '../shared/ConfirmModal.svelte';

  export let activity = null;
  export let canEdit = false;
  export let apiUrls = {};

  let showCompleteForm = false;
  let outcomeText = '';
  let completing = false;
  let completeError = '';

  let showDeleteModal = false;
  let deleting = false;

  function formatDate(iso) {
    if (!iso) return '—';
    const d = new Date(iso);
    if (isNaN(d)) return iso;
    return d.toLocaleString(undefined, {
      year: 'numeric', month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  }

  async function handleComplete() {
    completing = true;
    completeError = '';
    const res = await apiPost(apiUrls.complete, { outcome: outcomeText });
    completing = false;
    if (res.ok) {
      window.location.reload();
    } else {
      const d = await res.json().catch(() => ({}));
      completeError = d.detail || d.error || 'Failed to mark complete.';
    }
  }

  async function handleDelete() {
    deleting = true;
    const res = await apiDelete(apiUrls.activityDetail);
    deleting = false;
    if (res.ok) {
      window.location.href = '/activities/';
    } else {
      showDeleteModal = false;
    }
  }
</script>

{#if activity}
<div class="max-w-3xl mx-auto py-8 px-4">
  <!-- Header -->
  <div class="flex items-start justify-between mb-6">
    <div class="flex items-start gap-4">
      {#if activity.activityType}
      <div class="h-12 w-12 rounded-full flex items-center justify-center flex-shrink-0"
        style="background-color: {activity.activityType.color}20;">
        <span class="text-lg" style="color: {activity.activityType.color};">{activity.activityType.icon}</span>
      </div>
      {/if}
      <div>
        <h1 class="text-2xl font-bold text-gray-900">{activity.title}</h1>
        <div class="mt-1">
          <StatusBadge status={activity.status} />
          {#if activity.activityType}
          <span class="ml-2 text-sm text-gray-500">{activity.activityType.name}</span>
          {/if}
        </div>
      </div>
    </div>

    {#if canEdit}
    <div class="flex gap-2 flex-shrink-0">
      <a href="/activities/{activity.id}/edit/"
        class="inline-flex items-center px-3 py-2 text-sm font-medium bg-indigo-600 text-white rounded-md hover:bg-indigo-700">
        Edit
      </a>
      {#if activity.status !== 'completed' && activity.status !== 'cancelled'}
      <button type="button"
        on:click={() => { showCompleteForm = !showCompleteForm; completeError = ''; }}
        class="inline-flex items-center px-3 py-2 text-sm font-medium bg-green-600 text-white rounded-md hover:bg-green-700">
        Complete
      </button>
      {/if}
      <button type="button"
        on:click={() => showDeleteModal = true}
        class="inline-flex items-center px-3 py-2 text-sm font-medium bg-red-600 text-white rounded-md hover:bg-red-700">
        Delete
      </button>
    </div>
    {/if}
  </div>

  <!-- Inline Complete Form -->
  {#if showCompleteForm}
  <div class="mb-6 bg-green-50 border border-green-200 rounded-lg p-4">
    <h3 class="text-sm font-semibold text-green-800 mb-2">Mark as Complete</h3>
    <textarea
      bind:value={outcomeText}
      rows="3"
      placeholder="Add outcome notes (optional)..."
      class="w-full border border-green-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-green-500 focus:border-green-500"
    ></textarea>
    {#if completeError}
    <p class="mt-1 text-sm text-red-600">{completeError}</p>
    {/if}
    <div class="flex gap-2 mt-2">
      <button type="button" on:click={handleComplete} disabled={completing}
        class="px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-md hover:bg-green-700 disabled:opacity-50">
        {completing ? 'Saving...' : 'Mark Complete'}
      </button>
      <button type="button" on:click={() => showCompleteForm = false}
        class="px-4 py-2 border border-gray-300 text-gray-700 text-sm rounded-md hover:bg-gray-50">
        Cancel
      </button>
    </div>
  </div>
  {/if}

  <!-- Detail card -->
  <div class="bg-white shadow rounded-lg overflow-hidden">
    <!-- Info grid -->
    <div class="px-6 py-5 border-b border-gray-200">
      <h2 class="text-base font-semibold text-gray-900 mb-4">Activity Information</h2>
      <dl class="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-4">
        <div>
          <dt class="text-sm font-medium text-gray-500">Scheduled Date</dt>
          <dd class="mt-1 text-sm text-gray-900">{formatDate(activity.scheduledDate)}</dd>
        </div>

        <div>
          <dt class="text-sm font-medium text-gray-500">Status</dt>
          <dd class="mt-1"><StatusBadge status={activity.status} /></dd>
        </div>

        {#if activity.assignedToName}
        <div>
          <dt class="text-sm font-medium text-gray-500">Assigned To</dt>
          <dd class="mt-1 text-sm text-gray-900">{activity.assignedToName}</dd>
        </div>
        {/if}

        {#if activity.leadTitle && activity.leadId}
        <div>
          <dt class="text-sm font-medium text-gray-500">Opportunity</dt>
          <dd class="mt-1 text-sm">
            <a href="/crm/opportunities/{activity.leadId}/edit/"
              class="text-indigo-600 hover:text-indigo-800">{activity.leadTitle}</a>
          </dd>
        </div>
        {/if}

        {#if activity.createdByName}
        <div>
          <dt class="text-sm font-medium text-gray-500">Created By</dt>
          <dd class="mt-1 text-sm text-gray-900">{activity.createdByName}</dd>
        </div>
        {/if}

        <div>
          <dt class="text-sm font-medium text-gray-500">Created At</dt>
          <dd class="mt-1 text-sm text-gray-900">{formatDate(activity.createdAt)}</dd>
        </div>

        {#if activity.completedDate}
        <div class="sm:col-span-2">
          <dt class="text-sm font-medium text-gray-500">Completed At</dt>
          <dd class="mt-1 text-sm text-gray-900">{formatDate(activity.completedDate)}</dd>
        </div>
        {/if}

        {#if activity.description}
        <div class="sm:col-span-2">
          <dt class="text-sm font-medium text-gray-500">Description</dt>
          <dd class="mt-1 text-sm text-gray-900 whitespace-pre-line">{activity.description}</dd>
        </div>
        {/if}
      </dl>
    </div>

    <!-- Outcome section -->
    {#if activity.outcome}
    <div class="px-6 py-5 border-b border-gray-200">
      <h2 class="text-base font-semibold text-gray-900 mb-2">Outcome</h2>
      <p class="text-sm text-gray-900 whitespace-pre-line">{activity.outcome}</p>
    </div>
    {/if}
  </div>

  <!-- Back link -->
  <div class="mt-4">
    <button type="button" on:click={() => history.back()}
      class="text-sm text-gray-500 hover:text-gray-700">
      &larr; Back
    </button>
  </div>
</div>

<!-- Delete confirmation modal -->
{#if showDeleteModal}
<ConfirmModal
  title="Delete Activity"
  message="Are you sure you want to delete this activity? This action cannot be undone."
  confirmLabel="Delete"
  cancelLabel="Cancel"
  danger={true}
  loading={deleting}
  onConfirm={handleDelete}
  onCancel={() => showDeleteModal = false}
/>
{/if}

{:else}
<div class="max-w-3xl mx-auto py-16 px-4 text-center text-gray-500">
  Activity not found.
</div>
{/if}
