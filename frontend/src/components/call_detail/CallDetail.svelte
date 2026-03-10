<script>
  import CallInfoCard from './CallInfoCard.svelte';
  import RecordingPlayer from './RecordingPlayer.svelte';
  import TranscriptSection from './TranscriptSection.svelte';
  import AiAnalysisSection from './AiAnalysisSection.svelte';
  import CallNotesForm from './CallNotesForm.svelte';
  import EventLogSection from './EventLogSection.svelte';
  import LinkedContactPanel from './LinkedContactPanel.svelte';
  import LinkedOpportunityPanel from './LinkedOpportunityPanel.svelte';

  export let call;
  export let apiUrls;

  // Local mutable copies
  let contact = call.contact_id ? { id: call.contact_id, name: call.contact_name } : null;
  let opportunity = call.opportunity_id ? { id: call.opportunity_id, title: call.opportunity_title } : null;
</script>

<div class="max-w-7xl mx-auto py-6 px-4">
  <div class="mb-4">
    <a href="/calls/" class="text-blue-600 hover:underline text-sm">← Back to Calls</a>
    <h1 class="text-2xl font-semibold text-gray-900 mt-1">Call Details</h1>
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
    <div class="lg:col-span-2 space-y-6">
      <CallInfoCard {call} {apiUrls} />
      <RecordingPlayer recording={call.recording} downloadUrl={apiUrls.recordingDownload} />
      <TranscriptSection transcript={call.transcript} {apiUrls} callId={call.id} />
      <AiAnalysisSection analysis={call.analysis} {apiUrls} callId={call.id} />
      <CallNotesForm initialNotes={call.notes ?? ''} {apiUrls} />
      <EventLogSection logs={call.logs ?? []} />
    </div>
    <div class="space-y-6">
      <LinkedContactPanel {contact} {apiUrls} on:linked={(e) => contact = e.detail} />
      <LinkedOpportunityPanel {opportunity} {apiUrls} on:linked={(e) => opportunity = e.detail} />
    </div>
  </div>
</div>
