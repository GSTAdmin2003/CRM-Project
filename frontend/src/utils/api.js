import { getCsrfToken } from './csrf.js';

/**
 * Thin fetch wrapper: attaches CSRF token + credentials for all mutating requests.
 */
export async function apiFetch(url, options = {}) {
    const method = (options.method || 'GET').toUpperCase();
    const headers = {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
    };
    if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
        headers['X-CSRFToken'] = getCsrfToken();
    }
    const response = await fetch(url, {
        credentials: 'same-origin',
        ...options,
        headers,
    });
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
