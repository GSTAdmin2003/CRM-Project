import '../app.css';
import { installGlobalHandlers } from '../utils/debug.js';
import UserForm from '../components/settings/UserForm.svelte';

installGlobalHandlers();

let instance = null;

function mount() {
    const el = document.getElementById('svelte-user_form-root');
    const dataEl = document.getElementById('user_form-init-data');
    if (!el || !dataEl) return;

    if (instance) { instance.$destroy(); instance = null; }

    let props;
    try { props = JSON.parse(dataEl.textContent); } catch (e) { props = {}; }

    instance = new UserForm({ target: el, props });
}

mount();
window.addEventListener('crm:pageSwapped', () => setTimeout(mount, 0));
