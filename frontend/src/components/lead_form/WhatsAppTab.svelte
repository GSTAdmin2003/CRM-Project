<script>
  import { apiGet, apiPost } from '../../utils/api.js';
  import { onDestroy, tick } from 'svelte';

  export let conversationId = null;
  export let apiUrls = {};

  let messages = [];
  let loading = true;
  let sending = false;
  let newMessage = '';
  let error = '';
  let sendError = '';
  let messagesEl;
  let ws = null;
  let wsReconnectTimer = null;
  let _activeConvId = null; // tracks which conv the WS is open for

  // 24-hour window: open if customer sent a message within the last 24h
  $: windowOpen = messages.some(
    m => m.direction === 'inbound' &&
         Date.now() - new Date(m.timestamp).getTime() < 24 * 60 * 60 * 1000
  );

  async function sendNamedTemplate(templateName) {
    if (sending || !conversationId) return;
    showTemplates = false;
    sending = true;
    sendError = '';
    try {
      const url = `${apiUrls.conversations}${conversationId}/send_named_template/`;
      const res = await apiPost(url, { template_name: templateName });
      if (res.ok) {
        const msg = await res.json();
        messages = [...messages, msg];
        await scrollToBottom();
      } else {
        let detail = 'Failed to send template';
        try {
          const err = await res.json();
          detail = err.detail || err.error || detail;
        } catch { /* ignore */ }
        sendError = detail;
        console.error('[CRM:WhatsApp] Template send failed:', res.status, detail);
      }
    } catch (e) {
      sendError = 'Failed to send — network error';
      console.error('[CRM:WhatsApp] Template send error (network):', e);
    } finally {
      sending = false;
    }
  }

  $: conversationUrl = conversationId
    ? `${apiUrls.conversations}${conversationId}/`
    : null;
  $: messagesUrl = conversationId
    ? `${apiUrls.conversations}${conversationId}/messages/`
    : null;

  // Re-init whenever conversationId changes (also handles initial load)
  let _prevConvId = undefined;
  $: if (conversationId !== _prevConvId) {
    const newId = conversationId;
    _prevConvId = newId;
    _activeConvId = newId;
    messages = [];
    error = '';
    sendError = '';
    disconnectWs();
    if (newId) {
      loading = true;
      fetchMessages().then(() => {
        if (_activeConvId === newId) connectWs(newId);
      });
    } else {
      loading = false;
    }
  }

  onDestroy(() => {
    _activeConvId = null;
    clearTimeout(wsReconnectTimer);
    disconnectWs();
  });

  async function fetchMessages() {
    loading = true;
    error = '';
    try {
      const res = await apiGet(messagesUrl);
      if (res.ok) {
        const data = await res.json();
        messages = data.results || data;
        await scrollToBottom();
      } else if (res.status === 404) {
        error = 'Conversation not found';
        console.error('[CRM:WhatsApp] Conversation not found for id', conversationId);
      } else {
        error = 'Failed to load messages';
        console.error('[CRM:WhatsApp] fetchMessages failed', res.status);
      }
    } catch (e) {
      error = 'Failed to load messages';
      console.error('[CRM:WhatsApp] fetchMessages error (network):', e);
    } finally {
      loading = false;
    }
  }

  // Silently refresh messages to pick up status changes (delivered/read/failed)
  // without resetting scroll position to top.
  async function refreshStatuses() {
    if (!messagesUrl) return;
    try {
      const res = await apiGet(messagesUrl);
      if (res.ok) {
        const data = await res.json();
        const fetched = data.results || data;
        // Build an id→status map from the server response
        const statusMap = Object.fromEntries(fetched.map(m => [m.id, m.status]));
        const prevStatusMap = Object.fromEntries(messages.map(m => [m.id, m.status]));
        // Detect transitions to 'failed' — log using server-side data so status shows 'failed'
        const newlyFailed = fetched.filter(
          m => m.status === 'failed' && prevStatusMap[m.id] !== 'failed'
        );
        if (newlyFailed.length > 0) {
          console.error('[CRM:WhatsApp] Message delivery failed:', newlyFailed);
        }
        // Merge: add any server messages not yet in local list, update statuses in-place.
        // This avoids dropping messages that were appended by sendMessage() or the WS handler.
        const localIds = new Set(messages.map(m => m.id));
        const newFromServer = fetched.filter(m => !localIds.has(m.id));
        messages = [
          ...messages.map(m => statusMap[m.id] !== undefined ? { ...m, status: statusMap[m.id] } : m),
          ...newFromServer,
        ];
      }
    } catch {
      // silent — status refresh is best-effort
    }
  }

  function connectWs(convId) {
    if (!convId || ws) return;
    const wsProto = location.protocol === 'https:' ? 'wss' : 'ws';
    const wsUrl = `${wsProto}://${location.host}/ws/messaging/${convId}/`;
    ws = new WebSocket(wsUrl);

    ws.onmessage = async (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.type === 'message' && data.message) {
          // New inbound message pushed by server
          messages = [...messages, data.message];
          await scrollToBottom();
        } else if (data.type === 'update') {
          // Status update (sent→delivered→read, or failed) — refresh to reflect
          await refreshStatuses();
        }
      } catch {
        // ignore malformed frames
      }
    };

    ws.onclose = () => {
      ws = null;
      // Auto-reconnect if this conversation is still active
      if (_activeConvId === convId) {
        wsReconnectTimer = setTimeout(() => {
          if (_activeConvId === convId) connectWs(convId);
        }, 3000);
      }
    };

    ws.onerror = () => {
      ws?.close();
    };
  }

  function disconnectWs() {
    clearTimeout(wsReconnectTimer);
    if (ws) {
      ws.onclose = null; // prevent reconnect on intentional close
      ws.close();
      ws = null;
    }
  }

  async function sendMessage() {
    if (!newMessage.trim() || sending || !conversationId) return;
    sending = true;
    sendError = '';
    const body = newMessage.trim();
    newMessage = '';
    try {
      const res = await apiPost(messagesUrl, { body });
      if (res.ok) {
        const msg = await res.json();
        messages = [...messages, msg];
        await scrollToBottom();
      } else {
        newMessage = body;
        let detail = 'Failed to send';
        try {
          const err = await res.json();
          detail = err.detail || err.error || detail;
        } catch { /* ignore */ }
        sendError = detail;
        console.error('[CRM:WhatsApp] Send failed:', res.status, detail);
      }
    } catch (e) {
      newMessage = body;
      sendError = 'Failed to send — network error';
      console.error('[CRM:WhatsApp] Send error (network):', e);
    } finally {
      sending = false;
    }
  }

  function handleKeydown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  async function scrollToBottom() {
    await tick();
    if (messagesEl) messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  const STATUS_ICON = {
    sent: '✓',
    delivered: '✓✓',
    read: '✓✓',
    failed: '✗',
    received: '↩',
  };
</script>

{#if !conversationId}
  <div class="text-center py-8 text-gray-400">
    <svg class="w-10 h-10 mx-auto mb-2 text-gray-300" fill="currentColor" viewBox="0 0 24 24">
      <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/>
      <path d="M11.5 2C6.253 2 2 6.253 2 11.5c0 1.822.496 3.525 1.355 4.991L2.05 21.95l5.514-1.285A9.45 9.45 0 0011.5 21C16.747 21 21 16.747 21 11.5S16.747 2 11.5 2z"/>
    </svg>
    <p class="text-sm">No WhatsApp conversation linked to this lead.</p>
  </div>
{:else}
  <div class="flex flex-col h-96">
    <!-- Message list -->
    <div
      class="flex-1 overflow-y-auto space-y-2 pr-1"
      bind:this={messagesEl}
    >
      {#if loading}
        <p class="text-xs text-gray-400 text-center py-4">Loading…</p>
      {:else if error}
        <p class="text-xs text-red-500 text-center py-4">{error}</p>
      {:else if messages.length === 0}
        <p class="text-xs text-gray-400 text-center py-4">No messages yet.</p>
      {:else}
        {#each messages as msg (msg.id)}
          {@const isOut = msg.direction === 'outbound'}
          <div class="flex {isOut ? 'justify-end' : 'justify-start'}">
            <div
              class="max-w-xs px-3 py-2 rounded-2xl text-sm
                {isOut
                  ? 'bg-green-500 text-white rounded-br-sm'
                  : 'bg-gray-100 text-gray-900 rounded-bl-sm'}"
            >
              <p class="whitespace-pre-wrap break-words">{msg.body}</p>
              <div class="flex items-center justify-end gap-1 mt-0.5">
                <span class="text-xs opacity-60">
                  {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
                {#if isOut}
                  {@const failTitle = msg.status === 'failed'
                    ? (msg.meta_error_message
                        ? `Delivery failed: ${msg.meta_error_message}${msg.meta_error_code ? ` (code ${msg.meta_error_code})` : ''}`
                        : 'Delivery failed')
                    : msg.status}
                  <span
                    class="text-xs {msg.status === 'read' ? 'text-blue-200' : msg.status === 'failed' ? 'text-red-300' : 'opacity-60'}"
                    title={failTitle}
                  >
                    {STATUS_ICON[msg.status] || ''}
                  </span>
                {/if}
              </div>
            </div>
          </div>
        {/each}
      {/if}
    </div>

    <!-- Send error banner -->
    {#if sendError}
      <div class="mx-1 mt-1 px-3 py-1.5 bg-red-50 border border-red-200 rounded text-xs text-red-700 flex items-start gap-1.5">
        <span class="flex-shrink-0 mt-0.5">⚠</span>
        <span>{sendError}</span>
        <button type="button" class="ml-auto text-red-400 hover:text-red-600" on:click={() => sendError = ''}>✕</button>
      </div>
    {/if}

    <!-- Send input -->
    <div class="flex gap-2 mt-2 pt-2 border-t border-gray-100">
      <textarea
        bind:value={newMessage}
        on:keydown={handleKeydown}
        rows="2"
        placeholder="Type a message… (Enter to send)"
        class="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-green-500"
      ></textarea>

      {#if windowOpen}
        <!-- 24h window open — free text send -->
        <button
          type="button"
          class="px-3 py-2 bg-green-500 text-white rounded-lg text-sm font-medium hover:bg-green-600 disabled:opacity-50 transition-colors self-end"
          disabled={sending || !newMessage.trim()}
          on:click={sendMessage}
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
      {:else}
        <!-- 24h window closed — send Hello template instead -->
        <button
          type="button"
          title="24h window closed — send greeting template"
          class="px-3 py-2 bg-blue-500 text-white rounded-lg text-sm font-medium hover:bg-blue-600 disabled:opacity-50 transition-colors self-end whitespace-nowrap"
          disabled={sending}
          on:click={() => sendNamedTemplate('hello_how_are_you')}
        >
          {sending ? '…' : 'Say Hi'}
        </button>
      {/if}
    </div>
  </div>
{/if}
