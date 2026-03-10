import '../app.css';
import { installGlobalHandlers } from '../utils/debug.js';
import WhatsappTemplateForm from '../components/settings/WhatsappTemplateForm.svelte';

installGlobalHandlers();

let instance = null;

function mount() {
    const el = document.getElementById('svelte-whatsapp_template_form-root');
    const dataEl = document.getElementById('whatsapp_template_form-init-data');
    if (!el || !dataEl) return;

    if (instance) { instance.$destroy(); instance = null; }

    let props;
    try { props = JSON.parse(dataEl.textContent); } catch (e) { props = {}; }

    instance = new WhatsappTemplateForm({ target: el, props });
}

mount();
window.addEventListener('crm:pageSwapped', () => setTimeout(mount, 0));
