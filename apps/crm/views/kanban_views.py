"""
DRF APIViews for the Kanban board.

All business logic is delegated to KanbanService.
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.exceptions import NotFoundError, PermissionDeniedError

from ..serializers import UpdateLeadStageSerializer
from ..serializers.kanban import KanbanStageSerializer
from ..serializers.lead import LeadDetailSerializer
from ..services import KanbanService


class KanbanView(APIView):
    """
    GET /crm/api/kanban/

    Returns the full kanban board data: stages with nested lead cards.
    Supports query params: ?view=personal|team&team=<id>|all
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        view_context = request.query_params.get("view", "personal")
        team_id = request.query_params.get("team", "all")

        data = KanbanService.get_kanban_data(
            user=request.user,
            view_context=view_context,
            team_id=team_id,
        )

        # Serialize the kanban stages
        serialized_stages = KanbanStageSerializer(data["stages"], many=True).data

        return Response({
            "stages": serialized_stages,
            "selected_team_id": data["selected_team_id"],
            "view_context": data["view_context"],
        })


class UpdateLeadStageView(APIView):
    """
    PATCH /crm/api/leads/{lead_id}/stage/

    Move a lead to a new stage (kanban drag-and-drop).
    """

    permission_classes = [IsAuthenticated]

    def patch(self, request, lead_id):
        serializer = UpdateLeadStageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            lead = KanbanService.update_lead_stage(
                lead_pk=lead_id,
                new_stage_pk=serializer.validated_data["stage_id"],
                user=request.user,
            )
        except NotFoundError as e:
            return Response({"detail": e.message}, status=status.HTTP_404_NOT_FOUND)
        except PermissionDeniedError as e:
            return Response({"detail": e.message}, status=status.HTTP_403_FORBIDDEN)

        return Response(LeadDetailSerializer(lead).data)
