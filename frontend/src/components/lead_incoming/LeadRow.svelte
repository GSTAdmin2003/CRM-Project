<script>
  import { apiPost } from '../../utils/api.js';

  export let lead = {};
  export let apiUrls = {};
  export let onConverted = () => {};
  export let isSelected = false;

  let converting = false;

  const STATUS_BADGE = {
    new: 'bg-blue-100 text-blue-800',
    converted: 'bg-green-100 text-green-800',
    rejected: 'bg-red-100 text-red-800',
  };

  async function convert(e) {
    e.stopPropagation();
    if (!confirm(`Convert "${lead.title || lead.company_name}" to an opportunity?`)) return;
    converting = true;
    try {
      const res = await apiPost(`/crm/api/leads/${lead.id}/convert/`, {});
      if (res.ok) {
        const data = await res.json();
        onConverted(lead.id, data);
      }
    } catch {
      // Ignore
    } finally {
      converting = false;
    }
  }

  function navigate() {
    window.location.href = apiUrls.leadEdit.replace('{id}', lead.id);
  }
</script>

<tr
  class="hover:bg-gray-50 cursor-pointer transition-colors border-b border-gray-100 last:border-b-0"
  on:click={navigate}
>
  <td class="px-4 py-3 w-8">
    <input
      type="checkbox"
      bind:checked={isSelected}
      on:click|stopPropagation
      class="rounded border-gray-300"
    />
  </td>
  <td class="px-4 py-3">
    <p class="text-sm font-medium text-gray-900">{lead.title || lead.company_name || '—'}</p>
    {#if lead.company_name_display && lead.company_name_display !== lead.title}
      <p class="text-xs text-gray-500">{lead.company_name_display}</p>
    {/if}
  </td>
  <td class="px-4 py-3 text-sm text-gray-600">{lead.assigned_to_name || '—'}</td>
  <td class="px-4 py-3 text-sm text-gray-600">
    {#if lead.message}
      <span class="truncate max-w-xs block" title={lead.message}>{lead.message.slice(0, 60)}{lead.message.length > 60 ? '…' : ''}</span>
    {:else}
      —
    {/if}
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
      class="px-3 py-1 bg-indigo-600 text-white rounded text-xs font-medium hover:bg-indigo-700 transition-colors disabled:opacity-50"
      disabled={converting}
      on:click={convert}
    >
      {converting ? 'Converting…' : 'Convert'}
    </button>
  </td>
</tr>
