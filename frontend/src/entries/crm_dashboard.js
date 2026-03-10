import '../app.css';
import { installGlobalHandlers } from '../utils/debug.js';
import CrmDashboard from '../components/crm/CrmDashboard.svelte';

installGlobalHandlers();

let instance = null;

function mount() {
    const el = document.getElementById('svelte-crm_dashboard-root');
    const dataEl = document.getElementById('crm_dashboard-init-data');
    if (!el || !dataEl) return;

    if (instance) {
        instance.$destroy();
        instance = null;
    }

    let props;
    try {
        props = JSON.parse(dataEl.textContent);
    } catch (e) {
        console.error('crm_dashboard: failed to parse init data', e);
        return;
    }

    instance = new CrmDashboard({ target: el, props });
}

mount();
window.addEventListener('crm:pageSwapped', () => setTimeout(mount, 0));
