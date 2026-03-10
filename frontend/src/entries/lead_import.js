import '../app.css';
import { installGlobalHandlers } from '../utils/debug.js';
import LeadImport from '../components/crm/LeadImport.svelte';

installGlobalHandlers();

let instance = null;

function mount() {
    const el = document.getElementById('svelte-lead_import-root');
    const dataEl = document.getElementById('lead_import-init-data');
    if (!el || !dataEl) return;

    if (instance) {
        instance.$destroy();
        instance = null;
    }

    let props;
    try {
        props = JSON.parse(dataEl.textContent);
    } catch (e) {
        console.error('lead_import: failed to parse init data', e);
        return;
    }

    instance = new LeadImport({ target: el, props });
}

mount();
window.addEventListener('crm:pageSwapped', () => setTimeout(mount, 0));
