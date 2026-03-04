<script>
  import { apiGet } from '../../utils/api.js';
  import { onMount } from 'svelte';
  import OpportunityFilters from './OpportunityFilters.svelte';
  import OpportunityRow from './OpportunityRow.svelte';

  export let isManager = false;
  export let isExecutive = false;
  export let stages = [];
  export let teams = [];
  export let apiUrls = {};

  let leads = [];
  let loading = true;
  let error = '';
  let page = 1;
  let totalCount = 0;
  let pageSize = 25;

  let filters = {
    stage_id: '',
    status: '',
    team_id: '',
    search: '',
  };

  let searchTimeout = null;

  $: totalPages = Math.ceil(totalCount / pageSize);

  onMount(async () => {
    await fetchLeads();
  });

  $: {
    // Re-fetch when filters change (debounce search)
    if (searchTimeout) clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      page = 1;
      fetchLeads();
    }, 300);
  }

  async function fetchLeads() {
    loading = true;
    error = '';
    const params = new URLSearchParams({
      lead_type: 'opportunity',
      page: String(page),
    });
    if (filters.stage_id) params.set('stage', filters.stage_id);
    if (filters.status) params.set('status', filters.status);
    if (filters.team_id) params.set('sales_team', filters.team_id);
    if (filters.search) params.set('search', filters.search);

    try {
      const res = await apiGet(`${apiUrls.leads}?${params}`);
      if (res.ok) {
        const data = await res.json();
        leads = data.results || data;
        totalCount = data.count ?? leads.length;
      } else {
        error = 'Failed to load opportunities';
      }
    } catch {
      error = 'Failed to load opportunities';
    } finally {
      loading = false;
    }
  }

  function handleDeleted(leadId) {
    leads = leads.filter((l) => l.id !== leadId);
    totalCount = Math.max(0, totalCount - 1);
  }

  async function prevPage() {
    if (page > 1) { page -= 1; await fetchLeads(); }
  }
  async function nextPage() {
    if (page < totalPages) { page += 1; await fetchLeads(); }
  }

  function navigateCreate() {
    if (typeof window.crmNavigate === 'function') {
      window.crmNavigate('/crm/opportunities/create/');
    } else {
      window.location.href = '/crm/opportunities/create/';
    }
  }
</script>

<div class="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
  <!-- Header -->
  <div class="flex items-center justify-between mb-6">
    <div>
      <h1 class="text-3xl font-bold text-gray-900">Opportunities</h1>
      <p class="text-sm text-gray-500 mt-1">Sales pipeline and opportunity tracking</p>
    </div>
    <div class="flex gap-2">
      <a
        href="/crm/opportunities/import/"
        class="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-md text-sm font-medium hover:bg-green-700 transition-colors"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"/>
        </svg>
        Import
      </a>
      <button
        type="button"
        class="px-4 py-2 bg-indigo-600 text-white rounded-md text-sm font-medium hover:bg-indigo-700 transition-colors"
        on:click={navigateCreate}
      >
        Add Opportunity
      </button>
    </div>
  </div>

  <!-- Filters -->
  <OpportunityFilters
    bind:filters
    {stages}
    {teams}
    {isExecutive}
  />

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
    {:else if leads.length === 0}
      <p class="text-center py-16 text-gray-400 text-sm">No opportunities found.</p>
    {:else}
      <table class="w-full">
        <thead>
          <tr class="bg-gray-50 border-b border-gray-200 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
            <th class="px-4 py-3">Opportunity</th>
            <th class="px-4 py-3">Stage</th>
            <th class="px-4 py-3">Assigned To</th>
            <th class="px-4 py-3">Value</th>
            <th class="px-4 py-3">Status</th>
            <th class="px-4 py-3">Created</th>
            <th class="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody>
          {#each leads as lead (lead.id)}
            <OpportunityRow
              {lead}
              {apiUrls}
              onDeleted={handleDeleted}
            />
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
