<script>
  import { onMount } from 'svelte';

  export let apiUrls = {};
  export let currentLanguage = 'en';

  let language = currentLanguage;
  let saving = false;
  let error = null;
  let success = false;

  const languageOptions = [
    { value: 'en', label: 'English' },
    { value: 'ka', label: 'Georgian' },
  ];

  function getCsrf() {
    const m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? m[1] : '';
  }

  async function load() {
    if (!apiUrls.language) return;
    try {
      const res = await fetch(apiUrls.language);
      if (res.ok) {
        const data = await res.json();
        language = data.language || 'en';
      }
    } catch (e) {
      // use hydrated value
    }
  }

  async function save() {
    saving = true;
    error = null;
    try {
      const res = await fetch(apiUrls.language, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrf(),
        },
        body: JSON.stringify({ language }),
      });
      saving = false;
      if (res.ok) {
        success = true;
        setTimeout(() => (success = false), 3000);
      } else {
        const d = await res.json();
        error = d.language || d.detail || 'Save failed.';
      }
    } catch (e) {
      saving = false;
      error = 'Network error. Please try again.';
    }
  }

  onMount(load);
</script>

<div class="max-w-lg">

  {#if success}
    <div class="mb-4 px-4 py-3 rounded-lg bg-green-50 border border-green-200 text-sm text-green-800">
      Default preferred language updated.
    </div>
  {/if}

  {#if error}
    <div class="mb-4 px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-800">
      {error}
    </div>
  {/if}

  <div class="bg-white shadow rounded-lg">
    <div class="px-4 py-5 sm:p-6">
      <h3 class="text-lg font-medium text-gray-900 mb-1">Default Preferred Language</h3>
      <p class="text-sm text-gray-500 mb-6">
        This is the fallback language when no language is set on a company, contact, or user.
      </p>

      <div class="space-y-3 mb-6">
        {#each languageOptions as opt}
          <label
            class="flex items-center gap-3 p-3 rounded-lg border cursor-pointer {language === opt.value ? 'border-indigo-400 bg-indigo-50' : 'border-gray-200 hover:border-gray-300'}"
          >
            <input
              type="radio"
              name="preferred_language"
              value={opt.value}
              bind:group={language}
              class="h-4 w-4 text-indigo-600 border-gray-300 focus:ring-indigo-500"
            />
            <span class="text-sm font-medium text-gray-900">{opt.label}</span>
          </label>
        {/each}
      </div>

      <button
        on:click={save}
        disabled={saving}
        class="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-md text-sm font-medium disabled:opacity-50"
      >
        {saving ? 'Saving...' : 'Save'}
      </button>
    </div>
  </div>

  <!-- Info box -->
  <div class="mt-4 bg-blue-50 border border-blue-200 rounded-lg p-4">
    <div class="text-sm text-blue-700">
      <p class="font-medium mb-1">Language inheritance</p>
      <ul class="space-y-1 list-disc list-inside text-blue-600">
        <li>Contact preferred language falls back to Company</li>
        <li>Company preferred language falls back to this system default</li>
        <li>User preferred language falls back to this system default</li>
      </ul>
    </div>
  </div>

</div>
