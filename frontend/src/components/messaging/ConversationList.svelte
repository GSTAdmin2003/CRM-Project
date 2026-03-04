<script>
  import { apiGet } from '../../utils/api.js';
  import { onMount } from 'svelte';

  export let apiUrls = {};
  export let selectedId = null;
  export let onSelect = () => {};

  let conversations = [];
  let loading = true;
  let error = '';

  onMount(async () => {
    await fetchConversations();
  });

  async function fetchConversations() {
    loading = true;
    error = '';
    try {
      const res = await apiGet(apiUrls.conversations);
      if (res.ok) {
        const data = await res.json();
        conversations = data.results || data;
      } else {
        error = 'Failed to load conversations';
      }
    } catch {
      error = 'Failed to load conversations';
    } finally {
      loading = false;
    }
  }

  function selectConversation(conv) {
    selectedId = conv.id;
    onSelect(conv);
    // Mark unread count as 0 optimistically
    conversations = conversations.map((c) =>
      c.id === conv.id ? { ...c, unread_count: 0 } : c
    );
  }

  function formatTime(ts) {
    if (!ts) return '';
    const d = new Date(ts);
    const now = new Date();
    const isToday = d.toDateString() === now.toDateString();
    return isToday
      ? d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      : d.toLocaleDateString([], { month: 'short', day: 'numeric' });
  }
</script>

<div class="flex flex-col h-full border-r border-gray-200">
  <div class="px-4 py-3 border-b border-gray-100 flex items-center gap-2">
    <svg class="w-5 h-5 text-green-500 flex-shrink-0" fill="currentColor" viewBox="0 0 24 24">
      <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/>
      <path d="M11.5 2C6.253 2 2 6.253 2 11.5c0 1.822.496 3.525 1.355 4.991L2.05 21.95l5.514-1.285A9.45 9.45 0 0011.5 21C16.747 21 21 16.747 21 11.5S16.747 2 11.5 2z"/>
    </svg>
    <h2 class="text-sm font-semibold text-gray-900">WhatsApp Inbox</h2>
    {#if !loading}
      <span class="ml-auto text-xs text-gray-400">{conversations.length}</span>
    {/if}
  </div>

  <div class="flex-1 overflow-y-auto divide-y divide-gray-50">
    {#if loading}
      <div class="flex items-center justify-center py-10 text-gray-400 text-sm">
        <svg class="w-4 h-4 animate-spin mr-2" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
        </svg>
        Loading…
      </div>
    {:else if error}
      <p class="text-center py-8 text-red-500 text-sm">{error}</p>
    {:else if conversations.length === 0}
      <p class="text-center py-10 text-gray-400 text-sm">No conversations.</p>
    {:else}
      {#each conversations as conv (conv.id)}
        <button
          type="button"
          class="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-gray-50 transition-colors
            {selectedId === conv.id ? 'bg-green-50 border-r-2 border-green-500' : ''}"
          on:click={() => selectConversation(conv)}
        >
          <!-- Avatar -->
          <div class="w-10 h-10 rounded-full bg-green-100 flex items-center justify-center text-green-700 font-semibold text-sm flex-shrink-0">
            {(conv.display_name || '?')[0].toUpperCase()}
          </div>

          <div class="flex-1 min-w-0">
            <div class="flex items-center justify-between">
              <p class="text-sm font-medium text-gray-900 truncate">{conv.display_name || conv.phone_number}</p>
              <div class="flex items-center gap-1 flex-shrink-0 ml-2">
                {#if conv.unread_count > 0}
                  <span class="bg-green-500 text-white text-xs rounded-full px-1.5 py-0.5 min-w-5 text-center font-medium">
                    {conv.unread_count > 9 ? '9+' : conv.unread_count}
                  </span>
                {/if}
                <span class="text-xs text-gray-400">{formatTime(conv.last_message_at)}</span>
              </div>
            </div>
            {#if conv.last_message_preview}
              <p class="text-xs text-gray-500 truncate mt-0.5">{conv.last_message_preview}</p>
            {/if}
          </div>
        </button>
      {/each}
    {/if}
  </div>
</div>
