<script>
  export let logs = [];

  function formatTime(ts) {
    if (!ts) return '';
    return new Date(ts).toLocaleTimeString();
  }
</script>

{#if logs.length > 0}
<div class="bg-white rounded-lg shadow p-4">
  <h3 class="text-base font-semibold text-gray-900 mb-3">Event Log</h3>
  <div class="space-y-1 max-h-48 overflow-y-auto">
    {#each logs as log}
      <div class="flex items-start gap-3 text-sm">
        <span class="text-gray-400 whitespace-nowrap text-xs font-mono">{formatTime(log.timestamp)}</span>
        <span class="text-gray-600 font-medium">{log.event}</span>
        {#if log.data && Object.keys(log.data).length > 0}
          <span class="text-gray-400 text-xs">{JSON.stringify(log.data)}</span>
        {/if}
      </div>
    {/each}
  </div>
</div>
{/if}
