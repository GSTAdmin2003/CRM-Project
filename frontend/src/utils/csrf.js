/**
 * Read the CSRF token from the browser cookie.
 * Always called at request time so the token is never stale.
 */
export function getCsrfToken() {
    const name = 'csrftoken';
    if (!document.cookie) return '';
    for (const raw of document.cookie.split(';')) {
        const cookie = raw.trim();
        if (cookie.startsWith(name + '=')) {
            return decodeURIComponent(cookie.slice(name.length + 1));
        }
    }
    return '';
}
