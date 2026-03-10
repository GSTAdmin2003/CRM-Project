<script>
  export let initialNotes;
  export let apiUrls;

  let notes = initialNotes ?? '';
  let saving = false;
  let saved = false;

  async function save() {
    saving = true;
    saved = false;
    const fd = new FormData();
    fd.append('notes', notes);
    const res = await fetch(apiUrls.updateNotes, {
      method: 'POST',
      headers: { 'X-CSRFToken': getCsrf() },
      body: fd,
    });
    saving = false;
    if (res.ok) {
      saved = true;
      setTimeout(() => (saved = false), 2000);
    }
  }

  function getCsrf() {
    const m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? m[1] : '';
  }
</script>

<div class="bg-white rounded-lg shadow p-4">
  <h3 class="text-base font-semibold text-gray-900 mb-3">Notes</h3>
  <textarea
    bind:value={notes}
    rows="4"
    class="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
    placeholder="Add notes about this call…"
  ></textarea>
  <div class="flex items-center gap-3 mt-2">
    <button
      on:click={save}
      disabled={saving}
      class="text-sm bg-indigo-600 text-white px-3 py-1 rounded hover:bg-indigo-700 disabled:opacity-50"
    >
      {saving ? 'Saving…' : 'Save notes'}
    </button>
    {#if saved}<span class="text-sm text-green-600">Saved!</span>{/if}
  </div>
</div>
