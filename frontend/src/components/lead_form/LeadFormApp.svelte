<script>
  import { onMount } from 'svelte';
  import { setCurrentLead } from '../../stores/leadStore.js';

  import StageBar from './StageBar.svelte';
  import LeadNavBar from './LeadNavBar.svelte';
  import LeadInfoPanel from './LeadInfoPanel.svelte';
  import ContactSection from './ContactSection.svelte';
  import CallControls from './CallControls.svelte';
  import TabPanel from './TabPanel.svelte';

  // Props injected from the data island
  export let leadId = null;
  export let lead = {};
  export let stages = [];
  export let activityTypes = [];
  export let waConversationId = null;
  export let userLanguage = 'en';
  export let prevLeadId = null;
  export let nextLeadId = null;
  export let navParams = '';
  export let currentIndex = 0;
  export let totalCount = 0;
  export let apiUrls = {};

  // Mutable lead state
  let currentLead = { ...lead };

  let savingStatus = false;
  let converting = false;
  let convertError = '';
  let showLostModal = false;
  let lostReason = '';

  async function handleConvert() {
    if (converting || savingStatus) return;
    converting = true;
    savingStatus = true;
    convertError = '';
    try {
      const { apiPost } = await import('../../utils/api.js');
      const res = await apiPost(apiUrls.convert, {});
      if (res.ok) {
        const data = await res.json();
        window.location.href = `/crm/opportunities/${data.id}/edit/`;
      } else {
        const d = await res.json().catch(() => ({}));
        convertError = d.detail || 'Conversion failed.';
      }
    } catch {
      convertError = 'Conversion failed.';
    } finally {
      converting = false;
      savingStatus = false;
    }
  }

  async function handleReject() {
    if (!lostReason.trim() || savingStatus) return;
    savingStatus = true;
    try {
      const { apiPatch } = await import('../../utils/api.js');
      const res = await apiPatch(apiUrls.lead, { status: 'lost', lost_reason: lostReason });
      if (res.ok) {
        window.location.href = '/crm/leads/';
      }
    } finally {
      savingStatus = false;
    }
  }

  // Conversation ID comes directly from the lead data (wa_conversation_id is a
  // computed field on LeadDetailSerializer — resolved by phone number server-side).
  // When the contact/phone changes and the lead is re-PATCHed, the response
  // includes the updated wa_conversation_id — no separate API query needed.
  // Prefer the FK-based value from the serialized lead; fall back to the
  // phone-resolved value from _resolve_wa_conversation_id (top-level prop).
  $: currentWaConversationId = (currentLead.wa_conversation_id ?? waConversationId) ?? null;

  onMount(() => {
    setCurrentLead(currentLead);
  });

  function handleLeadUpdated(updatedLead) {
    console.log('[CRM:LEAD-APP] handleLeadUpdated called ▶',
      'updatedLead.phone:', updatedLead?.phone,
      '| updatedLead.contact:', updatedLead?.contact,
      '| updatedLead keys:', Object.keys(updatedLead || {}));
    currentLead = { ...currentLead, ...updatedLead };
    console.log('[CRM:LEAD-APP] currentLead after merge — phone:', currentLead.phone, 'contact:', currentLead.contact);
    setCurrentLead(currentLead);
  }

  $: currentStageId = currentLead.stage ? currentLead.stage.id : null;
</script>

<div class="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
  <!-- Top bar: title + nav -->
  <div class="flex items-center justify-between mb-3">
    <div class="flex items-center gap-3 min-w-0">
      <a
        href={currentLead.status === 'new' ? '/crm/leads/' : `/crm/opportunities/${navParams || ''}`}
        class="text-gray-400 hover:text-gray-600 flex-shrink-0"
        on:click|preventDefault={() => window.location.href = currentLead.status === 'new' ? '/crm/leads/' : `/crm/opportunities/${navParams || ''}`}
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"/>
        </svg>
      </a>
      <h1 class="text-xl font-bold text-gray-900 truncate">{currentLead.title}</h1>
    </div>
    <LeadNavBar
      {prevLeadId}
      {nextLeadId}
      {navParams}
      {currentIndex}
      {totalCount}
    />
  </div>

  <!-- Stage bar (opportunities) / Action buttons (leads) -->
  {#if currentLead.status === 'new'}
    <div class="flex flex-col gap-2 mb-4">
      <div class="flex gap-2">
        <button
          type="button"
          disabled={savingStatus}
          on:click={handleConvert}
          class="px-5 py-2 rounded-full text-sm font-medium border transition-colors bg-green-600 text-white border-green-600 hover:bg-green-700 disabled:opacity-50"
        >{converting ? 'Converting…' : 'Convert to Opportunity'}</button>

        <button
          type="button"
          disabled={savingStatus}
          on:click={() => { showLostModal = true; }}
          class="px-5 py-2 rounded-full text-sm font-medium border transition-colors bg-white text-red-600 border-red-300 hover:border-red-500 hover:bg-red-50 disabled:opacity-50"
        >Lost</button>
      </div>
      {#if convertError}
        <p class="text-sm text-red-600">{convertError}</p>
      {/if}
    </div>

    <!-- Lost reason modal -->
    {#if showLostModal}
      <div class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-40">
        <div class="bg-white rounded-xl shadow-xl p-6 w-full max-w-md mx-4">
          <h3 class="text-lg font-semibold text-gray-900 mb-3">Mark as Lost</h3>
          <textarea
            bind:value={lostReason}
            placeholder="Reason for losing this lead…"
            rows="4"
            class="w-full border border-gray-300 rounded-lg p-3 text-sm focus:outline-none focus:ring-2 focus:ring-red-400 resize-none"
          ></textarea>
          <div class="flex justify-end gap-3 mt-4">
            <button
              type="button"
              on:click={() => { showLostModal = false; lostReason = ''; }}
              class="px-4 py-2 text-sm rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50"
            >Cancel</button>
            <button
              type="button"
              disabled={!lostReason.trim() || savingStatus}
              on:click={handleReject}
              class="px-4 py-2 text-sm rounded-lg bg-red-600 text-white hover:bg-red-700 disabled:opacity-50"
            >Confirm Lost</button>
          </div>
        </div>
      </div>
    {/if}
  {:else}
    <StageBar
      {stages}
      currentStageId={currentStageId}
      {apiUrls}
      on:lead:stageChanged={(e) => handleLeadUpdated({ stage: stages.find(s => s.id === e.detail.stageId) })}
    />
  {/if}

  <!-- Two-column layout -->
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <!-- Left column: Info + Contact + Call -->
    <div class="lg:col-span-1 flex flex-col gap-4">
      <LeadInfoPanel
        lead={currentLead}
        {apiUrls}
        onLeadUpdated={handleLeadUpdated}
      />

      <ContactSection
        lead={currentLead}
        {apiUrls}
        onLeadUpdated={handleLeadUpdated}
      />

      <CallControls lead={currentLead} conversationId={currentWaConversationId} {apiUrls} />
    </div>

    <!-- Right column: Tabs (Notes / Activities / WhatsApp) -->
    <div class="lg:col-span-2">
      <TabPanel
        lead={currentLead}
        {leadId}
        {apiUrls}
        {activityTypes}
        {userLanguage}
        onLeadUpdated={handleLeadUpdated}
      />
    </div>
  </div>
</div>
