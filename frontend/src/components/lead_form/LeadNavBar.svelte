<script>
  export let prevLeadId = null;
  export let nextLeadId = null;
  export let navParams = '';
  export let currentIndex = 0;
  export let totalCount = 0;

  function navigate(leadId) {
    if (!leadId) return;
    // Only use navParams if it's a proper query string; guard against stale/invalid values.
    const qs = (typeof navParams === 'string' && navParams.startsWith('?')) ? navParams : '';
    window.crmNavigate(`/crm/opportunities/${leadId}/edit/${qs}`);
  }
</script>

<div class="flex items-center gap-2 text-sm text-gray-500">
  <button
    type="button"
    class="p-1.5 rounded hover:bg-gray-100 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
    disabled={!prevLeadId}
    on:click={() => navigate(prevLeadId)}
    title="Previous"
  >
    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
    </svg>
  </button>

  {#if totalCount > 0}
    <span class="font-medium text-gray-700">{currentIndex} / {totalCount}</span>
  {/if}

  <button
    type="button"
    class="p-1.5 rounded hover:bg-gray-100 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
    disabled={!nextLeadId}
    on:click={() => navigate(nextLeadId)}
    title="Next"
  >
    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
    </svg>
  </button>
</div>
