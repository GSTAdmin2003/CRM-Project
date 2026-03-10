<script>
  import { onMount } from 'svelte';
  import { getCsrfToken } from '../../utils/csrf.js';

  export let apiUrls = {};

  let loading = true;
  let errorMsg = '';

  // Current sound URLs from the API
  let currentSounds = {
    hold_music: null,
    welcome_sound: null,
    non_working_hours_sound: null,
  };

  // Pending upload files (File objects)
  let pendingFiles = {
    hold_music: null,
    welcome_sound: null,
    non_working_hours_sound: null,
  };

  // Per-section state
  let uploadState = {
    hold_music: { saving: false, success: '', error: '' },
    welcome_sound: { saving: false, success: '', error: '' },
    non_working_hours_sound: { saving: false, success: '', error: '' },
  };

  const SOUND_LABELS = {
    hold_music: 'Hold Music',
    welcome_sound: 'Welcome Sound',
    non_working_hours_sound: 'Non-Working Hours Sound',
  };

  const SOUND_DESCRIPTIONS = {
    hold_music: 'Played when a caller is placed on hold.',
    welcome_sound: 'Played as a greeting when a call is answered.',
    non_working_hours_sound: 'Played when a caller calls outside of working hours.',
  };

  function extractFilename(url) {
    if (!url) return null;
    const parts = url.split('/');
    return decodeURIComponent(parts[parts.length - 1] || url);
  }

  onMount(async () => {
    try {
      const res = await fetch(apiUrls.voipSounds, { credentials: 'same-origin' });
      if (res.ok) {
        const data = await res.json();
        currentSounds = {
          hold_music: data.hold_music || null,
          welcome_sound: data.welcome_sound || null,
          non_working_hours_sound: data.non_working_hours_sound || null,
        };
      } else if (res.status === 403) {
        errorMsg = 'Admin access required to view sound settings.';
      } else {
        errorMsg = 'Failed to load sound settings.';
      }
    } catch (e) {
      errorMsg = 'Network error loading sound settings.';
    } finally {
      loading = false;
    }
  });

  function handleFileInput(soundKey, e) {
    const file = e.target?.files?.[0];
    if (file) {
      pendingFiles = { ...pendingFiles, [soundKey]: file };
      uploadState[soundKey] = { saving: false, success: '', error: '' };
    }
    // Reset input so the same file can be re-selected
    if (e.target) e.target.value = '';
  }

  function clearPending(soundKey) {
    pendingFiles = { ...pendingFiles, [soundKey]: null };
    uploadState[soundKey] = { saving: false, success: '', error: '' };
  }

  async function uploadSound(soundKey) {
    const file = pendingFiles[soundKey];
    if (!file) return;

    uploadState[soundKey] = { saving: true, success: '', error: '' };

    const formData = new FormData();
    formData.append(soundKey, file);

    try {
      const res = await fetch(apiUrls.sipSettings, {
        method: 'PATCH',
        credentials: 'same-origin',
        headers: {
          'X-CSRFToken': getCsrfToken(),
          // Do NOT set Content-Type — browser sets it with boundary for multipart
        },
        body: formData,
      });

      if (res.ok) {
        // Refresh the sounds list to show the newly uploaded file
        const refreshRes = await fetch(apiUrls.voipSounds, { credentials: 'same-origin' });
        if (refreshRes.ok) {
          const data = await refreshRes.json();
          currentSounds = {
            hold_music: data.hold_music || null,
            welcome_sound: data.welcome_sound || null,
            non_working_hours_sound: data.non_working_hours_sound || null,
          };
        }
        pendingFiles = { ...pendingFiles, [soundKey]: null };
        uploadState[soundKey] = { saving: false, success: `${SOUND_LABELS[soundKey]} uploaded successfully.`, error: '' };
      } else {
        const d = await res.json().catch(() => ({}));
        uploadState[soundKey] = {
          saving: false,
          success: '',
          error: d.detail || JSON.stringify(d) || 'Upload failed.',
        };
      }
    } catch (e) {
      uploadState[soundKey] = { saving: false, success: '', error: 'Network error during upload.' };
    }
  }
</script>

<div class="space-y-6 max-w-2xl">
  <div class="bg-white rounded-lg shadow p-6">
    <h2 class="text-base font-semibold text-gray-900 mb-1">VoIP Sounds</h2>
    <p class="text-sm text-gray-500">
      Upload audio files for hold music, greetings, and non-working hours messages.
      Accepted formats: MP3, WAV, OGG.
    </p>
  </div>

  {#if loading}
    <div class="bg-white rounded-lg shadow p-6 flex items-center gap-2 text-sm text-gray-500">
      <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
      </svg>
      Loading sound settings…
    </div>
  {:else}
    {#if errorMsg}
      <div class="bg-white rounded-lg shadow p-6">
        <div class="rounded-md bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          {errorMsg}
        </div>
      </div>
    {/if}

    {#each Object.keys(SOUND_LABELS) as soundKey}
      {@const label = SOUND_LABELS[soundKey]}
      {@const description = SOUND_DESCRIPTIONS[soundKey]}
      {@const currentUrl = currentSounds[soundKey]}
      {@const currentFilename = extractFilename(currentUrl)}
      {@const pending = pendingFiles[soundKey]}
      {@const state = uploadState[soundKey]}

      <div class="bg-white rounded-lg shadow p-6">
        <h3 class="text-sm font-semibold text-gray-900 mb-1">{label}</h3>
        <p class="text-xs text-gray-500 mb-4">{description}</p>

        {#if state.success}
          <div class="mb-3 rounded-md bg-green-50 border border-green-200 px-3 py-2 text-sm text-green-700">
            {state.success}
          </div>
        {/if}
        {#if state.error}
          <div class="mb-3 rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
            {state.error}
          </div>
        {/if}

        <!-- Current file status -->
        <div class="mb-4">
          {#if currentUrl}
            <div class="flex items-center gap-2 px-3 py-2 bg-green-50 border border-green-200 rounded-md">
              <svg class="w-4 h-4 text-green-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"/>
              </svg>
              <div class="min-w-0 flex-1">
                <p class="text-xs font-medium text-green-800">Configured</p>
                <p class="text-xs text-green-700 truncate">{currentFilename}</p>
              </div>
              <a
                href={currentUrl}
                target="_blank"
                rel="noopener"
                class="flex-shrink-0 text-xs text-indigo-600 hover:text-indigo-800 font-medium"
              >
                Preview
              </a>
            </div>
          {:else}
            <div class="flex items-center gap-2 px-3 py-2 bg-gray-50 border border-gray-200 rounded-md">
              <svg class="w-4 h-4 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"/>
              </svg>
              <p class="text-xs text-gray-500">Not configured — system default will be used.</p>
            </div>
          {/if}
        </div>

        <!-- Upload area -->
        {#if pending}
          <!-- Pending file selected -->
          <div class="flex items-center justify-between px-3 py-2 bg-blue-50 border border-blue-200 rounded-md mb-3">
            <div class="flex items-center gap-2 min-w-0">
              <svg class="w-4 h-4 text-blue-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"/>
              </svg>
              <span class="text-sm text-blue-800 truncate">{pending.name}</span>
            </div>
            <button
              type="button"
              class="ml-2 flex-shrink-0 text-xs text-red-500 hover:text-red-700 font-medium"
              on:click={() => clearPending(soundKey)}
            >
              Remove
            </button>
          </div>
          <button
            type="button"
            disabled={state.saving}
            on:click={() => uploadSound(soundKey)}
            class="bg-indigo-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 inline-flex items-center gap-2"
          >
            {#if state.saving}
              <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
              </svg>
              Uploading…
            {:else}
              Upload {label}
            {/if}
          </button>
        {:else}
          <!-- File picker -->
          <label class="cursor-pointer inline-flex items-center gap-2 px-4 py-2 border border-gray-300 rounded text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 transition-colors">
            <svg class="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
            </svg>
            {currentUrl ? 'Replace file' : 'Upload file'}
            <input
              type="file"
              accept="audio/*,.mp3,.wav,.ogg,.m4a"
              class="hidden"
              on:change={(e) => handleFileInput(soundKey, e)}
            />
          </label>
        {/if}
      </div>
    {/each}
  {/if}
</div>
