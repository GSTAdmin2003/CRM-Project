import '../app.css';
import { installGlobalHandlers } from '../utils/debug.js';
import ActivitiesDashboard from '../components/activities/ActivitiesDashboard.svelte';

installGlobalHandlers();

let instance = null;

function mount() {
    const el = document.getElementById('svelte-activities-root');
    const dataEl = document.getElementById('activities-init-data');
    if (!el || !dataEl) return;

    if (instance) {
        instance.$destroy();
        instance = null;
    }

    let props;
    try {
        props = JSON.parse(dataEl.textContent);
    } catch (e) {
        console.error('activities: failed to parse init data', e);
        return;
    }

    instance = new ActivitiesDashboard({ target: el, props });
}

mount();
window.addEventListener('crm:pageSwapped', () => setTimeout(mount, 0));
