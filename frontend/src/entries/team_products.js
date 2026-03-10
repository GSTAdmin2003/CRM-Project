import '../app.css';
import { installGlobalHandlers } from '../utils/debug.js';
import TeamProducts from '../components/settings/TeamProducts.svelte';

installGlobalHandlers();

let instance = null;

function mount() {
    const el = document.getElementById('svelte-team_products-root');
    const dataEl = document.getElementById('team_products-init-data');
    if (!el || !dataEl) return;

    if (instance) { instance.$destroy(); instance = null; }

    let props;
    try { props = JSON.parse(dataEl.textContent); } catch (e) { props = {}; }

    instance = new TeamProducts({ target: el, props });
}

mount();
window.addEventListener('crm:pageSwapped', () => setTimeout(mount, 0));
