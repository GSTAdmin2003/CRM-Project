<script>
  // Generic confirm-action page component.
  // Props passed from the Django view's init_data_json.
  export let title = 'Confirm Action';
  export let message = 'Are you sure?';
  export let details = [];       // [{label, value}]
  export let confirmLabel = 'Confirm';
  export let confirmClass = 'bg-red-600 hover:bg-red-700';
  export let cancelUrl = '/';
  export let postUrl = '';       // defaults to window.location.pathname
  export let csrfToken = '';
</script>

<div class="mx-auto max-w-2xl px-4 py-8 sm:px-6 lg:px-8">
  <div class="bg-white shadow rounded-lg p-6">
    <h2 class="text-lg font-semibold text-gray-900 mb-4">{title}</h2>
    <p class="text-sm text-gray-600 mb-4">{message}</p>

    {#if details.length > 0}
      <div class="bg-gray-50 rounded-md p-4 mb-6">
        <dl class="space-y-2">
          {#each details as d}
            <div class="flex justify-between">
              <dt class="text-sm font-medium text-gray-500">{d.label}</dt>
              <dd class="text-sm text-gray-900">{d.value}</dd>
            </div>
          {/each}
        </dl>
      </div>
    {/if}

    <form method="post" action={postUrl || undefined} class="flex justify-end gap-3">
      <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken} />
      <a
        href={cancelUrl}
        class="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
      >
        Cancel
      </a>
      <button
        type="submit"
        class="px-4 py-2 border border-transparent rounded-md text-sm font-medium text-white {confirmClass} focus:outline-none"
      >
        {confirmLabel}
      </button>
    </form>
  </div>
</div>
