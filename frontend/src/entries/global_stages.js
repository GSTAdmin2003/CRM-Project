import '../app.css';
import { installGlobalHandlers } from '../utils/debug.js';
import GlobalStages from '../components/settings/GlobalStages.svelte';

installGlobalHandlers();

let instance = null;

function mount() {
    const el = document.getElementById('svelte-global_stages-root');
    const dataEl = document.getElementById('global_stages-init-data');
    if (!el || !dataEl) return;

    if (instance) { instance.$destroy(); instance = null; }

    let props;
    try { props = JSON.parse(dataEl.textContent); } catch (e) { props = {}; }

    instance = new GlobalStages({ target: el, props });
}

mount();
window.addEventListener('crm:pageSwapped', () => setTimeout(mount, 0));
