<script>
  import { apiGet, apiPost, apiPatch } from '../../utils/api.js';
  import { getCsrfToken } from '../../utils/csrf.js';
  import { onMount } from 'svelte';

  const debug = new URLSearchParams(window.location.search).get('debug') === '1';

  export let leadId = null;
  export let apiUrls = {};
  export let activityTypes = [];

  let activities = [];
  let loading = true;
  let error = '';

  // Quick-create form state
  let showCreate = false;
  let creating = false;
  let newActivity = { activity_type_id: '', title: '', scheduled_date: '', description: '' };

  // Filter state
  let statusFilter = '';

  // Detail expand state
  let expandedId = null;
  let detailData = {};
  let detailLoading = false;

  // Recording modal state
  let modal = { open: false, loading: false, callData: null, error: '', retranscribing: false, reanalyzing: false };
  let _pollTimer = null;

  async function openRecordingModal(callId) {
    modal = { open: true, loading: true, callData: null, error: '', retranscribing: false, reanalyzing: false };
    try {
      const res = await apiGet(`/calls/api/calls/${callId}/`);
      if (res.ok) {
        modal = { ...modal, loading: false, callData: await res.json() };
      } else {
        modal = { ...modal, loading: false, error: 'Failed to load call data' };
      }
    } catch {
      modal = { ...modal, loading: false, error: 'Failed to load call data' };
    }
  }

  function closeModal() {
    if (_pollTimer) { clearInterval(_pollTimer); _pollTimer = null; }
    modal = { open: false, loading: false, callData: null, error: '', retranscribing: false, reanalyzing: false };
  }

  async function _refreshCallData() {
    if (!modal.callData) return;
    try {
      const res = await apiGet(`/calls/api/calls/${modal.callData.id}/`);
      if (res.ok) modal = { ...modal, callData: await res.json() };
    } catch { /* ignore */ }
  }

  function _startPolling(doneCheck) {
    if (_pollTimer) clearInterval(_pollTimer);
    _pollTimer = setInterval(async () => {
      await _refreshCallData();
      if (doneCheck(modal.callData)) {
        clearInterval(_pollTimer);
        _pollTimer = null;
        modal = { ...modal, retranscribing: false, reanalyzing: false };
      }
    }, 3000);
  }

  async function retranscribe() {
    if (!modal.callData) return;
    const langCode = modal.callData.transcript?.language_code || 'en';
    modal = { ...modal, retranscribing: true };
    const fd = new FormData();
    fd.append('language', langCode);
    try {
      const res = await fetch(`/calls/${modal.callData.id}/transcript/start/`, {
        method: 'POST', body: fd, credentials: 'same-origin',
        headers: { 'X-CSRFToken': getCsrfToken() },
      });
      if (res.ok) {
        await _refreshCallData();
        _startPolling((d) => d?.transcript?.status === 'completed' || d?.transcript?.status === 'failed');
      } else {
        modal = { ...modal, retranscribing: false };
      }
    } catch {
      modal = { ...modal, retranscribing: false };
    }
  }

  async function reanalyze() {
    if (!modal.callData) return;
    modal = { ...modal, reanalyzing: true };
    const fd = new FormData();
    try {
      const res = await fetch(`/calls/${modal.callData.id}/analysis/start/`, {
        method: 'POST', body: fd, credentials: 'same-origin',
        headers: { 'X-CSRFToken': getCsrfToken() },
      });
      if (res.ok) {
        await _refreshCallData();
        _startPolling((d) => d?.analysis?.status === 'completed' || d?.analysis?.status === 'failed');
      } else {
        modal = { ...modal, reanalyzing: false };
      }
    } catch {
      modal = { ...modal, reanalyzing: false };
    }
  }

  $: filteredActivities = statusFilter
    ? activities.filter((a) => a.status === statusFilter)
    : activities;

  onMount(async () => {
    await fetchActivities();
  });

  async function fetchActivities() {
    loading = true;
    error = '';
    try {
      const url = `${apiUrls.activities}?lead=${leadId}&ordering=-id`;
      const res = await apiGet(url);
      if (res.ok) {
        const data = await res.json();
        activities = data.results || data;
      } else {
        error = 'Failed to load activities';
      }
    } catch {
      error = 'Failed to load activities';
    } finally {
      loading = false;
    }
  }

  async function toggleDetail(actId) {
    if (expandedId === actId) {
      expandedId = null;
      return;
    }
    expandedId = actId;
    if (detailData[actId]) return; // already fetched
    detailLoading = true;
    try {
      const res = await apiGet(`${apiUrls.activities}${actId}/`);
      if (res.ok) detailData[actId] = await res.json();
    } finally {
      detailLoading = false;
    }
  }

  async function createActivity() {
    if (creating || !newActivity.title || !newActivity.activity_type_id) return;
    creating = true;
    try {
      const res = await apiPost(apiUrls.activities, {
        ...newActivity,
        lead_id: leadId,
        activity_type_id: Number(newActivity.activity_type_id),
      });
      if (res.ok) {
        showCreate = false;
        newActivity = { activity_type_id: '', title: '', scheduled_date: '', description: '' };
        await fetchActivities();
      } else {
        const err = await res.json().catch(() => ({}));
        error = JSON.stringify(err);
      }
    } catch {
      error = 'Failed to create activity';
    } finally {
      creating = false;
    }
  }

  async function markComplete(activityId) {
    try {
      const res = await apiPost(`${apiUrls.activities}${activityId}/complete/`, {});
      if (res.ok) {
        // Refresh list and clear cached detail so it reloads on next open
        delete detailData[activityId];
        detailData = detailData;
        await fetchActivities();
      }
    } catch {
      // Ignore
    }
  }

  function formatDate(dateStr) {
    if (!dateStr) return '';
    return new Date(dateStr).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
  }

  const STATUS_COLOR = {
    planned: 'bg-blue-100 text-blue-800',
    completed: 'bg-green-100 text-green-800',
    cancelled: 'bg-gray-100 text-gray-600',
  };
</script>

<div class="flex flex-col gap-3">
  <!-- Header row -->
  <div class="flex items-center gap-2 justify-between">
    <div class="flex gap-2">
      <select
        bind:value={statusFilter}
        class="border border-gray-200 rounded px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        <option value="">All</option>
        <option value="planned">Planned</option>
        <option value="completed">Completed</option>
        <option value="cancelled">Cancelled</option>
      </select>
    </div>
    <button
      type="button"
      class="flex items-center gap-1 px-3 py-1.5 bg-indigo-600 text-white rounded text-xs font-medium hover:bg-indigo-700 transition-colors"
      on:click={() => (showCreate = !showCreate)}
    >
      <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
      </svg>
      Add Activity
    </button>
  </div>

  <!-- Quick create form -->
  {#if showCreate}
    <div class="bg-gray-50 border border-gray-200 rounded-lg p-3 space-y-2">
      <div class="grid grid-cols-2 gap-2">
        <select
          bind:value={newActivity.activity_type_id}
          class="border border-gray-200 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Type…</option>
          {#each activityTypes as t}
            <option value={t.id}>{t.name}</option>
          {/each}
        </select>
        <input
          type="date"
          bind:value={newActivity.scheduled_date}
          class="border border-gray-200 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>
      <input
        type="text"
        bind:value={newActivity.title}
        placeholder="Title"
        class="w-full border border-gray-200 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
      <textarea
        bind:value={newActivity.description}
        rows="2"
        placeholder="Description (optional)"
        class="w-full border border-gray-200 rounded px-2 py-1.5 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
      ></textarea>
      <div class="flex gap-2 justify-end">
        <button
          type="button"
          class="px-3 py-1.5 text-xs text-gray-600 hover:text-gray-900"
          on:click={() => (showCreate = false)}
        >Cancel</button>
        <button
          type="button"
          class="px-3 py-1.5 bg-indigo-600 text-white rounded text-xs font-medium hover:bg-indigo-700 disabled:opacity-50"
          disabled={creating}
          on:click={createActivity}
        >{creating ? 'Creating…' : 'Create'}</button>
      </div>
    </div>
  {/if}

  <!-- Activity list -->
  {#if loading}
    <p class="text-sm text-gray-400 text-center py-4">Loading activities…</p>
  {:else if error}
    <p class="text-sm text-red-500">{error}</p>
  {:else if filteredActivities.length === 0}
    <p class="text-sm text-gray-400 text-center py-4">No activities yet.</p>
  {:else}
    <div class="space-y-2">
      {#each filteredActivities as act (act.id)}
        <div class="bg-white border rounded-lg overflow-hidden transition-colors
          {expandedId === act.id ? 'border-indigo-300' : 'border-gray-100 hover:border-gray-200'}">

          <!-- Row — clickable -->
          <button
            type="button"
            class="w-full flex items-start gap-3 px-3 py-2.5 text-left"
            on:click={() => toggleDetail(act.id)}
          >
            <!-- Icon -->
            <div class="w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5"
                 style="background-color: {act.activity_type?.color || '#e5e7eb'}20; color: {act.activity_type?.color || '#6b7280'}">
              <i class="text-xs {act.activity_type?.icon || 'fas fa-tasks'}"></i>
            </div>

            <!-- Content -->
            <div class="flex-1 min-w-0">
              <div class="flex items-start justify-between gap-2">
                <p class="text-sm font-medium text-gray-900 truncate">{act.title}</p>
                <span class="text-xs px-2 py-0.5 rounded-full flex-shrink-0 {STATUS_COLOR[act.status] || 'bg-gray-100 text-gray-600'}">
                  {act.status}
                </span>
              </div>
              <p class="text-xs text-gray-500 mt-0.5">
                <span class="text-gray-400">#{act.id}</span>
                {#if act.scheduled_date}<span class="mx-1">·</span>{act.scheduled_date}{/if}
              </p>
            </div>

            <!-- Chevron -->
            <svg class="w-4 h-4 text-gray-400 flex-shrink-0 mt-1 transition-transform {expandedId === act.id ? 'rotate-180' : ''}"
                 fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
            </svg>
          </button>

          <!-- Expanded detail panel -->
          {#if expandedId === act.id}
            <div class="border-t border-gray-100 px-3 py-3 bg-gray-50 space-y-3">
              {#if detailLoading && !detailData[act.id]}
                <p class="text-xs text-gray-400">Loading…</p>
              {:else if detailData[act.id]}
                {@const d = detailData[act.id]}

                <!-- Type + assigned to -->
                <div class="flex items-center gap-4 text-xs text-gray-500">
                  {#if d.activity_type?.name}
                    <span class="flex items-center gap-1">
                      <i class="{d.activity_type.icon || 'fas fa-tasks'}" style="color:{d.activity_type.color}"></i>
                      {d.activity_type.name}
                    </span>
                  {/if}
                  {#if d.assigned_to_name}
                    <span>Assigned: <span class="text-gray-700">{d.assigned_to_name}</span></span>
                  {/if}
                  {#if d.created_by_name}
                    <span>By: <span class="text-gray-700">{d.created_by_name}</span></span>
                  {/if}
                </div>

                <!-- Description -->
                {#if d.description}
                  <div>
                    <p class="text-xs font-medium text-gray-500 mb-1">Description</p>
                    <p class="text-sm text-gray-700 whitespace-pre-wrap">{d.description}</p>
                  </div>
                {/if}

                <!-- Outcome -->
                {#if d.outcome}
                  <div>
                    <p class="text-xs font-medium text-gray-500 mb-1">Outcome</p>
                    <p class="text-sm text-gray-700 whitespace-pre-wrap">{d.outcome}</p>
                  </div>
                {/if}

                <!-- Dates -->
                <div class="flex gap-4 text-xs text-gray-500">
                  {#if d.scheduled_date}
                    <span>Scheduled: <span class="text-gray-700">{d.scheduled_date}</span></span>
                  {/if}
                  {#if d.completed_at}
                    <span>Completed: <span class="text-gray-700">{formatDate(d.completed_at)}</span></span>
                  {/if}
                </div>

                <!-- Check recording button -->
                {#if d.call_recording}
                  <button
                    type="button"
                    class="flex items-center gap-1.5 px-3 py-1.5 border border-indigo-300 text-indigo-700 hover:bg-indigo-50 rounded text-xs font-medium transition-colors"
                    on:click|stopPropagation={() => openRecordingModal(d.call_recording.call_id)}
                  >
                    <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M12 2a3 3 0 0 1 3 3v6a3 3 0 0 1-6 0V5a3 3 0 0 1 3-3zm7 9a7 7 0 0 1-14 0H3a9 9 0 0 0 8 8.94V22h2v-2.06A9 9 0 0 0 21 11h-2z"/>
                    </svg>
                    Check Recording
                  </button>
                {/if}

                <!-- Complete button -->
                {#if act.status === 'planned'}
                  <div class="flex justify-end">
                    <button
                      type="button"
                      class="flex items-center gap-1.5 px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white rounded text-xs font-medium transition-colors"
                      on:click|stopPropagation={() => markComplete(act.id)}
                    >
                      <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                      </svg>
                      Mark Complete
                    </button>
                  </div>
                {/if}
              {/if}
            </div>
          {/if}
        </div>
      {/each}
    </div>
  {/if}
</div>

<!-- Recording / Transcript / Analysis modal -->
{#if modal.open}
  <!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
  <div
    class="fixed inset-0 z-50 flex items-center justify-center p-4"
    style="background:rgba(0,0,0,0.5)"
    on:click={closeModal}
  >
    <div
      class="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[85vh] flex flex-col"
      on:click|stopPropagation
    >
      <!-- Modal header -->
      <div class="flex items-center justify-between px-5 py-4 border-b border-gray-200">
        <h2 class="text-base font-semibold text-gray-900">Call Recording</h2>
        <button type="button" class="text-gray-400 hover:text-gray-600" on:click={closeModal}>
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
          </svg>
        </button>
      </div>

      <!-- Modal body -->
      <div class="overflow-y-auto flex-1 px-5 py-4 space-y-5">
        {#if modal.loading}
          <p class="text-sm text-gray-400 text-center py-8">Loading…</p>
        {:else if modal.error}
          <p class="text-sm text-red-500 text-center py-8">{modal.error}</p>
        {:else if modal.callData}
          {@const c = modal.callData}

          <!-- Call meta -->
          <div class="flex items-center gap-4 text-xs text-gray-500">
            <span class="capitalize">{c.direction}</span>
            {#if c.duration_formatted}<span>{c.duration_formatted}</span>{/if}
            {#if c.from_number}<span>{c.from_number} → {c.to_number}</span>{/if}
          </div>

          <!-- Recording player -->
          {#if c.recording}
            <div class="space-y-2">
              <p class="text-xs font-semibold text-gray-600 uppercase tracking-wide">Recording</p>
              <audio controls src="/calls/recording/{c.recording.id}/download/" class="w-full"></audio>
              <div class="flex items-center gap-3 text-xs text-gray-400">
                {#if c.recording.duration}<span>{c.recording.duration}s</span>{/if}
                {#if c.recording.file_size_formatted}<span>{c.recording.file_size_formatted}</span>{/if}
                <a href="/calls/recording/{c.recording.id}/download/" download class="text-indigo-600 hover:text-indigo-800 font-medium ml-auto">Download</a>
              </div>
            </div>
          {:else}
            <p class="text-xs text-gray-400">No recording available for this call.</p>
          {/if}

          {#if debug}
            <!-- Debug: Transcript -->
            <div class="space-y-2">
              <div class="flex items-center justify-between">
                <p class="text-xs font-semibold text-gray-600 uppercase tracking-wide">
                  Transcript
                  {#if c.transcript}<span class="ml-1 font-normal text-gray-400 normal-case">({c.transcript.status}{c.transcript.language_code ? ' · ' + c.transcript.language_code : ''})</span>{/if}
                </p>
                <button
                  type="button"
                  class="flex items-center gap-1 px-2 py-1 text-xs border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50"
                  disabled={modal.retranscribing || !c.recording}
                  on:click|stopPropagation={retranscribe}
                >
                  {#if modal.retranscribing}
                    <svg class="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                    </svg>
                    Transcribing…
                  {:else}
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                    </svg>
                    Retranscribe
                  {/if}
                </button>
              </div>
              {#if c.transcript?.status === 'completed'}
                <div class="grid grid-cols-2 gap-3">
                  <div class="bg-gray-50 rounded-lg p-3">
                    <p class="text-xs font-medium text-gray-500 mb-1">Caller</p>
                    <p class="text-sm text-gray-700 whitespace-pre-wrap">{c.transcript.caller_text || '—'}</p>
                  </div>
                  <div class="bg-blue-50 rounded-lg p-3">
                    <p class="text-xs font-medium text-blue-500 mb-1">Agent</p>
                    <p class="text-sm text-gray-700 whitespace-pre-wrap">{c.transcript.agent_text || '—'}</p>
                  </div>
                </div>
              {:else if c.transcript}
                <p class="text-xs text-gray-400 capitalize">Transcript {c.transcript.status}</p>
              {:else}
                <p class="text-xs text-gray-400">No transcript yet.</p>
              {/if}
            </div>

            <!-- Debug: AI Analysis -->
            <div class="space-y-2">
              <div class="flex items-center justify-between">
                <p class="text-xs font-semibold text-gray-600 uppercase tracking-wide">
                  AI Analysis
                  {#if c.analysis}<span class="ml-1 font-normal text-gray-400 normal-case">({c.analysis.status})</span>{/if}
                </p>
                <button
                  type="button"
                  class="flex items-center gap-1 px-2 py-1 text-xs border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50"
                  disabled={modal.reanalyzing || c.transcript?.status !== 'completed'}
                  on:click|stopPropagation={reanalyze}
                >
                  {#if modal.reanalyzing}
                    <svg class="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                    </svg>
                    Analyzing…
                  {:else}
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.347.347a3.5 3.5 0 01-4.95 0l-.347-.347z"/>
                    </svg>
                    Re-analyze
                  {/if}
                </button>
              </div>
              {#if c.analysis?.status === 'completed'}
                <p class="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">{c.analysis.analysis_text}</p>
              {:else if c.analysis}
                <p class="text-xs text-gray-400 capitalize">Analysis {c.analysis.status}</p>
              {:else}
                <p class="text-xs text-gray-400">No analysis yet.</p>
              {/if}
            </div>
          {/if}
        {/if}
      </div>
    </div>
  </div>
{/if}
