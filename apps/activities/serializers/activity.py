from rest_framework import serializers

from ..models import Activity, ActivityType


class ActivityTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityType
        fields = ["id", "name", "icon", "color", "is_active"]
        read_only_fields = ["id"]


class ActivityListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""

    activity_type = ActivityTypeSerializer(read_only=True)
    lead_title = serializers.CharField(source="lead.title", read_only=True)
    assigned_to_name = serializers.CharField(
        source="assigned_to.get_full_name", read_only=True, default=""
    )
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Activity
        fields = [
            "id",
            "title",
            "activity_type",
            "lead_title",
            "scheduled_date",
            "status",
            "assigned_to_name",
            "is_overdue",
            "created_at",
        ]


class ActivityDetailSerializer(serializers.ModelSerializer):
    """Full serializer for detail/retrieve views."""

    activity_type = ActivityTypeSerializer(read_only=True)
    lead_title = serializers.CharField(source="lead.title", read_only=True)
    lead_id = serializers.IntegerField(source="lead.id", read_only=True)
    assigned_to_name = serializers.CharField(
        source="assigned_to.get_full_name", read_only=True, default=""
    )
    created_by_name = serializers.CharField(
        source="created_by.get_full_name", read_only=True, default=""
    )
    is_overdue = serializers.BooleanField(read_only=True)
    call_recording = serializers.SerializerMethodField()

    def get_call_recording(self, obj):
        call = obj.call.first()
        if not call:
            return None
        result = {
            "call_id": call.id,
            "duration": call.duration_formatted,
            "direction": call.direction,
        }
        try:
            rec = call.recording
            result["recording_id"] = rec.id
            result["file_size"] = rec.file_size_formatted
            result["download_url"] = f"/calls/recording/{rec.id}/download/"
        except Exception:
            pass
        return result

    class Meta:
        model = Activity
        fields = [
            "id",
            "title",
            "description",
            "activity_type",
            "lead_id",
            "lead_title",
            "scheduled_date",
            "status",
            "outcome",
            "assigned_to",
            "assigned_to_name",
            "created_by",
            "created_by_name",
            "is_overdue",
            "completed_at",
            "created_at",
            "updated_at",
            "call_recording",
        ]
        read_only_fields = ["id", "created_by", "completed_at", "created_at", "updated_at"]


class ActivityCreateUpdateSerializer(serializers.Serializer):
    """Write serializer — delegates to ActivityService."""

    lead_id = serializers.IntegerField()
    activity_type_id = serializers.IntegerField()
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    scheduled_date = serializers.DateField()
    status = serializers.ChoiceField(
        choices=Activity.STATUS_CHOICES, required=False, default="planned"
    )
    assigned_to_id = serializers.IntegerField(required=False, allow_null=True)
    outcome = serializers.CharField(required=False, allow_blank=True, default="")
