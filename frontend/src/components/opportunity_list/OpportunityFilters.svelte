<script>
  export let stages = [];
  export let teams = [];
  export let isExecutive = false;

  export let filters = {
    stage_id: '',
    status: '',
    team_id: '',
    search: '',
  };

  const STATUS_OPTIONS = [
    ['', 'All statuses'],
    ['new', 'New'],
    ['contacted', 'Contacted'],
    ['qualified', 'Qualified'],
    ['proposal', 'Proposal Sent'],
    ['negotiation', 'In Negotiation'],
    ['won', 'Won'],
    ['lost', 'Lost'],
    ['on_hold', 'On Hold'],
  ];
</script>

<div class="flex flex-wrap gap-2 mb-4 items-center">
  <input
    type="text"
    bind:value={filters.search}
    placeholder="Search opportunities…"
    class="border border-gray-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 min-w-48"
  />

  <select
    bind:value={filters.stage_id}
    class="border border-gray-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
  >
    <option value="">All stages</option>
    {#each stages as stage}
      <option value={stage.id}>{stage.name}</option>
    {/each}
  </select>

  <select
    bind:value={filters.status}
    class="border border-gray-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
  >
    {#each STATUS_OPTIONS as [val, label]}
      <option value={val}>{label}</option>
    {/each}
  </select>

  {#if isExecutive && teams.length > 0}
    <select
      bind:value={filters.team_id}
      class="border border-gray-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
    >
      <option value="">All teams</option>
      {#each teams as team}
        <option value={team.id}>{team.name}</option>
      {/each}
    </select>
  {/if}
</div>
