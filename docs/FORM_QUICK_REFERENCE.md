# Form Layout Quick Reference

## Essential CSS Classes

### Layout
- Container: `w-full px-6 py-4`
- Grid (2-col): `grid grid-cols-1 lg:grid-cols-2 gap-4`
- Grid (1-col): `grid grid-cols-1 gap-4`

### Form Sections
```html
<div class="form-section">
    <div class="form-section-header">
        <h3 class="font-semibold text-gray-900">Title</h3>
    </div>
    <div class="form-section-content">
        <!-- fields -->
    </div>
</div>
```

### Field Group
```html
<div class="field-group">
    <label class="field-label">
        Name <span class="field-required">*</span>
    </label>
    {{ form.field }}
    <p class="error-message">Error text</p>
</div>
```

### Form Actions
```html
<div class="form-actions">
    <a href="#" class="btn btn-secondary">Cancel</a>
    <button type="submit" class="btn btn-primary">Save</button>
</div>
```

## Status Bar

### HTML
```html
<div class="bg-white border border-gray-200 rounded-lg mb-6">
    <div class="px-6 py-4">
        <div class="status-statusbar" id="status-statusbar">
            <div class="status-item" data-status="value1">Label 1</div>
            <div class="status-item" data-status="value2">Label 2</div>
        </div>
        <div class="hidden">{{ form.status }}</div>
    </div>
</div>
```

### JavaScript
```javascript
const statusField = document.getElementById('id_status');
const statusBar = document.getElementById('status-statusbar');

function renderStatusBar() {
    const currentStatus = statusField.value;
    statusBar.querySelectorAll('.status-item').forEach(item => {
        item.classList.toggle('active', item.dataset.status === currentStatus);
    });
}

statusBar.addEventListener('click', (e) => {
    const item = e.target.closest('.status-item');
    if (item) {
        statusField.value = item.dataset.status;
        renderStatusBar();
    }
});

renderStatusBar();
```

## Breadcrumb
```html
<nav class="flex mb-4" aria-label="Breadcrumb">
    <ol class="inline-flex items-center space-x-1 md:space-x-3">
        <li class="inline-flex items-center">
            <a href="{% url 'app:dashboard' %}"
               class="inline-flex items-center text-sm font-medium text-gray-700 hover:text-indigo-600">
                <svg class="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M10.707 2.293a1 1 0 00-1.414 0l-7 7a1 1 0 001.414 1.414L4 10.414V17a1 1 0 001 1h2a1 1 0 001-1v-2a1 1 0 011-1h2a1 1 0 011 1v2a1 1 0 001 1h2a1 1 0 001-1v-6.586l.293.293a1 1 0 001.414-1.414l-7-7z"></path>
                </svg>
                App Name
            </a>
        </li>
        <li>
            <div class="flex items-center">
                <svg class="w-6 h-6 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd"></path>
                </svg>
                <span class="ml-1 text-sm font-medium text-gray-500 md:ml-2">{{ action }}</span>
            </div>
        </li>
    </ol>
</nav>
```

## Django Form Widgets

```python
widgets = {
    # Text
    'name': forms.TextInput(attrs={'class': 'form-field'}),

    # Email
    'email': forms.EmailInput(attrs={'class': 'form-field'}),

    # Textarea
    'description': forms.Textarea(attrs={'class': 'form-field form-textarea', 'rows': 4}),

    # Select
    'category': forms.Select(attrs={'class': 'form-field'}),

    # Date
    'date': forms.DateInput(attrs={'class': 'form-field', 'type': 'date'}),

    # Number
    'amount': forms.NumberInput(attrs={'class': 'form-field', 'step': '0.01'}),

    # Hidden (for status bar)
    'status': forms.HiddenInput(),
}
```

## Common Patterns

### Two Fields Side-by-Side
```html
<div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
    <div class="field-group">...</div>
    <div class="field-group">...</div>
</div>
```

### Full Width Section in 2-Col Grid
```html
<div class="form-section lg:col-span-2">
    <!-- content -->
</div>
```

### Conditional Section
```html
<div id="conditional-section" class="form-section" style="display: none;">
    <!-- content -->
</div>
```

```javascript
function toggle() {
    const section = document.getElementById('conditional-section');
    section.style.display = condition ? 'block' : 'none';
}
```

## File Locations

- Guidelines: `/docs/FORM_LAYOUT_GUIDELINES.md`
- HTML Template: `/docs/templates/form_template.html`
- Forms.py Template: `/docs/templates/form_template.py`

## Checklist

- [ ] `w-full px-6 py-4` container
- [ ] Breadcrumb with SVG home icon
- [ ] Form has `id` attribute
- [ ] CSRF token included
- [ ] Grid: `grid grid-cols-1 lg:grid-cols-2 gap-4`
- [ ] Sections use `.form-section`
- [ ] Fields use `.field-group`
- [ ] Labels use `.field-label`
- [ ] Required: `.field-required`
- [ ] Errors: `.error-message`
- [ ] Widgets have `.form-field` class
- [ ] Actions: `.form-actions` (sticky)
- [ ] Buttons: `.btn .btn-primary` / `.btn .btn-secondary`
