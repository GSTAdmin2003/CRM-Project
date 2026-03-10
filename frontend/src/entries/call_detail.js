import '../app.css';
import { installGlobalHandlers } from '../utils/debug.js';
import CallDetail from '../components/call_detail/CallDetail.svelte';

installGlobalHandlers();

let instance = null;

function mount() {
    const el = document.getElementById('svelte-call_detail-root');
    const dataEl = document.getElementById('call_detail-init-data');
    if (!el || !dataEl) return;

    if (instance) {
        instance.$destroy();
        instance = null;
    }

    let props;
    try {
        props = JSON.parse(dataEl.textContent);
    } catch (e) {
        console.error('call_detail: failed to parse init data', e);
        return;
    }

    instance = new CallDetail({ target: el, props });
}

mount();
window.addEventListener('crm:pageSwapped', () => setTimeout(mount, 0));
