from rest_framework import serializers

from ..models import WhatsAppConversation, WhatsAppMessage, WhatsAppTemplate


class WhatsAppMessageSerializer(serializers.ModelSerializer):
    sent_by_name = serializers.CharField(
        source="sent_by.get_full_name", read_only=True, default=""
    )
    body = serializers.CharField(required=True)

    class Meta:
        model = WhatsAppMessage
        fields = [
            "id",
            "direction",
            "body",
            "status",
            "meta_error_code",
            "meta_error_message",
            "timestamp",
            "sent_by",
            "sent_by_name",
            "wa_message_id",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "direction",
            "status",
            "meta_error_code",
            "meta_error_message",
            "timestamp",
            "sent_by",
            "sent_by_name",
            "wa_message_id",
            "created_at",
        ]


class WhatsAppConversationSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)
    last_message_preview = serializers.CharField(read_only=True)
    contact_name = serializers.CharField(
        source="contact.name", read_only=True, default=""
    )
    lead_title = serializers.CharField(
        source="lead.title", read_only=True, default=""
    )

    class Meta:
        model = WhatsAppConversation
        fields = [
            "id",
            "phone_number",
            "display_name",
            "contact",
            "contact_name",
            "lead",
            "lead_title",
            "last_message_at",
            "unread_count",
            "last_message_preview",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class WhatsAppTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WhatsAppTemplate
        fields = ["id", "display_name", "body_preview", "variable_names", "language"]
        read_only_fields = fields
