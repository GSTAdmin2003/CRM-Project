from django.contrib import admin

from apps.messaging.models import WhatsAppConfig, WhatsAppConversation, WhatsAppMessage


@admin.register(WhatsAppConfig)
class WhatsAppConfigAdmin(admin.ModelAdmin):
    list_display = ("phone_number_id", "is_active", "updated_at")
    readonly_fields = ("updated_at",)


@admin.register(WhatsAppConversation)
class WhatsAppConversationAdmin(admin.ModelAdmin):
    list_display = ("phone_number", "contact", "lead", "unread_count", "last_message_at")
    list_filter = ("last_message_at",)
    search_fields = ("phone_number",)
    raw_id_fields = ("contact", "lead")


@admin.register(WhatsAppMessage)
class WhatsAppMessageAdmin(admin.ModelAdmin):
    list_display = ("conversation", "direction", "status", "timestamp", "sent_by")
    list_filter = ("direction", "status")
    search_fields = ("body", "wa_message_id")
    raw_id_fields = ("conversation", "sent_by")
