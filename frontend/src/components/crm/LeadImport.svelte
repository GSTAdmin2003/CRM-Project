<script>
  export let apiUrls = {};

  let state = 'upload'; // upload | preview | results
  let uploading = false;
  let confirming = false;
  let error = null;
  let previewData = null;
  let importResults = null;
  let fileInput;

  function getCsrf() {
    const m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? m[1] : '';
  }

  async function handleUpload() {
    const file = fileInput?.files?.[0];
    if (!file) { error = 'Please select a CSV file.'; return; }
    uploading = true;
    error = null;
    const fd = new FormData();
    fd.append('file', file);
    const res = await fetch(apiUrls.upload, {
      method: 'POST',
      headers: { 'X-CSRFToken': getCsrf() },
      body: fd,
    });
    uploading = false;
    if (res.ok) {
      previewData = await res.json();
      state = 'preview';
    } else {
      const data = await res.json().catch(() => ({}));
      error = data.error || 'Upload failed. Please check the file format.';
    }
  }

  async function handleConfirm() {
    confirming = true;
    error = null;
    const res = await fetch(apiUrls.confirm, {
      method: 'POST',
      headers: { 'X-CSRFToken': getCsrf(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ rows: previewData.rows }),
    });
    confirming = false;
    if (res.ok) {
      importResults = await res.json();
      state = 'results';
    } else {
      const data = await res.json().catch(() => ({}));
      error = data.error || 'Import failed.';
    }
  }

  function reset() {
    state = 'upload';
    previewData = null;
    importResults = null;
    error = null;
    if (fileInput) fileInput.value = '';
  }
</script>

<div class="max-w-3xl mx-auto py-8 px-4">
  <div class="mb-6">
    <h1 class="text-2xl font-semibold text-gray-900">Import Opportunities</h1>
    <p class="text-sm text-gray-500 mt-1">Upload a CSV file to import opportunities in bulk.</p>
  </div>

  {#if error}
    <div class="mb-4 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">{error}</div>
  {/if}

  {#if state === 'upload'}
    <div class="bg-white rounded-lg shadow p-6 space-y-4">
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">CSV File</label>
        <input bind:this={fileInput} type="file" accept=".csv" class="block w-full text-sm text-gray-600" />
      </div>
      <div class="flex items-center gap-4">
        <button
          on:click={handleUpload}
          disabled={uploading}
          class="bg-indigo-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
        >
          {uploading ? 'Uploading…' : 'Upload & Preview'}
        </button>
        {#if apiUrls.template}
          <a href={apiUrls.template} class="text-sm text-indigo-600 hover:underline">Download template</a>
        {/if}
      </div>
    </div>

  {:else if state === 'preview' && previewData}
    <div class="bg-white rounded-lg shadow p-6 space-y-4">
      <p class="text-sm text-gray-600">
        Found <strong>{previewData.total ?? previewData.rows?.length ?? 0}</strong> rows to import.
      </p>
      {#if previewData.rows?.length > 0}
        <div class="overflow-x-auto">
          <table class="min-w-full text-sm divide-y divide-gray-200">
            <thead>
              <tr>
                {#each Object.keys(previewData.rows[0]) as col}
                  <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">{col}</th>
                {/each}
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
              {#each previewData.rows.slice(0, 5) as row}
                <tr>
                  {#each Object.values(row) as val}
                    <td class="px-3 py-2 text-gray-700 truncate max-w-xs">{val ?? ''}</td>
                  {/each}
                </tr>
              {/each}
            </tbody>
          </table>
          {#if previewData.rows.length > 5}
            <p class="text-xs text-gray-400 mt-2">Showing 5 of {previewData.rows.length} rows.</p>
          {/if}
        </div>
      {/if}
      <div class="flex gap-3">
        <button
          on:click={handleConfirm}
          disabled={confirming}
          class="bg-indigo-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
        >
          {confirming ? 'Importing…' : 'Confirm Import'}
        </button>
        <button on:click={reset} class="text-sm text-gray-600 px-4 py-2 rounded border border-gray-300 hover:bg-gray-50">
          Cancel
        </button>
      </div>
    </div>

  {:else if state === 'results' && importResults}
    <div class="bg-white rounded-lg shadow p-6 space-y-4">
      <div class="flex items-center gap-3">
        <span class="text-green-600 text-xl">✓</span>
        <h2 class="text-lg font-medium text-gray-900">Import Complete</h2>
      </div>
      <div class="grid grid-cols-3 gap-4 text-center">
        <div class="p-3 bg-green-50 rounded">
          <div class="text-2xl font-bold text-green-700">{importResults.created ?? 0}</div>
          <div class="text-xs text-gray-500 mt-1">Created</div>
        </div>
        <div class="p-3 bg-yellow-50 rounded">
          <div class="text-2xl font-bold text-yellow-700">{importResults.skipped ?? 0}</div>
          <div class="text-xs text-gray-500 mt-1">Skipped</div>
        </div>
        <div class="p-3 bg-red-50 rounded">
          <div class="text-2xl font-bold text-red-700">{importResults.errors ?? 0}</div>
          <div class="text-xs text-gray-500 mt-1">Errors</div>
        </div>
      </div>
      <div class="flex gap-3">
        <a href="/crm/opportunities/" class="bg-indigo-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-indigo-700">
          View Opportunities
        </a>
        <button on:click={reset} class="text-sm text-gray-600 px-4 py-2 rounded border border-gray-300 hover:bg-gray-50">
          Import more
        </button>
      </div>
    </div>
  {/if}
</div>
