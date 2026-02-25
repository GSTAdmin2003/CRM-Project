from rest_framework import serializers

from ..models import Lead, LeadActivity, LeadFile, LeadStage


class LeadStageNestedSerializer(serializers.ModelSerializer):
    """Minimal stage serializer for nesting inside lead serializers."""

    class Meta:
        model = LeadStage
        fields = ["id", "name", "color", "probability", "is_closed_stage"]
        read_only_fields = ["id"]


class LeadActivityNestedSerializer(serializers.ModelSerializer):
    """Minimal activity serializer for nesting inside lead detail."""

    user_name = serializers.CharField(source="user.get_full_name", read_only=True, default="")

    class Meta:
        model = LeadActivity
        fields = [
            "id",
            "activity_type",
            "subject",
            "description",
            "duration",
            "outcome",
            "follow_up_date",
            "user_name",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class LeadFileNestedSerializer(serializers.ModelSerializer):
    """Minimal file serializer for nesting inside lead detail."""

    uploaded_by_name = serializers.CharField(
        source="uploaded_by.get_full_name", read_only=True, default=""
    )

    class Meta:
        model = LeadFile
        fields = ["id", "file", "filename", "description", "uploaded_by_name", "uploaded_at"]
        read_only_fields = ["id", "uploaded_at"]


class LeadListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""

    stage_name = serializers.CharField(source="stage.name", read_only=True, default="")
    assigned_to_name = serializers.CharField(
        source="assigned_to.get_full_name", read_only=True, default=""
    )
    company_name_display = serializers.CharField(
        source="company.display_name", read_only=True, default=""
    )

    class Meta:
        model = Lead
        fields = [
            "id",
            "lead_type",
            "title",
            "company_name",
            "company_name_display",
            "estimated_value",
            "probability",
            "stage_name",
            "assigned_to_name",
            "status",
            "message",
            "created_at",
        ]


class LeadDetailSerializer(serializers.ModelSerializer):
    """Full serializer for detail/retrieve views."""

    stage = LeadStageNestedSerializer(read_only=True)
    activities = LeadActivityNestedSerializer(many=True, read_only=True)
    files = LeadFileNestedSerializer(many=True, read_only=True)
    assigned_to_name = serializers.CharField(
        source="assigned_to.get_full_name", read_only=True, default=""
    )
    created_by_name = serializers.CharField(
        source="created_by.get_full_name", read_only=True, default=""
    )
    contact_full_name = serializers.CharField(read_only=True)
    weighted_value = serializers.FloatField(read_only=True)
    converted_from_id = serializers.IntegerField(
        source="converted_from.id", read_only=True, default=None
    )

    class Meta:
        model = Lead
        fields = [
            "id",
            "lead_type",
            "title",
            "full_name",
            "first_name",
            "last_name",
            "email",
            "phone",
            "company_name",
            "position",
            "message",
            "stage",
            "estimated_value",
            "probability",
            "expected_close_date",
            "source",
            "status",
            "custom_fields",
            "notes",
            "assigned_to",
            "assigned_to_name",
            "sales_team",
            "company",
            "contact",
            "converted_from_id",
            "created_by",
            "created_by_name",
            "contact_full_name",
            "weighted_value",
            "activities",
            "files",
            "created_at",
            "updated_at",
            "last_activity",
        ]
        read_only_fields = [
            "id",
            "created_by",
            "created_at",
            "updated_at",
            "last_activity",
        ]


class LeadCreateUpdateSerializer(serializers.Serializer):
    """Write serializer for opportunities -- delegates to LeadService."""

    title = serializers.CharField(max_length=200)
    full_name = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")
    company_name = serializers.CharField(
        max_length=200, required=False, allow_blank=True, default=""
    )
    position = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    estimated_value = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, default=0
    )
    probability = serializers.IntegerField(required=False, min_value=0, max_value=100)
    expected_close_date = serializers.DateField(required=False, allow_null=True)
    source = serializers.ChoiceField(choices=Lead.SOURCE_CHOICES, required=False, default="other")
    status = serializers.ChoiceField(choices=Lead.STATUS_CHOICES, required=False, default="new")
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    stage_id = serializers.IntegerField(required=False, allow_null=True)
    assigned_to_id = serializers.IntegerField(required=False, allow_null=True)
    company_id = serializers.IntegerField(required=False, allow_null=True)
    contact_id = serializers.IntegerField(required=False, allow_null=True)
    sales_team_id = serializers.IntegerField(required=False, allow_null=True)


class LeadIncomingCreateSerializer(serializers.Serializer):
    """Write serializer for leads -- delegates to LeadService.create_lead()."""

    company_id = serializers.IntegerField(required=False, allow_null=True)
    contact_id = serializers.IntegerField(required=False, allow_null=True)
    message = serializers.CharField(required=False, allow_blank=True, default="")
    sales_team_id = serializers.IntegerField(required=False, allow_null=True)
    assigned_to_id = serializers.IntegerField(required=False, allow_null=True)
    status = serializers.ChoiceField(
        choices=Lead.STATUS_CHOICES, required=False, default="new"
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")
