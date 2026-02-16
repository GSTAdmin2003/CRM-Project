from rest_framework import serializers

from ..models import LeadStage


class LeadStageSerializer(serializers.ModelSerializer):
    """Full serializer for stage views."""

    sales_team_name = serializers.CharField(
        source="sales_team.name", read_only=True, default=""
    )
    created_by_name = serializers.CharField(
        source="created_by.get_full_name", read_only=True, default=""
    )
    lead_count = serializers.IntegerField(source="leads.count", read_only=True)

    class Meta:
        model = LeadStage
        fields = [
            "id",
            "name",
            "description",
            "order",
            "color",
            "is_active",
            "is_closed_stage",
            "probability",
            "sales_team",
            "sales_team_name",
            "created_by",
            "created_by_name",
            "lead_count",
            "created_at",
        ]
        read_only_fields = ["id", "created_by", "created_at"]


class LeadStageCreateUpdateSerializer(serializers.Serializer):
    """Write serializer -- delegates to StageService."""

    name = serializers.CharField(max_length=50)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    color = serializers.CharField(max_length=7, required=False, default="#6B7280")
    probability = serializers.IntegerField(required=False, default=0, min_value=0, max_value=100)
    is_closed_stage = serializers.BooleanField(required=False, default=False)
    sales_team_id = serializers.IntegerField()
