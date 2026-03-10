import '../app.css';
import { installGlobalHandlers } from '../utils/debug.js';
import StageList from '../components/crm/StageList.svelte';

installGlobalHandlers();

let instance = null;

function mount() {
    const el = document.getElementById('svelte-stage_list-root');
    const dataEl = document.getElementById('stage_list-init-data');
    if (!el || !dataEl) return;

    if (instance) {
        instance.$destroy();
        instance = null;
    }

    let props;
    try {
        props = JSON.parse(dataEl.textContent);
    } catch (e) {
        console.error('stage_list: failed to parse init data', e);
        return;
    }

    instance = new StageList({ target: el, props });
}

mount();
window.addEventListener('crm:pageSwapped', () => setTimeout(mount, 0));
