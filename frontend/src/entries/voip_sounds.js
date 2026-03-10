import '../app.css';
import { installGlobalHandlers } from '../utils/debug.js';
import VoipSounds from '../components/settings/VoipSounds.svelte';

installGlobalHandlers();

let instance = null;

function mount() {
    const el = document.getElementById('svelte-voip_sounds-root');
    const dataEl = document.getElementById('voip_sounds-init-data');
    if (!el || !dataEl) return;

    if (instance) { instance.$destroy(); instance = null; }

    let props;
    try { props = JSON.parse(dataEl.textContent); } catch (e) { props = {}; }

    instance = new VoipSounds({ target: el, props });
}

mount();
window.addEventListener('crm:pageSwapped', () => setTimeout(mount, 0));
