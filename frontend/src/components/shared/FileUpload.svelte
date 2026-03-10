<script>
  export let currentFile = null;
  export let accept = '*';
  export let label = 'Upload File';
  export let onFile = () => {};
  export let onRemove = () => {};

  let dragOver = false;
  let inputEl;

  function handleDrop(e) {
    dragOver = false;
    const file = e.dataTransfer?.files?.[0];
    if (file) onFile(file);
  }

  function handleInput(e) {
    const file = e.target?.files?.[0];
    if (file) onFile(file);
    // Reset input so the same file can be re-selected after removal
    if (inputEl) inputEl.value = '';
  }

  function handleDragOver(e) {
    e.preventDefault();
    dragOver = true;
  }

  function handleDragLeave() {
    dragOver = false;
  }
</script>

{#if currentFile}
  <!-- Current file display -->
  <div class="flex items-center justify-between px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg">
    <div class="flex items-center gap-2 min-w-0">
      <svg class="w-4 h-4 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
          d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"/>
      </svg>
      <span class="text-sm text-gray-700 truncate">{currentFile}</span>
    </div>
    <button
      type="button"
      class="ml-2 flex-shrink-0 text-xs text-red-500 hover:text-red-700 font-medium transition-colors"
      on:click={onRemove}
    >
      Remove
    </button>
  </div>
{:else}
  <!-- Drop zone -->
  <div
    role="button"
    tabindex="0"
    class="flex flex-col items-center justify-center gap-2 px-4 py-6 border-2 border-dashed rounded-lg cursor-pointer transition-colors
      {dragOver
        ? 'border-blue-500 bg-blue-50'
        : 'border-gray-300 bg-gray-50 hover:border-gray-400 hover:bg-gray-100'}"
    on:dragover={handleDragOver}
    on:dragleave={handleDragLeave}
    on:drop|preventDefault={handleDrop}
    on:click={() => inputEl?.click()}
    on:keydown={(e) => e.key === 'Enter' || e.key === ' ' ? inputEl?.click() : null}
  >
    <svg class="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
        d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
    </svg>
    <p class="text-sm text-gray-600">
      <span class="font-medium text-blue-600 hover:text-blue-700">{label}</span>
      <span class="text-gray-500"> or drag and drop</span>
    </p>
  </div>

  <input
    bind:this={inputEl}
    type="file"
    {accept}
    class="hidden"
    on:change={handleInput}
  />
{/if}
