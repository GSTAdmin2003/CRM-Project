def dialpad_context(request):
    """Inject dialpad SIP data into every template for authenticated users."""
    if not request.user.is_authenticated:
        return {}

    agent_extension = getattr(request.user, "extension", None) or "100"
    return {
        "dialpad_ws_url": "ws://localhost:8088/ws",
        "dialpad_sip_extension": agent_extension,
        "dialpad_sip_domain": "localhost",
    }
