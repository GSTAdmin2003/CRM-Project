from rest_framework import serializers


class KanbanLeadSerializer(serializers.Serializer):
    """Serializer for a lead card on the kanban board."""

    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    company_name = serializers.CharField(read_only=True)
    estimated_value = serializers.CharField(read_only=True)
    probability = serializers.IntegerField(read_only=True)
    assigned_to = serializers.CharField(read_only=True)
    created_at = serializers.CharField(read_only=True)
    last_activity = serializers.CharField(read_only=True)
    unread_message_count = serializers.IntegerField(read_only=True)


class KanbanStageInfoSerializer(serializers.Serializer):
    """Serializer for stage metadata on the kanban board."""

    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    color = serializers.CharField(read_only=True)
    probability = serializers.IntegerField(read_only=True)


class KanbanStageSerializer(serializers.Serializer):
    """Serializer for a kanban stage with its nested leads."""

    stage = KanbanStageInfoSerializer(read_only=True)
    leads = KanbanLeadSerializer(many=True, read_only=True)
    total_value = serializers.FloatField(read_only=True)
    count = serializers.IntegerField(read_only=True)


class KanbanDataSerializer(serializers.Serializer):
    """Serializer for the full kanban board data."""

    stages = KanbanStageSerializer(many=True, read_only=True)


class UpdateLeadStageSerializer(serializers.Serializer):
    """Write serializer for updating a lead's stage via kanban drag-and-drop."""

    stage_id = serializers.IntegerField()
