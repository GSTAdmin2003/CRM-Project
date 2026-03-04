<script>
  import { apiGet } from '../../utils/api.js';
  import { onMount } from 'svelte';
  import LeadRow from './LeadRow.svelte';

  export let isExecutive = false;
  export let isManager = false;
  export let teams = [];
  export let statusChoices = [];
  export let apiUrls = {};

  let leads = [];
  let loading = true;
  let error = '';
  let totalCount = 0;
  let page = 1;
  let pageSize = 25;

  // Filters
  let statusFilter = '';
  let teamFilter = '';
  let searchQuery = '';

  // Bulk selection
  let selectedIds = new Set();
  let searchTimeout = null;

  $: totalPages = Math.ceil(totalCount / pageSize);
  $: allSelected = leads.length > 0 && leads.every((l) => selectedIds.has(l.id));

  onMount(async () => {
    await fetchLeads();
  });

  $: {
    if (searchTimeout) clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      page = 1;
      fetchLeads();
    }, 300);
  }

  async function fetchLeads() {
    loading = true;
    error = '';
    const params = new URLSearchParams({ lead_type: 'lead', page: String(page) });
    if (statusFilter) params.set('status', statusFilter);
    if (teamFilter) params.set('sales_team', teamFilter);
    if (searchQuery) params.set('search', searchQuery);

    try {
      const res = await apiGet(`${apiUrls.leads}?${params}`);
      if (res.ok) {
        const data = await res.json();
        leads = data.results || data;
        totalCount = data.count ?? leads.length;
        selectedIds = new Set(); // reset selection on reload
      } else {
        error = 'Failed to load leads';
      }
    } catch {
      error = 'Failed to load leads';
    } finally {
      loading = false;
    }
  }

  function handleConverted(leadId) {
    leads = leads.filter((l) => l.id !== leadId);
    totalCount = Math.max(0, totalCount - 1);
    selectedIds.delete(leadId);
    selectedIds = new Set(selectedIds);
  }

  function toggleSelectAll() {
    if (allSelected) {
      selectedIds = new Set();
    } else {
      selectedIds = new Set(leads.map((l) => l.id));
    }
  }

  function isSelected(id) {
    return selectedIds.has(id);
  }

  function setSelected(id, val) {
    if (val) selectedIds.add(id);
    else selectedIds.delete(id);
    selectedIds = new Set(selectedIds);
  }

  async function prevPage() {
    if (page > 1) { page -= 1; await fetchLeads(); }
  }
  async function nextPage() {
    if (page < totalPages) { page += 1; await fetchLeads(); }
  }
</script>

<div class="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
  <!-- Header -->
  <div class="flex items-center justify-between mb-6">
    <div>
      <h1 class="text-3xl font-bold text-gray-900">Leads</h1>
      <p class="text-sm text-gray-500 mt-1">Incoming lead captures and inquiries</p>
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
      <a
        href="/crm/leads/create/"
        class="px-4 py-2 bg-indigo-600 text-white rounded-md text-sm font-medium hover:bg-indigo-700 transition-colors"
      >
        Add Lead
      </a>
    </div>
  </div>

  <!-- Filters -->
  <div class="flex flex-wrap gap-2 mb-4">
    <input
      type="text"
      bind:value={searchQuery}
      placeholder="Search leads…"
      class="border border-gray-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 min-w-48"
    />
    <select
      bind:value={statusFilter}
      on:change={() => { page = 1; fetchLeads(); }}
      class="border border-gray-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
    >
      <option value="">All statuses</option>
      {#each statusChoices as [val, label]}
        <option value={val}>{label}</option>
      {/each}
    </select>
    {#if isExecutive && teams.length > 0}
      <select
        bind:value={teamFilter}
        on:change={() => { page = 1; fetchLeads(); }}
        class="border border-gray-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        <option value="">All teams</option>
        {#each teams as team}
          <option value={team.id}>{team.name}</option>
        {/each}
      </select>
    {/if}
  </div>

  <!-- Bulk actions -->
  {#if selectedIds.size > 0}
    <div class="mb-3 px-4 py-2 bg-indigo-50 border border-indigo-200 rounded-lg flex items-center gap-3 text-sm">
      <span class="font-medium text-indigo-800">{selectedIds.size} selected</span>
      <span class="text-indigo-400">|</span>
      <button type="button" class="text-indigo-600 hover:text-indigo-800 font-medium">Bulk convert</button>
    </div>
  {/if}

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
      <p class="text-center py-16 text-gray-400 text-sm">No leads found.</p>
    {:else}
      <table class="w-full">
        <thead>
          <tr class="bg-gray-50 border-b border-gray-200 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
            <th class="px-4 py-3 w-8">
              <input
                type="checkbox"
                checked={allSelected}
                on:change={toggleSelectAll}
                class="rounded border-gray-300"
              />
            </th>
            <th class="px-4 py-3">Lead</th>
            <th class="px-4 py-3">Assigned To</th>
            <th class="px-4 py-3">Message</th>
            <th class="px-4 py-3">Status</th>
            <th class="px-4 py-3">Created</th>
            <th class="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody>
          {#each leads as lead (lead.id)}
            <LeadRow
              {lead}
              {apiUrls}
              isSelected={isSelected(lead.id)}
              onConverted={handleConverted}
              on:selectionChange={(e) => setSelected(lead.id, e.detail)}
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
