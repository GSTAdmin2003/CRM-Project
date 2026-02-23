from rest_framework import serializers

from ..models import Call, CallLog, CallRecording


class CallRecordingSerializer(serializers.ModelSerializer):
    file_size_formatted = serializers.CharField(read_only=True)

    class Meta:
        model = CallRecording
        fields = ["id", "file", "duration", "file_size", "file_size_formatted", "created_at"]
        read_only_fields = ["id", "file", "duration", "file_size", "created_at"]


class CallLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallLog
        fields = ["id", "event", "data", "timestamp"]
        read_only_fields = ["id", "event", "data", "timestamp"]


class CallListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""

    contact_name = serializers.CharField(source="contact.name", read_only=True, default=None)
    opportunity_title = serializers.CharField(
        source="opportunity.title", read_only=True, default=None
    )
    user_name = serializers.CharField(
        source="user.get_full_name", read_only=True, default=""
    )
    duration_formatted = serializers.CharField(read_only=True)
    has_recording = serializers.SerializerMethodField()
    activity_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Call
        fields = [
            "id",
            "direction",
            "status",
            "from_number",
            "to_number",
            "contact_name",
            "opportunity_title",
            "user_name",
            "duration",
            "duration_formatted",
            "started_at",
            "has_recording",
            "activity_id",
            "created_at",
        ]

    def get_has_recording(self, obj) -> bool:
        return hasattr(obj, "recording") and obj.recording is not None


class CallDetailSerializer(serializers.ModelSerializer):
    """Full serializer for detail/retrieve views."""

    contact_name = serializers.CharField(source="contact.name", read_only=True, default=None)
    contact_id = serializers.IntegerField(source="contact.id", read_only=True, default=None)
    opportunity_title = serializers.CharField(
        source="opportunity.title", read_only=True, default=None
    )
    opportunity_id = serializers.IntegerField(
        source="opportunity.id", read_only=True, default=None
    )
    user_name = serializers.CharField(
        source="user.get_full_name", read_only=True, default=""
    )
    duration_formatted = serializers.CharField(read_only=True)
    recording = CallRecordingSerializer(read_only=True)
    logs = CallLogSerializer(many=True, read_only=True)
    activity_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Call
        fields = [
            "id",
            "asterisk_channel_id",
            "asterisk_uniqueid",
            "direction",
            "status",
            "from_number",
            "to_number",
            "contact_id",
            "contact_name",
            "opportunity_id",
            "opportunity_title",
            "activity_id",
            "user",
            "user_name",
            "duration",
            "duration_formatted",
            "started_at",
            "answered_at",
            "ended_at",
            "notes",
            "recording",
            "logs",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "asterisk_channel_id",
            "asterisk_uniqueid",
            "direction",
            "status",
            "from_number",
            "to_number",
            "user",
            "duration",
            "started_at",
            "answered_at",
            "ended_at",
            "created_at",
            "updated_at",
        ]


class CallCreateSerializer(serializers.Serializer):
    """Write serializer for initiating calls -- delegates to CallService."""

    phone_number = serializers.CharField(max_length=20)
    contact_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    lead_id = serializers.IntegerField(required=False, allow_null=True, default=None)
