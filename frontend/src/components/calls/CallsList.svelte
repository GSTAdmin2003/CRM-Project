<script>
  import { apiGet } from '../../utils/api.js';
  import { onMount } from 'svelte';
  import CallRow from './CallRow.svelte';

  export let isManager = false;
  export let isExecutive = false;
  export let apiUrls = {};

  let calls = [];
  let loading = true;
  let error = '';
  let page = 1;
  let totalCount = 0;
  let pageSize = 25;

  // Filters
  let direction = '';
  let status = '';
  let search = '';
  let startDate = '';
  let endDate = '';

  let searchTimeout = null;
  $: totalPages = Math.ceil(totalCount / pageSize);

  onMount(async () => {
    await fetchCalls();
  });

  $: {
    if (searchTimeout) clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      page = 1;
      fetchCalls();
    }, 300);
  }

  async function fetchCalls() {
    loading = true;
    error = '';
    const params = new URLSearchParams({ page: String(page) });
    if (direction) params.set('direction', direction);
    if (status) params.set('status', status);
    if (search) params.set('search', search);
    if (startDate) params.set('started_at__date__gte', startDate);
    if (endDate) params.set('started_at__date__lte', endDate);

    try {
      const res = await apiGet(`${apiUrls.calls}?${params}`);
      if (res.ok) {
        const data = await res.json();
        calls = data.results || data;
        totalCount = data.count ?? calls.length;
      } else {
        error = 'Failed to load calls';
      }
    } catch {
      error = 'Failed to load calls';
    } finally {
      loading = false;
    }
  }

  async function prevPage() {
    if (page > 1) { page -= 1; await fetchCalls(); }
  }
  async function nextPage() {
    if (page < totalPages) { page += 1; await fetchCalls(); }
  }

  const STATUS_OPTIONS = ['', 'initiated', 'ringing', 'answered', 'ended', 'failed', 'busy', 'no_answer'];
</script>

<div class="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
  <div class="flex items-center justify-between mb-6">
    <div>
      <h1 class="text-3xl font-bold text-gray-900">Calls</h1>
      <p class="text-sm text-gray-500 mt-1">Call history and recordings</p>
    </div>
  </div>

  <!-- Filters -->
  <div class="flex flex-wrap gap-2 mb-4">
    <input
      type="text"
      bind:value={search}
      placeholder="Search number…"
      class="border border-gray-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 min-w-40"
    />

    <select
      bind:value={direction}
      on:change={() => { page = 1; fetchCalls(); }}
      class="border border-gray-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
    >
      <option value="">All directions</option>
      <option value="inbound">Inbound ↙</option>
      <option value="outbound">Outbound ↗</option>
    </select>

    <select
      bind:value={status}
      on:change={() => { page = 1; fetchCalls(); }}
      class="border border-gray-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
    >
      <option value="">All statuses</option>
      {#each STATUS_OPTIONS.filter(Boolean) as s}
        <option value={s}>{s.replace('_', ' ')}</option>
      {/each}
    </select>

    <input
      type="date"
      bind:value={startDate}
      on:change={() => { page = 1; fetchCalls(); }}
      class="border border-gray-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      title="From date"
    />
    <input
      type="date"
      bind:value={endDate}
      on:change={() => { page = 1; fetchCalls(); }}
      class="border border-gray-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      title="To date"
    />
  </div>

  <!-- Table -->
  <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
    {#if loading}
      <div class="flex items-center justify-center py-16 text-gray-400">
        <svg class="w-5 h-5 animate-spin mr-2" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
        </svg>
        Loading…
      </div>
    {:else if error}
      <p class="text-center py-10 text-red-500 text-sm">{error}</p>
    {:else if calls.length === 0}
      <p class="text-center py-16 text-gray-400 text-sm">No calls found.</p>
    {:else}
      <table class="w-full">
        <thead>
          <tr class="bg-gray-50 border-b border-gray-200 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
            <th class="px-4 py-3">Dir</th>
            <th class="px-4 py-3">From</th>
            <th class="px-4 py-3">To</th>
            <th class="px-4 py-3">Status</th>
            <th class="px-4 py-3">Duration</th>
            <th class="px-4 py-3">Agent</th>
            <th class="px-4 py-3">Started</th>
            <th class="px-4 py-3 text-center">Rec</th>
          </tr>
        </thead>
        <tbody>
          {#each calls as call (call.id)}
            <CallRow {call} {apiUrls} />
          {/each}
        </tbody>
      </table>

      <!-- Pagination -->
      {#if totalPages > 1}
        <div class="flex items-center justify-between px-4 py-3 border-t border-gray-100 text-sm text-gray-500">
          <span>{totalCount} total</span>
          <div class="flex items-center gap-2">
            <button
              type="button"
              class="px-3 py-1 border border-gray-200 rounded hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
              disabled={page === 1}
              on:click={prevPage}
            >Prev</button>
            <span>{page} / {totalPages}</span>
            <button
              type="button"
              class="px-3 py-1 border border-gray-200 rounded hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
              disabled={page >= totalPages}
              on:click={nextPage}
            >Next</button>
          </div>
        </div>
      {/if}
    {/if}
  </div>
</div>
