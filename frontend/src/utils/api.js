import { getCsrfToken } from './csrf.js';
import { dbg } from './debug.js';

/**
 * Thin fetch wrapper: attaches CSRF token + credentials for all mutating requests.
 */
export async function apiFetch(url, options = {}) {
    const method = (options.method || 'GET').toUpperCase();
    const headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        ...(options.headers || {}),
    };
    if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
        headers['X-CSRFToken'] = getCsrfToken();
    }

    dbg('API', `→ ${method} ${url}`, options.body ? JSON.parse(options.body) : '');

    const response = await fetch(url, {
        credentials: 'same-origin',
        ...options,
        headers,
    });

    if (!response.ok) {
        const text = await response.clone().text();
        console.error('[CRM:API]', `✗ ${method} ${url}`, response.status, text);
    } else {
        dbg('API', `← ${response.status} ${url}`);
    }

    return response;
}

export async function apiGet(url) {
    return apiFetch(url, { method: 'GET' });
}

export async function apiPatch(url, body) {
    return apiFetch(url, {
        method: 'PATCH',
        body: JSON.stringify(body),
    });
}

export async function apiPost(url, body) {
    return apiFetch(url, {
        method: 'POST',
        body: JSON.stringify(body),
    });
}

export async function apiDelete(url) {
    return apiFetch(url, { method: 'DELETE' });
}
