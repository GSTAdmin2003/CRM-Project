import { writable } from 'svelte/store';

export const toasts = writable([]);

export function showToast(type, message, duration = 3500) {
    const id = Date.now() + Math.random();
    toasts.update(t => [...t, { id, type, message }]);
    setTimeout(() => toasts.update(t => t.filter(x => x.id !== id)), duration);
}
