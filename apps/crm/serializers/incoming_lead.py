from rest_framework import serializers

from ..models import IncomingLead


class IncomingLeadListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""

    company_name = serializers.CharField(
        source="company.display_name", read_only=True, default=""
    )
    contact_name = serializers.CharField(source="contact.name", read_only=True, default="")
    assigned_to_name = serializers.CharField(
        source="assigned_to.get_full_name", read_only=True, default=""
    )
    sales_team_name = serializers.CharField(
        source="sales_team.name", read_only=True, default=""
    )

    class Meta:
        model = IncomingLead
        fields = [
            "id",
            "company_name",
            "contact_name",
            "message",
            "status",
            "assigned_to_name",
            "sales_team_name",
            "created_at",
        ]


class IncomingLeadDetailSerializer(serializers.ModelSerializer):
    """Full serializer for detail/retrieve views."""

    company_name = serializers.CharField(
        source="company.display_name", read_only=True, default=""
    )
    contact_name = serializers.CharField(source="contact.name", read_only=True, default="")
    assigned_to_name = serializers.CharField(
        source="assigned_to.get_full_name", read_only=True, default=""
    )
    sales_team_name = serializers.CharField(
        source="sales_team.name", read_only=True, default=""
    )
    created_by_name = serializers.CharField(
        source="created_by.get_full_name", read_only=True, default=""
    )
    converted_opportunity_id = serializers.IntegerField(
        source="converted_opportunity.id", read_only=True, default=None
    )
    converted_opportunity_title = serializers.CharField(
        source="converted_opportunity.title", read_only=True, default=""
    )

    class Meta:
        model = IncomingLead
        fields = [
            "id",
            "company",
            "company_name",
            "contact",
            "contact_name",
            "message",
            "status",
            "notes",
            "sales_team",
            "sales_team_name",
            "assigned_to",
            "assigned_to_name",
            "converted_opportunity_id",
            "converted_opportunity_title",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_by",
            "created_at",
            "updated_at",
        ]


class IncomingLeadCreateSerializer(serializers.Serializer):
    """Write serializer -- delegates to IncomingLeadService."""

    company_id = serializers.IntegerField(required=False, allow_null=True)
    contact_id = serializers.IntegerField(required=False, allow_null=True)
    message = serializers.CharField(required=False, allow_blank=True, default="")
    sales_team_id = serializers.IntegerField(required=False, allow_null=True)
    assigned_to_id = serializers.IntegerField(required=False, allow_null=True)
    status = serializers.ChoiceField(
        choices=IncomingLead.STATUS_CHOICES, required=False, default="new"
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")
