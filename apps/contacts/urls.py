from django.urls import path
from . import views

app_name = 'contacts'

urlpatterns = [
    # Dashboard
    path('', views.dashboard_home, name='dashboard_home'),
    
    # Company URLs
    path('companies/', views.company_list, name='company_list'),
    path('companies/create/', views.company_create, name='company_create'),
    path('companies/<int:pk>/', views.company_detail, name='company_detail'),
    path('companies/<int:pk>/edit/', views.company_edit, name='company_edit'),
    path('companies/<int:pk>/delete/', views.company_delete, name='company_delete'),
    
    # Company Import URLs
    path('companies/import/', views.company_import, name='company_import'),
    path('companies/import/upload/', views.company_import_upload, name='company_import_upload'),
    path('companies/import/confirm/', views.company_import_confirm, name='company_import_confirm'),
    path('companies/import/template/', views.company_import_template, name='company_import_template'),

    # Contact URLs
    path('companies/<int:company_pk>/contacts/create/', views.contact_create, name='contact_create'),
    path('contacts/<int:pk>/', views.contact_detail, name='contact_detail'),
    path('contacts/<int:pk>/edit/', views.contact_edit, name='contact_edit'),
    path('contacts/<int:pk>/delete/', views.contact_delete, name='contact_delete'),
    path('companies/<int:company_pk>/contacts/<int:contact_pk>/toggle-favorite/', views.toggle_favorite_contact, name='toggle_favorite_contact'),
]