import '../app.css';
import { installGlobalHandlers } from '../utils/debug.js';
import GeneralLanguage from '../components/settings/GeneralLanguage.svelte';

installGlobalHandlers();

let instance = null;

function mount() {
    const el = document.getElementById('svelte-general_language-root');
    const dataEl = document.getElementById('general_language-init-data');
    if (!el || !dataEl) return;

    if (instance) { instance.$destroy(); instance = null; }

    let props;
    try { props = JSON.parse(dataEl.textContent); } catch (e) { props = {}; }

    instance = new GeneralLanguage({ target: el, props });
}

mount();
window.addEventListener('crm:pageSwapped', () => setTimeout(mount, 0));
