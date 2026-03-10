<script>
  import { toasts } from './toastStore.js';

  const STYLES = {
    success: {
      container: 'bg-green-50 border-green-200 text-green-800',
      icon: 'text-green-500',
      path: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z',
    },
    error: {
      container: 'bg-red-50 border-red-200 text-red-800',
      icon: 'text-red-500',
      path: 'M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z',
    },
    warning: {
      container: 'bg-yellow-50 border-yellow-200 text-yellow-800',
      icon: 'text-yellow-500',
      path: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z',
    },
    info: {
      container: 'bg-blue-50 border-blue-200 text-blue-800',
      icon: 'text-blue-500',
      path: 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
    },
  };

  function dismiss(id) {
    toasts.update(t => t.filter(x => x.id !== id));
  }

  function getStyle(type) {
    return STYLES[type] || STYLES.info;
  }
</script>

<!-- Fixed container: top-right -->
<div
  class="fixed top-4 right-4 z-[9999] flex flex-col gap-2 w-80 pointer-events-none"
  aria-live="polite"
  aria-atomic="false"
>
  {#each $toasts as toast (toast.id)}
    {@const style = getStyle(toast.type)}
    <div
      class="flex items-start gap-3 px-4 py-3 rounded-lg border shadow-md pointer-events-auto
        {style.container}"
      role="alert"
    >
      <!-- Icon -->
      <svg class="w-5 h-5 flex-shrink-0 mt-0.5 {style.icon}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={style.path}/>
      </svg>

      <!-- Message -->
      <p class="text-sm flex-1">{toast.message}</p>

      <!-- Close -->
      <button
        type="button"
        class="flex-shrink-0 text-current opacity-50 hover:opacity-100 transition-opacity"
        on:click={() => dismiss(toast.id)}
        aria-label="Dismiss notification"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
        </svg>
      </button>
    </div>
  {/each}
</div>
