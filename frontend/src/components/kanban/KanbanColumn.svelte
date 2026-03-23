<script>
    import { onMount, onDestroy, createEventDispatcher } from 'svelte';
    import Sortable from 'sortablejs';
    import LeadCard from './LeadCard.svelte';

    export let stageData;   // { stage: {id, name, color, probability}, leads: [...], total_value, count }
    export let currentView;
    export let selectedTeamId;

    const dispatch = createEventDispatcher();

    let columnEl;
    let sortable;

    onMount(() => {
        sortable = new Sortable(columnEl, {
            group: 'kanban',
            animation: 150,
            ghostClass: 'opacity-50',
            chosenClass: 'dragging',
            onEnd(evt) {
                const leadId = evt.item.dataset.leadId;
                const newStageId = evt.to.dataset.stageId;
                if (leadId && newStageId && newStageId !== String(stageData.stage.id)) {
                    dispatch('stageUpdate', { leadId: parseInt(leadId), newStageId: parseInt(newStageId) });
                }
            },
        });
    });

    onDestroy(() => {
        if (sortable) sortable.destroy();
    });

    function handleEdit({ detail }) {
        let url = `/crm/opportunities/${detail.leadId}/edit/?view=${currentView}`;
        if (selectedTeamId && selectedTeamId !== 'all') url += `&team=${selectedTeamId}`;
        if (detail.stageId) url += `&stage=${detail.stageId}`;
        window.location.href = url;
    }

    function handleDelete({ detail }) {
        dispatch('deleteLead', { leadId: detail.leadId, title: detail.title });
    }

    function handleMarkWon({ detail }) {
        dispatch('markWon', { leadId: detail.leadId });
    }

    function handleMarkLost({ detail }) {
        dispatch('markLost', { leadId: detail.leadId, title: detail.title });
    }

    function formatTotal(val) {
        return Math.round(val).toLocaleString();
    }
</script>

<div class="flex-shrink-0 w-80">
    <div class="bg-gray-50 rounded-lg shadow-sm">
        <!-- Column header -->
        <div class="bg-white px-4 py-3 border-b border-gray-200 rounded-t-lg sticky top-0 z-10">
            <div class="flex items-center justify-between">
                <div class="flex items-center space-x-2">
                    <div class="w-3 h-3 rounded-full" style="background-color: {stageData.stage.color}"></div>
                    <h3 class="text-sm font-semibold text-gray-900">{stageData.stage.name}</h3>
                    <span class="text-xs text-gray-500">({stageData.count})</span>
                </div>
                <div class="text-sm text-gray-600">
                    ${formatTotal(stageData.total_value)}
                </div>
            </div>
        </div>

        <!-- Cards container (SortableJS target) -->
        <div
            bind:this={columnEl}
            class="min-h-[500px] max-h-[80vh] overflow-y-auto p-4 space-y-3"
            data-stage-id={stageData.stage.id}
        >
            {#each stageData.leads as lead (lead.id)}
                <LeadCard
                    {lead}
                    stageId={stageData.stage.id}
                    on:edit={handleEdit}
                    on:delete={handleDelete}
                    on:markWon={handleMarkWon}
                    on:markLost={handleMarkLost}
                />
            {/each}
        </div>
    </div>
</div>
