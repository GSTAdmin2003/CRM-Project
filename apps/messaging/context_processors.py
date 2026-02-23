from django.db.models import Sum


def whatsapp_unread_count(request):
    if request.user.is_authenticated:
        from apps.messaging.models import WhatsAppConversation

        count = (
            WhatsAppConversation.objects.aggregate(total=Sum("unread_count"))["total"]
            or 0
        )
        return {"wa_unread_count": count}
    return {"wa_unread_count": 0}
