<script>
  export let apiUrls = {};
  export let stats = { rolesCount: 0, usersCount: 0, appsCount: 0 };
  export let currentCc = '';

  let cc = currentCc;
  let saving = false;
  let error = null;
  let success = false;

  function getCsrf() {
    const m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? m[1] : '';
  }

  async function saveCountryCode() {
    if (!cc.trim()) { error = 'Please enter a valid country code (digits only).'; return; }
    saving = true;
    error = null;
    try {
      const formData = new FormData();
      formData.append('default_country_code', cc.trim());
      formData.append('csrfmiddlewaretoken', getCsrf());
      const res = await fetch(apiUrls.phoneSettings, {
        method: 'POST',
        body: formData,
      });
      saving = false;
      if (res.ok || res.redirected) {
        success = true;
        setTimeout(() => (success = false), 3000);
      } else {
        error = 'Failed to save country code.';
      }
    } catch (e) {
      saving = false;
      error = 'Network error. Please try again.';
    }
  }
</script>

<div class="space-y-6">

  {#if success}
    <div class="px-4 py-3 rounded-lg bg-green-50 border border-green-200 text-sm text-green-800">
      Default country code saved.
    </div>
  {/if}

  {#if error}
    <div class="px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-800">
      {error}
    </div>
  {/if}

  <!-- Stats -->
  <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
    <div class="bg-green-50 border border-green-200 rounded-lg p-4">
      <dt class="text-sm font-medium text-gray-500 truncate">Roles</dt>
      <dd class="text-2xl font-semibold text-gray-900 mt-1">{stats.rolesCount}</dd>
    </div>
    <div class="bg-purple-50 border border-purple-200 rounded-lg p-4">
      <dt class="text-sm font-medium text-gray-500 truncate">Users</dt>
      <dd class="text-2xl font-semibold text-gray-900 mt-1">{stats.usersCount}</dd>
    </div>
    <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
      <dt class="text-sm font-medium text-gray-500 truncate">Apps</dt>
      <dd class="text-2xl font-semibold text-gray-900 mt-1">{stats.appsCount}</dd>
    </div>
  </div>

  <!-- Administration -->
  <div>
    <h3 class="text-lg leading-6 font-medium text-gray-900 mb-4">Administration</h3>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">

      <div class="bg-white border border-gray-200 rounded-lg p-6">
        <h4 class="text-base font-medium text-gray-900 mb-1">User Management</h4>
        <p class="text-sm text-gray-500 mb-4">Manage user accounts and permissions.</p>
        <a href={apiUrls.userListUrl} class="text-sm text-indigo-600 hover:text-indigo-500">
          View All Users
        </a>
      </div>

      <div class="bg-white border border-gray-200 rounded-lg p-6">
        <h4 class="text-base font-medium text-gray-900 mb-1">System Status</h4>
        <p class="text-sm text-gray-500 mb-4">Quick overview of system health.</p>
        <div class="space-y-2">
          <div class="flex justify-between">
            <span class="text-sm text-gray-500">System Status</span>
            <span class="text-sm font-medium text-green-600">Operational</span>
          </div>
          <div class="flex justify-between">
            <span class="text-sm text-gray-500">Database</span>
            <span class="text-sm font-medium text-green-600">Connected</span>
          </div>
        </div>
      </div>

    </div>
  </div>

  <!-- Country Code -->
  <div>
    <h3 class="text-lg leading-6 font-medium text-gray-900 mb-4">Regional Settings</h3>
    <div class="bg-white border border-gray-200 rounded-lg p-6">
      <h4 class="text-base font-medium text-gray-900 mb-1">Default Country Code</h4>
      <p class="text-sm text-gray-500 mb-4">
        Applied automatically to phone numbers entered without a country code throughout the system.
      </p>

      <div class="flex items-end gap-4">
        <div class="flex-1 max-w-xs">
          <label class="block text-sm font-medium text-gray-700 mb-1">Country Code</label>
          <div class="flex rounded-lg border border-gray-300 overflow-hidden focus-within:ring-2 focus-within:ring-indigo-500 focus-within:border-transparent">
            <span class="inline-flex items-center px-3 bg-gray-50 border-r border-gray-300 text-gray-500 text-sm font-medium select-none">+</span>
            <input
              type="text"
              bind:value={cc}
              placeholder="e.g. 995"
              maxlength="5"
              pattern="[0-9]+"
              class="flex-1 px-3 py-2 text-sm focus:outline-none bg-white"
            />
          </div>
          <p class="mt-1 text-xs text-gray-500">
            Digits only — e.g. <strong>995</strong> for Georgia, <strong>1</strong> for USA.
          </p>
        </div>
        <button
          on:click={saveCountryCode}
          disabled={saving}
          class="inline-flex items-center px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50"
        >
          {saving ? 'Saving...' : 'Save'}
        </button>
      </div>

      {#if cc}
        <p class="mt-3 text-xs text-gray-500">
          A number like <code class="font-mono bg-gray-100 px-1 rounded">571535389</code>
          will be saved as <code class="font-mono bg-gray-100 px-1 rounded">+{cc}571535389</code>.
        </p>
      {/if}
    </div>
  </div>

</div>
