<script>
  import { apiGet, apiPatch } from '../../utils/api.js';

  export let lead = {};
  export let apiUrls = {};
  export let onLeadUpdated = () => {};

  // Opportunity fields
  let title = lead.title || '';
  let estimatedValue = lead.estimated_value || '';
  let probability = lead.probability ?? '';
  let expectedCloseDate = lead.expected_close_date || '';
  let source = lead.source || 'other';

  // Company search state
  let contactQuery = '';
  let contactResults = [];
  let searchTimeout = null;
  let searching = false;
  let isOpen = false;
  let isSavingCompany = false; // guard: prevent reactive sync during async save

  let selectedContact = lead.company
    ? { id: lead.company, name: lead.company_name_display || lead.company_name || '' }
    : null;

  // Only sync from lead prop when we are NOT mid-save (avoids race condition reset)
  $: if (!isSavingCompany) {
    if (!lead.company) {
      selectedContact = null;
    } else if (lead.company && (!selectedContact || selectedContact.id !== lead.company)) {
      selectedContact = { id: lead.company, name: lead.company_name_display || lead.company_name || '' };
    }
  }

  const SOURCE_OPTIONS = [
    ['website', 'Website'],
    ['referral', 'Referral'],
    ['cold_call', 'Cold Call'],
    ['email', 'Email'],
    ['social', 'Social Media'],
    ['partner', 'Partner'],
    ['event', 'Event'],
    ['advertisement', 'Advertisement'],
    ['other', 'Other'],
  ];

  let saving = false;
  let saveError = '';

  async function saveField(field, value) {
    if (saving) return;
    saving = true;
    saveError = '';
    try {
      const res = await apiPatch(apiUrls.lead, { [field]: value });
      if (res.ok) {
        onLeadUpdated(await res.json());
      } else {
        saveError = 'Save failed';
      }
    } catch {
      saveError = 'Save failed';
    } finally {
      saving = false;
    }
  }

  // Company search
  async function searchContacts() {
    if (contactQuery.length < 2) { contactResults = []; return; }
    searching = true;
    try {
      const res = await apiGet(`${apiUrls.companySearch}?q=${encodeURIComponent(contactQuery)}`);
      if (res.ok) {
        const data = await res.json();
        contactResults = data.companies || data;
      }
    } catch {
      contactResults = [];
    } finally {
      searching = false;
    }
  }

  function onContactInput() {
    isOpen = true;
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(searchContacts, 300);
  }

  function openDropdown() {
    isOpen = true;
    if (contactQuery.length >= 2) searchContacts();
  }

  async function selectContact(company) {
    isSavingCompany = true;
    selectedContact = { id: company.id, name: company.name };
    contactQuery = '';
    contactResults = [];
    isOpen = false;

    let patchData = { company_id: company.id, contact_id: null };
    try {
      const res = await apiGet(`/crm/api/company/${company.id}/contacts/`);
      if (res.ok) {
        const data = await res.json();
        const isIndividual = data.company?.contact_type === 'individual';
        const fav = (data.contacts || []).find(c => c.is_favorite) || (data.contacts || [])[0];
        // Always sync the company_name text field so page refresh shows the correct name
        patchData.company_name = data.company?.name || company.name;
        if (fav) {
          patchData.contact_id = fav.id;
          patchData.full_name = fav.name || '';
          patchData.email = fav.email || '';
          patchData.phone = fav.phone || fav.mobile || '';
          patchData.position = fav.position || '';
        } else if (isIndividual) {
          // Individual with no Contact record — use company's own contact info
          patchData.full_name = data.company?.name || '';
          patchData.email = data.company?.email || '';
          patchData.phone = data.company?.phone || '';
          patchData.position = '';
        }
      }
    } catch { /* link company only */ }

    try {
      const patchRes = await apiPatch(apiUrls.lead, patchData);
      if (patchRes.ok) onLeadUpdated(await patchRes.json());
      else saveError = 'Failed to save contact';
    } finally {
      isSavingCompany = false;
    }
  }

  async function clearContact() {
    isSavingCompany = true;
    selectedContact = null;
    contactQuery = '';
    contactResults = [];
    isOpen = false;
    try {
      const res = await apiPatch(apiUrls.lead, { company_id: null, contact_id: null });
      if (res.ok) onLeadUpdated(await res.json());
    } finally {
      isSavingCompany = false;
    }
  }

  function onBlurDropdown() {
    setTimeout(() => { isOpen = false; contactResults = []; }, 150);
  }
</script>

<div class="bg-white rounded-lg border border-gray-200 p-4 space-y-3">
  <h3 class="text-sm font-semibold text-gray-700">Lead Details</h3>

  <!-- Title -->
  <div>
    <label class="block text-xs font-medium text-gray-500 mb-1">Title</label>
    <input
      type="text"
      bind:value={title}
      on:blur={() => saveField('title', title)}
      class="w-full border border-gray-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
    />
  </div>

  <!-- Value & Probability -->
  <div class="grid grid-cols-2 gap-2">
    <div>
      <label class="block text-xs font-medium text-gray-500 mb-1">Estimated Value</label>
      <input
        type="number"
        bind:value={estimatedValue}
        on:blur={() => saveField('estimated_value', estimatedValue)}
        min="0" step="0.01"
        class="w-full border border-gray-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
    </div>
    <div>
      <label class="block text-xs font-medium text-gray-500 mb-1">Probability (%)</label>
      <input
        type="number"
        bind:value={probability}
        on:blur={() => saveField('probability', probability)}
        min="0" max="100"
        class="w-full border border-gray-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
    </div>
  </div>

  <!-- Close date & Source -->
  <div class="grid grid-cols-2 gap-2">
    <div>
      <label class="block text-xs font-medium text-gray-500 mb-1">Expected Close Date</label>
      <input
        type="date"
        bind:value={expectedCloseDate}
        on:blur={() => saveField('expected_close_date', expectedCloseDate || null)}
        class="w-full border border-gray-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
    </div>
    <div>
      <label class="block text-xs font-medium text-gray-500 mb-1">Source</label>
      <select
        bind:value={source}
        on:change={() => saveField('source', source)}
        class="w-full border border-gray-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        {#each SOURCE_OPTIONS as [val, label]}
          <option value={val}>{label}</option>
        {/each}
      </select>
    </div>
  </div>

  <!-- Contact searchable select -->
  <div>
    <label class="block text-xs font-medium text-gray-500 mb-1">Contact</label>
    <div class="relative">
      {#if selectedContact && !isOpen}
        <button
          type="button"
          class="w-full flex items-center justify-between border border-gray-200 rounded px-3 py-1.5 text-sm bg-white hover:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors"
          on:click={openDropdown}
        >
          <span class="flex items-center gap-2 min-w-0">
            <svg class="w-3.5 h-3.5 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
            </svg>
            <span class="truncate text-gray-800">{selectedContact.name}</span>
          </span>
          <div class="flex items-center gap-1 flex-shrink-0 ml-1">
            <span
              role="button"
              tabindex="0"
              class="text-gray-300 hover:text-gray-500 p-0.5 rounded transition-colors"
              on:click|stopPropagation={clearContact}
              on:keydown={(e) => e.key === 'Enter' && clearContact()}
              title="Clear"
            >
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
              </svg>
            </span>
            <svg class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
            </svg>
          </div>
        </button>
      {:else}
        <div class="relative">
          <input
            type="text"
            bind:value={contactQuery}
            on:input={onContactInput}
            on:focus={openDropdown}
            on:blur={onBlurDropdown}
            placeholder={selectedContact ? selectedContact.name : 'Search company…'}
            class="w-full border border-gray-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 pr-8"
          />
          <div class="absolute right-2 top-1/2 -translate-y-1/2">
            {#if searching}
              <svg class="w-4 h-4 animate-spin text-gray-400" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
              </svg>
            {:else}
              <svg class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
              </svg>
            {/if}
          </div>
        </div>
      {/if}

      {#if isOpen && contactResults.length > 0}
        <ul class="absolute z-20 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-56 overflow-y-auto">
          {#each contactResults as company}
            <li>
              <button
                type="button"
                class="w-full text-left px-3 py-2 hover:bg-gray-50 transition-colors"
                on:mousedown|preventDefault={() => selectContact(company)}
              >
                <p class="text-sm font-medium text-gray-800 truncate">{company.name}</p>
                {#if company.legal_id}
                  <p class="text-xs text-gray-400 truncate">{company.legal_id}</p>
                {/if}
              </button>
            </li>
          {/each}
        </ul>
      {:else if isOpen && contactQuery.length >= 2 && !searching}
        <div class="absolute z-20 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg px-3 py-2 text-sm text-gray-400">
          No results found
        </div>
      {/if}
    </div>
  </div>

  {#if saveError}
    <p class="text-xs text-red-500">{saveError}</p>
  {/if}
  {#if saving || isSavingCompany}
    <p class="text-xs text-gray-400">Saving…</p>
  {/if}
</div>
