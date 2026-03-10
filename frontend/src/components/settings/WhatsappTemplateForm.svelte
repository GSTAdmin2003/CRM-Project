<script>
  import { apiPost, apiFetch } from '../../utils/api.js';
  import { showToast } from '../shared/toastStore.js';
  import Toast from '../shared/Toast.svelte';

  export let apiUrls = {};
  export let template = null;

  const editMode = template !== null;

  let name = template?.name ?? '';
  let display_name = template?.display_name ?? '';
  let language = template?.language ?? 'en';
  let body_preview = template?.body_preview ?? '';
  let variable_names_text = (template?.variable_names ?? []).join(', ');
  let is_active = template?.is_active ?? true;
  let saving = false;
  let errors = {};

  const LANGUAGES = [
    { value: 'en', label: 'English (en)' },
    { value: 'ka', label: 'Georgian (ka)' },
  ];

  async function save() {
    saving = true;
    errors = {};

    const variable_names = variable_names_text
      .split(',')
      .map(s => s.trim())
      .filter(Boolean);

    const body = { name, display_name, language, body_preview, variable_names, is_active };

    let res;
    if (editMode) {
      res = await apiFetch(apiUrls.templateDetail, {
        method: 'PUT',
        body: JSON.stringify(body),
      });
    } else {
      res = await apiFetch(apiUrls.templates, {
        method: 'POST',
        body: JSON.stringify(body),
      });
    }

    if (res.ok) {
      showToast('success', editMode ? 'Template updated.' : 'Template created.');
      setTimeout(() => {
        window.location.href = apiUrls.listUrl;
      }, 800);
    } else {
      const data = await res.json().catch(() => ({}));
      if (typeof data === 'object') {
        errors = data;
      }
      showToast('error', 'Please correct the errors below.');
    }
    saving = false;
  }
</script>

<Toast />

<div class="space-y-8">
  <div class="space-y-5">
    <h3 class="text-sm font-semibold text-gray-900 uppercase tracking-wide border-b border-gray-200 pb-2">
      Template Identity
    </h3>

    <div class="grid grid-cols-1 sm:grid-cols-2 gap-5">
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">
          Template Name <span class="text-red-500">*</span>
        </label>
        <input
          type="text"
          bind:value={name}
          class="w-full text-sm border {errors.name ? 'border-red-400' : 'border-gray-300'} rounded-lg px-3 py-2 focus:ring-1 focus:ring-green-500 focus:border-green-500"
          placeholder="sales_pitch"
        />
        {#if errors.name}
          <p class="mt-1 text-xs text-red-600">{errors.name}</p>
        {/if}
        <p class="mt-1 text-xs text-gray-500">Exact name registered in Meta (lowercase, underscores).</p>
      </div>

      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">
          Display Name <span class="text-red-500">*</span>
        </label>
        <input
          type="text"
          bind:value={display_name}
          class="w-full text-sm border {errors.display_name ? 'border-red-400' : 'border-gray-300'} rounded-lg px-3 py-2 focus:ring-1 focus:ring-green-500 focus:border-green-500"
          placeholder="Sales Pitch (English)"
        />
        {#if errors.display_name}
          <p class="mt-1 text-xs text-red-600">{errors.display_name}</p>
        {/if}
        <p class="mt-1 text-xs text-gray-500">Friendly label shown to agents in the dropdown.</p>
      </div>
    </div>

    <div class="max-w-xs">
      <label class="block text-sm font-medium text-gray-700 mb-1">
        Language <span class="text-red-500">*</span>
      </label>
      <select
        bind:value={language}
        class="w-full text-sm border {errors.language ? 'border-red-400' : 'border-gray-300'} rounded-lg px-3 py-2 focus:ring-1 focus:ring-green-500 focus:border-green-500"
      >
        {#each LANGUAGES as lang}
          <option value={lang.value}>{lang.label}</option>
        {/each}
      </select>
      {#if errors.language}
        <p class="mt-1 text-xs text-red-600">{errors.language}</p>
      {/if}
    </div>
  </div>

  <!-- Template Content -->
  <div class="space-y-5">
    <h3 class="text-sm font-semibold text-gray-900 uppercase tracking-wide border-b border-gray-200 pb-2">
      Template Content
    </h3>

    <div>
      <label class="block text-sm font-medium text-gray-700 mb-1">
        Body Preview <span class="text-red-500">*</span>
      </label>
      <textarea
        bind:value={body_preview}
        rows="5"
        class="w-full text-sm border {errors.body_preview ? 'border-red-400' : 'border-gray-300'} rounded-lg px-3 py-2 focus:ring-1 focus:ring-green-500 focus:border-green-500"
        placeholder="Hello {'{{'+'1'+'}}' }, we have an offer for you..."
      ></textarea>
      {#if errors.body_preview}
        <p class="mt-1 text-xs text-red-600">{errors.body_preview}</p>
      {/if}
      <p class="mt-1 text-xs text-gray-500">
        Copy the body text from Meta exactly. Use <code class="font-mono">&#123;&#123;1&#125;&#125;</code>,
        <code class="font-mono">&#123;&#123;2&#125;&#125;</code> etc. for variables.
      </p>
    </div>

    <div>
      <label class="block text-sm font-medium text-gray-700 mb-1">Variable Names</label>
      <input
        type="text"
        bind:value={variable_names_text}
        class="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:ring-1 focus:ring-green-500 focus:border-green-500"
        placeholder="Customer Name, Appointment Date"
      />
      <p class="mt-1 text-xs text-gray-500">
        Comma-separated labels for each placeholder in order. Leave blank if no variables.
      </p>
    </div>
  </div>

  <!-- Active toggle -->
  <div class="flex items-start space-x-3">
    <input
      type="checkbox"
      id="is_active"
      bind:checked={is_active}
      class="mt-0.5 h-4 w-4 rounded border-gray-300 text-green-600 focus:ring-green-500"
    />
    <div>
      <label for="is_active" class="text-sm font-medium text-gray-700 cursor-pointer">Active</label>
      <p class="text-xs text-gray-500 mt-0.5">Inactive templates are hidden from the New Chat modal.</p>
    </div>
  </div>

  <!-- Actions -->
  <div class="pt-6 border-t border-gray-200 flex items-center justify-between">
    <a
      href={apiUrls.listUrl}
      class="text-sm text-gray-500 hover:text-gray-700 font-medium"
    >
      &larr; Back to Templates
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
      {editMode ? 'Save Changes' : 'Create Template'}
    </button>
  </div>
</div>
