"""
DRF ViewSets for the IncomingLead model.

All business logic is delegated to IncomingLeadService.
"""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.exceptions import ConflictError, NotFoundError, PermissionDeniedError, ValidationError
from core.models import User

from ..models import IncomingLead
from ..serializers import (
    IncomingLeadCreateSerializer,
    IncomingLeadDetailSerializer,
    IncomingLeadListSerializer,
)
from ..serializers.lead import LeadDetailSerializer
from ..services import IncomingLeadService


class IncomingLeadViewSet(viewsets.ModelViewSet):
    """
    CRUD for incoming leads with conversion support.

    list:     GET    /crm/api/incoming-leads/
    create:   POST   /crm/api/incoming-leads/
    read:     GET    /crm/api/incoming-leads/{id}/
    update:   PUT    /crm/api/incoming-leads/{id}/
    convert:  POST   /crm/api/incoming-leads/{id}/convert/
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "list":
            return IncomingLeadListSerializer
        if self.action in ("create", "update", "partial_update"):
            return IncomingLeadCreateSerializer
        return IncomingLeadDetailSerializer

    def get_queryset(self):
        status_filter = self.request.query_params.get("status", "all")
        team_filter = self.request.query_params.get("team", "all")

        return IncomingLeadService.list_incoming_leads(
            user=self.request.user,
            status_filter=status_filter,
            team_filter=team_filter,
        )

    def retrieve(self, request, *args, **kwargs):
        try:
            lead = IncomingLeadService.get_incoming_lead_or_raise(pk=kwargs["pk"])
        except NotFoundError as e:
            return Response({"detail": e.message}, status=status.HTTP_404_NOT_FOUND)

        if not lead.can_be_viewed_by(request.user):
            return Response(
                {"detail": "You do not have permission to view this lead"},
                status=status.HTTP_403_FORBIDDEN,
            )

        return Response(IncomingLeadDetailSerializer(lead).data)

    def create(self, request, *args, **kwargs):
        serializer = IncomingLeadCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Resolve assigned_to from ID
        assigned_to = None
        assigned_to_id = serializer.validated_data.get("assigned_to_id")
        if assigned_to_id:
            try:
                assigned_to = User.objects.get(pk=assigned_to_id)
            except User.DoesNotExist:
                return Response(
                    {"detail": "Assigned user not found"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            lead = IncomingLeadService.create_incoming_lead(
                created_by=request.user,
                company_id=serializer.validated_data.get("company_id"),
                contact_id=serializer.validated_data.get("contact_id"),
                message=serializer.validated_data.get("message", ""),
                sales_team_id=serializer.validated_data.get("sales_team_id"),
                assigned_to=assigned_to,
                status=serializer.validated_data.get("status", "new"),
                notes=serializer.validated_data.get("notes", ""),
            )
        except NotFoundError as e:
            return Response({"detail": e.message}, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as e:
            return Response({"detail": e.message}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            IncomingLeadDetailSerializer(lead).data, status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        """
        Update is not directly supported via IncomingLeadService.
        For now, return 405.
        """
        return Response(
            {"detail": "Incoming lead update is not supported via API"},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def destroy(self, request, *args, **kwargs):
        """
        Delete is not directly supported via IncomingLeadService.
        For now, return 405.
        """
        return Response(
            {"detail": "Incoming lead deletion is not supported via API"},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @action(detail=True, methods=["post"])
    def convert(self, request, pk=None):
        """Convert an incoming lead to an opportunity."""
        try:
            opportunity = IncomingLeadService.convert_to_opportunity(
                pk=pk, user=request.user
            )
        except NotFoundError as e:
            return Response({"detail": e.message}, status=status.HTTP_404_NOT_FOUND)
        except PermissionDeniedError as e:
            return Response({"detail": e.message}, status=status.HTTP_403_FORBIDDEN)
        except ConflictError as e:
            return Response({"detail": e.message}, status=status.HTTP_409_CONFLICT)
        except ValidationError as e:
            return Response({"detail": e.message}, status=status.HTTP_400_BAD_REQUEST)

        return Response(LeadDetailSerializer(opportunity).data, status=status.HTTP_201_CREATED)
