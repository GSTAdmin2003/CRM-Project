<script>
  import { createEventDispatcher } from 'svelte';
  export let opportunity;
  export let apiUrls;

  const dispatch = createEventDispatcher();

  let searching = false;
  let query = '';
  let results = [];
  let linking = false;

  async function search() {
    if (!query.trim()) return;
    searching = true;
    const res = await fetch(`${apiUrls.leads}?search=${encodeURIComponent(query)}&type=opportunity&limit=10`);
    if (res.ok) {
      const data = await res.json();
      results = data.results ?? data;
    }
    searching = false;
  }

  async function linkOpportunity(id, title) {
    linking = true;
    const fd = new FormData();
    fd.append('opportunity_id', id);
    const res = await fetch(apiUrls.linkOpportunity, {
      method: 'POST',
      headers: { 'X-CSRFToken': getCsrf() },
      body: fd,
    });
    linking = false;
    if (res.ok) {
      dispatch('linked', { id, title });
      query = '';
      results = [];
    }
  }

  function getCsrf() {
    const m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? m[1] : '';
  }
</script>

<div class="bg-white rounded-lg shadow p-4">
  <h3 class="text-base font-semibold text-gray-900 mb-3">Opportunity</h3>
  {#if opportunity}
    <div class="flex items-center gap-2">
      <span class="text-gray-700 text-sm">{opportunity.title}</span>
      <a href="/crm/opportunities/{opportunity.id}/" class="text-xs text-indigo-600 hover:underline">View</a>
    </div>
  {:else}
    <p class="text-sm text-gray-400 mb-3">No opportunity linked.</p>
    <div class="flex gap-2">
      <input
        bind:value={query}
        on:keydown={(e) => e.key === 'Enter' && search()}
        class="flex-1 border border-gray-300 rounded px-2 py-1 text-sm"
        placeholder="Search opportunities…"
      />
      <button on:click={search} class="text-sm bg-gray-100 px-3 py-1 rounded border border-gray-300 hover:bg-gray-200">
        {searching ? '…' : 'Search'}
      </button>
    </div>
    {#if results.length > 0}
      <ul class="mt-2 border rounded divide-y text-sm">
        {#each results as r}
          <li class="flex items-center justify-between px-3 py-2">
            <span>{r.title}</span>
            <button
              on:click={() => linkOpportunity(r.id, r.title)}
              disabled={linking}
              class="text-xs text-indigo-600 hover:underline disabled:opacity-50"
            >
              Link
            </button>
          </li>
        {/each}
      </ul>
    {/if}
  {/if}
</div>
