import { writable } from 'svelte/store';

/**
 * Shared store for the currently-open lead/opportunity.
 * Shared between LeadFormApp, CallControls, and any other panel
 * that needs to read or mutate the current lead.
 */
export const currentLead = writable(null);

/**
 * Set the current lead (call from LeadFormApp on load / after PATCH).
 * @param {Object} lead - LeadDetailSerializer output
 */
export function setCurrentLead(lead) {
    currentLead.set(lead);
}
