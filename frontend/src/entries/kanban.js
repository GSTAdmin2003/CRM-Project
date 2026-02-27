import '../app.css';
import KanbanBoard from '../components/kanban/KanbanBoard.svelte';

let instance = null;

function mount() {
    const el = document.getElementById('svelte-kanban-root');
    const dataEl = document.getElementById('kanban-init-data');
    if (!el || !dataEl) return;

    // Destroy previous instance if SPA navigation re-uses this entry
    if (instance) {
        instance.$destroy();
        instance = null;
    }

    let props;
    try {
        props = JSON.parse(dataEl.textContent);
    } catch (e) {
        console.error('kanban: failed to parse init data', e);
        return;
    }

    instance = new KanbanBoard({ target: el, props });
}

// Initial page load
mount();

// Re-mount after SPA navigation back to this page
window.addEventListener('crm:pageSwapped', () => setTimeout(mount, 0));
