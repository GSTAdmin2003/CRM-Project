import '../app.css';
import { installGlobalHandlers } from '../utils/debug.js';
import WhatsappConfig from '../components/settings/WhatsappConfig.svelte';

installGlobalHandlers();

let instance = null;

function mount() {
    const el = document.getElementById('svelte-whatsapp_config-root');
    const dataEl = document.getElementById('whatsapp_config-init-data');
    if (!el || !dataEl) return;

    if (instance) { instance.$destroy(); instance = null; }

    let props;
    try { props = JSON.parse(dataEl.textContent); } catch (e) { props = {}; }

    instance = new WhatsappConfig({ target: el, props });
}

mount();
window.addEventListener('crm:pageSwapped', () => setTimeout(mount, 0));
