<script>
  import StatusBadge from '../shared/StatusBadge.svelte';

  export let totalLeads = 0;
  export let totalValue = 0;
  export let weekActivities = [];
  export let apiUrls = {};

  function formatCurrency(value) {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value);
  }

  function formatDate(dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
  }

  const STATUS_MAP = {
    planned:    { label: 'Planned',    color: 'blue'   },
    completed:  { label: 'Completed',  color: 'green'  },
    cancelled:  { label: 'Cancelled',  color: 'red'    },
    in_progress:{ label: 'In Progress',color: 'yellow' },
  };
</script>

<div class="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
  <!-- Header -->
  <div class="mb-8 flex items-center justify-between">
    <div>
      <h1 class="text-3xl font-bold tracking-tight text-gray-900">CRM Dashboard</h1>
      <p class="mt-2 text-sm text-gray-600">Manage your sales pipeline and track opportunities</p>
    </div>
  </div>

  <!-- Stat Cards -->
  <div class="grid grid-cols-1 sm:grid-cols-3 gap-5 mb-8">
    <div class="bg-white overflow-hidden shadow rounded-lg">
      <div class="p-5 flex items-center">
        <div class="flex-shrink-0 w-10 h-10 bg-blue-500 rounded-md flex items-center justify-center">
          <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/>
          </svg>
        </div>
        <div class="ml-5">
          <p class="text-sm font-medium text-gray-500">Total Leads</p>
          <p class="text-2xl font-semibold text-gray-900">{totalLeads}</p>
        </div>
      </div>
    </div>

    <div class="bg-white overflow-hidden shadow rounded-lg">
      <div class="p-5 flex items-center">
        <div class="flex-shrink-0 w-10 h-10 bg-green-500 rounded-md flex items-center justify-center">
          <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
        </div>
        <div class="ml-5">
          <p class="text-sm font-medium text-gray-500">Pipeline Value</p>
          <p class="text-2xl font-semibold text-gray-900">{formatCurrency(totalValue)}</p>
        </div>
      </div>
    </div>

    <div class="bg-white overflow-hidden shadow rounded-lg">
      <div class="p-5 flex items-center">
        <div class="flex-shrink-0 w-10 h-10 bg-purple-500 rounded-md flex items-center justify-center">
          <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>
          </svg>
        </div>
        <div class="ml-5">
          <p class="text-sm font-medium text-gray-500">This Week's Activities</p>
          <p class="text-2xl font-semibold text-gray-900">{weekActivities.length}</p>
        </div>
      </div>
    </div>
  </div>

  <!-- Main content grid -->
  <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">

    <!-- This Week's Activities -->
    <div class="bg-white shadow rounded-lg">
      <div class="px-6 py-4 border-b border-gray-200">
        <h3 class="text-lg font-medium text-gray-900">This Week's Activities</h3>
      </div>
      <div class="px-6 py-4">
        {#if weekActivities.length === 0}
          <p class="text-sm text-gray-500 text-center py-8">No activities scheduled for this week</p>
        {:else}
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="text-left text-xs font-medium text-gray-500 uppercase tracking-wide border-b border-gray-200">
                  <th class="pb-2 pr-4">Date</th>
                  <th class="pb-2 pr-4">Type</th>
                  <th class="pb-2 pr-4">Title</th>
                  <th class="pb-2 pr-4">Lead</th>
                  <th class="pb-2 pr-4">Assignee</th>
                  <th class="pb-2">Status</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-100">
                {#each weekActivities as activity (activity.id)}
                  <tr class="hover:bg-gray-50">
                    <td class="py-3 pr-4 text-gray-500 whitespace-nowrap">{formatDate(activity.scheduledDate)}</td>
                    <td class="py-3 pr-4">
                      {#if activity.activityType}
                        <div class="flex items-center gap-1.5">
                          <span class="w-3 h-3 rounded-full flex-shrink-0" style="background-color: {activity.activityType.color || '#6B7280'};"></span>
                          <span class="text-gray-700">{activity.activityType.name}</span>
                        </div>
                      {:else}
                        <span class="text-gray-400">—</span>
                      {/if}
                    </td>
                    <td class="py-3 pr-4 font-medium text-gray-900">{activity.title}</td>
                    <td class="py-3 pr-4 text-gray-600">{activity.leadTitle || '—'}</td>
                    <td class="py-3 pr-4 text-gray-600">{activity.assignedTo || '—'}</td>
                    <td class="py-3"><StatusBadge status={activity.status} map={STATUS_MAP} /></td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {/if}
        <div class="mt-6 text-center">
          <a href="/activities/" class="text-indigo-600 hover:text-indigo-500 text-sm font-medium">
            View all activities →
          </a>
        </div>
      </div>
    </div>

    <!-- Quick Actions -->
    <div class="bg-white shadow rounded-lg">
      <div class="px-6 py-4 border-b border-gray-200">
        <h3 class="text-lg font-medium text-gray-900">Quick Actions</h3>
      </div>
      <div class="px-6 py-4">
        <div class="space-y-4">
          <a href="/crm/leads/" class="flex items-center p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-colors group">
            <div class="flex-shrink-0">
              <div class="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center group-hover:bg-blue-700">
                <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
                </svg>
              </div>
            </div>
            <div class="ml-4">
              <h4 class="text-sm font-medium text-gray-900">View Leads</h4>
              <p class="text-sm text-gray-500">Manage incoming lead inquiries</p>
            </div>
          </a>

          <a href="/crm/kanban/" class="flex items-center p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-green-500 hover:bg-green-50 transition-colors group">
            <div class="flex-shrink-0">
              <div class="w-10 h-10 bg-green-600 rounded-lg flex items-center justify-center group-hover:bg-green-700">
                <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"/>
                </svg>
              </div>
            </div>
            <div class="ml-4">
              <h4 class="text-sm font-medium text-gray-900">View Opportunities</h4>
              <p class="text-sm text-gray-500">Manage your pipeline visually</p>
            </div>
          </a>

          <a href="/crm/teams/" class="flex items-center p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-purple-500 hover:bg-purple-50 transition-colors group">
            <div class="flex-shrink-0">
              <div class="w-10 h-10 bg-purple-600 rounded-lg flex items-center justify-center group-hover:bg-purple-700">
                <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"/>
                </svg>
              </div>
            </div>
            <div class="ml-4">
              <h4 class="text-sm font-medium text-gray-900">Manage Teams</h4>
              <p class="text-sm text-gray-500">View and manage sales teams</p>
            </div>
          </a>
        </div>
      </div>
    </div>

  </div>
</div>
