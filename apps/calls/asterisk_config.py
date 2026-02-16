"""
Generate Asterisk PJSIP trunk configuration from SIPSettings model
and reload Asterisk when credentials change.

Also handles Music on Hold (MOH) configuration for custom hold music.
"""
import logging
import os
import re
import shutil

import requests
from django.conf import settings
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)

DYNAMIC_CONFIG_PATH = '/etc/asterisk/dynamic/pjsip_trunk.conf'
MOH_CONFIG_PATH = '/etc/asterisk/dynamic/musiconhold_custom.conf'
CUSTOM_MOH_DIR = '/var/lib/asterisk/custom-moh'


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
context=from-trunk
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


# =============================================================================
# Music on Hold (MOH) configuration
# =============================================================================

def generate_moh_config():
    """Generate musiconhold_custom.conf with a [crm-custom] class."""
    return """; =============================================================================
; Auto-generated custom Music on Hold config from CRM settings
; Do not edit manually - changes will be overwritten.
; =============================================================================

[crm-custom]
mode=files
directory=/var/lib/asterisk/custom-moh
"""


def generate_empty_moh_config():
    """Generate an empty MOH config (no custom hold music)."""
    return "; No custom hold music configured.\n"


def write_moh_config(sip_settings=None):
    """
    Write musiconhold_custom.conf and copy the audio file to the shared volume.
    If sip_settings has no hold_music, writes an empty config.
    """
    has_custom = sip_settings and sip_settings.hold_music

    if has_custom:
        content = generate_moh_config()
    else:
        content = generate_empty_moh_config()

    try:
        with open(MOH_CONFIG_PATH, 'w') as f:
            f.write(content)
        logger.info("Wrote musiconhold_custom.conf successfully")
    except Exception as e:
        logger.error(f"Failed to write musiconhold_custom.conf: {e}")
        return False

    if has_custom:
        try:
            os.makedirs(CUSTOM_MOH_DIR, exist_ok=True)

            # Clear old files from the custom MOH directory
            for existing in os.listdir(CUSTOM_MOH_DIR):
                os.remove(os.path.join(CUSTOM_MOH_DIR, existing))

            # Copy the uploaded file
            src = sip_settings.hold_music.path
            filename = os.path.basename(src)
            dst = os.path.join(CUSTOM_MOH_DIR, filename)
            shutil.copy2(src, dst)
            logger.info(f"Copied hold music to {dst}")
        except Exception as e:
            logger.error(f"Failed to copy hold music file: {e}")
            return False

    return True


def reload_asterisk_moh():
    """Tell Asterisk to reload the Music on Hold module via ARI."""
    ari_url = getattr(settings, 'ASTERISK_ARI_URL', 'http://asterisk:8088')
    ari_user = getattr(settings, 'ASTERISK_ARI_USER', '')
    ari_password = getattr(settings, 'ASTERISK_ARI_PASSWORD', '')

    try:
        response = requests.put(
            f'{ari_url}/ari/asterisk/modules/res_musiconhold.so',
            auth=HTTPBasicAuth(ari_user, ari_password),
            timeout=10,
        )
        if response.status_code in (200, 204):
            logger.info("Asterisk MOH module reloaded successfully")
            return True
        else:
            logger.warning(
                f"Asterisk MOH reload returned {response.status_code}: {response.text}"
            )
            return False
    except Exception as e:
        logger.error(f"Failed to reload Asterisk MOH: {e}")
        return False


AGENTS_CONFIG_PATH = '/etc/asterisk/dynamic/pjsip_agents.conf'


def update_agents_moh_suggest(moh_class):
    """
    Update moh_suggest= in the existing pjsip_agents.conf.
    Replaces any moh_suggest= line with the new value.
    """
    try:
        with open(AGENTS_CONFIG_PATH, 'r') as f:
            content = f.read()

        updated = re.sub(
            r'^moh_suggest=.*$',
            f'moh_suggest={moh_class}',
            content,
            flags=re.MULTILINE,
        )

        with open(AGENTS_CONFIG_PATH, 'w') as f:
            f.write(updated)
        logger.info(f"Updated agent endpoints moh_suggest to {moh_class}")
        return True
    except Exception as e:
        logger.error(f"Failed to update agents moh_suggest: {e}")
        return False


def apply_moh_settings(sip_settings=None):
    """
    Full pipeline: write MOH config, copy audio file, update agent endpoints,
    and reload Asterisk MOH + PJSIP.
    Called when user uploads/removes hold music.
    """
    has_custom = sip_settings and sip_settings.hold_music
    moh_class = 'crm-custom' if has_custom else 'default'

    written = write_moh_config(sip_settings)
    if not written:
        return False

    update_agents_moh_suggest(moh_class)
    reload_asterisk_pjsip()
    return reload_asterisk_moh()
