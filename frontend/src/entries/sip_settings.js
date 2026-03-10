import '../app.css';
import { installGlobalHandlers } from '../utils/debug.js';
import SipSettings from '../components/settings/SipSettings.svelte';

installGlobalHandlers();

let instance = null;

function mount() {
    const el = document.getElementById('svelte-sip_settings-root');
    const dataEl = document.getElementById('sip_settings-init-data');
    if (!el || !dataEl) return;

    if (instance) { instance.$destroy(); instance = null; }

    let props;
    try { props = JSON.parse(dataEl.textContent); } catch (e) { props = {}; }

    instance = new SipSettings({ target: el, props });
}

mount();
window.addEventListener('crm:pageSwapped', () => setTimeout(mount, 0));
