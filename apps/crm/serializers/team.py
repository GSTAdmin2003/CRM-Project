from rest_framework import serializers

from ..models import LeadStage, SalesTeam


class SalesTeamListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""

    manager_name = serializers.CharField(
        source="manager.get_full_name", read_only=True, default=""
    )
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = SalesTeam
        fields = ["id", "name", "manager_name", "is_active", "member_count", "created_at"]

    def get_member_count(self, obj):
        return obj.get_team_members().count()


class SalesTeamStageNestedSerializer(serializers.ModelSerializer):
    """Minimal stage serializer for nesting inside team detail."""

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
        ]
        read_only_fields = ["id"]


class SalesTeamMemberSerializer(serializers.Serializer):
    """Serializer for team member representation."""

    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    full_name = serializers.CharField(source="get_full_name", read_only=True)
    email = serializers.EmailField(read_only=True)


class SalesTeamDetailSerializer(serializers.ModelSerializer):
    """Full serializer for detail/retrieve views."""

    manager_name = serializers.CharField(
        source="manager.get_full_name", read_only=True, default=""
    )
    stages = serializers.SerializerMethodField()
    members = serializers.SerializerMethodField()

    class Meta:
        model = SalesTeam
        fields = [
            "id",
            "name",
            "description",
            "manager",
            "manager_name",
            "is_active",
            "stages",
            "members",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_stages(self, obj):
        stages = LeadStage.get_stages_for_team(obj)
        return SalesTeamStageNestedSerializer(stages, many=True).data

    def get_members(self, obj):
        members = obj.get_team_members()
        return SalesTeamMemberSerializer(members, many=True).data


class SalesTeamCreateUpdateSerializer(serializers.Serializer):
    """Write serializer -- delegates to TeamService."""

    name = serializers.CharField(max_length=100)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    manager_id = serializers.IntegerField(required=False, allow_null=True)
    is_active = serializers.BooleanField(required=False, default=True)
