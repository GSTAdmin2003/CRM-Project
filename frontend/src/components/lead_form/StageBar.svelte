<script>
  import { apiPost } from '../../utils/api.js';

  export let stages = [];
  export let currentStageId = null;
  export let apiUrls = {};

  let saving = false;

  async function selectStage(stageId) {
    if (stageId === currentStageId || saving) return;
    saving = true;
    try {
      const res = await apiPost(apiUrls.leadStage, { stage_id: stageId });
      if (res.ok) {
        currentStageId = stageId;
        // Notify parent that lead was updated
        const event = new CustomEvent('lead:stageChanged', { detail: { stageId }, bubbles: true });
        document.dispatchEvent(event);
      }
    } catch (e) {
      console.error('StageBar: failed to update stage', e);
    } finally {
      saving = false;
    }
  }
</script>

<div class="flex items-stretch border border-gray-200 rounded-lg overflow-hidden bg-gray-50 mb-4">
  {#each stages as stage, i}
    {@const isActive = stage.id === currentStageId}
    <button
      type="button"
      class="flex-1 px-4 py-3 text-sm font-medium text-center transition-all whitespace-nowrap overflow-hidden text-ellipsis border-r border-gray-200 last:border-r-0
        {isActive
          ? 'bg-blue-600 text-white font-semibold'
          : 'text-gray-500 hover:bg-gray-100 cursor-pointer'}
        {saving ? 'opacity-60 cursor-not-allowed' : ''}"
      disabled={saving}
      on:click={() => selectStage(stage.id)}
      title={stage.name}
    >
      {stage.name}
    </button>
  {/each}
</div>
