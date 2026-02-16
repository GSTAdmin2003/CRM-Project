"""
DRF ViewSets for the SalesTeam model.

All business logic is delegated to TeamService.
"""

from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.exceptions import NotFoundError, PermissionDeniedError, ValidationError

from ..models import SalesTeam
from ..serializers import (
    SalesTeamCreateUpdateSerializer,
    SalesTeamDetailSerializer,
    SalesTeamListSerializer,
)
from ..services import TeamService


class SalesTeamViewSet(viewsets.ModelViewSet):
    """
    CRUD for sales teams.

    list:    GET    /crm/api/teams/
    create:  POST   /crm/api/teams/
    read:    GET    /crm/api/teams/{id}/
    update:  PUT    /crm/api/teams/{id}/
    delete:  DELETE /crm/api/teams/{id}/
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "list":
            return SalesTeamListSerializer
        if self.action in ("create", "update", "partial_update"):
            return SalesTeamCreateUpdateSerializer
        return SalesTeamDetailSerializer

    def get_queryset(self):
        return TeamService.list_teams()

    def retrieve(self, request, *args, **kwargs):
        try:
            team = TeamService.get_team_or_raise(pk=kwargs["pk"])
        except NotFoundError as e:
            return Response({"detail": e.message}, status=status.HTTP_404_NOT_FOUND)

        return Response(SalesTeamDetailSerializer(team).data)

    def create(self, request, *args, **kwargs):
        serializer = SalesTeamCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            team = TeamService.create_team(
                name=serializer.validated_data["name"],
                description=serializer.validated_data.get("description", ""),
                manager_id=serializer.validated_data.get("manager_id"),
                is_active=serializer.validated_data.get("is_active", True),
                created_by=request.user,
            )
        except NotFoundError as e:
            return Response({"detail": e.message}, status=status.HTTP_404_NOT_FOUND)
        except PermissionDeniedError as e:
            return Response({"detail": e.message}, status=status.HTTP_403_FORBIDDEN)
        except ValidationError as e:
            return Response({"detail": e.message}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            SalesTeamDetailSerializer(team).data, status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        serializer = SalesTeamCreateUpdateSerializer(
            data=request.data, partial=kwargs.get("partial", False)
        )
        serializer.is_valid(raise_exception=True)

        update_fields = {}
        for field in ("name", "description", "manager_id", "is_active"):
            if field in serializer.validated_data:
                update_fields[field] = serializer.validated_data[field]

        try:
            team = TeamService.update_team(
                pk=kwargs["pk"], user=request.user, **update_fields
            )
        except NotFoundError as e:
            return Response({"detail": e.message}, status=status.HTTP_404_NOT_FOUND)
        except PermissionDeniedError as e:
            return Response({"detail": e.message}, status=status.HTTP_403_FORBIDDEN)
        except ValidationError as e:
            return Response({"detail": e.message}, status=status.HTTP_400_BAD_REQUEST)

        return Response(SalesTeamDetailSerializer(team).data)

    def destroy(self, request, *args, **kwargs):
        """Delete a team -- not supported by TeamService yet, return 405."""
        return Response(
            {"detail": "Team deletion is not supported"},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )
