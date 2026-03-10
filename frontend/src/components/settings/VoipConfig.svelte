<script>
  import { onMount } from 'svelte';
  import { getCsrfToken } from '../../utils/csrf.js';

  export let apiUrls = {};

  let loading = true;
  let saving = false;
  let successMsg = '';
  let errorMsg = '';

  // Form fields
  let server_ip = '';
  let server_port = 5060;
  let username = '';
  let caller_id = '';
  let is_active = true;

  onMount(async () => {
    try {
      const res = await fetch(apiUrls.voipConfig, { credentials: 'same-origin' });
      if (res.ok) {
        const data = await res.json();
        server_ip = data.server_ip ?? '';
        server_port = data.server_port ?? 5060;
        username = data.username ?? '';
        caller_id = data.caller_id ?? '';
        is_active = data.is_active ?? true;
      } else if (res.status === 403) {
        errorMsg = 'Admin access required to view VoIP configuration.';
      } else {
        errorMsg = 'Failed to load VoIP configuration.';
      }
    } catch (e) {
      errorMsg = 'Network error loading VoIP configuration.';
    } finally {
      loading = false;
    }
  });

  async function save() {
    saving = true;
    successMsg = '';
    errorMsg = '';

    const body = {
      server_ip,
      server_port: Number(server_port),
      username,
      caller_id,
      is_active,
    };

    try {
      const res = await fetch(apiUrls.voipConfig, {
        method: 'PATCH',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify(body),
      });

      if (res.ok) {
        const data = await res.json();
        server_ip = data.server_ip ?? server_ip;
        server_port = data.server_port ?? server_port;
        username = data.username ?? username;
        caller_id = data.caller_id ?? caller_id;
        is_active = data.is_active ?? is_active;
        successMsg = 'VoIP configuration saved successfully.';
      } else if (res.status === 403) {
        errorMsg = 'Admin access required to update VoIP configuration.';
      } else {
        const d = await res.json().catch(() => ({}));
        errorMsg = d.detail || JSON.stringify(d);
      }
    } catch (e) {
      errorMsg = 'Network error saving VoIP configuration.';
    } finally {
      saving = false;
    }
  }
</script>

<div class="bg-white rounded-lg shadow p-6 max-w-2xl">
  <h2 class="text-base font-semibold text-gray-900 mb-4">VoIP Configuration</h2>
  <p class="text-sm text-gray-500 mb-6">
    Configure the global SIP trunk settings for VoIP calls. Admin access required.
  </p>

  {#if loading}
    <div class="flex items-center gap-2 text-sm text-gray-500 py-8">
      <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
      </svg>
      Loading configuration…
    </div>
  {:else}
    {#if successMsg}
      <div class="mb-4 rounded-md bg-green-50 border border-green-200 px-4 py-3 text-sm text-green-700">
        {successMsg}
      </div>
    {/if}
    {#if errorMsg}
      <div class="mb-4 rounded-md bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
        {errorMsg}
      </div>
    {/if}

    <form on:submit|preventDefault={save} class="space-y-5">
      <!-- Server IP -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">
          SIP Server / Host
        </label>
        <input
          type="text"
          bind:value={server_ip}
          placeholder="sip.example.com"
          class="border border-gray-300 rounded px-3 py-2 text-sm w-full focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </div>

      <!-- Server Port -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">
          SIP Port
        </label>
        <input
          type="number"
          bind:value={server_port}
          min="1"
          max="65535"
          placeholder="5060"
          class="border border-gray-300 rounded px-3 py-2 text-sm w-full focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        <p class="mt-1 text-xs text-gray-500">Default SIP port is 5060.</p>
      </div>

      <!-- Username -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">
          Username / Extension
        </label>
        <input
          type="text"
          bind:value={username}
          placeholder="1001"
          autocomplete="off"
          class="border border-gray-300 rounded px-3 py-2 text-sm w-full focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </div>

      <!-- Caller ID -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">
          Caller ID (display name)
        </label>
        <input
          type="text"
          bind:value={caller_id}
          placeholder="Sales"
          class="border border-gray-300 rounded px-3 py-2 text-sm w-full focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </div>

      <!-- Is Active -->
      <div class="flex items-center gap-3">
        <input
          type="checkbox"
          id="voip-is-active"
          bind:checked={is_active}
          class="h-4 w-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
        />
        <label for="voip-is-active" class="text-sm font-medium text-gray-700 cursor-pointer">
          Enable SIP trunk
        </label>
      </div>

      <!-- Submit -->
      <div class="pt-2 border-t border-gray-100">
        <button
          type="submit"
          disabled={saving}
          class="bg-indigo-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 inline-flex items-center gap-2"
        >
          {#if saving}
            <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
            </svg>
          {/if}
          Save Configuration
        </button>
      </div>
    </form>
  {/if}
</div>
