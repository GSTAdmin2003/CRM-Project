"""
Template views -- existing Django views preserved during DRF transition.

These views render HTML templates. Business logic extracted to services where
possible; template views still do form handling directly for the Django form
workflow.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from ..forms import CompanyForm, ContactForm
from ..models import Company, Contact
from ..services import CompanyService, ContactService


PAGE_SIZE = 50


@login_required
def company_list(request):
    """List all companies with search and pagination."""
    search_query = request.GET.get('search', '')
    companies = Company.objects.annotate(contacts_count=Count('contacts'))

    if search_query:
        companies = companies.filter(
            Q(legal_name__icontains=search_query) |
            Q(brand_name__icontains=search_query) |
            Q(legal_id__icontains=search_query) |
            Q(industry__icontains=search_query) |
            Q(category__icontains=search_query)
        )

    companies = companies.order_by('legal_name')

    paginator = Paginator(companies, PAGE_SIZE)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'companies': page_obj,
        'page_obj': page_obj,
        'search_query': search_query,
        'total_companies': Company.objects.count(),
    }
    return render(request, 'contacts/company_list.html', context)


@login_required
def company_detail(request, pk):
    """Display company details and its contacts"""
    company = get_object_or_404(Company, pk=pk)
    contacts = company.contacts.all()

    context = {
        'company': company,
        'contacts': contacts,
    }
    return render(request, 'contacts/company_detail.html', context)


@login_required
def company_create(request):
    """Create a new company"""
    if request.method == 'POST':
        form = CompanyForm(request.POST)
        if form.is_valid():
            company = form.save(commit=False)
            company.created_by = request.user
            company.updated_by = request.user
            company.save()
            messages.success(request, f'"{company.legal_name}" created successfully.')
            return redirect('contacts:company_edit', pk=company.pk)
    else:
        form = CompanyForm()

    context = {
        'form': form,
        'action': 'Create',
    }
    return render(request, 'contacts/company_form.html', context)


@login_required
def company_edit(request, pk):
    """Edit an existing company — combined edit + detail page"""
    company = get_object_or_404(Company, pk=pk)

    if request.method == 'POST':
        form = CompanyForm(request.POST, instance=company)
        if form.is_valid():
            company = form.save(commit=False)
            company.updated_by = request.user
            company.save()
            messages.success(request, f'"{company.display_name}" saved successfully.')
            return redirect('contacts:company_edit', pk=company.pk)
    else:
        form = CompanyForm(instance=company)

    context = {
        'form': form,
        'company': company,
        'contacts': company.contacts.all(),
        'action': 'Edit',
    }
    return render(request, 'contacts/company_form.html', context)


@login_required
def company_delete(request, pk):
    """Delete a company"""
    company = get_object_or_404(Company, pk=pk)

    if request.method == 'POST':
        company_name = company.legal_name
        company.delete()
        messages.success(request, f'Company "{company_name}" deleted successfully!')
        return redirect('contacts:company_list')

    context = {
        'company': company,
    }
    return render(request, 'contacts/company_confirm_delete.html', context)


@login_required
def contact_create(request, company_pk):
    """Create a new contact for a company"""
    company = get_object_or_404(Company, pk=company_pk)

    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            contact = form.save(commit=False)
            contact.company = company
            contact.save()
            messages.success(request, f'Contact "{contact.name}" added successfully!')
            return redirect('contacts:company_detail', pk=company.pk)
    else:
        form = ContactForm()

    context = {
        'form': form,
        'company': company,
        'action': 'Add',
    }
    return render(request, 'contacts/contact_form.html', context)


@login_required
def contact_edit(request, company_pk, pk):
    """Edit an existing contact"""
    contact = get_object_or_404(Contact, pk=pk)

    if request.method == 'POST':
        form = ContactForm(request.POST, instance=contact)
        if form.is_valid():
            contact = form.save()
            messages.success(request, f'Contact "{contact.name}" updated successfully!')
            return redirect('contacts:company_detail', pk=contact.company.pk)
    else:
        form = ContactForm(instance=contact)

    context = {
        'form': form,
        'contact': contact,
        'company': contact.company,
        'action': 'Edit',
    }
    return render(request, 'contacts/contact_form.html', context)


@login_required
def contact_delete(request, company_pk, pk):
    """Delete a contact"""
    contact = get_object_or_404(Contact, pk=pk)
    company = contact.company

    if request.method == 'POST':
        contact_name = contact.name
        is_favorite = company.favorite_contact == contact

        # Check if this is the favorite contact and there are other contacts
        if is_favorite:
            other_contacts = company.contacts.exclude(pk=contact.pk)
            if other_contacts.exists():
                # Set another contact as favorite before deleting
                company.favorite_contact = other_contacts.first()
                company.save()
                messages.info(request, f'{company.favorite_contact.name} is now the favorite contact.')

        contact.delete()
        messages.success(request, f'Contact "{contact_name}" deleted successfully!')
        return redirect('contacts:company_detail', pk=company.pk)

    context = {
        'contact': contact,
        'company': company,
    }
    return render(request, 'contacts/contact_confirm_delete.html', context)


@login_required
def contact_detail(request, company_pk, pk):
    """Display contact details"""
    contact = get_object_or_404(Contact, pk=pk)

    context = {
        'contact': contact,
        'company': contact.company,
    }
    return render(request, 'contacts/contact_detail.html', context)


@login_required
@require_http_methods(["POST"])
def toggle_favorite_contact(request, company_pk, contact_pk):
    """Toggle favorite contact for a company"""
    company = get_object_or_404(Company, pk=company_pk)
    contact = get_object_or_404(Contact, pk=contact_pk, company=company)

    if company.favorite_contact == contact:
        # Check if there are other contacts to make favorite
        other_contacts = company.contacts.exclude(pk=contact.pk)
        if other_contacts.exists():
            # Set another contact as favorite (first one by name)
            company.favorite_contact = other_contacts.first()
            message = f'Set {company.favorite_contact.name} as favorite contact'
        else:
            # Can't remove favorite - this is the only contact
            message = f'{contact.name} remains favorite as it\'s the only contact'
    else:
        # Set as favorite
        company.favorite_contact = contact
        message = f'Set {contact.name} as favorite contact'

    company.save()

    if request.headers.get('HX-Request'):
        # Return JSON for HTMX requests
        return JsonResponse({
            'is_favorite': company.favorite_contact == contact,
            'message': message
        })

    messages.success(request, message)
    return redirect('contacts:company_detail', pk=company.pk)



# =============================================================================
# Company Import Views
# =============================================================================

@login_required
def company_import(request):
    """Company import page - shows upload form, preview, or results based on session state"""
    # Handle cancel action - clear session and reset to upload state
    if request.GET.get('cancel') == '1':
        request.session.pop('company_import_state', None)
        request.session.pop('company_import_preview', None)
        request.session.pop('company_import_results', None)
        return redirect('contacts:company_import')

    import_state = request.session.get('company_import_state', 'upload')
    preview_data = request.session.get('company_import_preview', None)
    import_results = request.session.get('company_import_results', None)

    context = {
        'import_state': import_state,
        'preview_data': preview_data,
        'import_results': import_results,
    }

    # Clean up results state after displaying
    if import_state == 'results':
        request.session.pop('company_import_state', None)
        request.session.pop('company_import_results', None)

    return render(request, 'contacts/company_import.html', context)


@login_required
@require_http_methods(["POST"])
def company_import_upload(request):
    """Handle Excel file upload and parse for preview"""
    from ..services.excel_import import parse_excel_file

    excel_file = request.FILES.get('excel_file')

    if not excel_file:
        messages.error(request, 'Please select an Excel file.')
        return redirect('contacts:company_import')

    if not excel_file.name.endswith('.xlsx'):
        messages.error(request, 'Only .xlsx files are supported.')
        return redirect('contacts:company_import')

    # Size limit: 5MB
    if excel_file.size > 5 * 1024 * 1024:
        messages.error(request, 'File size must be under 5MB.')
        return redirect('contacts:company_import')

    try:
        preview_data = parse_excel_file(excel_file, request.user)
        request.session['company_import_state'] = 'preview'
        request.session['company_import_preview'] = preview_data
    except ValueError as e:
        messages.error(request, str(e))
    except Exception as e:
        messages.error(request, f'Error parsing file: {str(e)}')

    return redirect('contacts:company_import')


@login_required
@require_http_methods(["POST"])
def company_import_confirm(request):
    """Process confirmed import from preview data"""
    from ..services.excel_import import execute_import

    preview_data = request.session.get('company_import_preview')

    if not preview_data:
        messages.error(request, 'No import data found. Please upload again.')
        return redirect('contacts:company_import')

    results = execute_import(preview_data, request.user)

    # Clean up preview, set results
    request.session.pop('company_import_preview', None)
    request.session['company_import_state'] = 'results'
    request.session['company_import_results'] = results

    return redirect('contacts:company_import')


@login_required
def company_import_template(request):
    """Generate and download company Excel import template"""
    from ..services.excel_template import generate_company_template

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="company_import_template.xlsx"'

    wb = generate_company_template()
    wb.save(response)

    return response


@login_required
def company_import_individual_template(request):
    """Generate and download individual Excel import template"""
    from ..services.excel_template import generate_individual_template

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="individual_import_template.xlsx"'

    generate_individual_template().save(response)

    return response


@login_required
def company_import_combined_template(request):
    """Generate and download combined Excel import template (companies + individuals)"""
    from ..services.excel_template import generate_combined_template

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="combined_import_template.xlsx"'

    generate_combined_template().save(response)

    return response
