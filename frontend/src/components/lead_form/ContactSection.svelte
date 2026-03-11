<script>
  import { apiGet, apiPatch } from '../../utils/api.js';

  export let lead = {};
  export let apiUrls = {};
  export let onLeadUpdated = () => {};

  // Fallback editable fields (used when no rep is selected)
  let fullName = lead.full_name || '';
  let email = lead.email || '';
  let phone = lead.phone || '';
  let position = lead.position || '';

  // Contact grid state
  let contacts = [];
  let loadingContacts = false;
  let selectedContactId = lead.contact ?? null;
  let showContactGrid = false;
  let companyContactType = 'company'; // 'company' | 'individual'
  let companyLegalId = '';

  // Track company changes → reload contacts, always clear rep fields immediately
  let trackedCompanyId = lead.company ?? null;
  $: {
    const newCompanyId = lead.company ?? null;
    if (newCompanyId !== trackedCompanyId) {
      trackedCompanyId = newCompanyId;
      selectedContactId = lead.contact ?? null;
      showContactGrid = false;
      // Always clear — avoids showing stale rep from a different company.
      // loadContacts will populate from displayContact if contacts exist.
      fullName = '';
      email = '';
      phone = '';
      position = '';
      if (newCompanyId) {
        loadContacts(newCompanyId);
      } else {
        contacts = [];
      }
    }
  }

  // Track contact changes from outside (e.g. rep selected in LeadInfoPanel)
  let trackedContactId = lead.contact ?? null;
  $: {
    const newContactId = lead.contact ?? null;
    if (newContactId !== trackedContactId) {
      trackedContactId = newContactId;
      selectedContactId = newContactId;
      fullName = lead.full_name || '';
      email = lead.email || '';
      phone = lead.phone || '';
      position = lead.position || '';
    }
  }

  // Load on mount if company already linked
  let mounted = false;
  $: if (!mounted && lead.company) {
    mounted = true;
    loadContacts(lead.company);
  }

  async function loadContacts(companyId) {
    loadingContacts = true;
    try {
      const res = await apiGet(`/crm/api/company/${companyId}/contacts/`);
      if (res.ok) {
        const data = await res.json();
        contacts = data.contacts || [];
        companyContactType = data.company?.contact_type || 'company';
        companyLegalId = data.company?.legal_id || '';
        // No Contact records found
        if (contacts.length === 0) {
          if (companyContactType === 'individual') {
            // For individuals, use the company's own contact info
            fullName = data.company?.name || '';
            email = data.company?.email || '';
            phone = data.company?.phone || '';
            position = '';
          } else {
            fullName = '';
            email = '';
            phone = '';
            position = '';
          }
        }
      }
    } catch {
      contacts = [];
    } finally {
      loadingContacts = false;
    }
  }

  let saving = false;

  async function saveField(field, value) {
    saving = true;
    try {
      const res = await apiPatch(apiUrls.lead, { [field]: value });
      if (res.ok) onLeadUpdated(await res.json());
    } finally {
      saving = false;
    }
  }

  async function saveLegalId(value) {
    if (!lead.company) return;
    saving = true;
    try {
      await apiPatch(`/contacts/api/companies/${lead.company}/`, { legal_id: value });
    } finally {
      saving = false;
    }
  }

  async function selectContact(contact) {
    console.log('[CRM:CONTACT-SEC] selectContact ▶', { id: contact.id, name: contact.name, phone: contact.phone, mobile: contact.mobile });
    selectedContactId = contact.id;
    showContactGrid = false;
    fullName = contact.name || '';
    email = contact.email || '';
    phone = contact.phone || contact.mobile || '';
    position = contact.position || '';

    const patchBody = {
      contact_id: contact.id,
      full_name: contact.name || '',
      email: contact.email || '',
      phone: contact.phone || contact.mobile || '',
      position: contact.position || '',
    };
    console.log('[CRM:CONTACT-SEC] PATCHing lead with:', patchBody);
    const res = await apiPatch(apiUrls.lead, patchBody);
    console.log('[CRM:CONTACT-SEC] PATCH response status:', res.status);
    if (res.ok) {
      const updatedLead = await res.json();
      console.log('[CRM:CONTACT-SEC] PATCH response lead.phone:', updatedLead?.phone, '| lead.contact:', updatedLead?.contact);
      onLeadUpdated(updatedLead);
    } else {
      const body = await res.text();
      console.error('[CRM:CONTACT-SEC] PATCH FAILED:', res.status, body);
    }
  }

  $: selectedContact = contacts.find(c => c.id === selectedContactId);
  $: displayContact = selectedContact || (contacts.length > 0 ? contacts.find(c => c.is_favorite) || contacts[0] : null);

  // Sync editable fields from displayContact whenever the displayed rep changes
  let trackedDisplayContactId = null;
  $: if ((displayContact?.id ?? null) !== trackedDisplayContactId) {
    trackedDisplayContactId = displayContact?.id ?? null;
    if (displayContact) {
      fullName = displayContact.name || '';
      email = displayContact.email || '';
      phone = displayContact.phone || displayContact.mobile || '';
      position = displayContact.position || '';
    }
  }
</script>

<div class="bg-white rounded-lg border border-gray-200 p-4 space-y-3">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <h3 class="text-sm font-semibold text-gray-700">Representative Information</h3>
    {#if saving}
      <span class="text-xs text-gray-400">Saving…</span>
    {/if}
  </div>

  {#if contacts.length > 0}
    {#if companyContactType !== 'individual'}
      <!-- Company type: show selector row + tile grid -->
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-1.5">
          {#if displayContact}
            <div class="w-6 h-6 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
              <span class="text-xs font-semibold text-blue-600">
                {displayContact.name?.charAt(0)?.toUpperCase() || '?'}
              </span>
            </div>
            <span class="text-xs font-medium text-gray-700">{displayContact.name}</span>
          {/if}
        </div>
        <button
          type="button"
          class="text-xs text-blue-600 hover:text-blue-800 font-medium transition-colors"
          on:click={() => showContactGrid = !showContactGrid}
        >
          {showContactGrid ? 'Hide' : 'Choose another representative'}
        </button>
      </div>

      {#if showContactGrid}
        <div class="grid grid-cols-2 gap-1.5">
          {#each contacts as contact}
            <button
              type="button"
              class="text-left px-2.5 py-2 rounded-lg border text-xs transition-colors
                {(selectedContactId ?? displayContact?.id) === contact.id
                  ? 'border-blue-500 bg-blue-50 text-blue-800'
                  : 'border-gray-200 bg-white hover:bg-gray-50 text-gray-700'}"
              on:click={() => selectContact(contact)}
            >
              <div class="flex items-center gap-1 mb-0.5">
                <p class="font-medium truncate flex-1">{contact.name}</p>
                {#if contact.is_favorite}
                  <svg class="w-3 h-3 text-amber-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
                  </svg>
                {/if}
              </div>
              {#if contact.position}
                <p class="text-gray-400 truncate">{contact.position}</p>
              {/if}
            </button>
          {/each}
        </div>
      {/if}

      <div class="border-t border-gray-100"></div>
    {/if}

    <!-- Contact info — editable inputs pre-filled from selected rep -->
    {#if displayContact}
      <div class="grid grid-cols-2 gap-2">
        <div>
          <label class="block text-xs font-medium text-gray-500 mb-1">Representative Name</label>
          <input
            type="text"
            bind:value={fullName}
            on:blur={() => saveField('full_name', fullName)}
            class="w-full border border-gray-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          {#if companyContactType === 'individual'}
            <label class="block text-xs font-medium text-gray-500 mb-1">ID</label>
            <input
              type="text"
              bind:value={companyLegalId}
              on:blur={() => saveLegalId(companyLegalId)}
              class="w-full border border-gray-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          {:else}
            <label class="block text-xs font-medium text-gray-500 mb-1">Position</label>
            <input
              type="text"
              bind:value={position}
              on:blur={() => saveField('position', position)}
              class="w-full border border-gray-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          {/if}
        </div>
      </div>
      <div class="grid grid-cols-2 gap-2">
        <div>
          <label class="block text-xs font-medium text-gray-500 mb-1">Email</label>
          <input
            type="email"
            bind:value={email}
            on:blur={() => saveField('email', email)}
            class="w-full border border-gray-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-500 mb-1">Phone</label>
          <input
            type="tel"
            bind:value={phone}
            on:blur={() => saveField('phone', phone)}
            class="w-full border border-gray-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>
    {/if}

  {:else if lead.company && loadingContacts}
    <p class="text-xs text-gray-400">Loading representatives…</p>

  {:else}
    <!-- No company linked (or individual with no contacts) — show manual editable fields -->
    <div class="grid grid-cols-2 gap-2">
      <div>
        <label class="block text-xs font-medium text-gray-500 mb-1">Representative Name</label>
        <input
          type="text"
          bind:value={fullName}
          on:blur={() => saveField('full_name', fullName)}
          class="w-full border border-gray-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>
      <div>
        {#if companyContactType === 'individual'}
          <label class="block text-xs font-medium text-gray-500 mb-1">ID</label>
          <input
            type="text"
            bind:value={companyLegalId}
            on:blur={() => saveLegalId(companyLegalId)}
            class="w-full border border-gray-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        {:else}
          <label class="block text-xs font-medium text-gray-500 mb-1">Position</label>
          <input
            type="text"
            bind:value={position}
            on:blur={() => saveField('position', position)}
            class="w-full border border-gray-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        {/if}
      </div>
    </div>

    <div class="grid grid-cols-2 gap-2">
      <div>
        <label class="block text-xs font-medium text-gray-500 mb-1">Email</label>
        <input
          type="email"
          bind:value={email}
          on:blur={() => saveField('email', email)}
          class="w-full border border-gray-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>
      <div>
        <label class="block text-xs font-medium text-gray-500 mb-1">Phone</label>
        <input
          type="tel"
          bind:value={phone}
          on:blur={() => saveField('phone', phone)}
          class="w-full border border-gray-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>
    </div>
  {/if}
</div>
