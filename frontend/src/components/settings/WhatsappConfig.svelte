<script>
  import { onMount } from 'svelte';
  import { apiGet, apiPatch } from '../../utils/api.js';
  import { showToast } from '../shared/toastStore.js';
  import Toast from '../shared/Toast.svelte';

  export let apiUrls = {};

  let config = null;
  let loading = true;
  let saving = false;

  // Form fields
  let phone_number_id = '';
  let waba_id = '';
  let app_id = '';
  let webhook_verify_token = '';
  let app_secret = '';
  let access_token = '';
  let is_active = false;
  let changeToken = false;

  onMount(async () => {
    const res = await apiGet(apiUrls.credentials);
    if (res.ok) {
      config = await res.json();
      phone_number_id = config.phone_number_id || '';
      waba_id = config.waba_id || '';
      app_id = config.app_id || '';
      webhook_verify_token = config.webhook_verify_token || '';
      app_secret = config.app_secret || '';
      is_active = config.is_active || false;
    } else {
      showToast('error', 'Failed to load WhatsApp configuration.');
    }
    loading = false;
  });

  async function save() {
    saving = true;
    const body = { phone_number_id, waba_id, app_id, webhook_verify_token, app_secret, is_active };
    if (changeToken && access_token.trim()) {
      body.access_token = access_token;
    }
    const res = await apiPatch(apiUrls.credentials, body);
    if (res.ok) {
      config = await res.json();
      changeToken = false;
      access_token = '';
      showToast('success', 'WhatsApp configuration saved.');
    } else {
      const data = await res.json().catch(() => ({}));
      showToast('error', data.detail || 'Failed to save configuration.');
    }
    saving = false;
  }

  function copyWebhookUrl() {
    const url = `${window.location.origin}/messaging/webhook/`;
    navigator.clipboard.writeText(url).then(() => {
      showToast('success', 'Webhook URL copied to clipboard.');
    });
  }
</script>

<Toast />

{#if loading}
  <div class="flex items-center justify-center py-20">
    <svg class="w-6 h-6 animate-spin text-green-500" fill="none" viewBox="0 0 24 24">
      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
    </svg>
  </div>
{:else if config !== null}
  <div class="space-y-8">
    <!-- Status banner -->
    {#if config.is_active && config.is_configured}
      <div class="flex items-center px-4 py-3 bg-green-50 border border-green-200 rounded-lg">
        <span class="w-2.5 h-2.5 bg-green-500 rounded-full mr-3 flex-shrink-0"></span>
        <div>
          <p class="text-sm font-medium text-green-800">WhatsApp is active</p>
          <p class="text-xs text-green-600 mt-0.5">Phone Number ID: <code class="font-mono">{config.phone_number_id}</code></p>
        </div>
      </div>
    {:else if config.is_configured}
      <div class="flex items-center px-4 py-3 bg-yellow-50 border border-yellow-200 rounded-lg">
        <span class="w-2.5 h-2.5 bg-yellow-400 rounded-full mr-3 flex-shrink-0"></span>
        <p class="text-sm font-medium text-yellow-800">Credentials saved but integration is disabled. Enable it below.</p>
      </div>
    {:else}
      <div class="flex items-center px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg">
        <span class="w-2.5 h-2.5 bg-gray-400 rounded-full mr-3 flex-shrink-0"></span>
        <p class="text-sm font-medium text-gray-600">WhatsApp is not configured. Fill in your Meta credentials below.</p>
      </div>
    {/if}

    <!-- Setup guide -->
    <details class="border border-blue-200 rounded-lg bg-blue-50">
      <summary class="px-4 py-3 cursor-pointer text-sm font-medium text-blue-800 flex items-center">
        How to get your Meta Cloud API credentials
      </summary>
      <div class="px-4 pb-4 text-sm text-blue-700 space-y-2 border-t border-blue-200 pt-3">
        <ol class="list-decimal list-inside space-y-1.5">
          <li>Go to <strong>developers.facebook.com</strong> &rarr; My Apps &rarr; your app</li>
          <li>Navigate to <strong>WhatsApp &rarr; API Setup</strong></li>
          <li>Copy the <strong>Phone Number ID</strong></li>
          <li>Generate or copy your <strong>Permanent Access Token</strong></li>
          <li>Find your <strong>App Secret</strong> under App Settings &rarr; Basic</li>
          <li>Set the Webhook URL to: <code class="bg-blue-100 px-1.5 py-0.5 rounded font-mono text-xs">{window.location.origin}/messaging/webhook/</code></li>
          <li>Set the Webhook Verify Token to match the value you enter below</li>
          <li>Subscribe to the <strong>messages</strong> webhook field</li>
        </ol>
      </div>
    </details>

    <!-- Form -->
    <div class="space-y-6">
      <!-- API Credentials -->
      <div>
        <h3 class="text-sm font-semibold text-gray-900 uppercase tracking-wide border-b border-gray-200 pb-2 mb-4">
          API Credentials
        </h3>

        <!-- Access Token -->
        <div class="mb-5">
          <label class="block text-sm font-medium text-gray-700 mb-1">
            Access Token <span class="text-red-500">*</span>
          </label>
          {#if config.access_token_set && !changeToken}
            <div class="flex items-center gap-3">
              <div class="flex-1 px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-500 font-mono">
                &#9679;&#9679;&#9679;&#9679;&#9679;&#9679;&#9679;&#9679; (token set)
              </div>
              <button
                type="button"
                class="text-sm text-indigo-600 hover:text-indigo-800 font-medium"
                on:click={() => (changeToken = true)}
              >
                Change
              </button>
            </div>
          {:else}
            <input
              type="text"
              bind:value={access_token}
              class="w-full font-mono text-sm border border-gray-300 rounded-lg px-3 py-2 focus:ring-1 focus:ring-green-500 focus:border-green-500"
              placeholder="Permanent access token from Meta"
              autocomplete="off"
              spellcheck="false"
            />
            {#if config.access_token_set}
              <button
                type="button"
                class="mt-1 text-xs text-gray-500 hover:text-gray-700"
                on:click={() => { changeToken = false; access_token = ''; }}
              >
                Cancel change
              </button>
            {/if}
          {/if}
          <p class="mt-1 text-xs text-gray-500">Permanent access token from Meta Business Suite. Keep this secret.</p>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-5">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              Phone Number ID <span class="text-red-500">*</span>
            </label>
            <input
              type="text"
              bind:value={phone_number_id}
              class="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:ring-1 focus:ring-green-500 focus:border-green-500"
              placeholder="123456789"
            />
            <p class="mt-1 text-xs text-gray-500">Found under WhatsApp &rarr; API Setup.</p>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">App Secret</label>
            <input
              type="text"
              bind:value={app_secret}
              class="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:ring-1 focus:ring-green-500 focus:border-green-500"
              placeholder="App secret"
            />
            <p class="mt-1 text-xs text-gray-500">Found under App Settings &rarr; Basic.</p>
          </div>
        </div>
      </div>

      <!-- Webhook -->
      <div>
        <h3 class="text-sm font-semibold text-gray-900 uppercase tracking-wide border-b border-gray-200 pb-2 mb-4">
          Webhook
        </h3>

        <div class="mb-5">
          <label class="block text-sm font-medium text-gray-700 mb-1">Webhook URL (set this in Meta console)</label>
          <div class="flex items-center bg-gray-50 border border-gray-300 rounded-lg px-3 py-2">
            <code class="text-xs font-mono text-gray-600 flex-1 select-all">
              {window.location.origin}/messaging/webhook/
            </code>
            <button
              type="button"
              on:click={copyWebhookUrl}
              class="ml-2 text-xs text-indigo-600 hover:text-indigo-800 font-medium flex-shrink-0"
            >
              Copy
            </button>
          </div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-5">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Webhook Verify Token</label>
            <input
              type="text"
              bind:value={webhook_verify_token}
              class="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:ring-1 focus:ring-green-500 focus:border-green-500"
              placeholder="your-verify-token"
            />
            <p class="mt-1 text-xs text-gray-500">Must match the token in Meta's Webhook configuration.</p>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">App ID</label>
            <input
              type="text"
              bind:value={app_id}
              class="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:ring-1 focus:ring-green-500 focus:border-green-500"
              placeholder="Facebook App ID"
            />
            <p class="mt-1 text-xs text-gray-500">Required for media uploads when submitting templates.</p>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">WABA ID</label>
            <input
              type="text"
              bind:value={waba_id}
              class="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:ring-1 focus:ring-green-500 focus:border-green-500"
              placeholder="WhatsApp Business Account ID"
            />
            <p class="mt-1 text-xs text-gray-500">Required to submit templates for Meta approval.</p>
          </div>
        </div>
      </div>

      <!-- Enable toggle -->
      <div class="flex items-start space-x-3 pt-2">
        <input
          type="checkbox"
          id="is_active"
          bind:checked={is_active}
          class="mt-0.5 h-4 w-4 rounded border-gray-300 text-green-600 focus:ring-green-500"
        />
        <div>
          <label for="is_active" class="text-sm font-medium text-gray-700 cursor-pointer">
            Enable WhatsApp integration
          </label>
          <p class="text-xs text-gray-500 mt-0.5">When disabled, sending and receiving messages is paused.</p>
        </div>
      </div>

      <!-- Save -->
      <div class="pt-4 border-t border-gray-200 flex items-center justify-between">
        <a
          href="/messaging/inbox/"
          class="inline-flex items-center text-sm text-green-600 hover:text-green-800 font-medium"
        >
          Open WhatsApp Inbox
        </a>
        <button
          type="button"
          on:click={save}
          disabled={saving}
          class="inline-flex items-center px-5 py-2.5 bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg shadow-sm transition-colors"
        >
          {#if saving}
            <svg class="w-4 h-4 animate-spin mr-2" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
            </svg>
          {/if}
          Save Configuration
        </button>
      </div>
    </div>
  </div>
{/if}
