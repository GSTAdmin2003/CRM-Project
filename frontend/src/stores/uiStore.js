import { writable } from 'svelte/store';

/**
 * UI state store: active tab, modal visibility flags.
 */
export const activeTab = writable('notes'); // 'notes' | 'activities' | 'whatsapp'

export const modals = writable({
    activityCreate: false,
});

export function openModal(name) {
    modals.update((s) => ({ ...s, [name]: true }));
}

export function closeModal(name) {
    modals.update((s) => ({ ...s, [name]: false }));
}
