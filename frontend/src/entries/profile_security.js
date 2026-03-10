import '../app.css';
import { installGlobalHandlers } from '../utils/debug.js';
import ProfileSecurity from '../components/settings/ProfileSecurity.svelte';

installGlobalHandlers();

let instance = null;

function mount() {
    const el = document.getElementById('svelte-profile_security-root');
    const dataEl = document.getElementById('profile_security-init-data');
    if (!el || !dataEl) return;

    if (instance) { instance.$destroy(); instance = null; }

    let props;
    try { props = JSON.parse(dataEl.textContent); } catch (e) { props = {}; }

    instance = new ProfileSecurity({ target: el, props });
}

mount();
window.addEventListener('crm:pageSwapped', () => setTimeout(mount, 0));
