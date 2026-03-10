<script>
  import { apiPost, apiPatch } from '../../utils/api.js';

  export let activity = null;
  export let activityTypes = [];
  export let leadId = null;
  export let apiUrls = {};

  let title = activity?.title ?? '';
  let description = activity?.description ?? '';
  let scheduledDate = activity?.scheduledDate ? activity.scheduledDate.slice(0, 16) : '';
  let activityTypeId = activity?.activityTypeId ?? (activityTypes[0]?.id ?? '');
  let status = activity?.status ?? 'planned';
  let saving = false;
  let errors = {};

  async function submit(e) {
    e.preventDefault();
    saving = true;
    errors = {};
    const body = {
      title,
      description,
      scheduled_date: scheduledDate || null,
      activity_type: activityTypeId,
      lead: activity?.leadId ?? leadId,
      status,
    };
    const res = activity
      ? await apiPatch(`${apiUrls.activities}${activity.id}/`, body)
      : await apiPost(apiUrls.activities, body);
    saving = false;
    if (res.ok) {
      window.location.href = '/activities/';
    } else {
      const d = await res.json().catch(() => ({}));
      errors = d;
    }
  }
</script>

<div class="max-w-2xl mx-auto py-8 px-4">
  <h1 class="text-2xl font-semibold text-gray-900 mb-6">
    {activity ? 'Edit Activity' : 'Create Activity'}
  </h1>

  <form on:submit={submit} class="space-y-6 bg-white shadow rounded-lg p-6">
    <div>
      <label class="block text-sm font-medium text-gray-700">Title *</label>
      <input type="text" bind:value={title} required
        class="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500">
      {#if errors.title}<p class="mt-1 text-sm text-red-600">{errors.title}</p>{/if}
    </div>

    <div>
      <label class="block text-sm font-medium text-gray-700">Activity Type</label>
      <select bind:value={activityTypeId}
        class="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2">
        {#each activityTypes as t}
          <option value={t.id}>{t.name}</option>
        {/each}
      </select>
    </div>

    <div>
      <label class="block text-sm font-medium text-gray-700">Scheduled Date</label>
      <input type="datetime-local" bind:value={scheduledDate}
        class="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2">
    </div>

    <div>
      <label class="block text-sm font-medium text-gray-700">Description</label>
      <textarea bind:value={description} rows="4"
        class="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"></textarea>
    </div>

    {#if activity}
    <div>
      <label class="block text-sm font-medium text-gray-700">Status</label>
      <select bind:value={status}
        class="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2">
        <option value="planned">Planned</option>
        <option value="in_progress">In Progress</option>
        <option value="completed">Completed</option>
        <option value="cancelled">Cancelled</option>
      </select>
    </div>
    {/if}

    <div class="flex gap-3 pt-2">
      <button type="submit" disabled={saving}
        class="flex-1 bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50">
        {saving ? 'Saving...' : (activity ? 'Save Changes' : 'Create Activity')}
      </button>
      <button type="button" on:click={() => history.back()}
        class="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50">
        Cancel
      </button>
    </div>
  </form>
</div>
