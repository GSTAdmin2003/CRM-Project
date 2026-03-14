from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import template_views
from .views import company_views, contact_views

router = DefaultRouter()
router.register(r"companies", company_views.CompanyViewSet, basename="company-api")
router.register(r"contacts", contact_views.ContactViewSet, basename="contact-api")

app_name = 'contacts'

urlpatterns = [
    # DRF API endpoints
    path("api/", include(router.urls)),

    # Contact list — root of the app (/contacts/)
    path('', template_views.company_list, name='company_list'),

    # Company CRUD
    path('create/', template_views.company_create, name='company_create'),
    path('<int:pk>/', template_views.company_edit, name='company_detail'),
    path('<int:pk>/', template_views.company_edit, name='company_edit'),
    path('<int:pk>/delete/', template_views.company_delete, name='company_delete'),

    # Import
    path('import/', template_views.company_import, name='company_import'),
    path('import/upload/', template_views.company_import_upload, name='company_import_upload'),
    path('import/confirm/', template_views.company_import_confirm, name='company_import_confirm'),
    path('import/template/', template_views.company_import_template, name='company_import_template'),
    path('import/template/individual/', template_views.company_import_individual_template, name='company_import_individual_template'),
    path('import/template/combined/', template_views.company_import_combined_template, name='company_import_combined_template'),

    # Individual contact (person) URLs — nested under company
    path('<int:company_pk>/contacts/create/', template_views.contact_create, name='contact_create'),
    path('<int:company_pk>/contacts/<int:pk>/', template_views.contact_detail, name='contact_detail'),
    path('<int:company_pk>/contacts/<int:pk>/edit/', template_views.contact_edit, name='contact_edit'),
    path('<int:company_pk>/contacts/<int:pk>/delete/', template_views.contact_delete, name='contact_delete'),
    path('<int:company_pk>/contacts/<int:contact_pk>/toggle-favorite/', template_views.toggle_favorite_contact, name='toggle_favorite_contact'),
]
