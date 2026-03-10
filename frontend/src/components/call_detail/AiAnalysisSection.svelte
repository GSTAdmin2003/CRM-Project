<script>
  export let analysis;
  export let apiUrls;
  export let callId;

  let polling = false;
  let localAnalysis = analysis;

  async function startAnalysis() {
    const res = await fetch(apiUrls.startAnalysis, { method: 'POST', headers: { 'X-CSRFToken': getCsrf() } });
    if (res.ok) {
      polling = true;
      pollStatus();
    }
  }

  async function pollStatus() {
    if (!polling) return;
    const res = await fetch(apiUrls.analysisStatus);
    if (res.ok) {
      const data = await res.json();
      localAnalysis = data;
      if (data.status === 'completed' || data.status === 'failed') {
        polling = false;
      } else {
        setTimeout(pollStatus, 2000);
      }
    } else {
      polling = false;
    }
  }

  function getCsrf() {
    const m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? m[1] : '';
  }

  $: statusLabel = localAnalysis?.status === 'completed' ? 'Completed'
    : localAnalysis?.status === 'failed' ? 'Failed'
    : localAnalysis?.status === 'processing' ? 'Processing…'
    : 'Not started';
</script>

<div class="bg-white rounded-lg shadow p-4">
  <div class="flex items-center justify-between mb-3">
    <h3 class="text-base font-semibold text-gray-900">AI Analysis</h3>
    {#if !localAnalysis || localAnalysis.status === 'failed'}
      <button
        on:click={startAnalysis}
        class="text-sm bg-indigo-600 text-white px-3 py-1 rounded hover:bg-indigo-700"
      >
        {localAnalysis ? 'Retry' : 'Analyse'}
      </button>
    {/if}
  </div>

  {#if polling}
    <p class="text-sm text-gray-500 animate-pulse">Analysing call…</p>
  {:else if localAnalysis?.status === 'completed' && localAnalysis.analysis_text}
    <div class="prose prose-sm max-w-none text-gray-700 whitespace-pre-wrap text-sm">
      {localAnalysis.analysis_text}
    </div>
  {:else if localAnalysis?.status === 'failed'}
    <p class="text-sm text-red-500">Analysis failed. Try again.</p>
  {:else if !localAnalysis}
    <p class="text-sm text-gray-400">No analysis yet.</p>
  {:else}
    <p class="text-sm text-gray-500">{statusLabel}</p>
  {/if}
</div>
