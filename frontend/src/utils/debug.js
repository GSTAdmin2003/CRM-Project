/**
 * Debug utility — activated by ?debug=1 in the URL.
 * Persists the flag to localStorage so it survives page navigation.
 *
 * Usage anywhere in the app:
 *   import { dbg, isDebug } from '../utils/debug.js';
 *   dbg('MyComponent', 'some value', obj);
 *
 * Entry files import this once to register global error handlers.
 */

const LS_KEY = 'crm:debug';

// Activate from URL param and persist, or deactivate if explicitly 0.
const param = new URLSearchParams(window.location.search).get('debug');
if (param === '1') {
    localStorage.setItem(LS_KEY, '1');
} else if (param === '0') {
    localStorage.removeItem(LS_KEY);
}

export const isDebug = localStorage.getItem(LS_KEY) === '1';

/** Conditional logger — no-op in production. */
export function dbg(category, ...args) {
    if (isDebug) {
        console.debug(`[CRM:${category}]`, ...args);
    }
}

/** Register global error catchers — call once per page load (from entry files). */
export function installGlobalHandlers() {
    if (!isDebug) return;

    // Unhandled JS errors
    window.addEventListener('error', (e) => {
        console.error('[CRM:GlobalError]', e.message, {
            source: e.filename,
            line: e.lineno,
            col: e.colno,
            error: e.error,
        });
    });

    // Unhandled promise rejections
    window.addEventListener('unhandledrejection', (e) => {
        console.error('[CRM:UnhandledRejection]', e.reason);
    });

    console.info('[CRM:Debug] Debug mode active. Use ?debug=0 to disable.');
}
