import '../app.css';
import { installGlobalHandlers } from '../utils/debug.js';
import LeadDetail from '../components/crm/LeadDetail.svelte';

installGlobalHandlers();

let instance = null;

function mount() {
    const el = document.getElementById('svelte-lead_detail-root');
    const dataEl = document.getElementById('lead_detail-init-data');
    if (!el || !dataEl) return;

    if (instance) {
        instance.$destroy();
        instance = null;
    }

    let props;
    try {
        props = JSON.parse(dataEl.textContent);
    } catch (e) {
        console.error('lead_detail: failed to parse init data', e);
        return;
    }

    instance = new LeadDetail({ target: el, props });
}

mount();
window.addEventListener('crm:pageSwapped', () => setTimeout(mount, 0));
