<script>
  import { apiGet, apiPost } from '../../utils/api.js';
  import { onMount, onDestroy, afterUpdate } from 'svelte';

  export let conversation = null;
  export let apiUrls = {};
  export let userLanguage = 'en';

  let messages = [];
  let loading = false;
  let newMessage = '';
  let sending = false;
  let sendingHi = false;
  let messagesEl;
  let ws = null;
  let lastConvId = null;

  $: if (conversation && conversation.id !== lastConvId) {
    lastConvId = conversation.id;
    loadMessages();
    reconnectWs();
  }

  onDestroy(() => {
    disconnectWs();
  });

  async function loadMessages() {
    if (!conversation) return;
    loading = true;
    try {
      const url = `${apiUrls.conversations}${conversation.id}/messages/`;
      const res = await apiGet(url);
      if (res.ok) {
        const data = await res.json();
        messages = data.results || data;
      }
    } catch {
      // Ignore
    } finally {
      loading = false;
    }
  }

  function reconnectWs() {
    disconnectWs();
    if (!conversation) return;
    const wsProto = location.protocol === 'https:' ? 'wss' : 'ws';
    ws = new WebSocket(`${wsProto}://${location.host}/ws/messaging/${conversation.id}/`);
    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.type === 'message' && data.message) {
          // Avoid dupes
          if (!messages.find((m) => m.id === data.message.id)) {
            messages = [...messages, data.message];
          }
        }
      } catch { /* Ignore */ }
    };
    ws.onclose = () => { ws = null; };
  }

  function disconnectWs() {
    if (ws) { ws.close(); ws = null; }
  }

  async function send() {
    if (!newMessage.trim() || sending || !conversation) return;
    sending = true;
    const body = newMessage.trim();
    newMessage = '';
    try {
      const res = await apiPost(`${apiUrls.conversations}${conversation.id}/messages/`, { body });
      if (res.ok) {
        const msg = await res.json();
        messages = [...messages, msg];
      } else {
        newMessage = body; // restore
      }
    } catch {
      newMessage = body;
    } finally {
      sending = false;
    }
  }

  async function sendHi() {
    if (sendingHi || !conversation) return;
    sendingHi = true;
    try {
      const res = await apiPost(
        `${apiUrls.conversations}${conversation.id}/send_named_template/`,
        { template_name: 'hello_how_are_you', language: userLanguage }
      );
      if (res.ok) {
        const msg = await res.json();
        messages = [...messages, msg];
      }
    } catch {
      // Ignore
    } finally {
      sendingHi = false;
    }
  }

  function handleKeydown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  afterUpdate(() => {
    if (messagesEl) messagesEl.scrollTop = messagesEl.scrollHeight;
  });

  const STATUS_ICON = { sent: '✓', delivered: '✓✓', read: '✓✓', failed: '✗', received: '↩' };
</script>

{#if !conversation}
  <div class="flex-1 flex items-center justify-center text-gray-400">
    <div class="text-center">
      <svg class="w-14 h-14 mx-auto mb-3 text-gray-200" fill="currentColor" viewBox="0 0 24 24">
        <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/>
        <path d="M11.5 2C6.253 2 2 6.253 2 11.5c0 1.822.496 3.525 1.355 4.991L2.05 21.95l5.514-1.285A9.45 9.45 0 0011.5 21C16.747 21 21 16.747 21 11.5S16.747 2 11.5 2z"/>
      </svg>
      <p class="text-sm">Select a conversation to start chatting</p>
    </div>
  </div>
{:else}
  <div class="flex flex-col h-full">
    <!-- Header -->
    <div class="px-4 py-3 border-b border-gray-100 flex items-center gap-3 bg-white">
      <div class="w-9 h-9 rounded-full bg-green-100 flex items-center justify-center text-green-700 font-semibold text-sm flex-shrink-0">
        {(conversation.display_name || '?')[0].toUpperCase()}
      </div>
      <div class="flex-1 min-w-0">
        <p class="text-sm font-semibold text-gray-900">{conversation.display_name || conversation.phone_number}</p>
        <p class="text-xs text-gray-400">{conversation.phone_number}</p>
      </div>
      {#if conversation.lead}
        <a
          href="/crm/opportunities/{conversation.lead}/edit/"
          class="text-xs text-indigo-600 hover:text-indigo-800 font-medium"
        >View lead</a>
      {/if}
    </div>

    <!-- Messages -->
    <div class="flex-1 overflow-y-auto p-4 space-y-2 bg-gray-50" bind:this={messagesEl}>
      {#if loading}
        <div class="flex items-center justify-center py-8 text-gray-400 text-sm">
          <svg class="w-4 h-4 animate-spin mr-2" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
          </svg>
          Loading…
        </div>
      {:else if messages.length === 0}
        <div class="flex flex-col items-center justify-center h-full gap-4 text-center">
          <svg class="w-12 h-12 text-gray-200" fill="currentColor" viewBox="0 0 24 24">
            <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/>
            <path d="M11.5 2C6.253 2 2 6.253 2 11.5c0 1.822.496 3.525 1.355 4.991L2.05 21.95l5.514-1.285A9.45 9.45 0 0011.5 21C16.747 21 21 16.747 21 11.5S16.747 2 11.5 2z"/>
          </svg>
          <p class="text-sm text-gray-400">No messages yet. Start the conversation.</p>
          <button
            type="button"
            class="flex items-center gap-2 px-5 py-2.5 bg-green-500 text-white text-sm font-medium rounded-xl hover:bg-green-600 disabled:opacity-50 transition-colors"
            disabled={sendingHi}
            on:click={sendHi}
          >
            {#if sendingHi}
              <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
              </svg>
              Sending…
            {:else}
              <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/>
            </svg>
              Send Hi
            {/if}
          </button>
        </div>
      {:else}
        {#each messages as msg (msg.id)}
          {@const isOut = msg.direction === 'outbound'}
          <div class="flex {isOut ? 'justify-end' : 'justify-start'}">
            <div
              class="max-w-xs sm:max-w-sm px-3 py-2 rounded-2xl text-sm shadow-sm
                {isOut ? 'bg-green-500 text-white rounded-br-sm' : 'bg-white text-gray-900 rounded-bl-sm border border-gray-100'}"
            >
              <p class="whitespace-pre-wrap break-words">{msg.body}</p>
              <div class="flex items-center justify-end gap-1 mt-1">
                <span class="text-xs {isOut ? 'opacity-70' : 'text-gray-400'}">
                  {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
                {#if isOut}
                  <span class="text-xs {msg.status === 'read' ? 'text-blue-300' : 'opacity-70'}">
                    {STATUS_ICON[msg.status] || ''}
                  </span>
                {/if}
              </div>
            </div>
          </div>
        {/each}
      {/if}
    </div>

    <!-- Send input (only shown after conversation has started) -->
    {#if messages.length > 0}
    <div class="px-4 py-3 border-t border-gray-100 bg-white flex gap-2 items-end">
      <textarea
        bind:value={newMessage}
        on:keydown={handleKeydown}
        rows="2"
        placeholder="Type a message… (Enter to send)"
        class="flex-1 border border-gray-200 rounded-xl px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-green-500 max-h-28"
      ></textarea>
      <button
        type="button"
        class="w-10 h-10 flex items-center justify-center bg-green-500 text-white rounded-xl hover:bg-green-600 disabled:opacity-50 transition-colors flex-shrink-0"
        disabled={sending || !newMessage.trim()}
        on:click={send}
      >
        {#if sending}
          <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
          </svg>
        {:else}
          <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
            <path d="M2 21l21-9L2 3v7l15 2-15 2v7z"/>
          </svg>
        {/if}
      </button>
    </div>
    {/if}
  </div>
{/if}
