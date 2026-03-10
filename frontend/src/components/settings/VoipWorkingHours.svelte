<script>
  import { onMount } from 'svelte';
  import { getCsrfToken } from '../../utils/csrf.js';

  export let apiUrls = {};

  let loading = true;
  let saving = false;
  let successMsg = '';
  let errorMsg = '';

  // Form fields
  let start_time = '09:00';
  let end_time = '18:00';

  // working_days is comma-separated day numbers: Mon=1,Tue=2,Wed=3,Thu=4,Fri=5,Sat=6,Sun=0
  const ALL_DAYS = [
    { value: 1, label: 'Mon' },
    { value: 2, label: 'Tue' },
    { value: 3, label: 'Wed' },
    { value: 4, label: 'Thu' },
    { value: 5, label: 'Fri' },
    { value: 6, label: 'Sat' },
    { value: 0, label: 'Sun' },
  ];

  // Set of selected day numbers
  let selectedDays = new Set([1, 2, 3, 4, 5]);

  function parseDays(str) {
    if (!str) return new Set();
    return new Set(
      str.split(',')
        .map(s => s.trim())
        .filter(s => s !== '')
        .map(Number)
        .filter(n => !isNaN(n))
    );
  }

  function formatDays(daySet) {
    // Return in ascending order: 0 (Sun) is included last per typical convention
    // but stored in whatever order; just sort numerically
    return [...daySet].sort((a, b) => a - b).join(',');
  }

  function toggleDay(val) {
    const copy = new Set(selectedDays);
    if (copy.has(val)) {
      copy.delete(val);
    } else {
      copy.add(val);
    }
    selectedDays = copy;
  }

  // Convert HH:MM:SS (API format) to HH:MM (input[type=time])
  function toTimeInput(val) {
    if (!val) return '';
    return val.slice(0, 5); // "09:00:00" -> "09:00"
  }

  // Convert HH:MM (input) to HH:MM:SS (API format)
  function toApiTime(val) {
    if (!val) return null;
    return val.length === 5 ? val + ':00' : val;
  }

  onMount(async () => {
    try {
      const res = await fetch(apiUrls.workingHours, { credentials: 'same-origin' });
      if (res.ok) {
        const data = await res.json();
        start_time = toTimeInput(data.working_hours_start) || '09:00';
        end_time = toTimeInput(data.working_hours_end) || '18:00';
        selectedDays = parseDays(data.working_days);
        if (selectedDays.size === 0) {
          selectedDays = new Set([1, 2, 3, 4, 5]);
        }
      } else if (res.status === 403) {
        errorMsg = 'Admin access required to view working hours.';
      } else {
        errorMsg = 'Failed to load working hours.';
      }
    } catch (e) {
      errorMsg = 'Network error loading working hours.';
    } finally {
      loading = false;
    }
  });

  async function save() {
    saving = true;
    successMsg = '';
    errorMsg = '';

    const body = {
      working_hours_start: toApiTime(start_time),
      working_hours_end: toApiTime(end_time),
      working_days: formatDays(selectedDays),
    };

    try {
      const res = await fetch(apiUrls.workingHours, {
        method: 'PATCH',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify(body),
      });

      if (res.ok) {
        const data = await res.json();
        start_time = toTimeInput(data.working_hours_start) || start_time;
        end_time = toTimeInput(data.working_hours_end) || end_time;
        selectedDays = parseDays(data.working_days);
        successMsg = 'Working hours saved successfully.';
      } else if (res.status === 403) {
        errorMsg = 'Admin access required to update working hours.';
      } else {
        const d = await res.json().catch(() => ({}));
        errorMsg = d.detail || JSON.stringify(d);
      }
    } catch (e) {
      errorMsg = 'Network error saving working hours.';
    } finally {
      saving = false;
    }
  }
</script>

<div class="bg-white rounded-lg shadow p-6 max-w-2xl">
  <h2 class="text-base font-semibold text-gray-900 mb-4">Working Hours</h2>
  <p class="text-sm text-gray-500 mb-6">
    Configure when inbound calls are accepted. Outside these hours, callers will
    hear the non-working hours sound.
  </p>

  {#if loading}
    <div class="flex items-center gap-2 text-sm text-gray-500 py-8">
      <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
      </svg>
      Loading working hours…
    </div>
  {:else}
    {#if successMsg}
      <div class="mb-4 rounded-md bg-green-50 border border-green-200 px-4 py-3 text-sm text-green-700">
        {successMsg}
      </div>
    {/if}
    {#if errorMsg}
      <div class="mb-4 rounded-md bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
        {errorMsg}
      </div>
    {/if}

    <form on:submit|preventDefault={save} class="space-y-6">

      <!-- Working Days -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">Working Days</label>
        <div class="flex flex-wrap gap-2">
          {#each ALL_DAYS as day}
            <button
              type="button"
              on:click={() => toggleDay(day.value)}
              class="px-3 py-1.5 rounded text-sm font-medium border transition-colors
                {selectedDays.has(day.value)
                  ? 'bg-indigo-600 text-white border-indigo-600'
                  : 'bg-white text-gray-700 border-gray-300 hover:border-indigo-400 hover:text-indigo-600'}"
            >
              {day.label}
            </button>
          {/each}
        </div>
        <p class="mt-1.5 text-xs text-gray-500">
          Selected: {[...selectedDays].length === 0 ? 'None (all calls rejected)' : ALL_DAYS.filter(d => selectedDays.has(d.value)).map(d => d.label).join(', ')}
        </p>
      </div>

      <!-- Time Range -->
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">
            Start Time
          </label>
          <input
            type="time"
            bind:value={start_time}
            class="border border-gray-300 rounded px-3 py-2 text-sm w-full focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">
            End Time
          </label>
          <input
            type="time"
            bind:value={end_time}
            class="border border-gray-300 rounded px-3 py-2 text-sm w-full focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
      </div>

      <!-- Submit -->
      <div class="pt-2 border-t border-gray-100">
        <button
          type="submit"
          disabled={saving}
          class="bg-indigo-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 inline-flex items-center gap-2"
        >
          {#if saving}
            <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
            </svg>
          {/if}
          Save Working Hours
        </button>
      </div>
    </form>
  {/if}
</div>
