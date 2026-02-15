"""
Generate Asterisk PJSIP trunk configuration from SIPSettings model
and reload Asterisk when credentials change.
"""
import logging
import time
import requests
from requests.auth import HTTPBasicAuth
from django.conf import settings

logger = logging.getLogger(__name__)

DYNAMIC_CONFIG_PATH = '/etc/asterisk/dynamic/pjsip_trunk.conf'


def generate_trunk_config(sip_settings):
    """Generate pjsip_trunk.conf content from a SIPSettings instance."""
    return f"""; =============================================================================
; Auto-generated SIP trunk config from CRM settings
; Do not edit manually - changes will be overwritten.
; =============================================================================

[sip-trunk]
type=registration
outbound_auth=sip-trunk-auth
server_uri=sip:{sip_settings.server_ip}
client_uri=sip:{sip_settings.username}@{sip_settings.server_ip}
retry_interval=60

[sip-trunk-auth]
type=auth
auth_type=userpass
username={sip_settings.username}
password={sip_settings.password}

[sip-trunk-endpoint]
type=endpoint
context=from-internal
disallow=all
allow=ulaw
allow=alaw
outbound_auth=sip-trunk-auth
aors=sip-trunk-aor
from_user={sip_settings.username}
from_domain={sip_settings.server_ip}

[sip-trunk-aor]
type=aor
contact=sip:{sip_settings.server_ip}:{sip_settings.server_port}

[sip-trunk-identify]
type=identify
endpoint=sip-trunk-endpoint
match={sip_settings.server_ip}
"""


def generate_empty_config():
    """Generate an empty trunk config (used when credentials are deleted)."""
    return "; No SIP trunk configured. Save credentials in CRM Settings > VoIP.\n"


def write_trunk_config(sip_settings=None):
    """
    Write the pjsip_trunk.conf file to the shared volume.
    If sip_settings is None or inactive, writes an empty config.
    """
    if sip_settings and sip_settings.is_active:
        content = generate_trunk_config(sip_settings)
    else:
        content = generate_empty_config()

    try:
        with open(DYNAMIC_CONFIG_PATH, 'w') as f:
            f.write(content)
        logger.info("Wrote pjsip_trunk.conf successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to write pjsip_trunk.conf: {e}")
        return False


def reload_asterisk_pjsip():
    """Tell Asterisk to reload PJSIP configuration via ARI."""
    ari_url = getattr(settings, 'ASTERISK_ARI_URL', 'http://asterisk:8088')
    ari_user = getattr(settings, 'ASTERISK_ARI_USER', '')
    ari_password = getattr(settings, 'ASTERISK_ARI_PASSWORD', '')

    try:
        # Use ARI to reload the PJSIP module
        response = requests.put(
            f'{ari_url}/ari/asterisk/modules/res_pjsip.so',
            auth=HTTPBasicAuth(ari_user, ari_password),
            timeout=10,
        )
        if response.status_code in (200, 204):
            logger.info("Asterisk PJSIP module reloaded successfully")
            return True
        else:
            logger.warning(f"Asterisk PJSIP reload returned {response.status_code}: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Failed to reload Asterisk PJSIP: {e}")
        return False


def apply_sip_settings(sip_settings=None):
    """
    Full pipeline: write config and reload Asterisk.
    Called when user saves/deletes SIP credentials.
    """
    written = write_trunk_config(sip_settings)
    if written:
        return reload_asterisk_pjsip()
    return False
