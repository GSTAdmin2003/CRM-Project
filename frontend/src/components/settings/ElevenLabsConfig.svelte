<script>
  import { onMount } from 'svelte';
  import { apiGet, apiPatch } from '../../utils/api.js';
  import { showToast } from '../shared/toastStore.js';
  import Toast from '../shared/Toast.svelte';

  export let apiUrls = {};

  let apiKeySet = false;
  let autoTranscribe = false;
  let loading = true;
  let saving = false;
  let clearing = false;
  let apiKey = '';
  let showKeyInput = false;

  onMount(async () => {
    const res = await apiGet(apiUrls.config);
    if (res.ok) {
      const data = await res.json();
      apiKeySet = data.api_key_set;
      autoTranscribe = data.auto_transcribe;
    } else {
      showToast('error', 'Failed to load ElevenLabs configuration.');
    }
    loading = false;
  });

  async function saveKey() {
    if (!apiKey.trim()) {
      showToast('error', 'API key cannot be empty.');
      return;
    }
    saving = true;
    const res = await apiPatch(apiUrls.config, { action: 'save_key', api_key: apiKey.trim() });
    if (res.ok) {
      const data = await res.json();
      apiKeySet = data.api_key_set;
      autoTranscribe = data.auto_transcribe;
      apiKey = '';
      showKeyInput = false;
      showToast('success', 'ElevenLabs API key saved.');
    } else {
      const data = await res.json().catch(() => ({}));
      showToast('error', data.api_key || 'Failed to save API key.');
    }
    saving = false;
  }

  async function clearKey() {
    if (!confirm('Remove ElevenLabs API key? Transcription will stop working.')) return;
    clearing = true;
    const res = await apiPatch(apiUrls.config, { action: 'clear_key' });
    if (res.ok) {
      apiKeySet = false;
      apiKey = '';
      showKeyInput = false;
      showToast('success', 'ElevenLabs API key removed.');
    } else {
      showToast('error', 'Failed to remove API key.');
    }
    clearing = false;
  }

  async function toggleAutoTranscribe(value) {
    const res = await apiPatch(apiUrls.config, { action: 'save_auto_transcribe', auto_transcribe: value });
    if (res.ok) {
      const data = await res.json();
      autoTranscribe = data.auto_transcribe;
      showToast('success', value ? 'Auto-transcription enabled.' : 'Auto-transcription disabled.');
    } else {
      showToast('error', 'Failed to update auto-transcription setting.');
      autoTranscribe = !value; // revert
    }
  }
</script>

<Toast />

{#if loading}
  <div class="flex items-center justify-center py-20">
    <svg class="w-6 h-6 animate-spin text-indigo-500" fill="none" viewBox="0 0 24 24">
      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
    </svg>
  </div>
{:else}
  <div class="space-y-6">
    <!-- Status banner -->
    {#if apiKeySet}
      <div class="flex items-center gap-3 p-4 bg-green-50 border border-green-200 rounded-lg">
        <svg class="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
        </svg>
        <div>
          <p class="text-sm font-medium text-green-800">API key configured</p>
          <p class="text-xs text-green-600">ElevenLabs Scribe is available for call transcription.</p>
        </div>
      </div>
    {:else}
      <div class="flex items-center gap-3 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
        <svg class="w-5 h-5 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
        </svg>
        <div>
          <p class="text-sm font-medium text-yellow-800">No API key configured</p>
          <p class="text-xs text-yellow-600">Call transcription will not work until an ElevenLabs API key is added.</p>
        </div>
      </div>
    {/if}

    <!-- How-to guide -->
    <div class="p-4 bg-blue-50 border border-blue-200 rounded-lg">
      <h3 class="text-sm font-semibold text-blue-800 mb-2">How to get an ElevenLabs API key</h3>
      <ol class="text-xs text-blue-700 space-y-1 list-decimal list-inside">
        <li>Go to <strong>elevenlabs.io</strong> and sign in</li>
        <li>Open <strong>Profile &rarr; API Keys</strong></li>
        <li>Click <strong>Create new API key</strong>, enable <strong>Speech to Text</strong> permission</li>
        <li>Copy the key and paste it below</li>
      </ol>
    </div>

    <!-- API Key section -->
    <div class="border border-gray-200 rounded-lg overflow-hidden">
      <div class="px-5 py-4 bg-gray-50 border-b border-gray-200">
        <h3 class="text-sm font-semibold text-gray-800">ElevenLabs API Key</h3>
      </div>
      <div class="px-5 py-4 space-y-4">
        {#if apiKeySet && !showKeyInput}
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <span class="text-sm text-gray-600 font-mono">sk_&#9679;&#9679;&#9679;&#9679;&#9679;&#9679;&#9679;&#9679; (configured)</span>
            </div>
            <div class="flex items-center gap-3">
              <button
                type="button"
                on:click={() => (showKeyInput = true)}
                class="text-sm text-indigo-600 hover:text-indigo-800 font-medium"
              >
                Change key
              </button>
              <button
                type="button"
                on:click={clearKey}
                disabled={clearing}
                class="text-sm text-red-600 hover:text-red-800 font-medium disabled:opacity-50"
              >
                {clearing ? 'Removing...' : 'Remove key'}
              </button>
            </div>
          </div>
        {:else}
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">API Key</label>
            <input
              type="text"
              bind:value={apiKey}
              class="w-full font-mono text-sm border border-gray-300 rounded-lg px-3 py-2 focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500"
              placeholder="sk_…"
              autocomplete="off"
              spellcheck="false"
            />
            <p class="mt-1 text-xs text-gray-500">Stored in the database. Keep it secure.</p>
          </div>
          <div class="flex items-center justify-between">
            {#if apiKeySet}
              <button
                type="button"
                on:click={() => { showKeyInput = false; apiKey = ''; }}
                class="text-sm text-gray-500 hover:text-gray-700"
              >
                Cancel
              </button>
            {:else}
              <span></span>
            {/if}
            <button
              type="button"
              on:click={saveKey}
              disabled={saving}
              class="inline-flex items-center px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
            >
              {#if saving}
                <svg class="w-4 h-4 animate-spin mr-2" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                </svg>
              {/if}
              Save API key
            </button>
          </div>
        {/if}
      </div>
    </div>

    <!-- Auto-transcription toggle -->
    <div class="border border-gray-200 rounded-lg overflow-hidden">
      <div class="px-5 py-4 bg-gray-50 border-b border-gray-200">
        <h3 class="text-sm font-semibold text-gray-800">Automatic Transcription</h3>
        <p class="text-xs text-gray-500 mt-0.5">When enabled, every call is transcribed automatically once the recording is ready.</p>
      </div>
      <div class="px-5 py-4">
        <label class="flex items-start gap-3 cursor-pointer select-none">
          <div class="relative mt-0.5 flex-shrink-0">
            <input
              type="checkbox"
              class="sr-only peer"
              checked={autoTranscribe}
              on:change={(e) => toggleAutoTranscribe(e.target.checked)}
            />
            <div class="w-10 h-6 bg-gray-200 rounded-full peer-checked:bg-indigo-600 transition-colors"></div>
            <div class="absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform peer-checked:translate-x-4"></div>
          </div>
          <div>
            <p class="text-sm font-medium text-gray-800">{autoTranscribe ? 'Enabled' : 'Disabled'}</p>
            <p class="text-xs text-gray-500 mt-0.5">
              Transcription uses 2-speaker diarization, team keywords, and timestamps.
              Language is resolved from the contact &rarr; company &rarr; system default.
            </p>
            {#if !apiKeySet}
              <p class="mt-2 text-xs text-yellow-700">
                An ElevenLabs API key must be configured above before transcription can run.
              </p>
            {/if}
          </div>
        </label>
      </div>
    </div>
  </div>
{/if}
