"""
DRF ViewSets for the calls app.

All business logic is delegated to CallService.
VoIP action endpoints use @action decorators for low-latency operations.
"""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.exceptions import NotFoundError, ValidationError

from ..models import Call, CallRecording
from ..serializers import (
    CallCreateSerializer,
    CallDetailSerializer,
    CallListSerializer,
)
from ..services import CallService


class CallViewSet(viewsets.ModelViewSet):
    """
    CRUD and VoIP actions for calls.

    list:       GET    /calls/api/calls/
    retrieve:   GET    /calls/api/calls/{id}/
    initiate:   POST   /calls/api/calls/initiate/
    hangup:     POST   /calls/api/calls/{id}/hangup/
    answer:     POST   /calls/api/calls/{id}/answer/
    status:     GET    /calls/api/calls/{id}/status/
    notes:      PATCH  /calls/api/calls/{id}/notes/
    active:     GET    /calls/api/calls/active/
    link_contact:     POST  /calls/api/calls/{id}/link-contact/
    link_opportunity: POST  /calls/api/calls/{id}/link-opportunity/
    """

    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_serializer_class(self):
        if self.action == "list":
            return CallListSerializer
        if self.action == "initiate":
            return CallCreateSerializer
        return CallDetailSerializer

    def get_queryset(self):
        direction = self.request.query_params.get("direction")
        call_status = self.request.query_params.get("status")
        user_filter = self.request.query_params.get("user")
        search = self.request.query_params.get("search", "")

        return CallService.list_calls_for_user(
            user=self.request.user,
            direction=direction,
            status=call_status,
            user_filter=user_filter,
            search=search,
        )

    def retrieve(self, request, *args, **kwargs):
        try:
            call = CallService.get_call_or_raise(pk=int(kwargs["pk"]))
        except NotFoundError as e:
            return Response({"detail": e.message}, status=status.HTTP_404_NOT_FOUND)

        serializer = CallDetailSerializer(call)
        return Response(serializer.data)

    # -- Disable default create/update/destroy in favor of custom actions ------

    def create(self, request, *args, **kwargs):
        """Disabled -- use the /initiate/ action instead."""
        return Response(
            {"detail": "Use the /initiate/ endpoint to create calls."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def update(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def partial_update(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def destroy(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    # -- Custom actions --------------------------------------------------------

    @action(detail=False, methods=["post"])
    def initiate(self, request):
        """Initiate an outbound call."""
        serializer = CallCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            call = CallService.initiate_call(
                user=request.user,
                phone_number=serializer.validated_data["phone_number"],
                contact_id=serializer.validated_data.get("contact_id"),
                lead_id=serializer.validated_data.get("lead_id"),
            )
        except ValidationError as e:
            return Response({"detail": e.message}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            CallDetailSerializer(call).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["post"])
    def hangup(self, request, pk=None):
        """Hang up an active call."""
        try:
            call = CallService.hangup_call(call_pk=int(pk), user=request.user)
        except NotFoundError as e:
            return Response({"detail": e.message}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(CallDetailSerializer(call).data)

    @action(detail=True, methods=["post"])
    def answer(self, request, pk=None):
        """Answer a ringing call."""
        try:
            call = CallService.answer_call(call_pk=int(pk), user=request.user)
        except NotFoundError as e:
            return Response({"detail": e.message}, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as e:
            return Response({"detail": e.message}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(CallDetailSerializer(call).data)

    @action(detail=True, methods=["get"], url_path="status")
    def call_status(self, request, pk=None):
        """Get current call status with live Asterisk sync."""
        try:
            status_data = CallService.get_call_status(call_pk=int(pk))
        except NotFoundError as e:
            return Response({"detail": e.message}, status=status.HTTP_404_NOT_FOUND)

        return Response(status_data)

    @action(detail=True, methods=["patch"])
    def notes(self, request, pk=None):
        """Update call notes."""
        notes_text = request.data.get("notes", "")

        try:
            call = CallService.update_call_notes(
                call_pk=int(pk), user=request.user, notes=notes_text
            )
        except NotFoundError as e:
            return Response({"detail": e.message}, status=status.HTTP_404_NOT_FOUND)

        return Response(CallDetailSerializer(call).data)

    @action(detail=False, methods=["get"])
    def active(self, request):
        """Get list of currently active calls."""
        calls_data = CallService.get_active_calls(user=request.user)
        return Response({"calls": calls_data})

    @action(detail=True, methods=["post"], url_path="link-contact")
    def link_contact(self, request, pk=None):
        """Link a call to a contact."""
        contact_id = request.data.get("contact_id")
        if not contact_id:
            return Response(
                {"detail": "contact_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            call = CallService.link_call_to_contact(
                call_pk=int(pk), contact_id=int(contact_id)
            )
        except NotFoundError as e:
            return Response({"detail": e.message}, status=status.HTTP_404_NOT_FOUND)

        return Response(CallDetailSerializer(call).data)

    @action(detail=True, methods=["post"], url_path="link-opportunity")
    def link_opportunity(self, request, pk=None):
        """Link a call to an opportunity."""
        lead_id = request.data.get("lead_id")
        if not lead_id:
            return Response(
                {"detail": "lead_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            call = CallService.link_call_to_opportunity(
                call_pk=int(pk), lead_id=int(lead_id)
            )
        except NotFoundError as e:
            return Response({"detail": e.message}, status=status.HTTP_404_NOT_FOUND)

        return Response(CallDetailSerializer(call).data)
