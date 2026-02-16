from rest_framework import serializers

from ..models import Company


class CompanyListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""

    display_name = serializers.CharField(read_only=True)
    contacts_count = serializers.IntegerField(source="contacts.count", read_only=True)

    class Meta:
        model = Company
        fields = [
            "id",
            "legal_id",
            "legal_name",
            "brand_name",
            "display_name",
            "industry",
            "category",
            "contacts_count",
            "created_at",
        ]


class CompanyDetailSerializer(serializers.ModelSerializer):
    """Full serializer for detail/retrieve views."""

    display_name = serializers.CharField(read_only=True)
    favorite_contact_name = serializers.CharField(
        source="favorite_contact.name", read_only=True, default=""
    )
    created_by_name = serializers.CharField(
        source="created_by.get_full_name", read_only=True, default=""
    )
    updated_by_name = serializers.CharField(
        source="updated_by.get_full_name", read_only=True, default=""
    )

    class Meta:
        model = Company
        fields = [
            "id",
            "legal_id",
            "legal_name",
            "brand_name",
            "display_name",
            "company_phone",
            "company_mobile",
            "company_email",
            "industry",
            "category",
            "favorite_contact",
            "favorite_contact_name",
            "created_by",
            "created_by_name",
            "updated_by",
            "updated_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "favorite_contact",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]


class CompanyCreateUpdateSerializer(serializers.Serializer):
    """Write serializer -- delegates to CompanyService."""

    legal_id = serializers.CharField(max_length=100)
    legal_name = serializers.CharField(max_length=200)
    brand_name = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")
    company_phone = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")
    company_mobile = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")
    company_email = serializers.EmailField(required=False, allow_blank=True, default="")
    industry = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    category = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
