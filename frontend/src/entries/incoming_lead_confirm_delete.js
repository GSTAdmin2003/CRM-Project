import '../app.css';
import ConfirmAction from '../components/shared/ConfirmAction.svelte';

let instance = null;

function mount() {
    const el = document.getElementById('svelte-incoming_lead_confirm_delete-root');
    const dataEl = document.getElementById('incoming_lead_confirm_delete-init-data');
    if (!el || !dataEl) return;
    if (instance) { instance.$destroy(); instance = null; }
    let props;
    try { props = JSON.parse(dataEl.textContent); } catch (e) { props = {}; }
    instance = new ConfirmAction({ target: el, props });
}

mount();
window.addEventListener('crm:pageSwapped', () => setTimeout(mount, 0));
