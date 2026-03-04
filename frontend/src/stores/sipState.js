import { writable } from 'svelte/store';

/**
 * Svelte store that mirrors the JsSIP SIP state from base.html.
 * base.html dispatches CustomEvents; we subscribe to them here.
 * Svelte components subscribe to this store for reactive SIP state.
 */
function createSipStore() {
    // Seed from current JsSIP UA state — the sip:registered event may have
    // already fired before this Svelte module was loaded.
    const alreadyRegistered = !!(window.sipUA && window.sipUA.isRegistered());

    const { subscribe, update } = writable({
        registered: alreadyRegistered,
        hasActiveCall: false,
        isMuted: false,
        isOnHold: false,
    });

    window.addEventListener('sip:registered', (e) =>
        update((s) => ({ ...s, registered: e.detail.registered })));

    window.addEventListener('sip:callStarted', (e) =>
        update((s) => ({
            ...s,
            hasActiveCall: true,
            number: e.detail.number || '',
            opportunityId: e.detail.opportunityId || null,
        })));

    window.addEventListener('sip:callEnded', () =>
        update((s) => ({ ...s, hasActiveCall: false, isMuted: false, isOnHold: false })));

    window.addEventListener('sip:muteChanged', (e) =>
        update((s) => ({ ...s, isMuted: e.detail.muted })));

    window.addEventListener('sip:holdChanged', (e) =>
        update((s) => ({ ...s, isOnHold: e.detail.onHold })));

    return { subscribe };
}

export const sipState = createSipStore();
