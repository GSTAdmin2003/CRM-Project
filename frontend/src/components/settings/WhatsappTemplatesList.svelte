<script>
  import { onMount } from 'svelte';
  import { apiGet, apiPost, apiDelete } from '../../utils/api.js';
  import { showToast } from '../shared/toastStore.js';
  import Toast from '../shared/Toast.svelte';
  import ConfirmModal from '../shared/ConfirmModal.svelte';

  export let apiUrls = {};

  let templates = [];
  let loading = true;
  let refreshing = false;
  let deleteTarget = null;
  let deleting = false;
  let actionLoading = {}; // track per-template action loading

  $: templateGroups = groupByName(templates);

  function groupByName(list) {
    const map = new Map();
    for (const t of list) {
      if (!map.has(t.name)) map.set(t.name, []);
      map.get(t.name).push(t);
    }
    return [...map.values()];
  }

  function resolveUrl(pattern, id) {
    return pattern.replace('{id}', id);
  }

  onMount(async () => {
    await loadTemplates();
  });

  async function loadTemplates() {
    loading = true;
    const res = await apiGet(apiUrls.templates);
    if (res.ok) {
      templates = await res.json();
    } else {
      showToast('error', 'Failed to load templates.');
    }
    loading = false;
  }

  async function refreshStatuses() {
    refreshing = true;
    const res = await apiPost(apiUrls.refresh, {});
    if (res.ok) {
      const data = await res.json();
      showToast('success', `Statuses refreshed. ${data.updated ?? 0} template(s) updated.`);
      await loadTemplates();
    } else {
      const data = await res.json().catch(() => ({}));
      showToast('error', data.error || 'Failed to refresh statuses.');
    }
    refreshing = false;
  }

  async function submitTemplate(tmpl) {
    actionLoading = { ...actionLoading, [`submit_${tmpl.id}`]: true };
    const url = resolveUrl(apiUrls.submit, tmpl.id);
    const res = await apiPost(url, {});
    if (res.ok) {
      showToast('success', `'${tmpl.display_name}' submitted for approval.`);
      await loadTemplates();
    } else {
      const data = await res.json().catch(() => ({}));
      showToast('error', data.error || 'Submission failed.');
    }
    actionLoading = { ...actionLoading, [`submit_${tmpl.id}`]: false };
  }

  async function deleteFromMeta(tmpl) {
    actionLoading = { ...actionLoading, [`meta_${tmpl.id}`]: true };
    const url = resolveUrl(apiUrls.deleteFromMeta, tmpl.id);
    const res = await apiPost(url, {});
    if (res.ok) {
      showToast('success', `'${tmpl.display_name}' deleted from Meta.`);
      await loadTemplates();
    } else {
      const data = await res.json().catch(() => ({}));
      showToast('error', data.error || 'Delete from Meta failed.');
    }
    actionLoading = { ...actionLoading, [`meta_${tmpl.id}`]: false };
  }

  async function deleteFromDb() {
    deleting = true;
    const url = resolveUrl(apiUrls.templateDetail, deleteTarget.id);
    const res = await apiDelete(url);
    if (res.ok) {
      templates = templates.filter(t => t.id !== deleteTarget.id);
      showToast('success', `'${deleteTarget.display_name}' deleted.`);
    } else {
      showToast('error', 'Failed to delete template.');
    }
    deleting = false;
    deleteTarget = null;
  }

  const STATUS_STYLES = {
    approved: 'bg-green-100 text-green-800',
    pending: 'bg-amber-100 text-amber-800',
    rejected: 'bg-red-100 text-red-800',
    paused: 'bg-orange-100 text-orange-800',
    draft: 'bg-gray-100 text-gray-600',
  };

  function statusStyle(s) {
    return STATUS_STYLES[s] || STATUS_STYLES.draft;
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
{:else}
  <div class="space-y-6">
    <!-- System notice -->
    <div class="flex items-start px-4 py-3 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-800">
      <svg class="w-4 h-4 mr-3 mt-0.5 flex-shrink-0 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
      </svg>
      <div>
        <p class="font-medium">Templates are system-managed</p>
        <p class="mt-0.5 text-blue-700">
          The <strong>sales_pitch</strong> template exists in English and Georgian.
          Submit each language for Meta approval separately. Once approved, agents can send pitches from lead pages.
        </p>
      </div>
    </div>

    {#if templateGroups.length > 0}
      <div class="overflow-hidden border border-gray-200 rounded-lg">
        <table class="min-w-full divide-y divide-gray-200 text-sm">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-4 py-3 text-left font-medium text-gray-500 uppercase tracking-wide text-xs">Template</th>
              <th class="px-4 py-3 text-left font-medium text-gray-500 uppercase tracking-wide text-xs">Body Preview</th>
              <th class="px-4 py-3 text-left font-medium text-gray-500 uppercase tracking-wide text-xs">Languages</th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-100">
            {#each templateGroups as group}
              <tr class="hover:bg-gray-50 align-top">
                <td class="px-4 py-3 whitespace-nowrap">
                  <p class="font-medium text-gray-900">{group[0].display_name}</p>
                  <code class="text-xs bg-gray-100 px-1.5 py-0.5 rounded font-mono text-gray-600">{group[0].name}</code>
                </td>
                <td class="px-4 py-3 text-gray-600 max-w-xs">
                  <p class="truncate">{group[0].body_preview}</p>
                  {#if group[0].variable_names && group[0].variable_names.length > 0}
                    <div class="flex flex-wrap gap-1 mt-1">
                      {#each group[0].variable_names as vname, i}
                        <span class="inline-flex items-center px-1.5 py-0.5 rounded text-xs bg-indigo-50 text-indigo-700 border border-indigo-100">
                          {i + 1}. {vname}
                        </span>
                      {/each}
                    </div>
                  {/if}
                </td>
                <td class="px-4 py-3">
                  <div class="space-y-2">
                    {#each group as tmpl}
                      <div class="flex items-center gap-2 flex-wrap">
                        <span class="inline-block px-2 py-0.5 rounded text-xs font-mono font-medium bg-gray-100 text-gray-700 border border-gray-200">
                          {tmpl.language}
                        </span>
                        <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium {statusStyle(tmpl.approval_status)}">
                          {tmpl.approval_status || 'draft'}
                        </span>

                        {#if tmpl.approval_status === 'draft' || tmpl.approval_status === 'rejected'}
                          <button
                            type="button"
                            disabled={actionLoading[`submit_${tmpl.id}`]}
                            on:click={() => submitTemplate(tmpl)}
                            class="text-indigo-600 hover:text-indigo-800 text-xs font-medium disabled:opacity-40"
                          >
                            {actionLoading[`submit_${tmpl.id}`] ? 'Submitting...' : 'Send for Approval'}
                          </button>
                        {:else if tmpl.approval_status === 'pending'}
                          <span class="text-xs text-amber-600">Awaiting Meta</span>
                        {:else if tmpl.approval_status === 'approved'}
                          <span class="text-xs text-green-600">Ready</span>
                          <button
                            type="button"
                            disabled={actionLoading[`meta_${tmpl.id}`]}
                            on:click={() => deleteFromMeta(tmpl)}
                            class="text-gray-400 hover:text-red-500 text-xs disabled:opacity-40"
                            title="Delete from Meta so you can resubmit cleanly"
                          >
                            {actionLoading[`meta_${tmpl.id}`] ? '...' : 'Delete from Meta'}
                          </button>
                        {/if}

                        <button
                          type="button"
                          on:click={() => (deleteTarget = tmpl)}
                          class="text-gray-300 hover:text-red-500 text-xs"
                          title="Delete from database"
                        >
                          Delete DB
                        </button>
                      </div>
                    {/each}
                  </div>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {:else}
      <div class="py-16 text-center border border-dashed border-gray-300 rounded-lg">
        <p class="text-gray-500 font-medium">No templates found</p>
        <p class="text-gray-400 text-sm mt-1">Run <code class="bg-gray-100 px-1 rounded">python manage.py migrate</code> to seed the default sales_pitch templates.</p>
      </div>
    {/if}

    <div class="pt-4 border-t border-gray-100 flex items-center justify-between flex-wrap gap-3">
      <div class="flex items-center space-x-4">
        <a href="/settings/whatsapp/" class="inline-flex items-center text-sm text-gray-500 hover:text-gray-700 font-medium">
          &larr; Back to Configuration
        </a>
        <a href="/messaging/inbox/" class="inline-flex items-center text-sm text-green-600 hover:text-green-800 font-medium">
          Open Inbox
        </a>
        <button
          type="button"
          on:click={refreshStatuses}
          disabled={refreshing}
          class="inline-flex items-center text-sm text-indigo-600 hover:text-indigo-800 font-medium disabled:opacity-40"
        >
          {refreshing ? 'Refreshing...' : 'Refresh Statuses'}
        </button>
      </div>
      <a href="/settings/crm/sales-pitch/" class="inline-flex items-center text-sm text-indigo-600 hover:text-indigo-800 font-medium">
        Manage Team Pitch PDFs &rarr;
      </a>
    </div>
  </div>
{/if}

{#if deleteTarget}
  <ConfirmModal
    title="Delete Template"
    message="Delete '{deleteTarget.display_name}' from the database? This cannot be undone."
    confirmLabel="Delete"
    loading={deleting}
    danger={true}
    onConfirm={deleteFromDb}
    onCancel={() => { if (!deleting) deleteTarget = null; }}
  />
{/if}
