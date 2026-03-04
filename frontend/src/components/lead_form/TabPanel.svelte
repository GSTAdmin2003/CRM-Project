<script>
  import { activeTab } from '../../stores/uiStore.js';
  import NotesTab from './NotesTab.svelte';
  import ActivitiesTab from './ActivitiesTab.svelte';
  import WhatsAppTab from './WhatsAppTab.svelte';

  export let lead = {};
  export let leadId = null;
  export let apiUrls = {};
  export let activityTypes = [];
  export let waConversationId = null;
  export let onLeadUpdated = () => {};

  const TABS = [
    { id: 'notes', label: 'Notes' },
    { id: 'activities', label: 'Activities' },
    { id: 'whatsapp', label: 'WhatsApp' },
  ];
</script>

<div class="bg-white rounded-lg border border-gray-200">
  <!-- Tab headers -->
  <div class="flex border-b border-gray-200">
    {#each TABS as tab}
      <button
        type="button"
        class="flex-1 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors
          {$activeTab === tab.id
            ? 'border-blue-600 text-blue-600'
            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}"
        on:click={() => activeTab.set(tab.id)}
      >
        {tab.label}
      </button>
    {/each}
  </div>

  <!-- Tab content -->
  <div class="p-4">
    {#if $activeTab === 'notes'}
      <NotesTab {lead} {apiUrls} {onLeadUpdated} />
    {:else if $activeTab === 'activities'}
      <ActivitiesTab {leadId} {apiUrls} {activityTypes} />
    {:else if $activeTab === 'whatsapp'}
      <WhatsAppTab conversationId={waConversationId} {apiUrls} />
    {/if}
  </div>
</div>
