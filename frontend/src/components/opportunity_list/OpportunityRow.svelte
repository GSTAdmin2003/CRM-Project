<script>
  import { apiDelete } from '../../utils/api.js';

  export let lead = {};
  export let apiUrls = {};
  export let onDeleted = () => {};

  let deleting = false;

  function navigate() {
    const url = apiUrls.leadEdit.replace('{id}', lead.id);
    if (typeof window.crmNavigate === 'function') {
      window.crmNavigate(url);
    } else {
      window.location.href = url;
    }
  }

  async function deleteLead(e) {
    e.stopPropagation();
    if (!confirm(`Delete "${lead.title}"?`)) return;
    deleting = true;
    try {
      const url = apiUrls.leadDelete.replace('{id}', lead.id);
      const res = await apiDelete(url);
      if (res.ok || res.status === 204) {
        onDeleted(lead.id);
      }
    } catch {
      // Ignore
    } finally {
      deleting = false;
    }
  }

  const STATUS_BADGE = {
    new: 'bg-blue-100 text-blue-800',
    contacted: 'bg-purple-100 text-purple-800',
    qualified: 'bg-yellow-100 text-yellow-800',
    proposal: 'bg-orange-100 text-orange-800',
    negotiation: 'bg-pink-100 text-pink-800',
    won: 'bg-green-100 text-green-800',
    lost: 'bg-red-100 text-red-800',
    on_hold: 'bg-gray-100 text-gray-600',
  };
</script>

<tr
  class="hover:bg-gray-50 cursor-pointer transition-colors border-b border-gray-100 last:border-b-0"
  on:click={navigate}
>
  <td class="px-4 py-3">
    <p class="text-sm font-medium text-gray-900">{lead.title}</p>
    {#if lead.company_name_display || lead.company_name}
      <p class="text-xs text-gray-500">{lead.company_name_display || lead.company_name}</p>
    {/if}
  </td>
  <td class="px-4 py-3 text-sm text-gray-600">{lead.stage_name || '—'}</td>
  <td class="px-4 py-3 text-sm text-gray-600">{lead.assigned_to_name || '—'}</td>
  <td class="px-4 py-3 text-sm text-gray-600">
    {lead.estimated_value ? `$${Number(lead.estimated_value).toLocaleString()}` : '—'}
  </td>
  <td class="px-4 py-3">
    <span class="text-xs px-2 py-0.5 rounded-full font-medium {STATUS_BADGE[lead.status] || 'bg-gray-100 text-gray-600'}">
      {lead.status}
    </span>
  </td>
  <td class="px-4 py-3 text-xs text-gray-400">
    {lead.created_at ? new Date(lead.created_at).toLocaleDateString() : ''}
  </td>
  <td class="px-4 py-3 text-right">
    <button
      type="button"
      class="p-1.5 text-gray-400 hover:text-red-500 transition-colors disabled:opacity-50"
      disabled={deleting}
      on:click={deleteLead}
      title="Delete"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
          d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
      </svg>
    </button>
  </td>
</tr>
