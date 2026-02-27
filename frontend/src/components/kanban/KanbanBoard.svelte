<script>
    import { onMount, onDestroy } from 'svelte';
    import KanbanColumn from './KanbanColumn.svelte';
    import { apiGet, apiPatch, apiPost } from '@/utils/api.js';

    // Props injected from JSON data island
    export let viewContext = 'personal';
    export let selectedTeamId = 'all';
    export let userTeamId = '';
    export let isManager = false;
    export let isExecutive = false;
    export let availableTeams = [];
    export let apiUrls = {};

    let stages = [];
    let loading = false;
    let error = null;
    let currentView = viewContext;
    let currentTeamId = selectedTeamId;

    // WebSocket
    let ws = null;

    function buildKanbanUrl() {
        let url = `${apiUrls.kanban}?view=${currentView}`;
        if (currentTeamId && currentTeamId !== 'all') url += `&team=${currentTeamId}`;
        return url;
    }

    async function loadKanbanData() {
        loading = true;
        error = null;
        try {
            const res = await apiGet(buildKanbanUrl());
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            stages = data.stages;
        } catch (e) {
            error = 'Failed to load pipeline data. Please try again.';
            console.error('Kanban load error:', e);
        } finally {
            loading = false;
        }
    }

    async function handleStageUpdate({ detail }) {
        const { leadId, newStageId } = detail;
        try {
            const url = apiUrls.leadStage.replace('{leadId}', leadId);
            const res = await apiPatch(url, { stage_id: newStageId });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            // Refresh to update column counts + totals
            await loadKanbanData();
        } catch (e) {
            console.error('Stage update error:', e);
            await loadKanbanData(); // Revert UI
        }
    }

    async function handleDeleteLead({ detail }) {
        const { leadId, title } = detail;
        if (!confirm(`Are you sure you want to delete the opportunity "${title}"?\n\nThis action cannot be undone.`)) {
            return;
        }
        try {
            const res = await apiPost(`/crm/opportunities/${leadId}/delete/`, {});
            if (!res.ok) {
                const body = await res.json().catch(() => ({}));
                alert(body.error || body.message || 'Error deleting opportunity.');
                return;
            }
            const result = await res.json().catch(() => ({}));
            if (result.success === false) {
                alert(result.error || result.message || 'Error deleting opportunity.');
                return;
            }
            await loadKanbanData();
        } catch (e) {
            console.error('Delete error:', e);
            alert('Network error. Please check your connection.');
        }
    }

    function onViewChange(e) {
        currentView = e.target.value;
        // If manager switches to team view, set their team
        if (currentView === 'team' && userTeamId && !isExecutive) {
            currentTeamId = userTeamId;
        } else if (currentView === 'team' && isExecutive && currentTeamId === 'all' && availableTeams.length > 0) {
            currentTeamId = String(availableTeams[0].id);
        } else if (currentView !== 'team') {
            currentTeamId = 'all';
        }
        loadKanbanData();
    }

    function onTeamChange(e) {
        currentTeamId = e.target.value;
        loadKanbanData();
    }

    // WebSocket: patch card badges without full reload
    function connectWs() {
        const scheme = location.protocol === 'https:' ? 'wss' : 'ws';
        ws = new WebSocket(`${scheme}://${location.host}/ws/kanban/`);
        ws.onmessage = handleWsMessage;
        ws.onclose = () => setTimeout(connectWs, 5000);
    }

    function handleWsMessage(e) {
        const data = JSON.parse(e.data);
        if (data.type !== 'card_update') return;
        // Patch the lead in our stages array reactively
        stages = stages.map((stageData) => ({
            ...stageData,
            leads: stageData.leads.map((lead) => {
                if (lead.id !== data.lead_id) return lead;
                return {
                    ...lead,
                    unread_message_count: data.unread_message_count,
                    last_message_preview: data.last_message_preview,
                };
            }),
        }));
    }

    function cleanup() {
        if (ws) { ws.onclose = null; ws.close(); ws = null; }
    }

    onMount(() => {
        loadKanbanData();
        connectWs();
        // Clean up when SPA nav swaps this page away
        window.addEventListener('crm:pageSwapped', cleanup, { once: true });
        return cleanup;
    });

    onDestroy(cleanup);
</script>

<div class="mx-auto max-w-full px-4 py-6 sm:px-6 lg:px-8">
    <!-- Page header -->
    <div class="mb-6">
        <div class="flex justify-between items-center">
            <div>
                <h1 class="text-3xl font-bold tracking-tight text-gray-900">Opportunity Pipeline</h1>
                <p class="mt-2 text-sm text-gray-600">
                    Drag and drop opportunities between stages to update their status
                </p>
            </div>
            <div class="flex items-center space-x-4">
                <!-- View switcher -->
                <div class="flex items-center space-x-2">
                    <label for="view-select" class="text-sm font-medium text-gray-700">View:</label>
                    <select
                        id="view-select"
                        class="border border-gray-300 rounded-md px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        value={currentView}
                        on:change={onViewChange}
                    >
                        <option value="personal">My Pipeline</option>
                        {#if isManager || isExecutive}
                            <option value="team">Team Pipeline</option>
                        {/if}
                    </select>
                </div>

                <!-- Team selector (executives only) -->
                {#if isExecutive && currentView === 'team'}
                    <div class="flex items-center space-x-2">
                        <label for="team-select" class="text-sm font-medium text-gray-700">Team:</label>
                        <select
                            id="team-select"
                            class="border border-gray-300 rounded-md px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                            value={currentTeamId}
                            on:change={onTeamChange}
                        >
                            {#each availableTeams as team (team.id)}
                                <option value={String(team.id)}>{team.name}</option>
                            {/each}
                        </select>
                    </div>
                {/if}

                <button
                    class="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors"
                    on:click={loadKanbanData}
                >
                    Refresh
                </button>
                <a
                    href={apiUrls.opportunityCreate}
                    class="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors"
                >
                    Add Opportunity
                </a>
            </div>
        </div>
    </div>

    <!-- Loading indicator -->
    {#if loading}
        <div class="text-center py-8">
            <div class="inline-flex items-center px-4 py-2 font-semibold leading-6 text-sm shadow rounded-md text-gray-500 bg-white">
                <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-gray-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Loading pipeline...
            </div>
        </div>
    {:else if error}
        <div class="text-center py-8 text-red-600">{error}</div>
    {:else}
        <!-- Kanban board -->
        <div class="flex gap-6 overflow-x-auto pb-6" style="min-height: 600px;">
            {#each stages as stageData (stageData.stage.id)}
                <KanbanColumn
                    {stageData}
                    {currentView}
                    {selectedTeamId}
                    on:stageUpdate={handleStageUpdate}
                    on:deleteLead={handleDeleteLead}
                />
            {/each}
        </div>
    {/if}
</div>
