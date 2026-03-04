<script>
  import { apiGet } from '../../utils/api.js';
  import { onMount } from 'svelte';
  import ActivityCard from './ActivityCard.svelte';
  import ActivityCreateModal from './ActivityCreateModal.svelte';

  export let isManager = false;
  export let isExecutive = false;
  export let userTeamId = null;
  export let availableTeams = [];
  export let activityTypes = [];
  export let apiUrls = {};

  let activities = [];
  let loading = true;
  let error = '';
  let showModal = false;

  // Filter state
  let viewContext = 'personal';
  let selectedTeam = 'all';
  let dateFilter = 'week';
  let customDate = '';
  let startDate = '';
  let endDate = '';
  let statusFilter = '';

  $: canSeeTeam = isManager || isExecutive;

  onMount(async () => {
    await fetchActivities();
  });

  async function fetchActivities() {
    loading = true;
    error = '';
    const params = new URLSearchParams({
      view: viewContext,
      filter: dateFilter,
    });
    if (selectedTeam !== 'all') params.set('team', selectedTeam);
    if (dateFilter === 'custom' && customDate) params.set('date', customDate);
    if (dateFilter === 'range') {
      if (startDate) params.set('start_date', startDate);
      if (endDate) params.set('end_date', endDate);
    }
    if (statusFilter) params.set('status', statusFilter);

    try {
      const res = await apiGet(`${apiUrls.activities}?${params}`);
      if (res.ok) {
        const data = await res.json();
        activities = data.results || data;
      } else {
        error = 'Failed to load activities';
      }
    } catch {
      error = 'Failed to load activities';
    } finally {
      loading = false;
    }
  }

  function handleCompleted(activityId) {
    activities = activities.map((a) =>
      a.id === activityId ? { ...a, status: 'completed' } : a
    );
  }

  function handleCreated(newActivity) {
    activities = [newActivity, ...activities];
  }

  const DATE_FILTER_OPTIONS = [
    ['today', 'Today'],
    ['week', 'This Week'],
    ['next_week', 'Next Week'],
    ['future', 'Future'],
    ['past', 'Past'],
    ['custom', 'Custom Date'],
    ['range', 'Date Range'],
  ];
</script>

<div class="max-w-4xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
  <!-- Header -->
  <div class="flex items-center justify-between mb-6">
    <div>
      <h1 class="text-3xl font-bold text-gray-900">Activities</h1>
      <p class="text-sm text-gray-500 mt-1">Track and manage your scheduled activities</p>
    </div>
    <button
      type="button"
      class="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors"
      on:click={() => (showModal = true)}
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
      </svg>
      New Activity
    </button>
  </div>

  <!-- Filters row -->
  <div class="flex flex-wrap gap-2 mb-4">
    <!-- View switcher -->
    {#if canSeeTeam}
      <div class="flex border border-gray-200 rounded-lg overflow-hidden text-sm">
        <button
          type="button"
          class="px-3 py-1.5 transition-colors {viewContext === 'personal' ? 'bg-indigo-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}"
          on:click={() => { viewContext = 'personal'; fetchActivities(); }}
        >My Activities</button>
        <button
          type="button"
          class="px-3 py-1.5 border-l border-gray-200 transition-colors {viewContext === 'team' ? 'bg-indigo-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}"
          on:click={() => { viewContext = 'team'; fetchActivities(); }}
        >Team View</button>
      </div>
    {/if}

    <!-- Date filter -->
    <select
      bind:value={dateFilter}
      on:change={fetchActivities}
      class="border border-gray-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
    >
      {#each DATE_FILTER_OPTIONS as [val, label]}
        <option value={val}>{label}</option>
      {/each}
    </select>

    {#if dateFilter === 'custom'}
      <input
        type="date"
        bind:value={customDate}
        on:change={fetchActivities}
        class="border border-gray-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
    {/if}

    {#if dateFilter === 'range'}
      <input
        type="date"
        bind:value={startDate}
        on:change={fetchActivities}
        class="border border-gray-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
      <span class="self-center text-gray-400 text-sm">to</span>
      <input
        type="date"
        bind:value={endDate}
        on:change={fetchActivities}
        class="border border-gray-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
    {/if}

    <!-- Status filter -->
    <select
      bind:value={statusFilter}
      on:change={fetchActivities}
      class="border border-gray-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
    >
      <option value="">All statuses</option>
      <option value="planned">Planned</option>
      <option value="completed">Completed</option>
      <option value="cancelled">Cancelled</option>
    </select>

    <!-- Team selector (team view + executive) -->
    {#if viewContext === 'team' && isExecutive && availableTeams.length > 0}
      <select
        bind:value={selectedTeam}
        on:change={fetchActivities}
        class="border border-gray-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        <option value="all">All teams</option>
        {#each availableTeams as team}
          <option value={team.id}>{team.name}</option>
        {/each}
      </select>
    {/if}
  </div>

  <!-- Activity list -->
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
  {:else if activities.length === 0}
    <div class="text-center py-16 text-gray-400">
      <svg class="w-10 h-10 mx-auto mb-3 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
          d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
      </svg>
      <p class="text-sm">No activities for this period.</p>
      <button
        type="button"
        class="mt-3 text-sm text-indigo-600 hover:text-indigo-800 font-medium"
        on:click={() => (showModal = true)}
      >Create your first activity</button>
    </div>
  {:else}
    <div class="space-y-2">
      {#each activities as activity (activity.id)}
        <ActivityCard
          {activity}
          {apiUrls}
          onCompleted={handleCompleted}
        />
      {/each}
    </div>
  {/if}
</div>

<!-- Create modal -->
<ActivityCreateModal
  bind:show={showModal}
  {apiUrls}
  {activityTypes}
  onCreated={handleCreated}
/>
