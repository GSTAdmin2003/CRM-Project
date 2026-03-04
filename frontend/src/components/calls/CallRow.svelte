<script>
  export let call = {};
  export let apiUrls = {};

  function navigate() {
    const url = apiUrls.callDetail.replace('{id}', call.id);
    if (typeof window.crmNavigate === 'function') {
      window.crmNavigate(url);
    } else {
      window.location.href = url;
    }
  }

  const STATUS_BADGE = {
    initiated: 'bg-yellow-100 text-yellow-800',
    ringing: 'bg-blue-100 text-blue-800',
    answered: 'bg-green-100 text-green-800',
    ended: 'bg-gray-100 text-gray-600',
    failed: 'bg-red-100 text-red-800',
    busy: 'bg-orange-100 text-orange-800',
    no_answer: 'bg-gray-100 text-gray-500',
  };

  const DIRECTION_ICON = {
    inbound: '↙',
    outbound: '↗',
  };

  function formatDuration(secs) {
    if (!secs) return '—';
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return m > 0 ? `${m}m ${s}s` : `${s}s`;
  }
</script>

<tr
  class="hover:bg-gray-50 cursor-pointer transition-colors border-b border-gray-100 last:border-b-0"
  on:click={navigate}
>
  <td class="px-4 py-3">
    <span
      class="text-sm font-medium {call.direction === 'inbound' ? 'text-green-600' : 'text-blue-600'}"
      title={call.direction}
    >
      {DIRECTION_ICON[call.direction] || '—'}
    </span>
  </td>
  <td class="px-4 py-3">
    <p class="text-sm text-gray-900">{call.from_number || '—'}</p>
  </td>
  <td class="px-4 py-3">
    <p class="text-sm text-gray-900">{call.to_number || '—'}</p>
  </td>
  <td class="px-4 py-3">
    <span class="text-xs px-2 py-0.5 rounded-full font-medium {STATUS_BADGE[call.status] || 'bg-gray-100 text-gray-600'}">
      {call.status?.replace('_', ' ') || '—'}
    </span>
  </td>
  <td class="px-4 py-3 text-sm text-gray-600">{formatDuration(call.duration)}</td>
  <td class="px-4 py-3 text-sm text-gray-600">{call.user_name || '—'}</td>
  <td class="px-4 py-3 text-xs text-gray-400">
    {call.started_at ? new Date(call.started_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' }) : '—'}
  </td>
  <td class="px-4 py-3 text-center">
    {#if call.has_recording}
      <svg class="w-4 h-4 text-indigo-500 inline" fill="currentColor" viewBox="0 0 24 24">
        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 14.5v-9l6 4.5-6 4.5z"/>
      </svg>
    {/if}
  </td>
</tr>
