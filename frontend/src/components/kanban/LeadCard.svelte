<script>
    import { createEventDispatcher } from 'svelte';

    export let lead;
    export let stageId;

    const dispatch = createEventDispatcher();

    let dropdownOpen = false;

    function toggleDropdown(e) {
        e.stopPropagation();
        dropdownOpen = !dropdownOpen;
    }

    function closeDropdown() {
        dropdownOpen = false;
    }

    function handleEdit() {
        dispatch('edit', { leadId: lead.id, stageId });
        dropdownOpen = false;
    }

    function handleDelete() {
        dispatch('delete', { leadId: lead.id, title: lead.title });
        dropdownOpen = false;
    }

    function handleMarkWon() {
        dispatch('markWon', { leadId: lead.id });
        dropdownOpen = false;
    }

    function handleMarkLost() {
        dispatch('markLost', { leadId: lead.id, title: lead.title });
        dropdownOpen = false;
    }

    function formatValue(val) {
        return parseFloat(val || 0).toLocaleString();
    }

    function formatDate(dateStr) {
        if (!dateStr) return '';
        return new Date(dateStr).toLocaleDateString();
    }
</script>

<svelte:window on:click={closeDropdown} />

<!-- svelte-ignore a11y-click-events-have-key-events -->
<div
    class="lead-card bg-white p-4 rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition-shadow cursor-grab active:cursor-grabbing"
    data-lead-id={lead.id}
    role="button"
    tabindex="0"
>
    <div class="flex justify-between items-start mb-2">
        <!-- Title + unread badge -->
        <h4
            class="text-sm font-medium text-gray-900 truncate flex-1 flex items-center gap-1 cursor-pointer"
            on:click={handleEdit}
        >
            {lead.title}
            {#if lead.unread_message_count > 0}
                <span
                    class="wa-badge inline-flex items-center justify-center min-w-[1.25rem] h-5 px-1 rounded-full bg-green-500 text-white font-bold flex-shrink-0 ml-1"
                    style="font-size:10px"
                    title="{lead.unread_message_count} unread WhatsApp message{lead.unread_message_count > 1 ? 's' : ''}"
                >
                    {lead.unread_message_count > 9 ? '9+' : lead.unread_message_count}
                </span>
            {/if}
        </h4>

        <!-- Dropdown -->
        <div class="relative ml-2">
            <button
                class="inline-flex items-center justify-center w-6 h-6 rounded text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
                on:click={toggleDropdown}
                title="Options"
            >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                </svg>
            </button>
            {#if dropdownOpen}
                <div
                    class="absolute right-0 top-full z-50 min-w-[120px] bg-white border border-gray-200 rounded-md shadow-lg"
                    on:click|stopPropagation
                >
                    <button
                        class="block w-full px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-50"
                        on:click={handleEdit}
                    >
                        <i class="fas fa-edit mr-2"></i>Edit
                    </button>
                    <button
                        class="block w-full px-3 py-2 text-left text-sm text-green-700 hover:bg-green-50"
                        on:click={handleMarkWon}
                    >
                        <i class="fas fa-trophy mr-2"></i>Mark Won
                    </button>
                    <button
                        class="block w-full px-3 py-2 text-left text-sm text-orange-600 hover:bg-orange-50"
                        on:click={handleMarkLost}
                    >
                        <i class="fas fa-times-circle mr-2"></i>Mark Lost
                    </button>
                    <button
                        class="block w-full px-3 py-2 text-left text-sm text-red-600 hover:bg-red-50"
                        on:click={handleDelete}
                    >
                        <i class="fas fa-trash mr-2"></i>Delete
                    </button>
                </div>
            {/if}
        </div>
    </div>

    <!-- Contact info -->
    <div class="space-y-1 mb-3 cursor-pointer" on:click={handleEdit}>
        <p class="text-sm text-gray-600 truncate">{lead.full_name || ''}</p>
        {#if lead.company_name}
            <p class="text-xs text-gray-500 truncate">{lead.company_name}</p>
        {/if}
    </div>

    <!-- Value + assigned -->
    <div class="flex justify-between items-center cursor-pointer" on:click={handleEdit}>
        <span class="text-sm font-semibold text-emerald-600">${formatValue(lead.estimated_value)}</span>
        <span class="text-xs text-gray-400">{lead.assigned_to || 'Unassigned'}</span>
    </div>

    <!-- Last activity -->
    <div class="mt-2 text-xs text-gray-400 cursor-pointer" on:click={handleEdit}>
        Updated {formatDate(lead.last_activity)}
    </div>

    <!-- WhatsApp preview -->
    {#if lead.last_message_preview}
        <div class="wa-preview mt-2 text-xs text-gray-500 truncate border-t border-gray-100 pt-2">
            <i class="fab fa-whatsapp text-green-500 mr-1"></i>{lead.last_message_preview}
        </div>
    {/if}
</div>
