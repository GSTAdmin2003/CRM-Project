import '../app.css';
import { installGlobalHandlers } from '../utils/debug.js';
import CallsList from '../components/calls/CallsList.svelte';

installGlobalHandlers();

let instance = null;

function mount() {
    const el = document.getElementById('svelte-calls-root');
    const dataEl = document.getElementById('calls-init-data');
    if (!el || !dataEl) return;

    if (instance) {
        instance.$destroy();
        instance = null;
    }

    let props;
    try {
        props = JSON.parse(dataEl.textContent);
    } catch (e) {
        console.error('calls: failed to parse init data', e);
        return;
    }

    instance = new CallsList({ target: el, props });
}

mount();
window.addEventListener('crm:pageSwapped', () => setTimeout(mount, 0));
