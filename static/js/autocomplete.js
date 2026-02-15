/**
 * Autocomplete Component
 *
 * A reusable autocomplete class that handles search, dropdown display,
 * keyboard navigation, selection, and view button functionality.
 *
 * Events dispatched:
 *   - autocomplete:select - When existing item is selected (detail: {id, display, item})
 *   - autocomplete:create - When "Create new" is clicked (detail: {name})
 *   - autocomplete:clear  - When selection is cleared
 */
class Autocomplete {
    /**
     * Initialize autocomplete for an input element.
     *
     * @param {HTMLInputElement} input - The input element with data-autocomplete="true"
     */
    constructor(input) {
        this.input = input;
        this.model = input.dataset.model || '';
        this.allowCreate = input.dataset.allowCreate === 'true';
        this.viewUrlName = input.dataset.viewUrlName || '';

        // Find or create component elements
        this.wrapper = this._findOrCreateWrapper();
        this.container = this._findOrCreateContainer();
        this.dropdown = this._findOrCreateDropdown();
        this.idInput = this._findOrCreateIdInput();
        this.viewBtn = this._findOrCreateViewBtn();

        // State
        this.selectedIndex = -1;
        this.results = [];
        this.config = {};
        this.searchTimeout = null;
        this.isOpen = false;

        // Bind methods
        this._onInput = this._onInput.bind(this);
        this._onKeydown = this._onKeydown.bind(this);
        this._onBlur = this._onBlur.bind(this);
        this._onFocus = this._onFocus.bind(this);
        this._onDocumentClick = this._onDocumentClick.bind(this);

        // Attach event listeners
        this._attachEvents();

        // Initialize view button visibility
        this._updateViewButton();
    }

    /**
     * Find or create the wrapper element.
     */
    _findOrCreateWrapper() {
        // Check if input is already in a wrapper
        const parent = this.input.parentElement;
        if (parent && parent.classList.contains('autocomplete-wrapper')) {
            return parent;
        }

        // Check if parent is a container inside a wrapper
        if (parent && parent.classList.contains('autocomplete-container')) {
            const grandparent = parent.parentElement;
            if (grandparent && grandparent.classList.contains('autocomplete-wrapper')) {
                return grandparent;
            }
        }

        // Create wrapper
        const wrapper = document.createElement('div');
        wrapper.className = 'autocomplete-wrapper';

        // Wrap existing container or input
        if (parent && parent.classList.contains('autocomplete-container')) {
            parent.parentNode.insertBefore(wrapper, parent);
            wrapper.appendChild(parent);
        } else {
            this.input.parentNode.insertBefore(wrapper, this.input);
            wrapper.appendChild(this.input);
        }

        return wrapper;
    }

    /**
     * Find or create the container element.
     */
    _findOrCreateContainer() {
        const parent = this.input.parentElement;
        if (parent && parent.classList.contains('autocomplete-container')) {
            return parent;
        }

        // Create container
        const container = document.createElement('div');
        container.className = 'autocomplete-container';

        // Move input into container
        this.input.parentNode.insertBefore(container, this.input);
        container.appendChild(this.input);

        return container;
    }

    /**
     * Find or create the dropdown element.
     */
    _findOrCreateDropdown() {
        // Look for existing dropdown in container
        let dropdown = this.container.querySelector('.autocomplete-dropdown');
        if (dropdown) {
            return dropdown;
        }

        // Create dropdown
        dropdown = document.createElement('div');
        dropdown.className = 'autocomplete-dropdown';
        this.container.appendChild(dropdown);

        return dropdown;
    }

    /**
     * Find or create the hidden ID input.
     */
    _findOrCreateIdInput() {
        // Look for existing ID input
        const inputName = this.input.name;
        const idInputName = inputName + '_id';

        // Check various locations
        let idInput = this.wrapper.querySelector(`input[name="${idInputName}"]`);
        if (!idInput) {
            idInput = this.container.querySelector(`input[name="${idInputName}"]`);
        }
        if (!idInput) {
            // Also check for company_id style naming
            const altName = inputName.replace(/([a-z])([A-Z])/g, '$1_$2').toLowerCase() + '_id';
            idInput = document.querySelector(`input[name="${altName}"]`);
        }
        if (!idInput) {
            // Check for common patterns like company-id or company_id
            idInput = document.getElementById(inputName + '-id') ||
                      document.getElementById(inputName + '_id') ||
                      document.getElementById(inputName.replace('_', '-') + '-id');
        }

        if (idInput) {
            return idInput;
        }

        // Create ID input
        idInput = document.createElement('input');
        idInput.type = 'hidden';
        idInput.name = idInputName;
        idInput.className = 'autocomplete-id-input';
        this.container.appendChild(idInput);

        return idInput;
    }

    /**
     * Find or create the view button.
     */
    _findOrCreateViewBtn() {
        // Look for existing view button
        let viewBtn = this.wrapper.querySelector('.autocomplete-view-btn, .company-view-icon');
        if (viewBtn) {
            return viewBtn;
        }

        // Don't create if no view URL configured
        if (!this.viewUrlName) {
            return null;
        }

        // Create view button
        viewBtn = document.createElement('a');
        viewBtn.className = 'autocomplete-view-btn';
        viewBtn.href = '#';
        viewBtn.target = '_blank';
        viewBtn.title = 'View Details';
        viewBtn.innerHTML = '<i class="fas fa-eye"></i>';
        this.wrapper.appendChild(viewBtn);

        return viewBtn;
    }

    /**
     * Attach event listeners.
     */
    _attachEvents() {
        this.input.addEventListener('input', this._onInput);
        this.input.addEventListener('keydown', this._onKeydown);
        this.input.addEventListener('blur', this._onBlur);
        this.input.addEventListener('focus', this._onFocus);
        document.addEventListener('click', this._onDocumentClick);
    }

    /**
     * Handle input events (typing).
     */
    _onInput(e) {
        const query = this.input.value.trim();

        // Clear selection when typing
        this.idInput.value = '';
        this._updateViewButton();

        // Dispatch clear event
        this.input.dispatchEvent(new CustomEvent('autocomplete:clear', {
            bubbles: true,
            detail: {}
        }));

        // Debounce search
        clearTimeout(this.searchTimeout);

        if (query.length < 1) {
            this._hideDropdown();
            return;
        }

        this.searchTimeout = setTimeout(() => {
            this._search(query);
        }, 250);
    }

    /**
     * Handle keyboard navigation.
     */
    _onKeydown(e) {
        if (!this.isOpen) {
            if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
                e.preventDefault();
                this._onFocus();
            }
            return;
        }

        const items = this.dropdown.querySelectorAll('.autocomplete-item');

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                this.selectedIndex = Math.min(this.selectedIndex + 1, items.length - 1);
                this._highlightItem(items);
                break;

            case 'ArrowUp':
                e.preventDefault();
                this.selectedIndex = Math.max(this.selectedIndex - 1, -1);
                this._highlightItem(items);
                break;

            case 'Enter':
                e.preventDefault();
                if (this.selectedIndex >= 0 && items[this.selectedIndex]) {
                    const item = items[this.selectedIndex];
                    const id = item.dataset.id;
                    const display = item.dataset.display;

                    if (id === 'new') {
                        this._createNew(display);
                    } else {
                        this._selectItem(id, display, this.results[this.selectedIndex]);
                    }
                }
                break;

            case 'Escape':
                e.preventDefault();
                this._hideDropdown();
                break;

            case 'Tab':
                this._hideDropdown();
                break;
        }
    }

    /**
     * Handle blur events.
     */
    _onBlur(e) {
        // Delay to allow click on dropdown items
        setTimeout(() => {
            if (!this.dropdown.contains(document.activeElement)) {
                this._hideDropdown();
            }
        }, 150);
    }

    /**
     * Handle focus events.
     */
    _onFocus(e) {
        const query = this.input.value.trim();
        if (query.length >= 1) {
            this._search(query);
        } else if (!this.idInput.value) {
            // Show initial results when focusing on empty field
            this._search('', 5);
        }
    }

    /**
     * Handle document clicks to close dropdown.
     */
    _onDocumentClick(e) {
        if (!this.wrapper.contains(e.target)) {
            this._hideDropdown();
        }
    }

    /**
     * Search for results via API.
     */
    async _search(query, limit = 10) {
        // Show loading state
        this.dropdown.innerHTML = '<div class="autocomplete-loading">Searching...</div>';
        this._showDropdown();

        try {
            const url = `/core/api/autocomplete/search/?model=${encodeURIComponent(this.model)}&q=${encodeURIComponent(query)}&limit=${limit}`;
            const response = await fetch(url);
            const data = await response.json();

            if (data.error) {
                console.error('Autocomplete error:', data.error);
                this._hideDropdown();
                return;
            }

            this.results = data.results || [];
            this.config = data.config || {};

            this._renderResults(query);
        } catch (error) {
            console.error('Autocomplete fetch error:', error);
            this._hideDropdown();
        }
    }

    /**
     * Render search results in dropdown.
     */
    _renderResults(query) {
        this.dropdown.innerHTML = '';
        this.selectedIndex = -1;

        if (this.results.length === 0 && !this.allowCreate) {
            this.dropdown.innerHTML = '<div class="autocomplete-no-results">No results found</div>';
            return;
        }

        // Add result items
        this.results.forEach((item, index) => {
            const div = document.createElement('div');
            div.className = 'autocomplete-item';
            div.dataset.index = index;
            div.dataset.id = item.id;
            div.dataset.display = item.display;

            let html = `<div class="autocomplete-item-primary">${this._escapeHtml(item.display)}</div>`;
            if (item.secondary || item.id_field) {
                const secondary = item.id_field
                    ? `${item.id_field}${item.secondary ? ' - ' + item.secondary : ''}`
                    : item.secondary;
                html += `<div class="autocomplete-item-secondary">${this._escapeHtml(secondary)}</div>`;
            }

            div.innerHTML = html;
            div.addEventListener('click', () => this._selectItem(item.id, item.display, item));
            this.dropdown.appendChild(div);
        });

        // Add "Create new" option if allowed and query provided
        const allowCreate = this.allowCreate || (this.config && this.config.allow_create);
        if (allowCreate && query && query.length >= 2) {
            // Check if exact match exists
            const exactMatch = this.results.some(r =>
                r.display.toLowerCase() === query.toLowerCase()
            );

            if (!exactMatch) {
                const createDiv = document.createElement('div');
                createDiv.className = 'autocomplete-item autocomplete-create-new';
                createDiv.dataset.index = this.results.length;
                createDiv.dataset.id = 'new';
                createDiv.dataset.display = query;
                createDiv.innerHTML = `<div class="autocomplete-item-primary"><i class="fas fa-plus-circle"></i>Create new: "${this._escapeHtml(query)}"</div>`;
                createDiv.addEventListener('click', () => this._createNew(query));
                this.dropdown.appendChild(createDiv);
            }
        }

        this._showDropdown();
    }

    /**
     * Highlight selected item.
     */
    _highlightItem(items) {
        items.forEach((item, index) => {
            item.classList.toggle('highlighted', index === this.selectedIndex);
        });

        // Scroll into view
        if (this.selectedIndex >= 0 && items[this.selectedIndex]) {
            items[this.selectedIndex].scrollIntoView({ block: 'nearest' });
        }
    }

    /**
     * Select an item.
     */
    _selectItem(id, display, item) {
        this.input.value = display;
        this.idInput.value = id;
        this._hideDropdown();
        this._updateViewButton(id);

        // Dispatch select event
        this.input.dispatchEvent(new CustomEvent('autocomplete:select', {
            bubbles: true,
            detail: { id, display, item }
        }));
    }

    /**
     * Handle "Create new" action.
     */
    _createNew(name) {
        this.input.value = name;
        this._hideDropdown();

        // Dispatch create event - form should handle actual creation
        this.input.dispatchEvent(new CustomEvent('autocomplete:create', {
            bubbles: true,
            detail: { name }
        }));
    }

    /**
     * Update view button visibility and URL.
     */
    _updateViewButton(id = null) {
        if (!this.viewBtn) return;

        const selectedId = id || this.idInput.value;

        if (selectedId && selectedId !== 'new') {
            // Build URL from pattern
            let url = '#';
            if (this.config && this.config.view_url_pattern) {
                url = this.config.view_url_pattern.replace('{id}', selectedId);
            } else {
                // Fallback: try to construct URL
                const viewUrlName = this.viewUrlName;
                if (viewUrlName.includes('company')) {
                    url = `/contacts/companies/${selectedId}/`;
                } else if (viewUrlName.includes('contact')) {
                    url = `/contacts/contacts/${selectedId}/`;
                }
            }

            this.viewBtn.href = url;
            this.viewBtn.classList.add('visible');
        } else {
            this.viewBtn.href = '#';
            this.viewBtn.classList.remove('visible');
        }
    }

    /**
     * Show dropdown.
     */
    _showDropdown() {
        this.dropdown.classList.add('visible');
        this.dropdown.style.display = 'block';
        this.isOpen = true;
    }

    /**
     * Hide dropdown.
     */
    _hideDropdown() {
        this.dropdown.classList.remove('visible');
        this.dropdown.style.display = 'none';
        this.isOpen = false;
        this.selectedIndex = -1;
    }

    /**
     * Escape HTML to prevent XSS.
     */
    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML;
    }

    /**
     * Set the selected value programmatically.
     */
    setValue(id, display) {
        this.input.value = display || '';
        this.idInput.value = id || '';
        this._updateViewButton(id);
    }

    /**
     * Get the current selected ID.
     */
    getValue() {
        return this.idInput.value;
    }

    /**
     * Clear the selection.
     */
    clear() {
        this.input.value = '';
        this.idInput.value = '';
        this._updateViewButton();
        this._hideDropdown();
    }

    /**
     * Destroy the autocomplete instance.
     */
    destroy() {
        this.input.removeEventListener('input', this._onInput);
        this.input.removeEventListener('keydown', this._onKeydown);
        this.input.removeEventListener('blur', this._onBlur);
        this.input.removeEventListener('focus', this._onFocus);
        document.removeEventListener('click', this._onDocumentClick);

        clearTimeout(this.searchTimeout);
    }
}

/**
 * Auto-initialize autocomplete on elements with data-autocomplete="true".
 */
function initAutocomplete() {
    const inputs = document.querySelectorAll('[data-autocomplete="true"]:not([data-autocomplete-initialized])');

    inputs.forEach(input => {
        new Autocomplete(input);
        input.dataset.autocompleteInitialized = 'true';
    });
}

// Initialize on DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAutocomplete);
} else {
    initAutocomplete();
}

// Re-initialize on dynamic content (for forms loaded via AJAX)
const observer = new MutationObserver((mutations) => {
    let shouldInit = false;
    mutations.forEach(mutation => {
        if (mutation.addedNodes.length > 0) {
            mutation.addedNodes.forEach(node => {
                if (node.nodeType === Node.ELEMENT_NODE) {
                    if (node.matches && node.matches('[data-autocomplete="true"]')) {
                        shouldInit = true;
                    } else if (node.querySelector && node.querySelector('[data-autocomplete="true"]')) {
                        shouldInit = true;
                    }
                }
            });
        }
    });
    if (shouldInit) {
        initAutocomplete();
    }
});

observer.observe(document.body, { childList: true, subtree: true });

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { Autocomplete, initAutocomplete };
}
