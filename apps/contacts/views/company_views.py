"""
DRF ViewSets for the Company model.

All business logic is delegated to CompanyService.
"""

from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.exceptions import NotFoundError, ValidationError

from ..models import Company
from ..serializers import (
    CompanyCreateUpdateSerializer,
    CompanyDetailSerializer,
    CompanyListSerializer,
)
from ..services import CompanyService


class CompanyViewSet(viewsets.ModelViewSet):
    """
    CRUD for companies.

    list:    GET    /contacts/api/companies/
    create:  POST   /contacts/api/companies/
    read:    GET    /contacts/api/companies/{id}/
    update:  PUT    /contacts/api/companies/{id}/
    delete:  DELETE /contacts/api/companies/{id}/
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "list":
            return CompanyListSerializer
        if self.action in ("create", "update", "partial_update"):
            return CompanyCreateUpdateSerializer
        return CompanyDetailSerializer

    def get_queryset(self):
        search = self.request.query_params.get("search", "")
        return CompanyService.list_companies(search=search)

    def retrieve(self, request, *args, **kwargs):
        try:
            company = CompanyService.get_company_or_raise(pk=kwargs["pk"])
        except NotFoundError as e:
            return Response({"detail": e.message}, status=status.HTTP_404_NOT_FOUND)

        return Response(CompanyDetailSerializer(company).data)

    def create(self, request, *args, **kwargs):
        serializer = CompanyCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            company = CompanyService.create_company(
                legal_id=serializer.validated_data["legal_id"],
                legal_name=serializer.validated_data["legal_name"],
                brand_name=serializer.validated_data.get("brand_name", ""),
                company_phone=serializer.validated_data.get("company_phone", ""),
                company_mobile=serializer.validated_data.get("company_mobile", ""),
                company_email=serializer.validated_data.get("company_email", ""),
                industry=serializer.validated_data.get("industry", ""),
                category=serializer.validated_data.get("category", ""),
                created_by=request.user,
            )
        except ValidationError as e:
            return Response({"detail": e.message}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            CompanyDetailSerializer(company).data, status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        serializer = CompanyCreateUpdateSerializer(
            data=request.data, partial=kwargs.get("partial", False)
        )
        serializer.is_valid(raise_exception=True)

        update_fields = {}
        allowed = {
            "contact_type", "preferred_language",
            "legal_id", "legal_name", "brand_name",
            "company_phone", "company_mobile", "company_email",
            "industry", "category",
        }
        for field in allowed:
            if field in serializer.validated_data:
                update_fields[field] = serializer.validated_data[field]

        try:
            company = CompanyService.update_company(
                pk=kwargs["pk"], updated_by=request.user, **update_fields
            )
        except NotFoundError as e:
            return Response({"detail": e.message}, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as e:
            return Response({"detail": e.message}, status=status.HTTP_400_BAD_REQUEST)

        return Response(CompanyDetailSerializer(company).data)

    def destroy(self, request, *args, **kwargs):
        try:
            CompanyService.delete_company(pk=kwargs["pk"])
        except NotFoundError as e:
            return Response({"detail": e.message}, status=status.HTTP_404_NOT_FOUND)

        return Response(status=status.HTTP_204_NO_CONTENT)
