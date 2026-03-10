import '../app.css';
import { installGlobalHandlers } from '../utils/debug.js';
import TeamForm from '../components/crm/TeamForm.svelte';

installGlobalHandlers();

let instance = null;

function mount() {
    const el = document.getElementById('svelte-team_form-root');
    const dataEl = document.getElementById('team_form-init-data');
    if (!el || !dataEl) return;

    if (instance) {
        instance.$destroy();
        instance = null;
    }

    let props;
    try {
        props = JSON.parse(dataEl.textContent);
    } catch (e) {
        console.error('team_form: failed to parse init data', e);
        return;
    }

    instance = new TeamForm({ target: el, props });
}

mount();
window.addEventListener('crm:pageSwapped', () => setTimeout(mount, 0));
