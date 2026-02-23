import hashlib
import hmac
import os

import requests

RESUMABLE_UPLOAD_BASE = "https://rupload.facebook.com/whatsapp-business-upload"

GRAPH_API_BASE = "https://graph.facebook.com/v21.0"


def _get_config():
    """Lazy-import to avoid circular imports at module load time."""
    from apps.messaging.models.wa_config import WhatsAppConfig

    return WhatsAppConfig.get_config()


def send_text_message(to_number: str, body: str) -> dict:
    """POST to Meta Cloud API. Returns response JSON. Raises on HTTP error."""
    config = _get_config()
    if not config or not config.is_configured():
        raise ValueError(
            "WhatsApp is not configured. Go to Settings → WhatsApp to add your credentials."
        )
    url = f"{GRAPH_API_BASE}/{config.phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {config.access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": body},
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.json()


def send_template_message(
    to_number: str,
    template_name: str,
    language_code: str,
    variables: list,
    document_media_id: str = "",
    document_filename: str = "",
) -> dict:
    """POST a template message to Meta Cloud API. Returns response JSON. Raises on HTTP error.

    Optionally includes a document header component when document_media_id is supplied.
    """
    config = _get_config()
    if not config or not config.is_configured():
        raise ValueError(
            "WhatsApp is not configured. Go to Settings → WhatsApp to add your credentials."
        )
    language_code = _LANGUAGE_TO_LOCALE.get(language_code, language_code)
    url = f"{GRAPH_API_BASE}/{config.phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {config.access_token}",
        "Content-Type": "application/json",
    }
    components = []
    if document_media_id:
        components.append({
            "type": "header",
            "parameters": [{
                "type": "document",
                "document": {
                    "id": document_media_id,
                    "filename": document_filename or "document.pdf",
                },
            }],
        })
    if variables:
        components.append({
            "type": "body",
            "parameters": [{"type": "text", "text": v} for v in variables],
        })
    template_payload: dict = {
        "name": template_name,
        "language": {"code": language_code},
    }
    if components:
        template_payload["components"] = components
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "template",
        "template": template_payload,
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.json()


def upload_media(file_path: str, mime_type: str, filename: str) -> str:
    """Upload a media file to Meta and return the media_id.

    POST to /v21.0/{phone_number_id}/media as multipart/form-data.
    Raises ValueError if not configured. Raises requests.HTTPError on failure.
    """
    config = _get_config()
    if not config or not config.is_configured():
        raise ValueError(
            "WhatsApp is not configured. Go to Settings → WhatsApp to add your credentials."
        )
    url = f"{GRAPH_API_BASE}/{config.phone_number_id}/media"
    headers = {"Authorization": f"Bearer {config.access_token}"}
    with open(file_path, "rb") as fh:
        files = {
            "file": (filename, fh, mime_type),
            "type": (None, mime_type),
            "messaging_product": (None, "whatsapp"),
        }
        resp = requests.post(url, headers=headers, files=files, timeout=30)
    resp.raise_for_status()
    return resp.json()["id"]


# Map short language codes to Meta locale codes
_LANGUAGE_TO_LOCALE = {
    "en": "en_US",
    "ka": "ka",
}


def fetch_template_statuses(waba_id: str) -> dict:
    """Fetch current approval statuses for all templates in the WABA.

    Returns a dict keyed by (name, locale) → lowercase status string.
    e.g. {("sales_pitch", "en_US"): "approved", ("sales_pitch", "ka_GE"): "pending"}

    Raises ValueError if WhatsApp is not configured or the API call fails.
    """
    config = _get_config()
    if not config or not config.is_configured():
        raise ValueError(
            "WhatsApp is not configured. Go to Settings → WhatsApp to add your credentials."
        )
    results = {}
    url = f"{GRAPH_API_BASE}/{waba_id}/message_templates"
    params = {"fields": "name,language,status", "limit": 100}
    headers = {"Authorization": f"Bearer {config.access_token}"}

    while url:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        if not resp.ok:
            try:
                msg = resp.json().get("error", {}).get("message", resp.text)
            except Exception:
                msg = resp.text
            raise ValueError(f"Meta API error {resp.status_code}: {msg}")
        data = resp.json()
        for t in data.get("data", []):
            key = (t.get("name", ""), t.get("language", ""))
            results[key] = t.get("status", "").lower()
        # Handle pagination
        url = data.get("paging", {}).get("next")
        params = {}  # next URL already includes params

    return results


def _get_meta_template_id(waba_id: str, template_name: str, locale: str) -> str:
    """Return Meta's internal template ID for the given name+locale, or '' if not found.

    Tries both the exact locale and the bare language prefix (e.g. 'ka' matches 'ka_GE')
    so that templates created via Meta Business Suite with a slightly different locale code
    are still found and can be deleted before resubmission.
    """
    config = _get_config()
    resp = requests.get(
        f"{GRAPH_API_BASE}/{waba_id}/message_templates",
        params={"name": template_name, "fields": "id,name,language,status"},
        headers={"Authorization": f"Bearer {config.access_token}"},
        timeout=10,
    )
    if not resp.ok:
        raise ValueError(
            f"Failed to look up existing template '{template_name}' on Meta "
            f"(HTTP {resp.status_code}): {resp.text}"
        )
    # Build candidate locales: exact match + bare language prefix (e.g. "ka" ↔ "ka_GE")
    lang_prefix = locale.split("_")[0]
    candidates = {locale, lang_prefix}
    for t in resp.json().get("data", []):
        t_lang = t.get("language", "")
        if t_lang == locale or t_lang.split("_")[0] == lang_prefix:
            return t.get("id", "")
    return ""


def _delete_meta_template(waba_id: str, template_id: str, template_name: str) -> None:
    """Delete a specific template variant from Meta by its internal ID."""
    config = _get_config()
    resp = requests.delete(
        f"{GRAPH_API_BASE}/{waba_id}/message_templates",
        params={"hsm_id": template_id, "name": template_name},
        headers={"Authorization": f"Bearer {config.access_token}"},
        timeout=10,
    )
    if not resp.ok:
        raise ValueError(f"Failed to delete existing Meta template: {resp.text}")


def upload_template_media_handle(file_path: str, mime_type: str, filename: str) -> str:
    """Upload a sample media file for use in template header examples.

    Uses Meta's Resumable Upload API:
      1. POST /{waba_id}/uploads  →  upload session ID
      2. POST rupload.facebook.com/…/{session_id}  →  header handle "4::…"

    Returns the handle string for use in template component example.header_handle.
    Raises ValueError on any API failure.
    """
    config = _get_config()
    if not config or not config.is_configured():
        raise ValueError("WhatsApp is not configured.")
    if not config.app_id:
        raise ValueError("App ID not set. Add it in Settings → WhatsApp → Configuration.")

    file_size = os.path.getsize(file_path)

    # Step 1: create upload session (requires App ID, not WABA ID)
    session_resp = requests.post(
        f"{GRAPH_API_BASE}/{config.app_id}/uploads",
        params={
            "file_length": file_size,
            "file_type": mime_type,
            "file_name": filename,
            "upload_session_type": "WA_MESSAGE_TEMPLATE_MEDIA",
            "access_token": config.access_token,
        },
        timeout=15,
    )
    if not session_resp.ok:
        raise ValueError(f"Upload session failed: {session_resp.text}")
    session_id = session_resp.json()["id"]

    # Step 2: upload file bytes to graph.facebook.com/{version}/{session-id}
    with open(file_path, "rb") as fh:
        file_bytes = fh.read()
    upload_resp = requests.post(
        f"{GRAPH_API_BASE}/{session_id}",
        headers={
            "Authorization": f"OAuth {config.access_token}",
            "file_offset": "0",
            "Content-Type": mime_type,
        },
        data=file_bytes,
        timeout=60,
    )
    if not upload_resp.ok:
        raise ValueError(f"File upload failed: {upload_resp.text}")
    handle = upload_resp.json().get("h")
    if not handle:
        raise ValueError(f"No handle returned by Meta upload: {upload_resp.text}")
    return handle


def submit_template_for_approval(
    waba_id: str,
    template_name: str,
    language: str,
    body_text: str,
    header_file_path: str = "",
    header_filename: str = "",
) -> dict:
    """Submit a WhatsApp template to Meta for approval.

    If header_file_path is provided, uploads the file as the DOCUMENT header example
    so Meta can approve the template with the document component included.

    POST to /v21.0/{waba_id}/message_templates.
    Returns the full Meta response JSON.
    Raises ValueError with Meta's error message on failure.
    """
    import re

    config = _get_config()
    if not config or not config.is_configured():
        raise ValueError(
            "WhatsApp is not configured. Go to Settings → WhatsApp to add your credentials."
        )
    locale = _LANGUAGE_TO_LOCALE.get(language, language)

    # Delete any existing Meta template for this name+locale before resubmitting.
    # Meta rejects submissions (2388049) if the template already exists — even in PENDING state.
    import time

    existing_id = _get_meta_template_id(waba_id, template_name, locale)
    if existing_id:
        _delete_meta_template(waba_id, existing_id, template_name)
        # Give Meta a moment to process the deletion before resubmitting.
        time.sleep(3)

    url = f"{GRAPH_API_BASE}/{waba_id}/message_templates"
    auth_headers = {
        "Authorization": f"Bearer {config.access_token}",
        "Content-Type": "application/json",
    }

    placeholders = re.findall(r"\{\{\d+\}\}", body_text)
    body_component: dict = {"type": "BODY", "text": body_text}
    if placeholders:
        body_component["example"] = {"body_text": [["Sample Value"] * len(placeholders)]}

    components = []
    if header_file_path and os.path.isfile(header_file_path):
        handle = upload_template_media_handle(
            header_file_path, "application/pdf", header_filename or "sample.pdf"
        )
        components.append({
            "type": "HEADER",
            "format": "DOCUMENT",
            "example": {"header_handle": [handle]},
        })
    components.append(body_component)

    payload = {
        "name": template_name,
        "language": locale,
        "category": "UTILITY",
        "allow_category_change": True,
        "components": components,
    }
    resp = requests.post(url, json=payload, headers=auth_headers, timeout=15)
    if not resp.ok:
        try:
            err = resp.json()
            error_obj = err.get("error", {})
            msg = (
                f"{error_obj.get('message', resp.text)} "
                f"(code={error_obj.get('code')}, "
                f"error_subcode={error_obj.get('error_subcode')}, "
                f"fbtrace_id={error_obj.get('fbtrace_id')})"
            )
        except Exception:
            msg = resp.text
        raise ValueError(f"Meta API error {resp.status_code}: {msg}")
    return resp.json()


def normalize_phone_for_whatsapp(phone: str, default_country_code: str = "") -> str:
    """Normalize a phone number to E.164 digits-only format for Meta API.

    Examples (default_country_code="995"):
      "+995571535389" → "995571535389"
      "00995571535389" → "995571535389"
      "0571535389"    → "995571535389"  (strip leading 0, prepend cc)
      "571535389"     → "995571535389"  (prepend cc)
      "995571535389"  → "995571535389"  (already has cc, untouched)
    """
    phone = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")

    if phone.startswith("+"):
        return phone[1:]  # Already E.164

    if phone.startswith("00"):
        return phone[2:]  # International with 00 prefix

    if not default_country_code:
        return phone  # No cc to apply

    cc = default_country_code.lstrip("+").lstrip("0").strip()
    if not cc:
        return phone

    if phone.startswith(cc):
        return phone  # Already contains country code

    if phone.startswith("0"):
        return cc + phone[1:]  # Local format with trunk prefix

    return cc + phone  # Bare local number — prepend cc


def check_whatsapp_number(phone: str) -> bool:
    """Check if a phone number is registered on WhatsApp via Meta Cloud API contacts endpoint.

    Returns True if the number is a valid WhatsApp user, False otherwise.
    Raises ValueError if WhatsApp is not configured or if the API call fails.
    """
    config = _get_config()
    if not config or not config.is_configured():
        raise ValueError(
            "WhatsApp is not configured. Go to Settings → WhatsApp to add your credentials."
        )
    normalized = phone.lstrip("+").strip()
    url = f"{GRAPH_API_BASE}/{config.phone_number_id}/contacts"
    headers = {
        "Authorization": f"Bearer {config.access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "blocking": "wait_for_result",
        "contacts": [f"+{normalized}"],
        "force_check": True,
        "type": "whatsapp",
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=15)
    if not resp.ok:
        try:
            err = resp.json().get("error", {})
            msg = err.get("message", resp.text)
        except Exception:
            msg = resp.text
        raise ValueError(f"Meta API error {resp.status_code}: {msg}")
    contacts = resp.json().get("contacts", [])
    return bool(contacts and contacts[0].get("status") == "valid")


def verify_webhook_signature(payload_bytes: bytes, x_hub_signature: str) -> bool:
    """Validate HMAC-SHA256 signature from Meta webhook."""
    config = _get_config()
    secret = config.app_secret if config else ""
    if not secret:
        return False
    expected = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", x_hub_signature or "")


def get_webhook_verify_token() -> str:
    """Return the configured webhook verify token."""
    config = _get_config()
    return config.webhook_verify_token if config else "crm-webhook-token"
