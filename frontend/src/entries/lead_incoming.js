import '../app.css';
import { installGlobalHandlers } from '../utils/debug.js';
import IncomingLeadList from '../components/lead_incoming/IncomingLeadList.svelte';

installGlobalHandlers();

let instance = null;

function mount() {
    const el = document.getElementById('svelte-lead-incoming-root');
    const dataEl = document.getElementById('lead-incoming-init-data');
    if (!el || !dataEl) return;

    if (instance) {
        instance.$destroy();
        instance = null;
    }

    let props;
    try {
        props = JSON.parse(dataEl.textContent);
    } catch (e) {
        console.error('lead_incoming: failed to parse init data', e);
        return;
    }

    instance = new IncomingLeadList({ target: el, props });
}

mount();
window.addEventListener('crm:pageSwapped', () => setTimeout(mount, 0));
