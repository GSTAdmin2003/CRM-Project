import '../app.css';
import { installGlobalHandlers } from '../utils/debug.js';
import ElevenLabsConfig from '../components/settings/ElevenLabsConfig.svelte';

installGlobalHandlers();

let instance = null;

function mount() {
    const el = document.getElementById('svelte-elevenlabs_config-root');
    const dataEl = document.getElementById('elevenlabs_config-init-data');
    if (!el || !dataEl) return;

    if (instance) { instance.$destroy(); instance = null; }

    let props;
    try { props = JSON.parse(dataEl.textContent); } catch (e) { props = {}; }

    instance = new ElevenLabsConfig({ target: el, props });
}

mount();
window.addEventListener('crm:pageSwapped', () => setTimeout(mount, 0));
