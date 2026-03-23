"""
DRF ViewSets for the Lead model (covers both opportunities and leads).

All business logic is delegated to LeadService.
"""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from core.models import User

from ..models import Lead
from ..serializers import (
    LeadCreateUpdateSerializer,
    LeadDetailSerializer,
    LeadIncomingCreateSerializer,
    LeadListSerializer,
)
from ..services import LeadService


class LeadViewSet(viewsets.ModelViewSet):
    """
    CRUD for leads with permission-scoped listing.

    Supports ?type=opportunity (default) or ?type=lead query parameter
    to switch between opportunities and leads.

    list:    GET    /crm/api/leads/
    create:  POST   /crm/api/leads/
    read:    GET    /crm/api/leads/{id}/
    update:  PUT    /crm/api/leads/{id}/
    delete:  DELETE /crm/api/leads/{id}/
    convert: POST   /crm/api/leads/{id}/convert/
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        lead_type = self.request.query_params.get("type", "opportunity")
        if self.action == "list":
            return LeadListSerializer
        if self.action == "create":
            if lead_type == "lead":
                return LeadIncomingCreateSerializer
            return LeadCreateUpdateSerializer
        if self.action in ("update", "partial_update"):
            return LeadCreateUpdateSerializer
        return LeadDetailSerializer

    def get_queryset(self):
        lead_type = self.request.query_params.get("type", "opportunity")
        qs = LeadService.list_leads_for_user(user=self.request.user)
        if lead_type == "lead":
            status = self.request.query_params.get("status", "new")
            return qs.filter(status=status)
        return qs.filter(status="converted")

    def retrieve(self, request, *args, **kwargs):
        try:
            lead = LeadService.get_lead_or_raise(pk=kwargs["pk"])
        except NotFoundError as e:
            return Response({"detail": e.message}, status=status.HTTP_404_NOT_FOUND)

        if not lead.can_be_viewed_by(request.user):
            return Response(
                {"detail": "You do not have permission to view this lead"},
                status=status.HTTP_403_FORBIDDEN,
            )

        return Response(LeadDetailSerializer(lead).data)

    def create(self, request, *args, **kwargs):
        lead_type = request.query_params.get("type", "opportunity")

        if lead_type == "lead":
            return self._create_lead(request)
        return self._create_opportunity(request)

    def _create_opportunity(self, request):
        serializer = LeadCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

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
            lead = LeadService.create_lead(
                title=serializer.validated_data["title"],
                company_id=serializer.validated_data.get("company_id"),
                stage_id=serializer.validated_data.get("stage_id"),
                assigned_to=assigned_to,
                created_by=request.user,
                full_name=serializer.validated_data.get("full_name", ""),
                email=serializer.validated_data.get("email", ""),
                phone=serializer.validated_data.get("phone", ""),
                company_name=serializer.validated_data.get("company_name", ""),
                position=serializer.validated_data.get("position", ""),
                estimated_value=serializer.validated_data.get("estimated_value", 0),
                expected_close_date=serializer.validated_data.get("expected_close_date"),
                source=serializer.validated_data.get("source", "other"),
                status=serializer.validated_data.get("status", "new"),
                notes=serializer.validated_data.get("notes", ""),
                contact_id=serializer.validated_data.get("contact_id"),
                sales_team_id=serializer.validated_data.get("sales_team_id"),
            )
        except NotFoundError as e:
            return Response({"detail": e.message}, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as e:
            return Response({"detail": e.message}, status=status.HTTP_400_BAD_REQUEST)

        return Response(LeadDetailSerializer(lead).data, status=status.HTTP_201_CREATED)

    def _create_lead(self, request):
        serializer = LeadIncomingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

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
            lead = LeadService.create_lead(
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

        return Response(LeadDetailSerializer(lead).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        serializer = LeadCreateUpdateSerializer(
            data=request.data, partial=kwargs.get("partial", False)
        )
        serializer.is_valid(raise_exception=True)

        update_fields = {}
        direct_fields = {
            "title", "full_name", "email", "phone", "company_name", "position",
            "estimated_value", "expected_close_date", "source", "status", "lost_reason",
            "notes", "stage_id", "company_id", "contact_id", "sales_team_id",
        }
        for field in direct_fields:
            if field in serializer.validated_data:
                update_fields[field] = serializer.validated_data[field]

        assigned_to_id = serializer.validated_data.get("assigned_to_id")
        if assigned_to_id is not None:
            update_fields["assigned_to_id"] = assigned_to_id

        try:
            lead = LeadService.update_lead(
                pk=kwargs["pk"], user=request.user, **update_fields
            )
        except NotFoundError as e:
            return Response({"detail": e.message}, status=status.HTTP_404_NOT_FOUND)
        except PermissionDeniedError as e:
            return Response({"detail": e.message}, status=status.HTTP_403_FORBIDDEN)
        except ValidationError as e:
            return Response({"detail": e.message}, status=status.HTTP_400_BAD_REQUEST)

        return Response(LeadDetailSerializer(lead).data)

    def destroy(self, request, *args, **kwargs):
        try:
            LeadService.delete_lead(pk=kwargs["pk"], user=request.user)
        except NotFoundError as e:
            return Response({"detail": e.message}, status=status.HTTP_404_NOT_FOUND)
        except PermissionDeniedError as e:
            return Response({"detail": e.message}, status=status.HTTP_403_FORBIDDEN)

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def convert(self, request, pk=None):
        """Convert a status='new' lead into a pipeline opportunity (status='converted')."""
        try:
            lead = LeadService.get_lead_or_raise(pk=pk)
        except NotFoundError as e:
            return Response({"detail": e.message}, status=status.HTTP_404_NOT_FOUND)

        if not lead.can_be_edited_by(request.user):
            return Response(
                {"detail": "You do not have permission to convert this lead"},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            opportunity = LeadService.convert_lead_to_opportunity(
                lead=lead, user=request.user
            )
        except ValidationError as e:
            return Response({"detail": e.message}, status=status.HTTP_400_BAD_REQUEST)
        except ConflictError as e:
            return Response({"detail": e.message}, status=status.HTTP_409_CONFLICT)

        return Response(LeadDetailSerializer(opportunity).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def mark_won(self, request, pk=None):
        """Mark a converted opportunity as won (status='won')."""
        try:
            lead = LeadService.get_lead_or_raise(pk=pk)
        except NotFoundError as e:
            return Response({"detail": e.message}, status=status.HTTP_404_NOT_FOUND)

        try:
            lead = LeadService.mark_won(lead=lead, user=request.user)
        except PermissionDeniedError as e:
            return Response({"detail": e.message}, status=status.HTTP_403_FORBIDDEN)
        except ConflictError as e:
            return Response({"detail": e.message}, status=status.HTTP_409_CONFLICT)

        return Response(LeadDetailSerializer(lead).data)

    @action(detail=True, methods=["post"])
    def mark_lost(self, request, pk=None):
        """Mark a lead or opportunity as lost (status='lost'). Accepts optional 'reason' in body."""
        try:
            lead = LeadService.get_lead_or_raise(pk=pk)
        except NotFoundError as e:
            return Response({"detail": e.message}, status=status.HTTP_404_NOT_FOUND)

        reason = request.data.get("reason", "")
        try:
            lead = LeadService.mark_lost(lead=lead, reason=reason, user=request.user)
        except PermissionDeniedError as e:
            return Response({"detail": e.message}, status=status.HTTP_403_FORBIDDEN)
        except ConflictError as e:
            return Response({"detail": e.message}, status=status.HTTP_409_CONFLICT)

        return Response(LeadDetailSerializer(lead).data)
