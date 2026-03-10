<script>
  export let title = 'Confirm';
  export let message = '';
  export let confirmLabel = 'Confirm';
  export let cancelLabel = 'Cancel';
  export let loading = false;
  export let onConfirm = () => {};
  export let onCancel = () => {};
  export let danger = false;
</script>

<div
  class="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4"
  on:click|self={onCancel}
  role="dialog"
  aria-modal="true"
  aria-labelledby="confirm-modal-title"
>
  <div class="bg-white rounded-xl shadow-xl w-full max-w-sm">
    <!-- Header -->
    <div class="flex items-center justify-between px-5 py-4 border-b border-gray-100">
      <h2 id="confirm-modal-title" class="text-base font-semibold text-gray-900">{title}</h2>
      <button
        type="button"
        class="text-gray-400 hover:text-gray-600 transition-colors"
        on:click={onCancel}
        aria-label="Close"
        disabled={loading}
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
        </svg>
      </button>
    </div>

    <!-- Body -->
    <div class="px-5 py-4">
      <p class="text-sm text-gray-600">{message}</p>
    </div>

    <!-- Footer -->
    <div class="flex justify-end gap-2 px-5 py-4 border-t border-gray-100">
      <button
        type="button"
        class="px-4 py-2 text-sm text-gray-600 hover:text-gray-900 transition-colors disabled:opacity-50"
        on:click={onCancel}
        disabled={loading}
      >
        {cancelLabel}
      </button>
      <button
        type="button"
        class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white rounded-lg transition-colors disabled:opacity-50
          {danger
            ? 'bg-red-600 hover:bg-red-700'
            : 'bg-blue-600 hover:bg-blue-700'}"
        on:click={onConfirm}
        disabled={loading}
      >
        {#if loading}
          <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
          </svg>
        {/if}
        {confirmLabel}
      </button>
    </div>
  </div>
</div>
