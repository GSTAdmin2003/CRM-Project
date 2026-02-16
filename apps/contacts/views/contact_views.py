"""
DRF ViewSets for the Contact model.

All business logic is delegated to ContactService.
"""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.exceptions import NotFoundError, ValidationError

from ..models import Contact
from ..serializers import (
    ContactCreateUpdateSerializer,
    ContactDetailSerializer,
    ContactListSerializer,
)
from ..services import ContactService


class ContactViewSet(viewsets.ModelViewSet):
    """
    CRUD for contacts.

    list:    GET    /contacts/api/contacts/                 -- optionally ?company_id=X
    create:  POST   /contacts/api/contacts/
    read:    GET    /contacts/api/contacts/{id}/
    update:  PUT    /contacts/api/contacts/{id}/
    delete:  DELETE /contacts/api/contacts/{id}/
    toggle_favorite: POST /contacts/api/contacts/{id}/toggle-favorite/
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "list":
            return ContactListSerializer
        if self.action in ("create", "update", "partial_update"):
            return ContactCreateUpdateSerializer
        return ContactDetailSerializer

    def get_queryset(self):
        qs = Contact.objects.select_related("company").all()
        company_id = self.request.query_params.get("company_id")
        if company_id:
            qs = qs.filter(company_id=company_id)
        return qs

    def retrieve(self, request, *args, **kwargs):
        try:
            contact = ContactService.get_contact_or_raise(pk=kwargs["pk"])
        except NotFoundError as e:
            return Response({"detail": e.message}, status=status.HTTP_404_NOT_FOUND)

        return Response(ContactDetailSerializer(contact).data)

    def create(self, request, *args, **kwargs):
        serializer = ContactCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        company_id = serializer.validated_data.get("company_id")
        if not company_id:
            return Response(
                {"detail": "company_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            contact = ContactService.create_contact(
                company_pk=company_id,
                name=serializer.validated_data["name"],
                position=serializer.validated_data["position"],
                email=serializer.validated_data.get("email", ""),
                phone=serializer.validated_data.get("phone", ""),
                mobile=serializer.validated_data.get("mobile", ""),
            )
        except NotFoundError as e:
            return Response({"detail": e.message}, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as e:
            return Response({"detail": e.message}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            ContactDetailSerializer(contact).data, status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        serializer = ContactCreateUpdateSerializer(
            data=request.data, partial=kwargs.get("partial", False)
        )
        serializer.is_valid(raise_exception=True)

        update_fields = {}
        allowed = {"name", "position", "email", "phone", "mobile"}
        for field in allowed:
            if field in serializer.validated_data:
                update_fields[field] = serializer.validated_data[field]

        try:
            contact = ContactService.update_contact(pk=kwargs["pk"], **update_fields)
        except NotFoundError as e:
            return Response({"detail": e.message}, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as e:
            return Response({"detail": e.message}, status=status.HTTP_400_BAD_REQUEST)

        return Response(ContactDetailSerializer(contact).data)

    def destroy(self, request, *args, **kwargs):
        try:
            ContactService.delete_contact(pk=kwargs["pk"])
        except NotFoundError as e:
            return Response({"detail": e.message}, status=status.HTTP_404_NOT_FOUND)

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="toggle-favorite")
    def toggle_favorite(self, request, pk=None):
        """Toggle whether this contact is the company's favorite."""
        try:
            contact = ContactService.get_contact_or_raise(pk=pk)
        except NotFoundError as e:
            return Response({"detail": e.message}, status=status.HTTP_404_NOT_FOUND)

        try:
            result = ContactService.toggle_favorite(
                company_pk=contact.company_id, contact_pk=int(pk)
            )
        except NotFoundError as e:
            return Response({"detail": e.message}, status=status.HTTP_404_NOT_FOUND)

        return Response(result)
