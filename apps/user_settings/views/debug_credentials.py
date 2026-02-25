"""
Debug-only view: test all configured third-party credentials.
Only accessible when debug_mode is active in the session.

Each integration runs a series of ordered test cases split into two groups:
  - outgoing: we call them
  - incoming: they call us (webhook / ARI events)

Results use status: ok | warning | error | not_configured | skipped
"""
import hashlib
import hmac
import json
import re
import time

from django.conf import settings as django_settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
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
        el_client = ElevenLabs(api_key=api_key, timeout=10)
    except ImportError:
        outgoing.append(_case("SDK installed", "error", "'elevenlabs' package not installed"))
        return {"label": "ElevenLabs (STT — Scribe)", "overall": "error",
                "outgoing": outgoing, "incoming": None}
    outgoing.append(_case("SDK installed", "ok", "elevenlabs SDK present"))

    # T2 — authenticate: try user.get(); a missing_permissions error means
    # the key IS valid but is scoped to STT only — treat as OK for our purposes.
    key_authenticated = False
    try:
        t0 = time.monotonic()
        user_info = el_client.user.get()
        ms = int((time.monotonic() - t0) * 1000)
        sub = getattr(user_info, "subscription", None)
        tier = getattr(sub, "tier", "unknown") if sub else "unknown"
        used = getattr(sub, "character_count", "?") if sub else "?"
        limit = getattr(sub, "character_limit", "?") if sub else "?"
        outgoing.append(_case(
            "API key authentication",
            "ok",
            f"tier={tier}, chars={used}/{limit}  [{ms}ms]",
        ))
        key_authenticated = True
    except Exception as exc:
        status_code = getattr(exc, "status_code", None)
        body = getattr(exc, "body", None)
        api_status = ""
        if isinstance(body, dict):
            inner = body.get("detail", body)
            if isinstance(inner, dict):
                api_status = inner.get("status", "")
        # missing_permissions = key is valid but STT-only (no user_read scope)
        if api_status == "missing_permissions":
            outgoing.append(_case(
                "API key authentication", "ok",
                "Key valid — STT-only scope (no user_read). This is fine for transcription.",
            ))
            key_authenticated = True
        else:
            # Genuine auth failure
            if isinstance(body, dict):
                inner = body.get("detail", body)
                msg = inner.get("message", str(inner)) if isinstance(inner, dict) else str(inner)
            else:
                msg = str(exc)[:150]
            outgoing.append(_case("API key authentication", "error",
                                  f"Invalid key — {msg}"))
            outgoing.append(_skip("STT model check", "auth failed"))
            return {"label": "ElevenLabs (STT — Scribe)", "overall": "error",
                    "outgoing": outgoing, "incoming": None}

    # T3 — confirm scribe_v2 is reachable (POST with empty body → 422, not 401/403)
    if key_authenticated:
        try:
            import httpx as _httpx
            t0 = time.monotonic()
            r = _httpx.post(
                "https://api.elevenlabs.io/v1/speech-to-text",
                headers={"xi-api-key": api_key},
                timeout=8,
            )
            ms = int((time.monotonic() - t0) * 1000)
            # 422 = unprocessable (missing audio) → endpoint reached & key accepted
            # 200 = shouldn't happen with empty body
            if r.status_code in (200, 422):
                outgoing.append(_case(
                    "STT endpoint reachable", "ok",
                    f"POST /v1/speech-to-text → HTTP {r.status_code} (key accepted)  [{ms}ms]",
                ))
            elif r.status_code in (401, 403):
                detail = r.json().get("detail", {})
                if isinstance(detail, dict):
                    detail = detail.get("message", str(detail))
                outgoing.append(_case("STT endpoint reachable", "error",
                                      f"HTTP {r.status_code} — {detail}"))
            else:
                outgoing.append(_case("STT endpoint reachable", "warning",
                                      f"Unexpected HTTP {r.status_code}"))
        except Exception as exc:
            outgoing.append(_case("STT endpoint reachable", "warning", str(exc)[:100]))

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


def _get_public_base_url() -> tuple:
    """
    Returns (url, source) where url is the public-facing base URL of this server,
    or (None, '') if none can be determined.

    Strategy:
      1. Query the local ngrok API (tries host.docker.internal and common Docker
         bridge gateway IPs) — returns the live HTTPS tunnel URL.
      2. Fall back to the first non-localhost, non-IP entry in ALLOWED_HOSTS.
    """
    import httpx

    # 1 — ngrok local API (port 4040 on the Docker host)
    for host in ("host.docker.internal", "172.17.0.1", "172.18.0.1", "172.19.0.1"):
        try:
            r = httpx.get(f"http://{host}:4040/api/tunnels", timeout=1.5)
            if r.status_code == 200:
                for tunnel in r.json().get("tunnels", []):
                    url = tunnel.get("public_url", "")
                    if url.startswith("https://"):
                        return url.rstrip("/"), f"ngrok API ({host}:4040)"
        except Exception:
            pass

    # 2 — ALLOWED_HOSTS fallback
    for host in django_settings.ALLOWED_HOSTS:
        if host in ("localhost", "127.0.0.1", "0.0.0.0", "*"):
            continue
        if host.startswith("."):
            continue
        if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", host):
            continue
        return f"https://{host}", "ALLOWED_HOSTS"

    return None, ""


def _test_whatsapp_incoming(config, headers: dict, GRAPH: str) -> list:
    """
    Test our ability to receive webhooks from Meta via live HTTP requests
    to the public URL (ngrok or whatever is in ALLOWED_HOSTS).
    """
    import httpx
    tests = []

    # T1 — webhook verify token set
    token = config.webhook_verify_token
    if not token:
        tests.append(_case("Verify token configured", "not_configured", "webhook_verify_token is empty"))
        for n in ["App secret configured", "Public webhook URL",
                  "Webhook verification challenge", "Webhook rejects invalid token",
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

    # T3 — discover the public URL
    public_url, url_source = _get_public_base_url()
    webhook_url = f"{public_url}/messaging/webhook/" if public_url else None

    if not public_url:
        tests.append(_case(
            "Public webhook URL", "error",
            "No public URL found — start ngrok and add its host to ALLOWED_HOSTS",
        ))
        for n in ["Webhook verification challenge", "Webhook rejects invalid token", "Webhook accepts valid POST"]:
            tests.append(_skip(n, "no public URL"))
    else:
        tests.append(_case("Public webhook URL", "ok", f"{webhook_url}  (via {url_source})"))

        # T4 — live webhook verification challenge (correct token → echo challenge)
        challenge = "crm_debug_test_12345"
        try:
            t0 = time.monotonic()
            r = httpx.get(
                webhook_url,
                params={"hub.mode": "subscribe", "hub.verify_token": token, "hub.challenge": challenge},
                timeout=10,
                follow_redirects=True,
            )
            ms = int((time.monotonic() - t0) * 1000)
            if r.status_code == 200 and r.text == challenge:
                tests.append(_case(
                    "Webhook verification challenge", "ok",
                    f"Echoed '{challenge}' through {public_url}  [{ms}ms]",
                ))
            else:
                tests.append(_case(
                    "Webhook verification challenge", "error",
                    f"Expected 200+'{challenge}', got HTTP {r.status_code} body={r.text[:80]!r}  [{ms}ms]",
                ))
        except Exception as exc:
            tests.append(_case("Webhook verification challenge", "error", str(exc)[:150]))

        # T5 — live reject: wrong verify token → 403
        try:
            t0 = time.monotonic()
            r = httpx.get(
                webhook_url,
                params={"hub.mode": "subscribe", "hub.verify_token": "wrong-token-xyz", "hub.challenge": "abc"},
                timeout=10,
                follow_redirects=True,
            )
            ms = int((time.monotonic() - t0) * 1000)
            if r.status_code == 403:
                tests.append(_case(
                    "Webhook rejects invalid token", "ok",
                    f"Correctly returned 403 for wrong verify_token  [{ms}ms]",
                ))
            else:
                tests.append(_case(
                    "Webhook rejects invalid token", "error",
                    f"Expected 403, got HTTP {r.status_code} — security issue!  [{ms}ms]",
                ))
        except Exception as exc:
            tests.append(_case("Webhook rejects invalid token", "error", str(exc)[:150]))

        # T6 — live POST with a minimal payload + correct HMAC signature
        try:
            payload_bytes = json.dumps({"object": "whatsapp_business_account", "entry": []}).encode()
            if config.app_secret:
                sig = "sha256=" + hmac.new(
                    config.app_secret.encode(), payload_bytes, hashlib.sha256
                ).hexdigest()
            else:
                sig = ""
            t0 = time.monotonic()
            r = httpx.post(
                webhook_url,
                content=payload_bytes,
                headers={"Content-Type": "application/json", "X-Hub-Signature-256": sig},
                timeout=10,
                follow_redirects=True,
            )
            ms = int((time.monotonic() - t0) * 1000)
            if r.status_code == 200:
                tests.append(_case(
                    "Webhook accepts valid POST", "ok",
                    f"200 for minimal signed payload through {public_url}  [{ms}ms]",
                ))
            else:
                tests.append(_case(
                    "Webhook accepts valid POST", "warning",
                    f"Got HTTP {r.status_code} (expected 200)  [{ms}ms]",
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
            for n in ["Active channels", "SIP settings in DB", "SIP endpoints registered"]:
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
            tests.append(_case("Active channels (/ari/channels)", "ok",
                                f"{count} active channel(s)  [{ms}ms]"))
        else:
            tests.append(_case("Active channels", "warning",
                                f"HTTP {resp.status_code}: {resp.text[:80]}"))
    except Exception as exc:
        tests.append(_case("Active channels", "warning", str(exc)[:150]))

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

    # T4 — SIP endpoints actually registered with Asterisk right now
    try:
        t0 = time.monotonic()
        resp = httpx.get(f"{ari_url}/ari/endpoints", auth=auth, timeout=6)
        ms = int((time.monotonic() - t0) * 1000)
        if resp.status_code == 200:
            endpoints = resp.json()
            registered = [e for e in endpoints if e.get("state") == "online"]
            offline = [e for e in endpoints if e.get("state") != "online"]
            reg_names = [e.get("resource", "?") for e in registered]
            off_names = [e.get("resource", "?") for e in offline]
            if not endpoints:
                tests.append(_case("SIP endpoints registered", "warning",
                                   f"No SIP endpoints configured in Asterisk  [{ms}ms]"))
            elif not registered:
                tests.append(_case(
                    "SIP endpoints registered", "error",
                    f"0/{len(endpoints)} online — offline: {', '.join(off_names)}  [{ms}ms]",
                ))
            else:
                detail = f"{len(registered)}/{len(endpoints)} online: {', '.join(reg_names)}"
                if off_names:
                    detail += f"  |  offline: {', '.join(off_names)}"
                tests.append(_case("SIP endpoints registered", "ok", f"{detail}  [{ms}ms]"))
        else:
            tests.append(_case("SIP endpoints registered", "warning",
                               f"HTTP {resp.status_code}: {resp.text[:80]}"))
    except Exception as exc:
        tests.append(_case("SIP endpoints registered", "warning", str(exc)[:150]))

    return tests


def _ari_ws_probe(ari_url: str, ari_user: str, ari_pass: str, app_name: str) -> tuple:
    """
    Perform a real WebSocket handshake against the ARI /events endpoint.
    Returns (status, detail) where status is 'ok'|'error'|'warning'.

    Uses a raw TCP socket + manual HTTP Upgrade request so we avoid
    asyncio event-loop conflicts with the running ASGI server.
    """
    import base64
    import os
    import socket

    host_port = ari_url.replace("http://", "").replace("https://", "")
    host, _, port_str = host_port.partition(":")
    port = int(port_str) if port_str else 8088
    path = f"/ari/events?app={app_name}&api_key={ari_user}:{ari_pass}"
    ws_key = base64.b64encode(os.urandom(16)).decode()

    handshake = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        f"Upgrade: websocket\r\n"
        f"Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {ws_key}\r\n"
        f"Sec-WebSocket-Version: 13\r\n"
        f"\r\n"
    )
    try:
        t0 = time.monotonic()
        sock = socket.create_connection((host, port), timeout=5)
        sock.sendall(handshake.encode())
        sock.settimeout(5)
        response = sock.recv(1024).decode("utf-8", errors="replace")
        ms = int((time.monotonic() - t0) * 1000)
        sock.close()
        if "101 Switching Protocols" in response:
            return "ok", f"WebSocket upgrade accepted by Asterisk  [{ms}ms]"
        first_line = response.split("\r\n")[0] if response else "(empty response)"
        return "error", f"Expected 101, got: {first_line}  [{ms}ms]"
    except OSError as exc:
        return "error", f"Cannot connect to {host}:{port} — {exc}"
    except Exception as exc:
        return "warning", str(exc)[:150]


def _test_asterisk_incoming(ari_url: str, auth, ari_user: str, ari_pass: str) -> list:
    """
    Test whether Asterisk can deliver real-time events to the CRM.
    Checks ari-handler connection status and performs a live WebSocket handshake.
    """
    tests = []
    import httpx

    # T1 — is crm-app registered? (only true when ari-handler is actively connected)
    try:
        t0 = time.monotonic()
        resp = httpx.get(f"{ari_url}/ari/applications", auth=auth, timeout=6)
        ms = int((time.monotonic() - t0) * 1000)
        if resp.status_code == 200:
            apps = resp.json()
            app_names = [a.get("name", "") for a in apps]
            if ARI_APP_NAME in app_names:
                tests.append(_case(
                    f"ari-handler connected ('{ARI_APP_NAME}' registered)",
                    "ok",
                    f"App registered — event handler is running  [{ms}ms]",
                ))
            else:
                tests.append(_case(
                    f"ari-handler connected ('{ARI_APP_NAME}' registered)",
                    "error",
                    f"'{ARI_APP_NAME}' not in ARI app list — ari-handler service is not running "
                    f"or its WebSocket is disconnected. Registered: {app_names or 'none'}  [{ms}ms]",
                ))
        else:
            tests.append(_case("ari-handler status", "error",
                                f"HTTP {resp.status_code}: {resp.text[:100]}"))
    except Exception as exc:
        tests.append(_case("ari-handler status", "error", str(exc)[:150]))

    # T2 — live WebSocket handshake using a separate probe app (does not disturb the real handler)
    t0 = time.monotonic()
    ws_status, ws_detail = _ari_ws_probe(ari_url, ari_user, ari_pass, "crm-debug-probe")
    tests.append(_case("ARI WebSocket handshake", ws_status, ws_detail))

    # T3 — crm-app details (only if registered)
    crm_registered = any(
        t["name"].startswith("ari-handler") and t["status"] == "ok" for t in tests
    )
    if crm_registered:
        try:
            t0 = time.monotonic()
            resp = httpx.get(f"{ari_url}/ari/applications/{ARI_APP_NAME}", auth=auth, timeout=6)
            ms = int((time.monotonic() - t0) * 1000)
            if resp.status_code == 200:
                d = resp.json()
                channels = len(d.get("channel_ids", []))
                bridges = len(d.get("bridge_ids", []))
                tests.append(_case(
                    f"'{ARI_APP_NAME}' details",
                    "ok",
                    f"active channels={channels}, bridges={bridges}  [{ms}ms]",
                ))
            else:
                tests.append(_case(f"'{ARI_APP_NAME}' details", "warning",
                                   f"HTTP {resp.status_code}: {resp.text[:80]}"))
        except Exception as exc:
            tests.append(_case(f"'{ARI_APP_NAME}' details", "warning", str(exc)[:150]))
    else:
        tests.append(_skip(f"'{ARI_APP_NAME}' details", "ari-handler not connected"))

    # T4 — working hours: would an inbound call be answered right now?
    try:
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
        import datetime
        from apps.calls.models import SIPSettings

        tz_name = getattr(django_settings, "ASTERISK_TIMEZONE", None) or django_settings.TIME_ZONE or "UTC"
        try:
            tz = ZoneInfo(tz_name)
        except ZoneInfoNotFoundError:
            tz = ZoneInfo("UTC")

        now = datetime.datetime.now(tz)
        day_abbr = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"][now.weekday()]
        current_t = now.time().replace(second=0, microsecond=0)
        time_str = now.strftime("%H:%M")
        tz_label = f"{time_str} {tz_name}"

        sip = SIPSettings.objects.filter(is_active=True).first()
        if not sip or not sip.working_hours_start or not sip.working_hours_end or not sip.working_days:
            tests.append(_case(
                "Working hours (inbound routing)",
                "ok",
                f"No schedule configured — calls accepted any time. Now: {tz_label}",
            ))
        else:
            days = [d.strip() for d in sip.working_days.split(",") if d.strip()]
            start = sip.working_hours_start
            end = sip.working_hours_end
            window = f"{start.strftime('%H:%M')}–{end.strftime('%H:%M')} ({', '.join(d.capitalize() for d in days)})"
            if day_abbr not in days:
                tests.append(_case(
                    "Working hours (inbound routing)", "warning",
                    f"Today ({day_abbr.capitalize()}) is not a working day — inbound calls play non-working message and hang up. "
                    f"Working schedule: {window}. Now: {tz_label}",
                ))
            elif not (start <= current_t <= end):
                tests.append(_case(
                    "Working hours (inbound routing)", "warning",
                    f"Current time {tz_label} is outside working hours — inbound calls play non-working message and hang up. "
                    f"Working schedule: {window}",
                ))
            else:
                tests.append(_case(
                    "Working hours (inbound routing)", "ok",
                    f"Within working hours. Now: {tz_label}, schedule: {window}",
                ))
    except Exception as exc:
        tests.append(_case("Working hours (inbound routing)", "warning", str(exc)[:150]))

    # T5 — SIP trunk registered (inbound calls arrive via trunk)
    try:
        t0 = time.monotonic()
        resp = httpx.get(f"{ari_url}/ari/endpoints/PJSIP/sip-trunk-endpoint", auth=auth, timeout=6)
        ms = int((time.monotonic() - t0) * 1000)
        if resp.status_code == 200:
            state = resp.json().get("state", "?")
            if state == "online":
                tests.append(_case("SIP trunk registered", "ok",
                                   f"sip-trunk-endpoint is online — carrier can deliver calls  [{ms}ms]"))
            else:
                tests.append(_case("SIP trunk registered", "error",
                                   f"sip-trunk-endpoint state={state} — inbound calls cannot arrive  [{ms}ms]"))
        elif resp.status_code == 404:
            tests.append(_case("SIP trunk registered", "warning",
                               f"sip-trunk-endpoint not found in Asterisk — trunk may not be configured  [{ms}ms]"))
        else:
            tests.append(_case("SIP trunk registered", "warning",
                               f"HTTP {resp.status_code}: {resp.text[:80]}"))
    except Exception as exc:
        tests.append(_case("SIP trunk registered", "warning", str(exc)[:150]))

    # T6 — agent endpoint available to receive the forwarded call (dialplan dials PJSIP/100)
    try:
        t0 = time.monotonic()
        resp = httpx.get(f"{ari_url}/ari/endpoints/PJSIP/100", auth=auth, timeout=6)
        ms = int((time.monotonic() - t0) * 1000)
        if resp.status_code == 200:
            state = resp.json().get("state", "?")
            if state == "online":
                tests.append(_case("Agent PJSIP/100 available", "ok",
                                   f"Endpoint 100 is online — will ring when call arrives  [{ms}ms]"))
            else:
                tests.append(_case("Agent PJSIP/100 available", "error",
                                   f"Endpoint 100 state={state} — dialplan will play 'nobody available' and hang up  [{ms}ms]"))
        else:
            tests.append(_case("Agent PJSIP/100 available", "warning",
                               f"HTTP {resp.status_code}: {resp.text[:80]}"))
    except Exception as exc:
        tests.append(_case("Agent PJSIP/100 available", "warning", str(exc)[:150]))

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
        tests_in += _test_asterisk_incoming(ari_url, auth, ari_user, ari_pass)

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
def test_integrations_view(request):
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
    path("test-integrations/", test_integrations_view, name="test_integrations"),
]
