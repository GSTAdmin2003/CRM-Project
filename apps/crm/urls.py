from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    incoming_lead_views,
    kanban_views,
    lead_views,
    stage_views,
    team_views,
    template_views,
)

router = DefaultRouter()
router.register(r"leads", lead_views.LeadViewSet, basename="lead")
router.register(r"teams", team_views.SalesTeamViewSet, basename="salesteam")
router.register(r"stages", stage_views.LeadStageViewSet, basename="leadstage")
router.register(r"incoming-leads", incoming_lead_views.IncomingLeadViewSet, basename="incoming-lead")

app_name = "crm"

urlpatterns = [
    # New DRF API endpoints
    path("api/", include(router.urls)),
    path("api/kanban/", kanban_views.KanbanView.as_view(), name="api_kanban"),
    path(
        "api/leads/<int:lead_id>/stage/",
        kanban_views.UpdateLeadStageView.as_view(),
        name="api_lead_stage_update",
    ),

    # Legacy API endpoints (kept for existing template JS)
    path(
        "api/opportunities/kanban/",
        template_views.api_kanban_data,
        name="api_kanban_data",
    ),
    path(
        "api/opportunities/<int:lead_id>/stage/",
        template_views.api_update_lead_stage,
        name="api_update_opportunity_stage",
    ),
    path(
        "api/opportunities/",
        template_views.api_lead_list_create,
        name="api_opportunity_list_create",
    ),
    path(
        "api/opportunities/<int:lead_id>/",
        template_views.api_lead_detail,
        name="api_opportunity_detail",
    ),
    path(
        "api/company/create/",
        template_views.api_create_company,
        name="api_create_company",
    ),
    path(
        "api/company/<int:company_id>/contacts/",
        template_views.api_company_contacts,
        name="api_company_contacts",
    ),
    path(
        "api/company/search/",
        template_views.api_company_search,
        name="api_company_search",
    ),
    path(
        "api/activity/quick-create/",
        template_views.api_quick_activity_create,
        name="api_quick_activity_create",
    ),

    # Dashboard
    path("", template_views.crm_dashboard, name="dashboard"),

    # Kanban Board
    path("kanban/", template_views.kanban_board, name="kanban_board"),

    # Opportunity management
    path("opportunities/", template_views.lead_list, name="opportunity_list"),
    path("opportunities/create/", template_views.lead_create, name="opportunity_create"),
    path("opportunities/import/", template_views.lead_import, name="opportunity_import"),
    path(
        "opportunities/import/upload/",
        template_views.lead_import_upload,
        name="opportunity_import_upload",
    ),
    path(
        "opportunities/import/confirm/",
        template_views.lead_import_confirm,
        name="opportunity_import_confirm",
    ),
    path(
        "opportunities/import/template/",
        template_views.lead_import_template,
        name="opportunity_import_template",
    ),
    path(
        "opportunities/<int:pk>/",
        template_views.lead_edit,
        name="opportunity_detail",
    ),  # Redirect detail to edit
    path("opportunities/<int:pk>/edit/", template_views.lead_edit, name="opportunity_edit"),
    path("opportunities/<int:pk>/delete/", template_views.lead_delete, name="opportunity_delete"),

    # Sales Team management
    path("teams/", template_views.team_list, name="team_list"),
    path("teams/create/", template_views.team_create, name="team_create"),
    path("teams/<int:pk>/", template_views.team_detail, name="team_detail"),
    path("teams/<int:pk>/edit/", template_views.team_edit, name="team_edit"),

    # Team-specific stage management
    path(
        "teams/<int:team_pk>/stages/create/",
        template_views.team_stage_create,
        name="team_stage_create",
    ),
    path(
        "teams/<int:team_pk>/stages/<int:stage_pk>/edit/",
        template_views.team_stage_edit,
        name="team_stage_edit",
    ),
    path(
        "teams/<int:team_pk>/stages/<int:stage_pk>/delete/",
        template_views.team_stage_delete,
        name="team_stage_delete",
    ),

    # Incoming leads management
    path("leads/", template_views.incoming_lead_list, name="lead_list"),
    path("leads/create/", template_views.incoming_lead_create, name="lead_create"),
    path("leads/<int:pk>/", template_views.incoming_lead_detail, name="lead_detail"),
    path("leads/<int:pk>/edit/", template_views.incoming_lead_edit, name="lead_edit"),
    path("leads/<int:pk>/delete/", template_views.incoming_lead_delete, name="lead_delete"),
    path("leads/<int:pk>/convert/", template_views.incoming_lead_convert, name="lead_convert"),
]
