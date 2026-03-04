<script>
  import { sipState } from '../../stores/sipState.js';
  import { currentLead } from '../../stores/leadStore.js';
  import { apiPost } from '../../utils/api.js';

  export let lead = {};
  export let apiUrls = {};
  export let conversationId = null;

  let sendingPitch = false;
  let pitchError = '';

  async function sendSalesPitch() {
    if (!conversationId || sendingPitch) return;
    sendingPitch = true;
    pitchError = '';
    try {
      const url = `${apiUrls.conversations}${conversationId}/send_named_template/`;
      const res = await apiPost(url, { template_name: 'sales_pitch', lead_id: lead.id });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        pitchError = err.detail || 'Failed to send pitch';
      }
    } catch {
      pitchError = 'Network error';
    } finally {
      sendingPitch = false;
    }
  }

  let elapsed = 0;
  let timerInterval = null;

  $: if ($sipState.hasActiveCall) {
    if (!timerInterval) {
      elapsed = 0;
      timerInterval = setInterval(() => (elapsed += 1), 1000);
    }
  } else {
    if (timerInterval) {
      clearInterval(timerInterval);
      timerInterval = null;
      elapsed = 0;
    }
  }

  function formatTime(secs) {
    const m = Math.floor(secs / 60).toString().padStart(2, '0');
    const s = (secs % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  }

  function makeCall() {
    const phone = lead.phone || '';
    if (!phone) return;
    window.currentOpportunityId = lead.id;
    window.currentContactId = lead.contact || null;
    // The global makeCall() reads from the dialpad #phone-number input, not its argument
    const dialpad = document.getElementById('phone-number');
    if (dialpad) dialpad.value = phone;
    if (typeof window.makeCall === 'function') {
      window.makeCall();
    }
  }

  function hangup() {
    if (typeof window.hangupCall === 'function') window.hangupCall();
  }

  function toggleMute() {
    if (typeof window.toggleMute === 'function') window.toggleMute();
  }

  function toggleHold() {
    if (typeof window.toggleHold === 'function') window.toggleHold();
  }
</script>

<div class="bg-white rounded-lg border border-gray-200 p-3">
  {#if !$sipState.hasActiveCall}
    <!-- Idle: show call button -->
    <button
      type="button"
      class="flex items-center gap-2 px-3 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed w-full justify-center"
      disabled={!$sipState.registered || !lead.phone}
      on:click={makeCall}
      title={lead.phone || 'No phone number'}
    >
      <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
        <path d="M6.62 10.79a15.053 15.053 0 006.59 6.59l2.2-2.2a1 1 0 011.01-.24 11.36 11.36 0 003.56.57 1 1 0 011 1V20a1 1 0 01-1 1A17 17 0 013 4a1 1 0 011-1h3.5a1 1 0 011 1 11.36 11.36 0 00.57 3.56 1 1 0 01-.25 1.01l-2.2 2.22z"/>
      </svg>
      {lead.phone || 'No number'}
    </button>
    {#if !$sipState.registered}
      <p class="text-xs text-gray-400 text-center mt-1">SIP not registered</p>
    {/if}

    <!-- Sales Pitch -->
    {#if conversationId}
      <button
        type="button"
        class="flex items-center gap-2 px-3 py-2 mt-2 w-full justify-center rounded-lg text-sm font-medium transition-colors
          bg-green-50 hover:bg-green-100 text-green-700 border border-green-200
          disabled:opacity-50 disabled:cursor-not-allowed"
        disabled={sendingPitch}
        on:click={sendSalesPitch}
      >
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
          <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/>
          <path d="M11.5 2C6.253 2 2 6.253 2 11.5c0 1.822.496 3.525 1.355 4.991L2.05 21.95l5.514-1.285A9.45 9.45 0 0011.5 21C16.747 21 21 16.747 21 11.5S16.747 2 11.5 2z"/>
        </svg>
        {sendingPitch ? 'Sending…' : 'Send Sales Pitch'}
      </button>
      {#if pitchError}
        <p class="text-xs text-red-500 text-center mt-1">{pitchError}</p>
      {/if}
    {/if}
  {:else}
    <!-- Active call controls -->
    <div class="flex items-center gap-2">
      <span class="text-sm font-mono text-green-700 font-semibold min-w-[4rem]">{formatTime(elapsed)}</span>

      <!-- Mute -->
      <button
        type="button"
        class="flex-1 flex items-center justify-center gap-1 px-2 py-2 rounded text-xs font-medium transition-colors
          {$sipState.isMuted ? 'bg-yellow-100 text-yellow-800 border border-yellow-300' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}"
        on:click={toggleMute}
        title={$sipState.isMuted ? 'Unmute' : 'Mute'}
      >
        {#if $sipState.isMuted}
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" clip-rule="evenodd"/>
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2"/>
          </svg>
        {:else}
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.536 8.464a5 5 0 010 7.072M12 6v12m0 0a7 7 0 01-7-7m7 7a7 7 0 007-7M9 12a3 3 0 003 3"/>
          </svg>
        {/if}
        {$sipState.isMuted ? 'Unmute' : 'Mute'}
      </button>

      <!-- Hold -->
      <button
        type="button"
        class="flex-1 flex items-center justify-center gap-1 px-2 py-2 rounded text-xs font-medium transition-colors
          {$sipState.isOnHold ? 'bg-orange-100 text-orange-800 border border-orange-300' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}"
        on:click={toggleHold}
        title={$sipState.isOnHold ? 'Resume' : 'Hold'}
      >
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
          <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
        </svg>
        {$sipState.isOnHold ? 'Resume' : 'Hold'}
      </button>

      <!-- Hangup -->
      <button
        type="button"
        class="flex-1 flex items-center justify-center gap-1 px-2 py-2 rounded text-xs font-medium bg-red-100 text-red-700 hover:bg-red-200 transition-colors"
        on:click={hangup}
        title="Hang up"
      >
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
          <path d="M6.62 10.79a15.053 15.053 0 006.59 6.59l2.2-2.2a1 1 0 011.01-.24 11.36 11.36 0 003.56.57 1 1 0 011 1V20a1 1 0 01-1 1A17 17 0 013 4a1 1 0 011-1h3.5a1 1 0 011 1 11.36 11.36 0 00.57 3.56 1 1 0 01-.25 1.01l-2.2 2.22z"/>
        </svg>
        Hang up
      </button>
    </div>
  {/if}
</div>
