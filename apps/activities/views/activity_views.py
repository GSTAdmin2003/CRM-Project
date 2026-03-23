"""
DRF ViewSets for the activities app.

All business logic is delegated to ActivityService.
"""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.exceptions import NotFoundError, PermissionDeniedError, ValidationError
from core.models import User

from ..models import Activity, ActivityType
from ..serializers import (
    ActivityCreateUpdateSerializer,
    ActivityDetailSerializer,
    ActivityListSerializer,
    ActivityTypeSerializer,
)
from ..services import ActivityService


class ActivityViewSet(viewsets.ModelViewSet):
    """
    CRUD for activities with permission-scoped listing.

    list:    GET    /activities/api/activities/
    create:  POST   /activities/api/activities/
    read:    GET    /activities/api/activities/{id}/
    update:  PUT    /activities/api/activities/{id}/
    delete:  DELETE /activities/api/activities/{id}/
    complete: POST  /activities/api/activities/{id}/complete/
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "list":
            return ActivityListSerializer
        if self.action in ("create", "update", "partial_update"):
            return ActivityCreateUpdateSerializer
        return ActivityDetailSerializer

    def get_queryset(self):
        lead_id = self.request.query_params.get("lead")

        # When filtering by a specific lead, skip date/team filters entirely
        if lead_id:
            return ActivityService.get_activities_for_user(
                user=self.request.user,
                view_context="personal",
                date_filter="all",
            ).filter(lead_id=lead_id)

        view_context = self.request.query_params.get("view", "personal")
        team_id = self.request.query_params.get("team")
        date_filter = self.request.query_params.get("filter", "week")
        custom_date = self.request.query_params.get("date", "")
        start_date = self.request.query_params.get("start_date", "")
        end_date = self.request.query_params.get("end_date", "")

        return ActivityService.get_activities_for_user(
            user=self.request.user,
            view_context=view_context,
            team_id=team_id,
            date_filter=date_filter,
            custom_date=custom_date,
            start_date=start_date,
            end_date=end_date,
        )

    def create(self, request, *args, **kwargs):
        serializer = ActivityCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        assigned_to = None
        assigned_to_id = serializer.validated_data.get("assigned_to_id")
        if assigned_to_id:
            try:
                assigned_to = User.objects.get(pk=assigned_to_id)
            except User.DoesNotExist:
                return Response(
                    {"detail": "Assigned user not found"}, status=status.HTTP_400_BAD_REQUEST
                )

        try:
            activity = ActivityService.create_activity(
                lead_id=serializer.validated_data["lead_id"],
                activity_type_id=serializer.validated_data["activity_type_id"],
                title=serializer.validated_data["title"],
                description=serializer.validated_data.get("description", ""),
                scheduled_date=serializer.validated_data["scheduled_date"],
                status=serializer.validated_data.get("status", "planned"),
                created_by=request.user,
                assigned_to=assigned_to,
            )
        except NotFoundError as e:
            return Response({"detail": e.message}, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as e:
            return Response({"detail": e.message}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            ActivityDetailSerializer(activity).data, status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        serializer = ActivityCreateUpdateSerializer(data=request.data, partial=kwargs.get("partial", False))
        serializer.is_valid(raise_exception=True)

        update_fields = {}
        for field in ("title", "description", "scheduled_date", "status", "outcome"):
            if field in serializer.validated_data:
                update_fields[field] = serializer.validated_data[field]

        if "activity_type_id" in serializer.validated_data:
            update_fields["activity_type_id"] = serializer.validated_data["activity_type_id"]

        assigned_to_id = serializer.validated_data.get("assigned_to_id")
        if assigned_to_id:
            try:
                update_fields["assigned_to"] = User.objects.get(pk=assigned_to_id)
            except User.DoesNotExist:
                return Response(
                    {"detail": "Assigned user not found"}, status=status.HTTP_400_BAD_REQUEST
                )

        try:
            activity = ActivityService.update_activity(
                pk=kwargs["pk"], user=request.user, **update_fields
            )
        except NotFoundError as e:
            return Response({"detail": e.message}, status=status.HTTP_404_NOT_FOUND)
        except PermissionDeniedError as e:
            return Response({"detail": e.message}, status=status.HTTP_403_FORBIDDEN)
        except ValidationError as e:
            return Response({"detail": e.message}, status=status.HTTP_400_BAD_REQUEST)

        return Response(ActivityDetailSerializer(activity).data)

    def destroy(self, request, *args, **kwargs):
        try:
            ActivityService.delete_activity(pk=kwargs["pk"], user=request.user)
        except NotFoundError as e:
            return Response({"detail": e.message}, status=status.HTTP_404_NOT_FOUND)
        except PermissionDeniedError as e:
            return Response({"detail": e.message}, status=status.HTTP_403_FORBIDDEN)

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """Mark an activity as completed."""
        outcome = request.data.get("outcome", "")
        try:
            activity = ActivityService.complete_activity(
                pk=pk, user=request.user, outcome=outcome
            )
        except NotFoundError as e:
            return Response({"detail": e.message}, status=status.HTTP_404_NOT_FOUND)
        except PermissionDeniedError as e:
            return Response({"detail": e.message}, status=status.HTTP_403_FORBIDDEN)
        except ValidationError as e:
            return Response({"detail": e.message}, status=status.HTTP_400_BAD_REQUEST)

        return Response(ActivityDetailSerializer(activity).data)


class ActivityTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only list of activity types.

    list:    GET /activities/api/activity-types/
    read:    GET /activities/api/activity-types/{id}/
    """

    queryset = ActivityType.objects.filter(is_active=True)
    serializer_class = ActivityTypeSerializer
    permission_classes = [IsAuthenticated]
