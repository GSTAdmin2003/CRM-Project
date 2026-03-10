import '../app.css';
import { installGlobalHandlers } from '../utils/debug.js';
import PitchManager from '../components/settings/PitchManager.svelte';

installGlobalHandlers();

let instance = null;

function mount() {
    const el = document.getElementById('svelte-pitch_manager-root');
    const dataEl = document.getElementById('pitch_manager-init-data');
    if (!el || !dataEl) return;

    if (instance) { instance.$destroy(); instance = null; }

    let props;
    try { props = JSON.parse(dataEl.textContent); } catch (e) { props = {}; }

    instance = new PitchManager({ target: el, props });
}

mount();
window.addEventListener('crm:pageSwapped', () => setTimeout(mount, 0));
