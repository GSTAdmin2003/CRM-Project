<script>
  import { apiDelete, apiPost, apiPatch } from '../../utils/api.js';
  import ConfirmModal from '../shared/ConfirmModal.svelte';
  import StatusBadge from '../shared/StatusBadge.svelte';

  export let lead = {};
  export let apiUrls = {};

  let showDeleteModal = false;
  let showConvertModal = false;
  let showRejectModal = false;
  let deleting = false;
  let converting = false;
  let rejecting = false;

  $: isActioned = lead.status === 'converted' || lead.status === 'rejected';

  function formatCurrency(value) {
    if (value == null) return '—';
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
  }

  function formatDate(dateStr) {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
  }

  async function doDelete() {
    deleting = true;
    const res = await apiDelete(`${apiUrls.leads || '/crm/api/leads/'}${lead.id}/`);
    if (res.ok) {
      window.location.href = '/crm/leads/';
    }
    deleting = false;
    showDeleteModal = false;
  }

  async function doConvert() {
    converting = true;
    const res = await apiPost(apiUrls.convertToOpportunity || `/crm/api/leads/${lead.id}/convert/`, {});
    converting = false;
    showConvertModal = false;
    if (res.ok) {
      const data = await res.json().catch(() => ({}));
      const newId = data.id || data.opportunity_id;
      if (newId) {
        window.location.href = `/crm/opportunities/${newId}/edit/`;
      } else {
        window.location.href = '/crm/opportunities/';
      }
    }
  }

  async function doReject() {
    rejecting = true;
    const res = await apiPatch(apiUrls.lead || `/crm/api/leads/${lead.id}/`, { status: 'rejected' });
    rejecting = false;
    showRejectModal = false;
    if (res.ok) {
      lead = { ...lead, status: 'rejected' };
    }
  }

  const STATUS_MAP = {
    new:       { label: 'Lead',      color: 'blue'  },
    converted: { label: 'Converted', color: 'green' },
    rejected:  { label: 'Lost',      color: 'red'   },
  };
</script>

<div class="max-w-6xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
  <!-- Header -->
  <div class="mb-6 flex items-start justify-between">
    <div>
      <div class="flex items-center gap-3 mb-1">
        <h1 class="text-3xl font-bold tracking-tight text-gray-900">{lead.title || 'Lead Detail'}</h1>
        <StatusBadge status={lead.status} map={STATUS_MAP} />
      </div>
      {#if lead.contact_full_name}
        <p class="text-lg text-gray-600">{lead.contact_full_name}</p>
      {/if}
    </div>
    <div class="flex items-center gap-3">
      {#if !isActioned}
        <button
          type="button"
          class="px-4 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 rounded-md transition-colors"
          on:click={() => (showConvertModal = true)}
        >
          Convert
        </button>
        <button
          type="button"
          class="px-4 py-2 text-sm font-medium text-white bg-orange-500 hover:bg-orange-600 rounded-md transition-colors"
          on:click={() => (showRejectModal = true)}
        >
          Lost
        </button>
      {/if}
      <a
        href="/crm/leads/{lead.id}/edit/"
        class="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors"
      >
        Edit
      </a>
      <button
        type="button"
        class="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-md transition-colors"
        on:click={() => (showDeleteModal = true)}
      >
        Delete
      </button>
    </div>
  </div>

  <!-- Info Grid -->
  <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
    <div class="bg-white border border-gray-200 rounded-xl p-6 space-y-4">
      <h3 class="text-base font-semibold text-gray-900 border-b border-gray-100 pb-2">Details</h3>

      <div class="grid grid-cols-2 gap-4 text-sm">
        <div>
          <p class="text-xs font-medium text-gray-500 uppercase tracking-wide mb-0.5">Contact</p>
          <p class="text-gray-900">{lead.contact_full_name || '—'}</p>
        </div>
        <div>
          <p class="text-xs font-medium text-gray-500 uppercase tracking-wide mb-0.5">Stage</p>
          <p class="text-gray-900">{lead.stage?.name || '—'}</p>
        </div>
        <div>
          <p class="text-xs font-medium text-gray-500 uppercase tracking-wide mb-0.5">Estimated Value</p>
          <p class="text-green-700 font-medium">{formatCurrency(lead.estimated_value)}</p>
        </div>
        <div>
          <p class="text-xs font-medium text-gray-500 uppercase tracking-wide mb-0.5">Assigned To</p>
          <p class="text-gray-900">{lead.assigned_to_name || '—'}</p>
        </div>
        <div>
          <p class="text-xs font-medium text-gray-500 uppercase tracking-wide mb-0.5">Created</p>
          <p class="text-gray-900">{formatDate(lead.created_at)}</p>
        </div>
      </div>
    </div>

    {#if lead.notes}
      <div class="bg-white border border-gray-200 rounded-xl p-6">
        <h3 class="text-base font-semibold text-gray-900 border-b border-gray-100 pb-2 mb-3">Notes</h3>
        <textarea
          readonly
          class="w-full h-40 px-3 py-2 border border-gray-200 rounded-md text-sm text-gray-700 bg-gray-50 resize-none focus:outline-none"
          value={lead.notes}
        ></textarea>
      </div>
    {/if}
  </div>
</div>

{#if showDeleteModal}
  <ConfirmModal
    title="Delete Lead"
    message="Are you sure you want to delete this lead? This action cannot be undone."
    confirmLabel="Delete"
    loading={deleting}
    danger={true}
    onConfirm={doDelete}
    onCancel={() => { if (!deleting) showDeleteModal = false; }}
  />
{/if}

{#if showRejectModal}
  <ConfirmModal
    title="Mark as Lost"
    message="Mark this lead as lost? It will be set to Rejected status."
    confirmLabel="Mark Lost"
    loading={rejecting}
    danger={false}
    onConfirm={doReject}
    onCancel={() => { if (!rejecting) showRejectModal = false; }}
  />
{/if}

{#if showConvertModal}
  <ConfirmModal
    title="Convert to Opportunity"
    message="Convert this lead to a sales opportunity? The lead will be marked as converted."
    confirmLabel="Convert"
    loading={converting}
    danger={false}
    onConfirm={doConvert}
    onCancel={() => { if (!converting) showConvertModal = false; }}
  />
{/if}
