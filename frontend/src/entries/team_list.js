import '../app.css';
import { installGlobalHandlers } from '../utils/debug.js';
import TeamList from '../components/crm/TeamList.svelte';

installGlobalHandlers();

let instance = null;

function mount() {
    const el = document.getElementById('svelte-team_list-root');
    const dataEl = document.getElementById('team_list-init-data');
    if (!el || !dataEl) return;

    if (instance) {
        instance.$destroy();
        instance = null;
    }

    let props;
    try {
        props = JSON.parse(dataEl.textContent);
    } catch (e) {
        console.error('team_list: failed to parse init data', e);
        return;
    }

    instance = new TeamList({ target: el, props });
}

mount();
window.addEventListener('crm:pageSwapped', () => setTimeout(mount, 0));
