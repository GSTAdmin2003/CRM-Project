from .template_views import (
    active_calls,
    answer_call,
    call_status,
    hangup_call,
    initiate_call,
    link_call_to_contact,
    link_call_to_opportunity,
    recording_download,
    register_inbound_call,
    sip_settings_view,
    update_call_notes,
)

__all__ = [
    "initiate_call",
    "register_inbound_call",
    "hangup_call",
    "answer_call",
    "call_status",
    "update_call_notes",
    "link_call_to_contact",
    "link_call_to_opportunity",
    "recording_download",
    "active_calls",
    "sip_settings_view",
]
