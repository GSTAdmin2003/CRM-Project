import '../app.css';
import { installGlobalHandlers } from '../utils/debug.js';
import ProfilePreferences from '../components/settings/ProfilePreferences.svelte';

installGlobalHandlers();

let instance = null;

function mount() {
    const el = document.getElementById('svelte-profile_preferences-root');
    const dataEl = document.getElementById('profile_preferences-init-data');
    if (!el || !dataEl) return;

    if (instance) { instance.$destroy(); instance = null; }

    let props;
    try { props = JSON.parse(dataEl.textContent); } catch (e) { props = {}; }

    instance = new ProfilePreferences({ target: el, props });
}

mount();
window.addEventListener('crm:pageSwapped', () => setTimeout(mount, 0));
