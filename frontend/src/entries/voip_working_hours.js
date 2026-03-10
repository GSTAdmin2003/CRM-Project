import '../app.css';
import { installGlobalHandlers } from '../utils/debug.js';
import VoipWorkingHours from '../components/settings/VoipWorkingHours.svelte';

installGlobalHandlers();

let instance = null;

function mount() {
    const el = document.getElementById('svelte-voip_working_hours-root');
    const dataEl = document.getElementById('voip_working_hours-init-data');
    if (!el || !dataEl) return;

    if (instance) { instance.$destroy(); instance = null; }

    let props;
    try { props = JSON.parse(dataEl.textContent); } catch (e) { props = {}; }

    instance = new VoipWorkingHours({ target: el, props });
}

mount();
window.addEventListener('crm:pageSwapped', () => setTimeout(mount, 0));
