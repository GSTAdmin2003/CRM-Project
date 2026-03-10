<script>
  import { apiPost } from '../../utils/api.js';
  export let call;
  export let apiUrls;

  async function hangup() {
    await apiPost(apiUrls.hangup, {});
    window.location.reload();
  }
</script>

<div class="bg-white shadow rounded-lg p-6">
  <div class="flex items-center justify-between mb-4">
    <h2 class="text-lg font-medium text-gray-900">Call Information</h2>
    <div class="flex gap-2">
      <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
        {call.direction === 'inbound' ? 'bg-blue-100 text-blue-800' : 'bg-purple-100 text-purple-800'}">
        {call.direction}
      </span>
      <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
        {call.status}
      </span>
    </div>
  </div>
  <dl class="grid grid-cols-2 gap-4 text-sm">
    <div><dt class="text-gray-500">From</dt><dd class="font-mono">{call.from_number}</dd></div>
    <div><dt class="text-gray-500">To</dt><dd class="font-mono">{call.to_number}</dd></div>
    <div><dt class="text-gray-500">Agent</dt><dd>{call.user_name || '—'}</dd></div>
    <div><dt class="text-gray-500">Duration</dt><dd>{call.duration_formatted || '—'}</dd></div>
    {#if call.started_at}
    <div><dt class="text-gray-500">Started</dt><dd>{new Date(call.started_at).toLocaleString()}</dd></div>
    {/if}
    {#if call.ended_at}
    <div><dt class="text-gray-500">Ended</dt><dd>{new Date(call.ended_at).toLocaleString()}</dd></div>
    {/if}
  </dl>
  {#if call.status === 'ringing' || call.status === 'answered'}
  <button on:click={hangup} class="mt-4 px-3 py-1 bg-red-600 text-white rounded text-sm hover:bg-red-700">
    Hang Up
  </button>
  {/if}
</div>
