import '../app.css';
import { installGlobalHandlers } from '../utils/debug.js';
import MessagingInbox from '../components/messaging/MessagingInbox.svelte';

installGlobalHandlers();

let instance = null;

function mount() {
    const el = document.getElementById('svelte-messaging-root');
    const dataEl = document.getElementById('messaging-init-data');
    if (!el || !dataEl) return;

    if (instance) {
        instance.$destroy();
        instance = null;
    }

    let props;
    try {
        props = JSON.parse(dataEl.textContent);
    } catch (e) {
        console.error('messaging: failed to parse init data', e);
        return;
    }

    instance = new MessagingInbox({ target: el, props });
}

mount();
window.addEventListener('crm:pageSwapped', () => setTimeout(mount, 0));
