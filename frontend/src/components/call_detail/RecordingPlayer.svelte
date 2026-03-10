<script>
  export let recording = null;
  export let downloadUrl = null;
</script>

<div class="bg-white shadow rounded-lg p-6">
  <h2 class="text-lg font-medium text-gray-900 mb-4">Recording</h2>
  {#if recording && recording.file}
    <audio controls class="w-full mb-3" src={recording.file}></audio>
    <div class="flex items-center justify-between text-sm text-gray-500">
      <span>{recording.file_size_formatted || ''}</span>
      {#if downloadUrl}
        <a href={downloadUrl} class="text-blue-600 hover:underline">Download</a>
      {/if}
    </div>
  {:else}
    <p class="text-gray-500 text-sm">No recording available.</p>
  {/if}
</div>
