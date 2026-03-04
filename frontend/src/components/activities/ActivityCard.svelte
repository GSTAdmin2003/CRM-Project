<script>
  import { apiPost } from '../../utils/api.js';

  export let activity = {};
  export let apiUrls = {};
  export let onCompleted = () => {};

  let completing = false;

  const STATUS_COLOR = {
    planned: 'bg-blue-100 text-blue-800 border-blue-200',
    completed: 'bg-green-100 text-green-800 border-green-200',
    cancelled: 'bg-gray-100 text-gray-500 border-gray-200',
  };

  const STATUS_DOT = {
    planned: 'bg-blue-400',
    completed: 'bg-green-400',
    cancelled: 'bg-gray-400',
  };

  async function markComplete() {
    if (completing || activity.status === 'completed') return;
    completing = true;
    try {
      const res = await apiPost(`${apiUrls.activities}${activity.id}/complete/`, {});
      if (res.ok) onCompleted(activity.id);
    } catch {
      // Ignore
    } finally {
      completing = false;
    }
  }

  $: isOverdue =
    activity.status === 'planned' &&
    activity.scheduled_date &&
    new Date(activity.scheduled_date) < new Date(new Date().toDateString());
</script>

<div
  class="bg-white border rounded-lg px-4 py-3 flex items-start gap-3 hover:border-gray-300 transition-colors
    {isOverdue ? 'border-red-200 bg-red-50/30' : 'border-gray-200'}"
>
  <!-- Icon -->
  <div
    class="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 text-sm"
    style="background-color: {activity.activity_type_color || '#e5e7eb'}20; color: {activity.activity_type_color || '#6b7280'}"
  >
    <i class="text-xs {activity.activity_type_icon || 'fas fa-tasks'}"></i>
  </div>

  <!-- Content -->
  <div class="flex-1 min-w-0">
    <div class="flex items-start justify-between gap-2">
      <div class="flex-1 min-w-0">
        <p class="text-sm font-medium text-gray-900 truncate">{activity.title}</p>
        {#if activity.lead_title}
          <p class="text-xs text-indigo-600 truncate">{activity.lead_title}</p>
        {/if}
      </div>
      <span class="flex-shrink-0 flex items-center gap-1 text-xs px-2 py-0.5 rounded-full border font-medium {STATUS_COLOR[activity.status] || 'bg-gray-100 text-gray-600 border-gray-200'}">
        <span class="w-1.5 h-1.5 rounded-full {STATUS_DOT[activity.status] || 'bg-gray-400'}"></span>
        {activity.status}
      </span>
    </div>
    <div class="flex items-center gap-3 mt-1 text-xs text-gray-400">
      {#if activity.scheduled_date}
        <span class="{isOverdue ? 'text-red-500 font-medium' : ''}">
          {new Date(activity.scheduled_date).toLocaleDateString()}
          {#if isOverdue}<span class="ml-1">Overdue</span>{/if}
        </span>
      {/if}
      {#if activity.assigned_to_name}
        <span>{activity.assigned_to_name}</span>
      {/if}
    </div>
  </div>

  <!-- Complete button -->
  {#if activity.status === 'planned'}
    <button
      type="button"
      class="flex-shrink-0 w-7 h-7 rounded-full border-2 border-gray-200 hover:border-green-400 hover:bg-green-50 flex items-center justify-center transition-colors disabled:opacity-50"
      disabled={completing}
      on:click={markComplete}
      title="Mark complete"
    >
      {#if completing}
        <svg class="w-3 h-3 animate-spin text-gray-400" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
        </svg>
      {:else}
        <svg class="w-3.5 h-3.5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
        </svg>
      {/if}
    </button>
  {:else if activity.status === 'completed'}
    <div class="flex-shrink-0 w-7 h-7 rounded-full bg-green-100 border-2 border-green-400 flex items-center justify-center">
      <svg class="w-3.5 h-3.5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
      </svg>
    </div>
  {/if}
</div>
