import '../app.css';
import { installGlobalHandlers } from '../utils/debug.js';
import StageForm from '../components/crm/StageForm.svelte';

installGlobalHandlers();

let instance = null;

function mount() {
    const el = document.getElementById('svelte-stage_form-root');
    const dataEl = document.getElementById('stage_form-init-data');
    if (!el || !dataEl) return;

    if (instance) {
        instance.$destroy();
        instance = null;
    }

    let props;
    try {
        props = JSON.parse(dataEl.textContent);
    } catch (e) {
        console.error('stage_form: failed to parse init data', e);
        return;
    }

    instance = new StageForm({ target: el, props });
}

mount();
window.addEventListener('crm:pageSwapped', () => setTimeout(mount, 0));
