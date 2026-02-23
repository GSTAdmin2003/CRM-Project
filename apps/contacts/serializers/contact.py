from rest_framework import serializers

from ..models import Contact


class ContactListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""

    company_name = serializers.CharField(source="company.display_name", read_only=True)
    is_favorite = serializers.SerializerMethodField()

    class Meta:
        model = Contact
        fields = [
            "id",
            "name",
            "position",
            "email",
            "phone",
            "mobile",
            "preferred_language",
            "company",
            "company_name",
            "is_favorite",
            "created_at",
        ]

    def get_is_favorite(self, obj):
        return obj.company.favorite_contact_id == obj.pk


class ContactDetailSerializer(serializers.ModelSerializer):
    """Full serializer for detail/retrieve views."""

    company_name = serializers.CharField(source="company.display_name", read_only=True)
    is_favorite = serializers.SerializerMethodField()

    class Meta:
        model = Contact
        fields = [
            "id",
            "name",
            "position",
            "email",
            "phone",
            "mobile",
            "preferred_language",
            "company",
            "company_name",
            "is_favorite",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "company", "created_at", "updated_at"]

    def get_is_favorite(self, obj):
        return obj.company.favorite_contact_id == obj.pk


class ContactCreateUpdateSerializer(serializers.Serializer):
    """Write serializer -- delegates to ContactService."""

    company_id = serializers.IntegerField(required=False)
    name = serializers.CharField(max_length=200)
    position = serializers.CharField(max_length=100)
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")
    mobile = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")
    preferred_language = serializers.ChoiceField(
        choices=[('', 'Company Default'), ('en', 'English'), ('ka', 'Georgian')],
        required=False,
        default='',
        allow_blank=True,
    )
