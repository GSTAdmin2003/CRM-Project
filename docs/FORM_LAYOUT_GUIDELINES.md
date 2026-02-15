# Form Layout Guidelines

## Overview
This document defines the standard form layout pattern to be used across all apps in the CRM system. Following these guidelines ensures consistency in user experience, maintainability, and visual coherence.

## Page Structure

### 1. Container Layout
All form pages must use full-width layout:

```html
{% extends 'base.html' %}

{% block content %}
<div class="w-full px-6 py-4">
    <!-- Form content here -->
</div>
{% endblock %}
```

**Rules:**
- Use `w-full px-6 py-4` for the main container
- NO centered containers (no `mx-auto max-w-7xl`)
- NO extra padding on outer container beyond `px-6 py-4`

### 2. Breadcrumb Navigation
Always include breadcrumb navigation at the top:

```html
<nav class="flex mb-4" aria-label="Breadcrumb">
    <ol class="inline-flex items-center space-x-1 md:space-x-3">
        <li class="inline-flex items-center">
            <a href="{% url 'app:dashboard' %}" class="inline-flex items-center text-sm font-medium text-gray-700 hover:text-indigo-600">
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

**Rules:**
- Use SVG home icon (NOT Font Awesome)
- First breadcrumb links to app dashboard
- Last breadcrumb shows current action (Create/Edit)
- Use consistent spacing classes

### 3. Form Element
Standard form structure:

```html
<form method="post" id="entity-form">
    {% csrf_token %}

    <!-- Status Bar (if applicable) -->

    <!-- Form Sections Grid -->

    <!-- Form Actions -->
</form>
```

**Rules:**
- Always include `id` attribute for JavaScript targeting
- Include CSRF token
- Use semantic naming for form ID

## Status Bar (Optional)

For entities with status/stage fields, use a status bar at the top:

```html
<!-- Status Bar -->
<div class="bg-white border border-gray-200 rounded-lg mb-6">
    <div class="px-6 py-4">
        <div class="status-statusbar" id="status-statusbar">
            <div class="status-item" data-status="status1">Status 1</div>
            <div class="status-item" data-status="status2">Status 2</div>
            <div class="status-item completed" data-status="status3">Status 3</div>
        </div>
        <!-- Hidden status field -->
        <div class="hidden">
            {{ form.status }}
        </div>
    </div>
</div>
```

### Status Bar CSS

```css
.status-statusbar {
    position: relative;
    display: flex;
    align-items: center;
    margin: 0;
    padding: 0;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    overflow: hidden;
    background: #f9fafb;
}

.status-item {
    position: relative;
    flex: 1;
    text-align: center;
    padding: 14px 16px;
    font-size: 13px;
    font-weight: 500;
    color: #6b7280;
    background: transparent;
    border-right: 1px solid #e5e7eb;
    cursor: pointer;
    transition: all 0.3s ease;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.status-item:last-child {
    border-right: none;
}

.status-item:hover {
    background: #f3f4f6;
}

.status-item.active {
    background: #3b82f6;
    color: white;
    font-weight: 600;
    position: relative;
}

.status-item.active::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: #1d4ed8;
}

/* Custom status colors */
.status-item.completed.active {
    background: #10b981;
}

.status-item.completed.active::after {
    background: #059669;
}

.status-item.cancelled.active {
    background: #dc2626;
}

.status-item.cancelled.active::after {
    background: #991b1b;
}
```

### Status Bar JavaScript

```javascript
document.addEventListener('DOMContentLoaded', function() {
    const statusField = document.getElementById('{{ form.status.id_for_label }}');
    const statusBar = document.getElementById('status-statusbar');

    function renderStatusBar() {
        const currentStatus = statusField.value;
        const statusItems = statusBar.querySelectorAll('.status-item');

        statusItems.forEach(item => {
            const itemStatus = item.dataset.status;
            if (itemStatus === currentStatus) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });
    }

    // Handle status bar clicks
    statusBar.addEventListener('click', function(e) {
        const statusItem = e.target.closest('.status-item');
        if (statusItem) {
            const newStatus = statusItem.dataset.status;
            statusField.value = newStatus;
            renderStatusBar();
        }
    });

    // Initial render on page load
    if (statusField && statusBar) {
        renderStatusBar();
    }
});
```

## Form Sections Grid

Use a responsive grid layout for form sections:

```html
<!-- Form Sections Grid -->
<div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
    <!-- Section 1 -->
    <div class="form-section">
        <!-- Section content -->
    </div>

    <!-- Section 2 -->
    <div class="form-section">
        <!-- Section content -->
    </div>
</div>
```

**Rules:**
- Use `grid grid-cols-1 lg:grid-cols-2 gap-4` for two-column layout
- Single column on mobile, two columns on large screens
- Use `gap-4` for consistent spacing
- Each section wrapped in `.form-section`

## Form Section Structure

Each form section follows this structure:

```html
<div class="form-section">
    <div class="form-section-header">
        <h3 class="font-semibold text-gray-900">Section Title</h3>
    </div>
    <div class="form-section-content">
        <!-- Field groups here -->
    </div>
</div>
```

### Form Section CSS

```css
.form-section {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    overflow: hidden;
    margin-bottom: 16px;
}

.form-section-header {
    padding: 16px 20px;
    border-bottom: 1px solid #e5e7eb;
    background: #f9fafb;
    border-radius: 8px 8px 0 0;
}

.form-section-content {
    padding: 20px;
}
```

## Field Groups

Each field must be wrapped in a field group:

```html
<div class="field-group">
    <label for="{{ form.field_name.id_for_label }}" class="field-label">
        Field Name <span class="field-required">*</span>
    </label>
    {{ form.field_name }}
    {% if form.field_name.errors %}
    <p class="error-message">{{ form.field_name.errors.0 }}</p>
    {% endif %}
</div>
```

### Optional: Field with Help Text

```html
<div class="field-group">
    <label for="{{ form.field_name.id_for_label }}" class="field-label">
        Field Name
    </label>
    {{ form.field_name }}
    {% if form.field_name.errors %}
    <p class="error-message">{{ form.field_name.errors.0 }}</p>
    {% endif %}
    <p class="mt-1 text-sm text-gray-500">Helper text explaining this field</p>
</div>
```

### Field Group CSS

```css
.field-group {
    margin-bottom: 16px;
}

.field-label {
    display: block;
    font-size: 13px;
    font-weight: 600;
    color: #374151;
    margin-bottom: 4px;
}

.field-required {
    color: #dc2626;
}

.error-message {
    color: #dc2626;
    font-size: 12px;
    margin-top: 4px;
}
```

## Form Fields

All form inputs should use the `.form-field` class:

```css
.form-field {
    width: 100%;
    padding: 8px 12px;
    border: 1px solid #d1d5db;
    border-radius: 4px;
    font-size: 14px;
    transition: border-color 0.2s ease;
}

.form-field:focus {
    outline: none;
    border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.form-textarea {
    resize: vertical;
    min-height: 80px;
}
```

### Applying Form Field Styles in Django Forms

In your `forms.py`:

```python
class MyModelForm(forms.ModelForm):
    class Meta:
        model = MyModel
        fields = ['field1', 'field2', 'field3']
        widgets = {
            'field1': forms.TextInput(attrs={
                'class': 'form-field',
                'placeholder': 'Enter field1'
            }),
            'field2': forms.Select(attrs={
                'class': 'form-field'
            }),
            'field3': forms.Textarea(attrs={
                'class': 'form-field form-textarea',
                'rows': 4
            }),
        }
```

## Form Actions Bar

Always include a sticky actions bar at the bottom:

```html
<!-- Form Actions -->
<div class="form-actions">
    <a href="{% url 'app:list' %}" class="btn btn-secondary">
        Cancel
    </a>
    <button type="submit" class="btn btn-primary">
        {% if object %}Save Changes{% else %}Create{% endif %}
    </button>
</div>
```

### Form Actions CSS

```css
.form-actions {
    position: sticky;
    bottom: 0;
    background: white;
    border-top: 1px solid #e5e7eb;
    padding: 16px 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.btn {
    padding: 8px 16px;
    border-radius: 4px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    border: none;
    transition: all 0.2s ease;
}

.btn-primary {
    background: #3b82f6;
    color: white;
}

.btn-primary:hover {
    background: #2563eb;
}

.btn-secondary {
    background: #e5e7eb;
    color: #374151;
}

.btn-secondary:hover {
    background: #d1d5db;
}
```

## Complete Template Example

```html
{% extends 'base.html' %}

{% block title %}{{ action }} - CRM System{% endblock %}

{% block extra_css %}
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
<style>
/* Include all CSS from above sections */
.status-statusbar { /* ... */ }
.status-item { /* ... */ }
.form-section { /* ... */ }
.form-section-header { /* ... */ }
.form-section-content { /* ... */ }
.field-group { /* ... */ }
.field-label { /* ... */ }
.field-required { /* ... */ }
.form-field { /* ... */ }
.form-textarea { /* ... */ }
.form-actions { /* ... */ }
.btn { /* ... */ }
.btn-primary { /* ... */ }
.btn-secondary { /* ... */ }
.error-message { /* ... */ }
</style>
{% endblock %}

{% block content %}
<div class="w-full px-6 py-4">
    <!-- Breadcrumb Navigation -->
    <nav class="flex mb-4" aria-label="Breadcrumb">
        <ol class="inline-flex items-center space-x-1 md:space-x-3">
            <li class="inline-flex items-center">
                <a href="{% url 'app:dashboard' %}" class="inline-flex items-center text-sm font-medium text-gray-700 hover:text-indigo-600">
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

    <form method="post" id="entity-form">
        {% csrf_token %}

        <!-- Status Bar (if applicable) -->
        <div class="bg-white border border-gray-200 rounded-lg mb-6">
            <div class="px-6 py-4">
                <div class="status-statusbar" id="status-statusbar">
                    <div class="status-item" data-status="status1">Status 1</div>
                    <div class="status-item" data-status="status2">Status 2</div>
                    <div class="status-item" data-status="status3">Status 3</div>
                </div>
                <div class="hidden">
                    {{ form.status }}
                </div>
            </div>
        </div>

        <!-- Form Sections Grid -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <!-- Section 1 -->
            <div class="form-section">
                <div class="form-section-header">
                    <h3 class="font-semibold text-gray-900">Section 1 Title</h3>
                </div>
                <div class="form-section-content">
                    <div class="field-group">
                        <label for="{{ form.field1.id_for_label }}" class="field-label">
                            Field 1 <span class="field-required">*</span>
                        </label>
                        {{ form.field1 }}
                        {% if form.field1.errors %}
                        <p class="error-message">{{ form.field1.errors.0 }}</p>
                        {% endif %}
                    </div>
                </div>
            </div>

            <!-- Section 2 -->
            <div class="form-section">
                <div class="form-section-header">
                    <h3 class="font-semibold text-gray-900">Section 2 Title</h3>
                </div>
                <div class="form-section-content">
                    <div class="field-group">
                        <label for="{{ form.field2.id_for_label }}" class="field-label">
                            Field 2
                        </label>
                        {{ form.field2 }}
                        {% if form.field2.errors %}
                        <p class="error-message">{{ form.field2.errors.0 }}</p>
                        {% endif %}
                    </div>
                </div>
            </div>
        </div>

        <!-- Form Actions -->
        <div class="form-actions">
            <a href="{% url 'app:list' %}" class="btn btn-secondary">
                Cancel
            </a>
            <button type="submit" class="btn btn-primary">
                {% if object %}Save Changes{% else %}Create{% endif %}
            </button>
        </div>
    </form>
</div>
{% endblock %}

{% block extra_js %}
<script>
    document.addEventListener('DOMContentLoaded', function() {
        const statusField = document.getElementById('{{ form.status.id_for_label }}');
        const statusBar = document.getElementById('status-statusbar');

        function renderStatusBar() {
            const currentStatus = statusField.value;
            const statusItems = statusBar.querySelectorAll('.status-item');

            statusItems.forEach(item => {
                const itemStatus = item.dataset.status;
                if (itemStatus === currentStatus) {
                    item.classList.add('active');
                } else {
                    item.classList.remove('active');
                }
            });
        }

        statusBar.addEventListener('click', function(e) {
            const statusItem = e.target.closest('.status-item');
            if (statusItem) {
                const newStatus = statusItem.dataset.status;
                statusField.value = newStatus;
                renderStatusBar();
            }
        });

        if (statusField && statusBar) {
            renderStatusBar();
        }
    });
</script>
{% endblock %}
```

## Layout Variations

### Single Column Layout

For simpler forms or when fields are wide:

```html
<div class="grid grid-cols-1 gap-4">
    <div class="form-section">
        <!-- Section content -->
    </div>
</div>
```

### Three Column Layout

For compact forms with many small fields:

```html
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
    <div class="form-section">
        <!-- Section content -->
    </div>
</div>
```

### Full Width Section

For sections that should span entire width in two-column layout:

```html
<div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
    <!-- Regular sections -->
    <div class="form-section">...</div>
    <div class="form-section">...</div>

    <!-- Full width section -->
    <div class="form-section lg:col-span-2">
        <div class="form-section-header">
            <h3 class="font-semibold text-gray-900">Full Width Section</h3>
        </div>
        <div class="form-section-content">
            <!-- Content -->
        </div>
    </div>
</div>
```

## Conditional Section Visibility

For sections that appear based on certain conditions (e.g., outcome only when completed):

```html
<div id="conditional-section" class="form-section" style="display: none;">
    <div class="form-section-header">
        <h3 class="font-semibold text-gray-900">Conditional Section</h3>
    </div>
    <div class="form-section-content">
        <!-- Content -->
    </div>
</div>
```

JavaScript to toggle:

```javascript
function toggleConditionalSection() {
    const conditionalSection = document.getElementById('conditional-section');
    const triggerField = document.getElementById('trigger-field');

    if (triggerField.value === 'expected_value') {
        conditionalSection.style.display = 'block';
    } else {
        conditionalSection.style.display = 'none';
    }
}

// Call on page load and field change
document.addEventListener('DOMContentLoaded', toggleConditionalSection);
document.getElementById('trigger-field').addEventListener('change', toggleConditionalSection);
```

## Field Layout Within Sections

### Standard Stacked Fields

Default layout - each field takes full width:

```html
<div class="form-section-content">
    <div class="field-group">
        <label class="field-label">Field 1</label>
        {{ form.field1 }}
    </div>
    <div class="field-group">
        <label class="field-label">Field 2</label>
        {{ form.field2 }}
    </div>
</div>
```

### Two Fields Side-by-Side

For related fields (e.g., first name / last name):

```html
<div class="form-section-content">
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div class="field-group">
            <label class="field-label">First Name</label>
            {{ form.first_name }}
        </div>
        <div class="field-group">
            <label class="field-label">Last Name</label>
            {{ form.last_name }}
        </div>
    </div>
</div>
```

## Django Form Configuration

Always configure form widgets with proper classes:

```python
from django import forms

class MyModelForm(forms.ModelForm):
    class Meta:
        model = MyModel
        fields = '__all__'
        widgets = {
            # Text inputs
            'name': forms.TextInput(attrs={
                'class': 'form-field',
                'placeholder': 'Enter name'
            }),

            # Email
            'email': forms.EmailInput(attrs={
                'class': 'form-field',
                'placeholder': 'email@example.com'
            }),

            # Select/Dropdown
            'category': forms.Select(attrs={
                'class': 'form-field'
            }),

            # Textarea
            'description': forms.Textarea(attrs={
                'class': 'form-field form-textarea',
                'rows': 4,
                'placeholder': 'Enter description'
            }),

            # Date
            'scheduled_date': forms.DateInput(attrs={
                'class': 'form-field',
                'type': 'date'
            }),

            # Number
            'amount': forms.NumberInput(attrs={
                'class': 'form-field',
                'step': '0.01',
                'min': '0'
            }),
        }
```

## Checklist for Creating New Forms

- [ ] Container uses `w-full px-6 py-4`
- [ ] Breadcrumb navigation included with SVG home icon
- [ ] Form has proper `id` attribute
- [ ] CSRF token included
- [ ] Status bar included (if entity has status/stage)
- [ ] Grid layout uses `grid grid-cols-1 lg:grid-cols-2 gap-4`
- [ ] Each section wrapped in `.form-section`
- [ ] Section headers use `.form-section-header` with `h3.font-semibold`
- [ ] Section content wrapped in `.form-section-content`
- [ ] All fields wrapped in `.field-group`
- [ ] All labels use `.field-label`
- [ ] Required fields marked with `.field-required`
- [ ] Error messages use `.error-message`
- [ ] Form widgets configured with `.form-field` class
- [ ] Form actions bar is sticky with `.form-actions`
- [ ] Buttons use `.btn .btn-primary` or `.btn .btn-secondary`
- [ ] Cancel button links to appropriate list/dashboard view
- [ ] Submit button text changes based on create/edit
- [ ] JavaScript for status bar included (if applicable)
- [ ] JavaScript for conditional sections included (if applicable)

## Benefits of This Standard

1. **Consistency**: All forms look and behave the same way
2. **Maintainability**: Easy to update styles globally
3. **Responsiveness**: Built-in mobile responsiveness
4. **Accessibility**: Proper label associations and semantic HTML
5. **User Experience**: Familiar interface across all modules
6. **Developer Experience**: Copy-paste template for new forms

## Migration Strategy for Existing Forms

To update existing forms to this standard:

1. Add CSS classes to `extra_css` block
2. Change container from centered to full-width
3. Update breadcrumb to use SVG icons
4. Wrap sections in `.form-section` structure
5. Update field groups to use `.field-group` pattern
6. Update form widgets to include `.form-field` class
7. Replace form actions with sticky `.form-actions` bar
8. Test responsiveness on mobile
9. Test all form submissions still work
10. Verify JavaScript interactions (if any)
