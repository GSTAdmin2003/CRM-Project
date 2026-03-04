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
  export let prevLeadId = null;
  export let nextLeadId = null;
  export let navParams = '';
  export let currentIndex = 0;
  export let totalCount = 0;
  export let apiUrls = {};

  // Mutable lead state
  let currentLead = { ...lead };

  // Conversation ID comes directly from the lead data (wa_conversation_id is a
  // computed field on LeadDetailSerializer — resolved by phone number server-side).
  // When the contact/phone changes and the lead is re-PATCHed, the response
  // includes the updated wa_conversation_id — no separate API query needed.
  $: currentWaConversationId = currentLead.wa_conversation_id ?? null;

  onMount(() => {
    setCurrentLead(currentLead);
  });

  function handleLeadUpdated(updatedLead) {
    currentLead = { ...currentLead, ...updatedLead };
    setCurrentLead(currentLead);
  }

  $: currentStageId = currentLead.stage ? currentLead.stage.id : null;
</script>

<div class="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
  <!-- Top bar: title + nav -->
  <div class="flex items-center justify-between mb-3">
    <div class="flex items-center gap-3 min-w-0">
      <a
        href="/crm/opportunities/{navParams || ''}"
        class="text-gray-400 hover:text-gray-600 flex-shrink-0"
        on:click|preventDefault={() => window.crmNavigate?.(`/crm/opportunities/${navParams || ''}`)}
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

  <!-- Stage bar -->
  <StageBar
    {stages}
    currentStageId={currentStageId}
    {apiUrls}
    on:lead:stageChanged={(e) => handleLeadUpdated({ stage: stages.find(s => s.id === e.detail.stageId) })}
  />

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
        waConversationId={currentWaConversationId}
        onLeadUpdated={handleLeadUpdated}
      />
    </div>
  </div>
</div>
