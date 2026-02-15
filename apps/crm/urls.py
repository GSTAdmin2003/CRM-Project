from django.urls import path
from . import views

app_name = 'crm'

urlpatterns = [
    # Dashboard
    path('', views.crm_dashboard, name='dashboard'),
    
    # Kanban Board
    path('kanban/', views.kanban_board, name='kanban_board'),
    
    # API endpoints
    path('api/opportunities/kanban/', views.api_kanban_data, name='api_kanban_data'),
    path('api/opportunities/<int:lead_id>/stage/', views.api_update_lead_stage, name='api_update_opportunity_stage'),
    path('api/opportunities/', views.api_lead_list_create, name='api_opportunity_list_create'),
    path('api/opportunities/<int:lead_id>/', views.api_lead_detail, name='api_opportunity_detail'),
    path('api/company/create/', views.api_create_company, name='api_create_company'),
    path('api/company/<int:company_id>/contacts/', views.api_company_contacts, name='api_company_contacts'),
    path('api/company/search/', views.api_company_search, name='api_company_search'),
    path('api/activity/quick-create/', views.api_quick_activity_create, name='api_quick_activity_create'),

    # Opportunity management
    path('opportunities/', views.lead_list, name='opportunity_list'),
    path('opportunities/create/', views.lead_create, name='opportunity_create'),
    path('opportunities/import/', views.lead_import, name='opportunity_import'),
    path('opportunities/import/upload/', views.lead_import_upload, name='opportunity_import_upload'),
    path('opportunities/import/confirm/', views.lead_import_confirm, name='opportunity_import_confirm'),
    path('opportunities/import/template/', views.lead_import_template, name='opportunity_import_template'),
    path('opportunities/<int:pk>/', views.lead_edit, name='opportunity_detail'),  # Redirect detail to edit
    path('opportunities/<int:pk>/edit/', views.lead_edit, name='opportunity_edit'),
    path('opportunities/<int:pk>/delete/', views.lead_delete, name='opportunity_delete'),
    
    # Sales Team management
    path('teams/', views.team_list, name='team_list'),
    path('teams/create/', views.team_create, name='team_create'),
    path('teams/<int:pk>/', views.team_detail, name='team_detail'),
    path('teams/<int:pk>/edit/', views.team_edit, name='team_edit'),
    
    # Team-specific stage management
    path('teams/<int:team_pk>/stages/create/', views.team_stage_create, name='team_stage_create'),
    path('teams/<int:team_pk>/stages/<int:stage_pk>/edit/', views.team_stage_edit, name='team_stage_edit'),
    path('teams/<int:team_pk>/stages/<int:stage_pk>/delete/', views.team_stage_delete, name='team_stage_delete'),

    # Leads management
    path('leads/', views.incoming_lead_list, name='lead_list'),
    path('leads/create/', views.incoming_lead_create, name='lead_create'),
    path('leads/<int:pk>/', views.incoming_lead_detail, name='lead_detail'),
    path('leads/<int:pk>/edit/', views.incoming_lead_edit, name='lead_edit'),
    path('leads/<int:pk>/delete/', views.incoming_lead_delete, name='lead_delete'),
    path('leads/<int:pk>/convert/', views.incoming_lead_convert, name='lead_convert'),
]