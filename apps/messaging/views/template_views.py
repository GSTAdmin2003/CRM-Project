import json

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
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
    """Messaging is only accessible from leads — redirect to opportunities."""
    return redirect('/crm/opportunities/')


@login_required
def conversation_detail(request, pk):
    return redirect('/crm/opportunities/')



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
