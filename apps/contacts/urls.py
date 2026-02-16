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

    # Existing template views
    # Dashboard
    path('', template_views.dashboard_home, name='dashboard_home'),

    # Company URLs
    path('companies/', template_views.company_list, name='company_list'),
    path('companies/create/', template_views.company_create, name='company_create'),
    path('companies/<int:pk>/', template_views.company_detail, name='company_detail'),
    path('companies/<int:pk>/edit/', template_views.company_edit, name='company_edit'),
    path('companies/<int:pk>/delete/', template_views.company_delete, name='company_delete'),

    # Company Import URLs
    path('companies/import/', template_views.company_import, name='company_import'),
    path('companies/import/upload/', template_views.company_import_upload, name='company_import_upload'),
    path('companies/import/confirm/', template_views.company_import_confirm, name='company_import_confirm'),
    path('companies/import/template/', template_views.company_import_template, name='company_import_template'),

    # Contact URLs
    path('companies/<int:company_pk>/contacts/create/', template_views.contact_create, name='contact_create'),
    path('contacts/<int:pk>/', template_views.contact_detail, name='contact_detail'),
    path('contacts/<int:pk>/edit/', template_views.contact_edit, name='contact_edit'),
    path('contacts/<int:pk>/delete/', template_views.contact_delete, name='contact_delete'),
    path('companies/<int:company_pk>/contacts/<int:contact_pk>/toggle-favorite/', template_views.toggle_favorite_contact, name='toggle_favorite_contact'),
]
