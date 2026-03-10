import '../app.css';
import TeamStageForm from '../components/crm/TeamStageForm.svelte';

let instance = null;

function mount() {
    const el = document.getElementById('svelte-team_stage_form-root');
    const dataEl = document.getElementById('team_stage_form-init-data');
    if (!el || !dataEl) return;
    if (instance) { instance.$destroy(); instance = null; }
    let props;
    try { props = JSON.parse(dataEl.textContent); } catch (e) { props = {}; }
    instance = new TeamStageForm({ target: el, props });
}

mount();
window.addEventListener('crm:pageSwapped', () => setTimeout(mount, 0));
