import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.messaging.meta_client import (
    check_whatsapp_number,
    get_webhook_verify_token,
    verify_webhook_signature,
)
from apps.messaging.models import WhatsAppConversation, WhatsAppTemplate
from apps.messaging.services import WhatsAppService


@login_required
def inbox(request):
    """WhatsApp inbox — renders Svelte shell."""
    import json
    from django.core.serializers.json import DjangoJSONEncoder

    from apps.user_settings.models import UserPreferences
    user_lang = UserPreferences.get_or_create_for_user(request.user).language
    init_data = {
        'apiUrls': {
            'conversations': '/messaging/api/conversations/',
        },
        'userLanguage': user_lang,
    }
    return render(request, 'messaging/inbox.html', {
        'init_data_json': json.dumps(init_data, cls=DjangoJSONEncoder),
    })


@login_required
def conversation_detail(request, pk):
    conv = get_object_or_404(WhatsAppConversation, pk=pk)
    WhatsAppService.mark_conversation_read(conversation_id=pk)
    messages_qs = conv.messages.order_by("timestamp")
    return render(
        request,
        "messaging/conversation.html",
        {"conv": conv, "messages": messages_qs},
    )


@login_required
def messages_partial(request, pk):
    conv = get_object_or_404(WhatsAppConversation, pk=pk)
    WhatsAppService.mark_conversation_read(conversation_id=pk)
    messages_qs = conv.messages.order_by("timestamp")
    return render(
        request,
        "messaging/messages_partial.html",
        {"messages": messages_qs},
    )


@login_required
@require_POST
def send_message(request, pk):
    body = request.POST.get("body", "").strip()
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    if not body:
        if is_ajax:
            return JsonResponse({"error": "Message cannot be empty."}, status=400)
        messages.warning(request, "Message cannot be empty.")
    else:
        try:
            WhatsAppService.send_message(
                conversation_id=pk, body=body, sent_by=request.user
            )
            if is_ajax:
                return JsonResponse({"success": True})
        except Exception as e:
            if is_ajax:
                return JsonResponse({"error": str(e)}, status=500)
            messages.error(request, f"Failed to send: {e}")
    return redirect("messaging:conversation_detail", pk=pk)



@login_required
def template_variables_api(request, pk):
    """Return template schema as JSON (fallback — Alpine.js uses inline data instead)."""
    template = get_object_or_404(WhatsAppTemplate, pk=pk, is_active=True)
    return JsonResponse(
        {
            "id": template.pk,
            "display_name": template.display_name,
            "body_preview": template.body_preview,
            "variable_names": template.variable_names,
        }
    )


@csrf_exempt
def webhook(request):
    if request.method == "GET":
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")
        if mode == "subscribe" and token == get_webhook_verify_token():
            return HttpResponse(challenge, content_type="text/plain")
        return HttpResponse(status=403)

    if request.method == "POST":
        sig = request.headers.get("X-Hub-Signature-256", "")
        if not settings.DEBUG and not verify_webhook_signature(request.body, sig):
            return HttpResponse(status=403)
        try:
            payload = json.loads(request.body)
            WhatsAppService.handle_webhook_payload(payload)
        except Exception:
            pass  # Always 200 to Meta
        return HttpResponse(status=200)

    return HttpResponse(status=405)


@login_required
@require_POST
def check_whatsapp_phone(request):
    """AJAX: check if a given phone number is registered on WhatsApp.

    Normalizes the number using the system default_country_code setting,
    then checks the local conversation DB first (certain), then falls back to Meta API.
    """
    phone = request.POST.get("phone", "").strip()
    if not phone:
        return JsonResponse({"status": "error", "message": "No phone number provided."})

    # Normalize to E.164 with + prefix (reads default_country_code from SystemConfiguration)
    from core.utils import normalize_phone
    e164 = normalize_phone(phone)           # e.g. "+995571535389"
    digits = e164.lstrip("+")              # e.g. "995571535389" (for DB lookup)

    # 1. Local DB check — if we already have a conversation, number is definitely on WhatsApp
    if WhatsAppConversation.objects.filter(phone_number=digits).exists():
        return JsonResponse({"status": "ok", "has_whatsapp": True, "phone": e164, "source": "local"})

    # 2. Meta API check
    try:
        has_whatsapp = check_whatsapp_number(e164)
        return JsonResponse({"status": "ok", "has_whatsapp": has_whatsapp, "phone": e164, "source": "api"})
    except Exception as exc:
        return JsonResponse({"status": "error", "message": str(exc)})
