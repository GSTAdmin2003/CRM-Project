"""
DRF ViewSets for the LeadStage model.

All business logic is delegated to StageService.
"""

from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.exceptions import ConflictError, NotFoundError, PermissionDeniedError, ValidationError

from ..models import LeadStage
from ..serializers import (
    LeadStageCreateUpdateSerializer,
    LeadStageSerializer,
)
from ..services import StageService


class LeadStageViewSet(viewsets.ModelViewSet):
    """
    CRUD for lead stages (kanban stages).

    list:    GET    /crm/api/stages/
    create:  POST   /crm/api/stages/
    read:    GET    /crm/api/stages/{id}/
    update:  PUT    /crm/api/stages/{id}/
    delete:  DELETE /crm/api/stages/{id}/
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return LeadStageCreateUpdateSerializer
        return LeadStageSerializer

    def get_queryset(self):
        """
        Return stages filtered by team if a 'team' query param is provided,
        otherwise return all active stages.
        """
        team_id = self.request.query_params.get("team")
        if team_id:
            from ..models import SalesTeam

            try:
                team = SalesTeam.objects.get(pk=team_id)
                return StageService.get_stages_for_team(team=team)
            except SalesTeam.DoesNotExist:
                return LeadStage.objects.none()
        return LeadStage.objects.filter(is_active=True).order_by("sales_team", "order")

    def retrieve(self, request, *args, **kwargs):
        try:
            stage = StageService.get_stage_or_raise(pk=kwargs["pk"])
        except NotFoundError as e:
            return Response({"detail": e.message}, status=status.HTTP_404_NOT_FOUND)

        return Response(LeadStageSerializer(stage).data)

    def create(self, request, *args, **kwargs):
        serializer = LeadStageCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            stage = StageService.create_stage(
                name=serializer.validated_data["name"],
                team_pk=serializer.validated_data["sales_team_id"],
                user=request.user,
                description=serializer.validated_data.get("description", ""),
                color=serializer.validated_data.get("color", "#6B7280"),
                probability=serializer.validated_data.get("probability", 0),
                is_closed_stage=serializer.validated_data.get("is_closed_stage", False),
            )
        except NotFoundError as e:
            return Response({"detail": e.message}, status=status.HTTP_404_NOT_FOUND)
        except PermissionDeniedError as e:
            return Response({"detail": e.message}, status=status.HTTP_403_FORBIDDEN)
        except ValidationError as e:
            return Response({"detail": e.message}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            LeadStageSerializer(stage).data, status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        serializer = LeadStageCreateUpdateSerializer(
            data=request.data, partial=kwargs.get("partial", False)
        )
        serializer.is_valid(raise_exception=True)

        update_fields = {}
        for field in ("name", "description", "color", "probability", "is_closed_stage"):
            if field in serializer.validated_data:
                update_fields[field] = serializer.validated_data[field]

        try:
            stage = StageService.update_stage(
                pk=kwargs["pk"], user=request.user, **update_fields
            )
        except NotFoundError as e:
            return Response({"detail": e.message}, status=status.HTTP_404_NOT_FOUND)
        except PermissionDeniedError as e:
            return Response({"detail": e.message}, status=status.HTTP_403_FORBIDDEN)
        except ValidationError as e:
            return Response({"detail": e.message}, status=status.HTTP_400_BAD_REQUEST)

        return Response(LeadStageSerializer(stage).data)

    def destroy(self, request, *args, **kwargs):
        try:
            StageService.delete_stage(pk=kwargs["pk"], user=request.user)
        except NotFoundError as e:
            return Response({"detail": e.message}, status=status.HTTP_404_NOT_FOUND)
        except PermissionDeniedError as e:
            return Response({"detail": e.message}, status=status.HTTP_403_FORBIDDEN)
        except ConflictError as e:
            return Response({"detail": e.message}, status=status.HTTP_409_CONFLICT)

        return Response(status=status.HTTP_204_NO_CONTENT)
