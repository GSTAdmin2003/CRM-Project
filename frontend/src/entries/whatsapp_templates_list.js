import '../app.css';
import { installGlobalHandlers } from '../utils/debug.js';
import WhatsappTemplatesList from '../components/settings/WhatsappTemplatesList.svelte';

installGlobalHandlers();

let instance = null;

function mount() {
    const el = document.getElementById('svelte-whatsapp_templates_list-root');
    const dataEl = document.getElementById('whatsapp_templates_list-init-data');
    if (!el || !dataEl) return;

    if (instance) { instance.$destroy(); instance = null; }

    let props;
    try { props = JSON.parse(dataEl.textContent); } catch (e) { props = {}; }

    instance = new WhatsappTemplatesList({ target: el, props });
}

mount();
window.addEventListener('crm:pageSwapped', () => setTimeout(mount, 0));
