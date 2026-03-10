import '../app.css';
import { installGlobalHandlers } from '../utils/debug.js';
import VoipConfig from '../components/settings/VoipConfig.svelte';

installGlobalHandlers();

let instance = null;

function mount() {
    const el = document.getElementById('svelte-voip_config-root');
    const dataEl = document.getElementById('voip_config-init-data');
    if (!el || !dataEl) return;

    if (instance) { instance.$destroy(); instance = null; }

    let props;
    try { props = JSON.parse(dataEl.textContent); } catch (e) { props = {}; }

    instance = new VoipConfig({ target: el, props });
}

mount();
window.addEventListener('crm:pageSwapped', () => setTimeout(mount, 0));
