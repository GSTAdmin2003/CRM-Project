<script>
  import { apiPatch } from '../../utils/api.js';

  export let lead = {};
  export let apiUrls = {};
  export let onLeadUpdated = () => {};

  let notes = lead.notes || '';
  let saving = false;
  let saveMsg = '';

  async function save() {
    if (saving) return;
    saving = true;
    saveMsg = '';
    try {
      const res = await apiPatch(apiUrls.lead, { notes });
      if (res.ok) {
        const updated = await res.json();
        onLeadUpdated(updated);
        saveMsg = 'Saved';
        setTimeout(() => (saveMsg = ''), 2000);
      } else {
        saveMsg = 'Save failed';
      }
    } catch {
      saveMsg = 'Save failed';
    } finally {
      saving = false;
    }
  }
</script>

<div class="flex flex-col gap-2">
  <textarea
    bind:value={notes}
    on:blur={save}
    rows="10"
    placeholder="Add notes about this opportunity…"
    class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-y focus:outline-none focus:ring-2 focus:ring-blue-500"
  ></textarea>
  <div class="flex items-center gap-2 justify-end text-xs text-gray-400">
    {#if saving}
      <span>Saving…</span>
    {:else if saveMsg}
      <span class="text-green-600">{saveMsg}</span>
    {:else}
      <span>Auto-saves on blur</span>
    {/if}
  </div>
</div>
