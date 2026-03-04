<script>
  import { apiGet, apiPost } from '../../utils/api.js';

  export let apiUrls = {};
  export let activityTypes = [];
  export let onCreated = () => {};
  export let show = false;

  let creating = false;
  let error = '';
  let leads = [];
  let leadSearchQuery = '';
  let leadSearchTimeout = null;

  let form = {
    activity_type_id: '',
    title: '',
    scheduled_date: new Date().toISOString().split('T')[0],
    description: '',
    lead_id: '',
  };

  function close() {
    show = false;
    error = '';
    form = {
      activity_type_id: '',
      title: '',
      scheduled_date: new Date().toISOString().split('T')[0],
      description: '',
      lead_id: '',
    };
    leads = [];
    leadSearchQuery = '';
  }

  async function searchLeads() {
    if (leadSearchQuery.length < 2) { leads = []; return; }
    try {
      const res = await apiGet(`/crm/api/leads/?search=${encodeURIComponent(leadSearchQuery)}&lead_type=opportunity`);
      if (res.ok) {
        const data = await res.json();
        leads = (data.results || data).slice(0, 8);
      }
    } catch { leads = []; }
  }

  function onLeadInput() {
    clearTimeout(leadSearchTimeout);
    leadSearchTimeout = setTimeout(searchLeads, 300);
  }

  async function submit() {
    if (creating || !form.title || !form.activity_type_id) return;
    creating = true;
    error = '';
    try {
      const payload = {
        ...form,
        activity_type_id: Number(form.activity_type_id),
        lead_id: form.lead_id ? Number(form.lead_id) : null,
      };
      const res = await apiPost(apiUrls.activities, payload);
      if (res.ok) {
        const created = await res.json();
        onCreated(created);
        close();
      } else {
        const err = await res.json().catch(() => ({}));
        error = JSON.stringify(err);
      }
    } catch {
      error = 'Failed to create activity';
    } finally {
      creating = false;
    }
  }
</script>

{#if show}
  <!-- Backdrop -->
  <div
    class="fixed inset-0 bg-black/40 z-40 flex items-center justify-center p-4"
    on:click|self={close}
    role="dialog"
    aria-modal="true"
  >
    <div class="bg-white rounded-xl shadow-xl w-full max-w-md z-50">
      <div class="flex items-center justify-between px-5 py-4 border-b border-gray-100">
        <h2 class="text-base font-semibold text-gray-900">New Activity</h2>
        <button type="button" class="text-gray-400 hover:text-gray-600" on:click={close}>
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
          </svg>
        </button>
      </div>

      <div class="p-5 space-y-3">
        <!-- Type + Date -->
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-xs font-medium text-gray-500 mb-1">Type *</label>
            <select
              bind:value={form.activity_type_id}
              class="w-full border border-gray-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select type…</option>
              {#each activityTypes as t}
                <option value={t.id}>{t.name}</option>
              {/each}
            </select>
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-500 mb-1">Date *</label>
            <input
              type="date"
              bind:value={form.scheduled_date}
              class="w-full border border-gray-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        <!-- Title -->
        <div>
          <label class="block text-xs font-medium text-gray-500 mb-1">Title *</label>
          <input
            type="text"
            bind:value={form.title}
            placeholder="Activity title"
            class="w-full border border-gray-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <!-- Linked opportunity (search) -->
        <div class="relative">
          <label class="block text-xs font-medium text-gray-500 mb-1">Opportunity (optional)</label>
          <input
            type="text"
            bind:value={leadSearchQuery}
            on:input={onLeadInput}
            placeholder="Search opportunity…"
            class="w-full border border-gray-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          {#if leads.length > 0}
            <ul class="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow max-h-40 overflow-y-auto">
              {#each leads as lead}
                <li>
                  <button
                    type="button"
                    class="w-full text-left px-3 py-2 text-sm hover:bg-gray-50"
                    on:click={() => {
                      form.lead_id = lead.id;
                      leadSearchQuery = lead.title;
                      leads = [];
                    }}
                  >{lead.title}</button>
                </li>
              {/each}
            </ul>
          {/if}
        </div>

        <!-- Description -->
        <div>
          <label class="block text-xs font-medium text-gray-500 mb-1">Description</label>
          <textarea
            bind:value={form.description}
            rows="3"
            class="w-full border border-gray-200 rounded px-3 py-1.5 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
          ></textarea>
        </div>

        {#if error}
          <p class="text-xs text-red-500">{error}</p>
        {/if}
      </div>

      <div class="flex justify-end gap-2 px-5 py-4 border-t border-gray-100">
        <button type="button" class="px-4 py-2 text-sm text-gray-600 hover:text-gray-900" on:click={close}>Cancel</button>
        <button
          type="button"
          class="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
          disabled={creating || !form.title || !form.activity_type_id}
          on:click={submit}
        >
          {creating ? 'Creating…' : 'Create Activity'}
        </button>
      </div>
    </div>
  </div>
{/if}
