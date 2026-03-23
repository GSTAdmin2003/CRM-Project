<script>
  import { onMount } from 'svelte';

  export let apiUrls = {};

  let users = [];
  let roles = [];
  let loading = true;
  let error = null;

  let searchQuery = '';
  let selectedRole = '';
  let selectedStatus = '';

  let togglingId = null;
  let toggleError = null;

  function getCsrf() {
    const m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? m[1] : '';
  }

  async function loadRoles() {
    if (!apiUrls.roles) return;
    try {
      const res = await fetch(apiUrls.roles);
      if (res.ok) roles = await res.json();
    } catch (e) { /* ignore */ }
  }

  async function loadUsers() {
    if (!apiUrls.users) { loading = false; return; }
    const params = new URLSearchParams();
    if (searchQuery) params.set('q', searchQuery);
    if (selectedStatus) params.set('status', selectedStatus);
    const url = apiUrls.users + (params.toString() ? '?' + params.toString() : '');
    try {
      const res = await fetch(url);
      if (res.ok) {
        let data = await res.json();
        // filter by role client-side (API doesn't support role filter)
        if (selectedRole) {
          data = data.filter(u =>
            u.roles && u.roles.some(r => r.name === selectedRole)
          );
        }
        users = data;
      } else {
        error = 'Failed to load users.';
      }
    } catch (e) {
      error = 'Network error.';
    }
    loading = false;
  }

  function clearFilters() {
    searchQuery = '';
    selectedRole = '';
    selectedStatus = '';
    loadUsers();
  }

  async function toggleActive(userId, currentActive) {
    togglingId = userId;
    toggleError = null;
    const url = apiUrls.toggleActive.replace('{id}', userId);
    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCsrf() },
      });
      if (res.ok) {
        const updated = await res.json();
        users = users.map(u => u.id === userId ? { ...u, is_active: updated.is_active } : u);
      } else {
        const d = await res.json();
        toggleError = d.detail || 'Failed to toggle status.';
      }
    } catch (e) {
      toggleError = 'Network error.';
    }
    togglingId = null;
  }

  function getEditUrl(userId) {
    return apiUrls.editUrl ? apiUrls.editUrl.replace('{id}', userId) : '#';
  }

  function getInitials(user) {
    if (user.first_name) return user.first_name[0].toUpperCase();
    return user.username[0].toUpperCase();
  }

  function getDisplayName(user) {
    const full = [user.first_name, user.last_name].filter(Boolean).join(' ');
    return full || user.username;
  }

  onMount(async () => {
    await Promise.all([loadRoles(), loadUsers()]);
  });
</script>

<div class="space-y-4">

  {#if toggleError}
    <div class="px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-800">
      {toggleError}
    </div>
  {/if}

  <!-- Filters -->
  <div class="flex flex-wrap items-end gap-3">
    <div class="flex-1 min-w-48">
      <label class="block text-xs font-medium text-gray-500 mb-1">Search</label>
      <input
        type="text"
        bind:value={searchQuery}
        placeholder="Name, email, username..."
        class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500"
      />
    </div>

    <div class="w-44">
      <label class="block text-xs font-medium text-gray-500 mb-1">Role</label>
      <select
        bind:value={selectedRole}
        class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500"
      >
        <option value="">All Roles</option>
        {#each roles as role}
          <option value={role.name}>{role.name}</option>
        {/each}
      </select>
    </div>

    <div class="w-36">
      <label class="block text-xs font-medium text-gray-500 mb-1">Status</label>
      <select
        bind:value={selectedStatus}
        class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500"
      >
        <option value="">All</option>
        <option value="active">Active</option>
        <option value="inactive">Inactive</option>
      </select>
    </div>

    <div class="flex items-end gap-2">
      <button
        on:click={loadUsers}
        class="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700"
      >
        Filter
      </button>
      {#if searchQuery || selectedRole || selectedStatus}
        <button
          on:click={clearFilters}
          class="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50"
        >
          Clear
        </button>
      {/if}
      <a
        href={apiUrls.createUrl}
        class="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 inline-flex items-center"
      >
        + Add User
      </a>
    </div>
  </div>

  <!-- User List -->
  {#if loading}
    <div class="flex items-center justify-center py-12">
      <div class="text-sm text-gray-400">Loading users...</div>
    </div>
  {:else if error}
    <div class="px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-800">
      {error}
    </div>
  {:else if users.length === 0}
    <div class="text-center py-16 bg-white rounded-md shadow">
      <p class="text-gray-500 text-sm">
        {searchQuery || selectedRole || selectedStatus ? 'No users match your filters.' : 'No users found.'}
      </p>
      {#if searchQuery || selectedRole || selectedStatus}
        <button on:click={clearFilters} class="mt-2 text-indigo-600 text-sm hover:underline">Clear filters</button>
      {:else}
        <a href={apiUrls.createUrl} class="mt-4 inline-block bg-indigo-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-indigo-700">
          Add User
        </a>
      {/if}
    </div>
  {:else}
    <div class="bg-white shadow overflow-hidden sm:rounded-md">
      <ul class="divide-y divide-gray-200">
        {#each users as u (u.id)}
          <li class="px-4 py-4 sm:px-6 hover:bg-gray-50">
            <div class="flex items-center justify-between gap-4">

              <!-- Avatar + Name -->
              <div class="flex items-center gap-3 min-w-0 flex-1">
                <div class="flex-shrink-0 h-10 w-10 rounded-full bg-indigo-100 flex items-center justify-center">
                  <span class="text-sm font-semibold text-indigo-700">{getInitials(u)}</span>
                </div>
                <div class="min-w-0">
                  <p class="text-sm font-medium text-gray-900 truncate">
                    {getDisplayName(u)}
                  </p>
                  <p class="text-xs text-gray-500 truncate">@{u.username} · {u.email}{u.extension ? ` · ext. ${u.extension}` : ''}</p>
                </div>
              </div>

              <!-- Roles -->
              <div class="hidden sm:flex flex-wrap gap-1 flex-shrink-0 w-48">
                {#if u.roles && u.roles.length > 0}
                  {#each u.roles as role}
                    <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium
                      {role.name === 'Owner' ? 'bg-purple-100 text-purple-800' :
                       role.name === 'Sales Manager' ? 'bg-blue-100 text-blue-800' :
                       role.name === 'Sales Executive' ? 'bg-green-100 text-green-800' :
                       'bg-gray-100 text-gray-700'}">
                      {role.name}
                    </span>
                  {/each}
                {:else}
                  <span class="text-xs text-gray-400 italic">No roles</span>
                {/if}
              </div>

              <!-- Status -->
              <div class="flex-shrink-0 text-right">
                {#if u.is_active}
                  <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    <span class="w-1.5 h-1.5 bg-green-500 rounded-full mr-1"></span>Active
                  </span>
                {:else}
                  <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                    <span class="w-1.5 h-1.5 bg-red-500 rounded-full mr-1"></span>Inactive
                  </span>
                {/if}
              </div>

              <!-- Actions -->
              <div class="flex-shrink-0 flex items-center gap-2">
                <a
                  href={getEditUrl(u.id)}
                  class="inline-flex items-center px-3 py-1.5 text-xs font-medium text-indigo-600 border border-indigo-200 rounded-md hover:bg-indigo-50"
                >
                  Edit
                </a>
                <button
                  on:click={() => toggleActive(u.id, u.is_active)}
                  disabled={togglingId === u.id}
                  class="inline-flex items-center px-3 py-1.5 text-xs font-medium rounded-md border disabled:opacity-50
                    {u.is_active ? 'text-red-600 border-red-200 hover:bg-red-50' : 'text-green-600 border-green-200 hover:bg-green-50'}"
                >
                  {togglingId === u.id ? '...' : (u.is_active ? 'Deactivate' : 'Activate')}
                </button>
              </div>

            </div>
          </li>
        {/each}
      </ul>
    </div>
  {/if}

</div>
