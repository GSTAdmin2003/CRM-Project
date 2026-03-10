import '../app.css';
import { installGlobalHandlers } from '../utils/debug.js';
import ProfilePersonalInfo from '../components/settings/ProfilePersonalInfo.svelte';

installGlobalHandlers();

let instance = null;

function mount() {
    const el = document.getElementById('svelte-profile_personal_info-root');
    const dataEl = document.getElementById('profile_personal_info-init-data');
    if (!el || !dataEl) return;

    if (instance) { instance.$destroy(); instance = null; }

    let props;
    try { props = JSON.parse(dataEl.textContent); } catch (e) { props = {}; }

    instance = new ProfilePersonalInfo({ target: el, props });
}

mount();
window.addEventListener('crm:pageSwapped', () => setTimeout(mount, 0));
