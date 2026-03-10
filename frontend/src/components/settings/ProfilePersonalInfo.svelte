<script>
  import { onMount } from 'svelte';

  export let apiUrls = {};
  export let currentUser = null;

  let loading = !currentUser;
  let saving = false;
  let error = null;
  let success = false;

  let firstName = currentUser ? currentUser.first_name : '';
  let lastName = currentUser ? currentUser.last_name : '';
  let email = currentUser ? currentUser.email : '';
  let username = currentUser ? currentUser.username : '';

  function getCsrf() {
    const m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? m[1] : '';
  }

  async function load() {
    if (!apiUrls.profile) { loading = false; return; }
    try {
      const res = await fetch(apiUrls.profile);
      if (res.ok) {
        const data = await res.json();
        firstName = data.first_name || '';
        lastName = data.last_name || '';
        email = data.email || '';
        username = data.username || '';
      }
    } catch (e) {
      // ignore, use hydrated data
    }
    loading = false;
  }

  async function save() {
    saving = true;
    error = null;
    try {
      const res = await fetch(apiUrls.profile, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrf(),
        },
        body: JSON.stringify({ first_name: firstName, last_name: lastName, email }),
      });
      saving = false;
      if (res.ok) {
        success = true;
        setTimeout(() => (success = false), 3000);
      } else {
        const d = await res.json();
        const msgs = [];
        for (const [k, v] of Object.entries(d)) {
          msgs.push(`${k}: ${Array.isArray(v) ? v.join(', ') : v}`);
        }
        error = msgs.join(' | ');
      }
    } catch (e) {
      saving = false;
      error = 'Network error. Please try again.';
    }
  }

  onMount(() => {
    if (!currentUser) load();
    else loading = false;
  });
</script>

{#if loading}
  <div class="flex items-center justify-center py-12">
    <div class="text-sm text-gray-400">Loading...</div>
  </div>
{:else}
  <div class="space-y-6">

    {#if success}
      <div class="px-4 py-3 rounded-lg bg-green-50 border border-green-200 text-sm text-green-800">
        Personal information updated successfully.
      </div>
    {/if}

    {#if error}
      <div class="px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-800">
        {error}
      </div>
    {/if}

    <!-- Basic Information -->
    <div class="bg-white border border-gray-200 rounded-lg p-6">
      <h3 class="text-lg font-medium text-gray-900 mb-6">Basic Information</h3>

      <div class="grid grid-cols-1 gap-6 sm:grid-cols-2">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">First Name</label>
          <input
            type="text"
            bind:value={firstName}
            class="block w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            placeholder="First name"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Last Name</label>
          <input
            type="text"
            bind:value={lastName}
            class="block w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            placeholder="Last name"
          />
        </div>

        <div class="sm:col-span-2">
          <label class="block text-sm font-medium text-gray-700 mb-1">Email Address</label>
          <input
            type="email"
            bind:value={email}
            class="block w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            placeholder="email@example.com"
          />
          <p class="mt-1 text-xs text-gray-500">Used for account notifications and login.</p>
        </div>
      </div>
    </div>

    <!-- Account Details -->
    <div class="bg-gray-50 border border-gray-200 rounded-lg p-6">
      <h3 class="text-lg font-medium text-gray-900 mb-4">Account Details</h3>
      <dl class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <dt class="text-sm font-medium text-gray-500">Username</dt>
          <dd class="mt-1 text-sm text-gray-900 font-mono">{username}</dd>
        </div>
        <div>
          <dt class="text-sm font-medium text-gray-500">Account Status</dt>
          <dd class="mt-1">
            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
              Active
            </span>
          </dd>
        </div>
      </dl>
    </div>

    <!-- Actions -->
    <div class="flex justify-end space-x-3">
      <a
        href="/settings/profile/"
        class="bg-white py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 hover:bg-gray-50"
      >
        Cancel
      </a>
      <button
        on:click={save}
        disabled={saving}
        class="bg-indigo-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
      >
        {saving ? 'Saving...' : 'Save Changes'}
      </button>
    </div>

  </div>
{/if}
