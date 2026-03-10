import '../app.css';
import { installGlobalHandlers } from '../utils/debug.js';
import AiConfig from '../components/settings/AiConfig.svelte';

installGlobalHandlers();

let instance = null;

function mount() {
    const el = document.getElementById('svelte-ai_config-root');
    const dataEl = document.getElementById('ai_config-init-data');
    if (!el || !dataEl) return;

    if (instance) { instance.$destroy(); instance = null; }

    let props;
    try { props = JSON.parse(dataEl.textContent); } catch (e) { props = {}; }

    instance = new AiConfig({ target: el, props });
}

mount();
window.addEventListener('crm:pageSwapped', () => setTimeout(mount, 0));
