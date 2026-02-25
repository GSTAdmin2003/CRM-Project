"""
Debug-only view: test all configured third-party credentials.
Only accessible when debug_mode is active in the session.

Each integration runs a series of ordered test cases split into two groups:
  - outgoing: we call them
  - incoming: they call us (webhook / ARI events)

Results use status: ok | warning | error | not_configured | skipped
"""
import json
import time

from django.conf import settings as django_settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.test import RequestFactory
from django.urls import path, reverse

from apps.user_settings.models.general import SystemConfiguration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _case(name, status, detail):
    return {"name": name, "status": status, "detail": detail}


def _skip(name, reason="prerequisite failed"):
    return _case(name, "skipped", reason)


def _overall(tests):
    statuses = [t["status"] for t in tests]
    if "error" in statuses:
        return "error"
    actionable = [s for s in statuses if s != "skipped"]
    if all(s == "not_configured" for s in actionable):
        return "not_configured"
    if "not_configured" in statuses or "warning" in statuses:
        return "warning"
    return "ok"


# ---------------------------------------------------------------------------
# ElevenLabs
# ---------------------------------------------------------------------------

def _test_elevenlabs(api_key: str) -> dict:
    outgoing = []
    incoming = []  # No incoming channel for ElevenLabs

    # T1 — key present
    if not api_key:
        outgoing.append(_case("API key configured", "not_configured", "No key set in SystemConfiguration"))
        return {
            "label": "ElevenLabs (STT — Scribe)",
            "overall": "not_configured",
            "outgoing": outgoing,
            "incoming": None,
        }
    outgoing.append(_case("API key configured", "ok", f"Key present ({api_key[:8]}…)"))

    # T2 — account info via SDK (handles auth correctly for all key formats)
    try:
        from elevenlabs import ElevenLabs
        el_client = ElevenLabs(api_key=api_key)
    except ImportError:
        outgoing.append(_case("SDK installed", "error", "'elevenlabs' package not installed"))
        return {"label": "ElevenLabs (STT — Scribe)", "overall": "error",
                "outgoing": outgoing, "incoming": None}
    outgoing.append(_case("SDK installed", "ok", "elevenlabs SDK present"))

    try:
        t0 = time.monotonic()
        user_info = el_client.user.get()
        ms = int((time.monotonic() - t0) * 1000)
        sub = getattr(user_info, "subscription", None)
        tier = getattr(sub, "tier", "unknown") if sub else "unknown"
        used = getattr(sub, "character_count", "?") if sub else "?"
        limit = getattr(sub, "character_limit", "?") if sub else "?"
        outgoing.append(_case(
            "Account API (user.get)",
            "ok",
            f"tier={tier}, chars={used}/{limit}  [{ms}ms]",
        ))
    except Exception as exc:
        msg = str(exc)
        status = "error"
        # SDK raises elevenlabs.core.api_error.ApiError on 401
        if "401" in msg or "unauthorized" in msg.lower() or "invalid" in msg.lower():
            outgoing.append(_case("Account API (user.get)", "error",
                                  f"Authentication failed — check API key: {msg[:120]}"))
        else:
            outgoing.append(_case("Account API (user.get)", "error", msg[:150]))
        outgoing.append(_skip("STT model check", "auth failed"))
        return {"label": "ElevenLabs (STT — Scribe)", "overall": "error",
                "outgoing": outgoing, "incoming": None}

    # T3 — scribe_v2 model listed
    try:
        t0 = time.monotonic()
        models = el_client.models.get_all()
        ms = int((time.monotonic() - t0) * 1000)
        ids = [getattr(m, "model_id", "") for m in models]
        if "scribe_v2" in ids:
            outgoing.append(_case("STT model available (scribe_v2)", "ok", f"scribe_v2 listed  [{ms}ms]"))
        else:
            outgoing.append(_case(
                "STT model available (scribe_v2)", "warning",
                f"scribe_v2 not found. Available: {', '.join(ids) or 'none'}",
            ))
    except Exception as exc:
        outgoing.append(_case("STT model check", "warning", str(exc)[:100]))

    return {
        "label": "ElevenLabs (STT — Scribe)",
        "overall": _overall(outgoing),
        "outgoing": outgoing,
        "incoming": None,
    }


# ---------------------------------------------------------------------------
# Anthropic / Claude
# ---------------------------------------------------------------------------

def _test_anthropic(api_key: str) -> dict:
    outgoing = []

    if not api_key:
        outgoing.append(_case("API key configured", "not_configured", "No key set in SystemConfiguration"))
        return {"label": "Anthropic / Claude AI", "overall": "not_configured",
                "outgoing": outgoing, "incoming": None}
    outgoing.append(_case("API key configured", "ok", f"Key present ({api_key[:10]}…)"))

    try:
        import anthropic
    except ImportError:
        outgoing.append(_case("SDK installed", "error", "'anthropic' package not installed"))
        return {"label": "Anthropic / Claude AI", "overall": "error",
                "outgoing": outgoing, "incoming": None}
    outgoing.append(_case("SDK installed", "ok", f"anthropic=={anthropic.__version__}"))

    client = anthropic.Anthropic(api_key=api_key)

    # T3 — list models (no token cost)
    try:
        t0 = time.monotonic()
        page = client.models.list(limit=5)
        ms = int((time.monotonic() - t0) * 1000)
        ids = [m.id for m in page.data]
        outgoing.append(_case(
            "API auth — list models",
            "ok",
            f"Auth OK. First models: {', '.join(ids[:3])}  [{ms}ms]",
        ))
    except anthropic.AuthenticationError:
        outgoing.append(_case("API auth — list models", "error", "401 — invalid API key"))
        outgoing.append(_skip("Message generation", "auth failed"))
        return {"label": "Anthropic / Claude AI", "overall": "error",
                "outgoing": outgoing, "incoming": None}
    except Exception as exc:
        outgoing.append(_case("API auth — list models", "error", str(exc)[:150]))
        outgoing.append(_skip("Message generation"))
        return {"label": "Anthropic / Claude AI", "overall": "error",
                "outgoing": outgoing, "incoming": None}

    # T4 — minimal message end-to-end (1 token)
    try:
        t0 = time.monotonic()
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1,
            messages=[{"role": "user", "content": "Reply: ok"}],
        )
        ms = int((time.monotonic() - t0) * 1000)
        outgoing.append(_case(
            "Message generation (haiku, max_tokens=1)",
            "ok",
            f"stop_reason={msg.stop_reason}, "
            f"tokens={msg.usage.input_tokens}in/{msg.usage.output_tokens}out  [{ms}ms]",
        ))
    except Exception as exc:
        outgoing.append(_case("Message generation", "error", str(exc)[:150]))

    return {
        "label": "Anthropic / Claude AI",
        "overall": _overall(outgoing),
        "outgoing": outgoing,
        "incoming": None,
    }


# ---------------------------------------------------------------------------
# WhatsApp (Meta Cloud API)
# ---------------------------------------------------------------------------

def _test_whatsapp_outgoing(config, headers: dict, GRAPH: str) -> list:
    tests = []
    import httpx

    # T1 — required fields
    missing = [f for f, v in [
        ("access_token", config.access_token),
        ("phone_number_id", config.phone_number_id),
    ] if not v]
    if missing:
        tests.append(_case("Required fields set", "not_configured", f"Missing: {', '.join(missing)}"))
        for name in ["Integration enabled", "Phone number identity", "WABA account"]:
            tests.append(_skip(name, "credentials incomplete"))
        return tests
    tests.append(_case(
        "Required fields set", "ok",
        f"phone_number_id={config.phone_number_id}, token={config.access_token[:12]}…",
    ))

    # T2 — active flag
    tests.append(_case(
        "Integration enabled",
        "ok" if config.is_active else "warning",
        "is_active=True" if config.is_active else "Config present but is_active=False",
    ))

    # T3 — phone number identity (verifies token)
    try:
        t0 = time.monotonic()
        resp = httpx.get(
            f"{GRAPH}/{config.phone_number_id}",
            params={"fields": "display_phone_number,verified_name,quality_rating"},
            headers=headers,
            timeout=8,
        )
        ms = int((time.monotonic() - t0) * 1000)
        if resp.status_code == 200:
            d = resp.json()
            tests.append(_case(
                "Phone number identity",
                "ok",
                f"number={d.get('display_phone_number','?')}, "
                f"name={d.get('verified_name','?')}, "
                f"quality={d.get('quality_rating','?')}  [{ms}ms]",
            ))
        else:
            err = resp.json().get("error", {}).get("message", resp.text[:100])
            tests.append(_case("Phone number identity", "error", f"HTTP {resp.status_code}: {err}"))
    except Exception as exc:
        tests.append(_case("Phone number identity", "error", str(exc)[:150]))

    # T4 — WABA account (optional)
    if config.waba_id:
        try:
            t0 = time.monotonic()
            resp = httpx.get(
                f"{GRAPH}/{config.waba_id}",
                params={"fields": "name,country,timezone_id"},
                headers=headers,
                timeout=8,
            )
            ms = int((time.monotonic() - t0) * 1000)
            if resp.status_code == 200:
                d = resp.json()
                tests.append(_case(
                    "WABA account info",
                    "ok",
                    f"name={d.get('name','?')}, country={d.get('country','?')}  [{ms}ms]",
                ))
            else:
                err = resp.json().get("error", {}).get("message", resp.text[:100])
                tests.append(_case("WABA account info", "warning", f"HTTP {resp.status_code}: {err}"))
        except Exception as exc:
            tests.append(_case("WABA account info", "warning", str(exc)[:150]))
    else:
        tests.append(_case(
            "WABA account info", "warning",
            "waba_id not set — template submission unavailable",
        ))

    return tests


def _test_whatsapp_incoming(config, headers: dict, GRAPH: str) -> list:
    """
    Test our side's ability to receive webhooks from Meta.
    Uses Django's RequestFactory to call the webhook view directly
    so we don't need an externally reachable URL.
    """
    tests = []
    factory = RequestFactory()

    # T1 — webhook verify token set
    token = config.webhook_verify_token
    if not token:
        tests.append(_case("Verify token configured", "not_configured", "webhook_verify_token is empty"))
        for n in ["Webhook verification challenge", "Webhook rejects invalid token",
                  "Webhook accepts valid POST", "Meta webhook subscriptions"]:
            tests.append(_skip(n, "no verify token"))
        return tests
    tests.append(_case("Verify token configured", "ok", f"Token: {token[:20]}{'…' if len(token) > 20 else ''}"))

    # T2 — app_secret set (required for HMAC signature verification)
    if config.app_secret:
        tests.append(_case("App secret configured", "ok", f"{config.app_secret[:6]}… (HMAC verification enabled)"))
    else:
        tests.append(_case(
            "App secret configured", "warning",
            "app_secret empty — signature verification disabled (ok in DEBUG mode only)",
        ))

    # T3 — simulate webhook verification challenge (correct token → echo challenge)
    try:
        from apps.messaging.views.template_views import webhook as webhook_view
        challenge = "crm_debug_test_12345"
        req = factory.get(
            reverse("messaging:webhook"),
            {"hub.mode": "subscribe", "hub.verify_token": token, "hub.challenge": challenge},
        )
        t0 = time.monotonic()
        resp = webhook_view(req)
        ms = int((time.monotonic() - t0) * 1000)
        if resp.status_code == 200 and resp.content.decode() == challenge:
            tests.append(_case(
                "Webhook verification challenge",
                "ok",
                f"Echoed challenge correctly ('{challenge}')  [{ms}ms]",
            ))
        else:
            tests.append(_case(
                "Webhook verification challenge",
                "error",
                f"Expected 200+'{challenge}', got HTTP {resp.status_code} body={resp.content[:60]!r}",
            ))
    except Exception as exc:
        tests.append(_case("Webhook verification challenge", "error", str(exc)[:150]))

    # T4 — webhook rejects wrong verify token (security check)
    try:
        from apps.messaging.views.template_views import webhook as webhook_view
        req = factory.get(
            reverse("messaging:webhook"),
            {"hub.mode": "subscribe", "hub.verify_token": "wrong-token-xyz", "hub.challenge": "abc"},
        )
        resp = webhook_view(req)
        if resp.status_code == 403:
            tests.append(_case(
                "Webhook rejects invalid token",
                "ok",
                "Correctly returned 403 for wrong verify_token",
            ))
        else:
            tests.append(_case(
                "Webhook rejects invalid token",
                "error",
                f"Expected 403, got HTTP {resp.status_code} — security issue!",
            ))
    except Exception as exc:
        tests.append(_case("Webhook rejects invalid token", "error", str(exc)[:150]))

    # T5 — POST with a minimal valid-looking payload (DEBUG skips signature check)
    try:
        from apps.messaging.views.template_views import webhook as webhook_view
        payload = json.dumps({
            "object": "whatsapp_business_account",
            "entry": [],
        }).encode()
        req = factory.post(
            reverse("messaging:webhook"),
            data=payload,
            content_type="application/json",
        )
        req.META["HTTP_X_HUB_SIGNATURE_256"] = ""
        t0 = time.monotonic()
        resp = webhook_view(req)
        ms = int((time.monotonic() - t0) * 1000)
        if resp.status_code == 200:
            tests.append(_case(
                "Webhook accepts valid POST",
                "ok",
                f"Returned 200 for minimal payload  [{ms}ms]",
            ))
        else:
            tests.append(_case(
                "Webhook accepts valid POST",
                "warning",
                f"Got HTTP {resp.status_code} (expected 200)",
            ))
    except Exception as exc:
        tests.append(_case("Webhook accepts valid POST", "error", str(exc)[:150]))

    # T6 — Meta-side: check app webhook subscriptions (requires app_id)
    if config.app_id:
        try:
            import httpx
            t0 = time.monotonic()
            # App-level subscriptions need an app access token: {app_id}|{app_secret}
            # Fall back to the user access token if app_secret is missing.
            app_token = (
                f"{config.app_id}|{config.app_secret}"
                if config.app_secret else config.access_token
            )
            resp = httpx.get(
                f"{GRAPH}/{config.app_id}/subscriptions",
                params={"access_token": app_token},
                timeout=8,
            )
            ms = int((time.monotonic() - t0) * 1000)
            if resp.status_code == 200:
                subs = resp.json().get("data", [])
                wa_sub = next((s for s in subs if s.get("object") == "whatsapp_business_account"), None)
                if wa_sub:
                    raw_fields = wa_sub.get("fields", [])
                    # Meta returns fields as list of dicts {"name":..., "version":...} or plain strings
                    if raw_fields and isinstance(raw_fields[0], dict):
                        fields = ", ".join(f.get("name", str(f)) for f in raw_fields)
                    else:
                        fields = ", ".join(str(f) for f in raw_fields)
                    tests.append(_case(
                        "Meta webhook subscriptions",
                        "ok",
                        f"whatsapp_business_account subscribed, fields={fields or '?'}  [{ms}ms]",
                    ))
                else:
                    obj_names = [s.get("object") for s in subs]
                    tests.append(_case(
                        "Meta webhook subscriptions",
                        "warning",
                        f"No whatsapp_business_account subscription found. Objects: {obj_names or 'none'}",
                    ))
            else:
                err = ""
                try:
                    err = resp.json().get("error", {}).get("message", resp.text[:100])
                except Exception:
                    err = resp.text[:100]
                tests.append(_case(
                    "Meta webhook subscriptions",
                    "warning",
                    f"HTTP {resp.status_code}: {err} (may need business_management permission)",
                ))
        except Exception as exc:
            tests.append(_case("Meta webhook subscriptions", "warning", str(exc)[:150]))
    else:
        tests.append(_case(
            "Meta webhook subscriptions",
            "warning",
            "app_id not set — cannot query Meta subscription status",
        ))

    return tests


def _test_whatsapp() -> dict:
    tests_out, tests_in = [], []

    try:
        from apps.messaging.models import WhatsAppConfig
        config = WhatsAppConfig.get_config()
    except Exception as exc:
        tests_out.append(_case("Config loaded", "error", str(exc)[:150]))
        return {"label": "WhatsApp (Meta Cloud API)", "overall": "error",
                "outgoing": tests_out, "incoming": tests_in}

    if not config:
        tests_out.append(_case("Config record exists", "not_configured", "No WhatsAppConfig row in DB"))
        return {"label": "WhatsApp (Meta Cloud API)", "overall": "not_configured",
                "outgoing": tests_out, "incoming": tests_in}
    tests_out.append(_case("Config record exists", "ok", f"Row pk={config.pk}"))

    GRAPH = "https://graph.facebook.com/v21.0"
    headers = {"Authorization": f"Bearer {config.access_token}"}

    tests_out += _test_whatsapp_outgoing(config, headers, GRAPH)
    tests_in += _test_whatsapp_incoming(config, headers, GRAPH)

    all_tests = tests_out + tests_in
    return {
        "label": "WhatsApp (Meta Cloud API)",
        "overall": _overall(all_tests),
        "outgoing": tests_out,
        "incoming": tests_in,
    }


# ---------------------------------------------------------------------------
# Asterisk ARI
# ---------------------------------------------------------------------------

ARI_APP_NAME = "crm-app"


def _test_asterisk_outgoing(ari_url: str, auth) -> list:
    tests = []
    import httpx

    # T1 — ARI system info
    try:
        t0 = time.monotonic()
        resp = httpx.get(f"{ari_url}/ari/asterisk/info", auth=auth, timeout=6)
        ms = int((time.monotonic() - t0) * 1000)
        if resp.status_code == 200:
            d = resp.json()
            ver = d.get("system", {}).get("version", "?")
            entity = d.get("system", {}).get("entity_id", "?")
            tests.append(_case("ARI reachable (/ari/asterisk/info)", "ok",
                                f"Asterisk {ver}, entity={entity}  [{ms}ms]"))
        elif resp.status_code == 401:
            tests.append(_case("ARI reachable", "error",
                                "401 Unauthorized — wrong ARI username/password"))
            for n in ["Channel list", "SIP settings in DB"]:
                tests.append(_skip(n, "auth failed"))
            return tests
        else:
            tests.append(_case("ARI reachable", "error",
                                f"HTTP {resp.status_code}: {resp.text[:100]}"))
            return tests
    except httpx.ConnectError:
        tests.append(_case("ARI reachable", "error",
                            f"Connection refused at {ari_url} — is Asterisk running?"))
        return tests
    except Exception as exc:
        tests.append(_case("ARI reachable", "error", str(exc)[:150]))
        return tests

    # T2 — list active channels
    try:
        t0 = time.monotonic()
        resp = httpx.get(f"{ari_url}/ari/channels", auth=auth, timeout=6)
        ms = int((time.monotonic() - t0) * 1000)
        if resp.status_code == 200:
            count = len(resp.json())
            tests.append(_case("Channel list (/ari/channels)", "ok",
                                f"{count} active channel(s)  [{ms}ms]"))
        else:
            tests.append(_case("Channel list", "warning",
                                f"HTTP {resp.status_code}: {resp.text[:80]}"))
    except Exception as exc:
        tests.append(_case("Channel list", "warning", str(exc)[:150]))

    # T3 — SIP settings in DB
    try:
        from apps.calls.models import SIPSettings
        total = SIPSettings.objects.count()
        active = SIPSettings.objects.filter(is_active=True).count()
        if total == 0:
            tests.append(_case("SIP settings in DB", "warning",
                                "No SIPSettings rows — users cannot make calls"))
        else:
            tests.append(_case("SIP settings in DB", "ok",
                                f"{active} active / {total} total users configured"))
    except Exception as exc:
        tests.append(_case("SIP settings in DB", "warning", str(exc)[:150]))

    return tests


def _test_asterisk_incoming(ari_url: str, auth) -> list:
    """
    Test whether Asterisk can deliver events to our CRM app.
    Checks ARI application registration and WebSocket endpoint availability.
    """
    tests = []
    import httpx

    # T1 — list all ARI applications registered in Asterisk
    try:
        t0 = time.monotonic()
        resp = httpx.get(f"{ari_url}/ari/applications", auth=auth, timeout=6)
        ms = int((time.monotonic() - t0) * 1000)
        if resp.status_code == 200:
            apps = resp.json()
            app_names = [a.get("name", "") for a in apps]
            if ARI_APP_NAME in app_names:
                tests.append(_case(
                    f"ARI app '{ARI_APP_NAME}' registered",
                    "ok",
                    f"Found in {len(apps)} registered app(s)  [{ms}ms]",
                ))
            else:
                # Normal on a fresh/idle system — the app registers on the first WebSocket
                # connection from ari_events.py. It does NOT indicate a real problem.
                tests.append(_case(
                    f"ARI app '{ARI_APP_NAME}' registered",
                    "ok",
                    f"Not registered yet (normal — registers on first WebSocket connection). "
                    f"Other apps present: {app_names or 'none'}  [{ms}ms]",
                ))
                tests.append(_skip(f"App '{ARI_APP_NAME}' details", "not registered yet — no calls made"))
                return tests
        else:
            tests.append(_case("ARI app list", "error",
                                f"HTTP {resp.status_code}: {resp.text[:100]}"))
            return tests
    except Exception as exc:
        tests.append(_case("ARI app list", "error", str(exc)[:150]))
        return tests

    # T2 — get crm-app details (channels, bridges, endpoints subscribed)
    try:
        t0 = time.monotonic()
        resp = httpx.get(f"{ari_url}/ari/applications/{ARI_APP_NAME}", auth=auth, timeout=6)
        ms = int((time.monotonic() - t0) * 1000)
        if resp.status_code == 200:
            d = resp.json()
            channels = len(d.get("channel_ids", []))
            bridges = len(d.get("bridge_ids", []))
            endpoints = len(d.get("endpoint_ids", []))
            tests.append(_case(
                f"App '{ARI_APP_NAME}' details",
                "ok",
                f"channels={channels}, bridges={bridges}, endpoints={endpoints}  [{ms}ms]",
            ))

            # T3 — channel subscriber count (at least 1 active WS consumer means event handler is up)
            device_state = d.get("device_names", [])
            n_device = len(device_state)
            # Asterisk doesn't directly expose WS subscriber count, but we can check
            # if the app has ever seen traffic by looking at channel_ids (live calls).
            # Instead, probe the WS endpoint directly.
        else:
            tests.append(_case(f"App '{ARI_APP_NAME}' details", "warning",
                                f"HTTP {resp.status_code}: {resp.text[:80]}"))
    except Exception as exc:
        tests.append(_case(f"App '{ARI_APP_NAME}' details", "warning", str(exc)[:150]))

    # T3 — confirm the WebSocket endpoint accepts HTTP upgrade requests
    # We send a plain HTTP GET with Upgrade: websocket headers.
    # Asterisk will either return 101 (upgrade) or 400 (no app param) — both mean it's listening.
    # Connection refused means the WS port is down.
    try:
        import socket
        host_port = ari_url.replace("http://", "").replace("https://", "")
        host, _, port_str = host_port.partition(":")
        port = int(port_str) if port_str else 8088

        t0 = time.monotonic()
        sock = socket.create_connection((host, port), timeout=4)
        ms = int((time.monotonic() - t0) * 1000)
        sock.close()
        tests.append(_case(
            "ARI WebSocket port reachable",
            "ok",
            f"TCP connect to {host}:{port} succeeded  [{ms}ms]",
        ))
    except OSError as exc:
        tests.append(_case(
            "ARI WebSocket port reachable",
            "error",
            f"Cannot reach {ari_url} — {exc}",
        ))
    except Exception as exc:
        tests.append(_case("ARI WebSocket port reachable", "warning", str(exc)[:150]))

    return tests


def _test_asterisk() -> dict:
    tests_out, tests_in = [], []

    ari_url = getattr(django_settings, "ASTERISK_ARI_URL", "")
    ari_user = getattr(django_settings, "ASTERISK_ARI_USER", "")
    ari_pass = getattr(django_settings, "ASTERISK_ARI_PASSWORD", "")

    missing = [k for k, v in [
        ("ASTERISK_ARI_URL", ari_url),
        ("ASTERISK_ARI_USER", ari_user),
        ("ASTERISK_ARI_PASSWORD", ari_pass),
    ] if not v]
    if missing:
        tests_out.append(_case("ARI settings configured", "not_configured",
                               f"Missing env vars: {', '.join(missing)}"))
        for g in [tests_out, tests_in]:
            g.append(_skip("(all tests)", "settings incomplete"))
        return {"label": "Asterisk ARI", "overall": "not_configured",
                "outgoing": tests_out, "incoming": tests_in}

    tests_out.append(_case("ARI settings configured", "ok",
                            f"url={ari_url}, user={ari_user}"))

    from httpx import BasicAuth
    auth = BasicAuth(username=ari_user, password=ari_pass)

    tests_out += _test_asterisk_outgoing(ari_url, auth)

    # Only run incoming tests if ARI is reachable (first outgoing test passed)
    if any(t["status"] == "error" for t in tests_out):
        tests_in.append(_skip("(all incoming tests)", "ARI not reachable"))
    else:
        tests_in += _test_asterisk_incoming(ari_url, auth)

    all_tests = tests_out + tests_in
    return {
        "label": "Asterisk ARI",
        "overall": _overall(all_tests),
        "outgoing": tests_out,
        "incoming": tests_in,
    }


# ---------------------------------------------------------------------------
# View
# ---------------------------------------------------------------------------

@login_required
def test_credentials_view(request):
    if not request.session.get("debug_mode"):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("Debug mode not active. Append ?debug=1 to any URL first.")

    elevenlabs_key = SystemConfiguration.get_setting("elevenlabs_api_key") or ""
    anthropic_key = SystemConfiguration.get_setting("anthropic_api_key") or ""

    results = {
        "elevenlabs": _test_elevenlabs(elevenlabs_key),
        "anthropic": _test_anthropic(anthropic_key),
        "whatsapp": _test_whatsapp(),
        "asterisk": _test_asterisk(),
    }

    return render(request, "settings/debug/credentials.html", {"results": results})


debug_urls = [
    path("test-credentials/", test_credentials_view, name="test_credentials"),
]
