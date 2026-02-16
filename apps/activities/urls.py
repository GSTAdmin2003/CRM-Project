from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import activity_views, template_views

router = DefaultRouter()
router.register(r"activities", activity_views.ActivityViewSet, basename="activity")
router.register(r"activity-types", activity_views.ActivityTypeViewSet, basename="activity-type")

app_name = "activities"

urlpatterns = [
    # DRF API endpoints
    path("api/", include(router.urls)),
    # Existing template views
    path("", template_views.activity_dashboard, name="dashboard"),
    path("create/", template_views.activity_create, name="activity_create"),
    path("<int:pk>/", template_views.activity_detail, name="activity_detail"),
    path("<int:pk>/edit/", template_views.activity_edit, name="activity_edit"),
    path("<int:pk>/delete/", template_views.activity_delete, name="activity_delete"),
    path("<int:pk>/complete/", template_views.activity_complete, name="activity_complete"),
]
