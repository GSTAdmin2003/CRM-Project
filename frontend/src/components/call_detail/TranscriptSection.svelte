<script>
  import { apiFetch } from '../../utils/api.js';
  import { getCsrfToken } from '../../utils/csrf.js';
  export let transcript = null;
  export let apiUrls;
  export let callId;

  let showLangModal = false;
  let selectedLang = 'en';
  let starting = false;

  async function startTranscription() {
    starting = true;
    await apiFetch(apiUrls.startTranscription, {
      method: 'POST',
      body: JSON.stringify({ language: selectedLang }),
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
    });
    starting = false;
    showLangModal = false;
    window.location.reload();
  }
</script>

<div class="bg-white shadow rounded-lg p-6">
  <div class="flex items-center justify-between mb-4">
    <h2 class="text-lg font-medium text-gray-900">Transcript</h2>
    {#if !transcript || transcript.status === 'failed'}
      <button on:click={() => showLangModal = true}
        class="px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700">
        Start Transcription
      </button>
    {/if}
  </div>

  {#if !transcript}
    <p class="text-gray-500 text-sm">No transcript available.</p>
  {:else if transcript.status === 'pending' || transcript.status === 'processing'}
    <div class="flex items-center gap-2 text-gray-600">
      <svg class="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
      </svg>
      <span>Transcribing...</span>
    </div>
  {:else if transcript.status === 'completed'}
    <div class="grid grid-cols-2 gap-4">
      <div>
        <h3 class="text-sm font-medium text-gray-700 mb-2">Caller</h3>
        <p class="text-sm text-gray-600 whitespace-pre-wrap">{transcript.caller_text || ''}</p>
      </div>
      <div>
        <h3 class="text-sm font-medium text-gray-700 mb-2">Agent</h3>
        <p class="text-sm text-gray-600 whitespace-pre-wrap">{transcript.agent_text || ''}</p>
      </div>
    </div>
    {#if transcript.language_code}
      <p class="mt-3 text-xs text-gray-400">Language: {transcript.language_code}</p>
    {/if}
  {:else if transcript.status === 'failed'}
    <p class="text-red-600 text-sm">{transcript.error_message || 'Transcription failed.'}</p>
  {/if}

  {#if showLangModal}
    <div class="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center">
      <div class="bg-white rounded-lg p-6 max-w-sm w-full mx-4">
        <h3 class="text-lg font-medium mb-4">Select Language</h3>
        <label class="flex items-center gap-2 mb-2 cursor-pointer">
          <input type="radio" bind:group={selectedLang} value="en"> English
        </label>
        <label class="flex items-center gap-2 mb-4 cursor-pointer">
          <input type="radio" bind:group={selectedLang} value="ka"> Georgian
        </label>
        <div class="flex gap-3">
          <button on:click={startTranscription} disabled={starting}
            class="flex-1 bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50">
            {starting ? 'Starting...' : 'Start'}
          </button>
          <button on:click={() => showLangModal = false}
            class="px-4 py-2 border border-gray-300 rounded text-gray-700 hover:bg-gray-50">
            Cancel
          </button>
        </div>
      </div>
    </div>
  {/if}
</div>
