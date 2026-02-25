"""
Generate Asterisk PJSIP trunk configuration from SIPSettings model
and reload Asterisk when credentials change.

Also handles Music on Hold (MOH) configuration for custom hold music,
and dynamic dialplan generation for welcome sounds / working-hours scheduling.
"""
import glob as _glob
import logging
import os
import re
import shutil
import subprocess

import requests
from django.conf import settings
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)

DYNAMIC_CONFIG_PATH = '/etc/asterisk/dynamic/pjsip_trunk.conf'
MOH_CONFIG_PATH = '/etc/asterisk/dynamic/musiconhold_custom.conf'
CUSTOM_MOH_DIR = '/var/lib/asterisk/custom-moh'
EXTENSIONS_CUSTOM_PATH = '/etc/asterisk/dynamic/extensions_custom.conf'
CUSTOM_SOUNDS_DIR = '/var/lib/asterisk/custom-sounds'


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
            f.flush()
            os.fsync(f.fileno())
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


def restart_asterisk_container():
    """Restart the Asterisk Docker container via Docker API unix socket."""
    import urllib3

    try:
        http = urllib3.HTTPConnectionPool(
            host='localhost', port=None,
            scheme='http+unix',
        )
        # Use requests_unixsocket-style or raw socket
        import socket as _socket
        import http.client

        class DockerConnection(http.client.HTTPConnection):
            def connect(self):
                self.sock = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
                self.sock.connect('/var/run/docker.sock')

        conn = DockerConnection('localhost')
        conn.request('POST', '/v1.41/containers/crmproject-asterisk-1/restart?t=5')
        resp = conn.getresponse()
        if resp.status == 204:
            logger.info("Asterisk container restarted successfully via Docker API")
            return True
        else:
            body = resp.read().decode()
            logger.warning(f"Docker restart returned {resp.status}: {body}")
            return reload_asterisk_pjsip()
    except Exception as e:
        logger.error(f"Failed to restart Asterisk container: {e}")
        return reload_asterisk_pjsip()


def apply_sip_settings(sip_settings=None):
    """
    Full pipeline: write config and restart Asterisk container.
    Called when user saves/deletes SIP credentials.
    """
    written = write_trunk_config(sip_settings)
    if written:
        return restart_asterisk_container()
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
    and reload Asterisk MOH.
    Called when user uploads/removes hold music.

    NOTE: We intentionally do NOT reload res_pjsip.so here because that drops
    the trunk registration and causes inbound calls to fail until re-registration.
    The agent moh_suggest change is picked up on the next PJSIP reload or restart.
    """
    has_custom = sip_settings and sip_settings.hold_music
    moh_class = 'crm-custom' if has_custom else 'default'

    written = write_moh_config(sip_settings)
    if not written:
        return False

    update_agents_moh_suggest(moh_class)
    return reload_asterisk_moh()


# =============================================================================
# Dynamic dialplan generation (welcome sound & working-hours scheduling)
# =============================================================================

def _get_ext(filepath):
    """Return file extension (without dot) from a path or FieldFile."""
    name = filepath if isinstance(filepath, str) else filepath.name
    return name.rsplit('.', 1)[-1].lower() if '.' in name else ''


def _remove_files_by_prefix(directory, prefix):
    """Remove all files in *directory* whose name starts with *prefix*."""
    for path in _glob.glob(os.path.join(directory, f'{prefix}.*')):
        try:
            os.remove(path)
        except OSError:
            pass


def _convert_to_asterisk_wav(src_path, dst_path):
    """
    Convert any audio file to Asterisk-native WAV (8kHz, 16-bit, mono PCM).
    Uses ffmpeg. Falls back to a plain copy if ffmpeg is unavailable.
    """
    try:
        subprocess.run(
            [
                'ffmpeg', '-y', '-i', src_path,
                '-ar', '8000', '-ac', '1', '-sample_fmt', 's16',
                dst_path,
            ],
            capture_output=True, check=True, timeout=30,
        )
        logger.info(f"Converted {src_path} -> {dst_path}")
        return True
    except FileNotFoundError:
        logger.warning("ffmpeg not found, falling back to plain copy")
        shutil.copy2(src_path, dst_path)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"ffmpeg conversion failed: {e.stderr.decode()}")
        return False


def generate_extensions_config(sip_settings):
    """
    Build [from-trunk-ring] dialplan with optional:
    - GotoIfTime() for working-hours gating
    - Playback() for non-working-hours announcement
    - Playback() for welcome greeting

    The dialplan runs entirely inside Asterisk and works independently
    of the Django app or any browser sessions. If no agent is registered,
    Dial() times out and the call hangs up gracefully.
    """
    lines = [
        '; =============================================================================',
        '; Auto-generated inbound call routing from CRM settings',
        '; Do not edit manually - changes will be overwritten.',
        '; =============================================================================',
        '',
        '[from-trunk-ring]',
    ]

    has_schedule = (
        sip_settings.working_hours_start
        and sip_settings.working_hours_end
        and sip_settings.working_days
    )
    has_welcome = bool(sip_settings.welcome_sound)
    has_non_working = bool(sip_settings.non_working_hours_sound)

    priority = 1

    def _add(app_line):
        nonlocal priority
        if priority == 1:
            lines.append(f'exten => s,{priority},{app_line}')
        else:
            lines.append(f' same => n,{app_line}')
        priority += 1

    _add('Answer()')
    _add('NoOp(Inbound call from ${CALLERID(num)})')

    if has_schedule:
        start = sip_settings.working_hours_start.strftime('%H:%M')
        end = sip_settings.working_hours_end.strftime('%H:%M')
        # Asterisk uses & to separate days in GotoIfTime (commas are field separators)
        days = sip_settings.working_days.replace(',', '&')  # "mon&tue&wed&thu&fri"
        _add(f'GotoIfTime({start}-{end},{days},*,*?s,working)')

        # Outside working hours path
        if has_non_working:
            _add(f'Playback({CUSTOM_SOUNDS_DIR}/non_working)')
        _add('Hangup()')

        # Working hours label
        lines.append(f' same => n(working),NoOp(Within working hours)')
        priority += 1

    # Welcome sound (played during working hours, or always if no schedule)
    if has_welcome:
        _add(f'Playback({CUSTOM_SOUNDS_DIR}/welcome)')

    # Dial the agent — m plays MOH to caller while ringing so they always hear sound
    _add('Set(CHANNEL(hangup_handler_push)=hangup-handler,s,1)')
    _add('MixMonitor(${UNIQUEID}.wav,br(${UNIQUEID}-rx.wav)t(${UNIQUEID}-tx.wav))')
    _add('Dial(PJSIP/100,30,m)')

    # After Dial — agent didn't answer or was busy
    _add('NoOp(Dial ended with status ${DIALSTATUS})')

    # Unavailable label — reached when agent not registered or Dial fails
    lines.append(f' same => n(unavail),NoOp(Agent unavailable)')
    priority += 1
    _add('Playback(vm-nobodyavail)')
    _add('Playback(vm-goodbye)')
    _add('Hangup()')

    return '\n'.join(lines) + '\n'


def generate_empty_extensions_config():
    """Default [from-trunk-ring] with no schedule or sounds."""
    return """; Default inbound call routing — no schedule or sounds configured.
[from-trunk-ring]
exten => s,1,Answer()
 same => n,NoOp(Inbound call from ${CALLERID(num)})
 same => n,Set(CHANNEL(hangup_handler_push)=hangup-handler,s,1)
 same => n,MixMonitor(${UNIQUEID}.wav,br(${UNIQUEID}-rx.wav)t(${UNIQUEID}-tx.wav))
 same => n,Dial(PJSIP/100,30,m)
 same => n,NoOp(Dial ended with status ${DIALSTATUS})
 same => n(unavail),NoOp(Agent unavailable)
 same => n,Playback(vm-nobodyavail)
 same => n,Playback(vm-goodbye)
 same => n,Hangup()
"""


def write_extensions_config(sip_settings=None):
    """
    Write extensions_custom.conf and copy sound files to the shared volume.
    If sip_settings is None, writes the default (no schedule) config.
    """
    has_any = sip_settings and (
        sip_settings.welcome_sound
        or sip_settings.non_working_hours_sound
        or sip_settings.working_hours_start
    )

    if has_any:
        content = generate_extensions_config(sip_settings)
    else:
        content = generate_empty_extensions_config()

    try:
        with open(EXTENSIONS_CUSTOM_PATH, 'w') as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        logger.info("Wrote extensions_custom.conf successfully")
    except Exception as e:
        logger.error(f"Failed to write extensions_custom.conf: {e}")
        return False

    # Copy sound files to shared volume
    os.makedirs(CUSTOM_SOUNDS_DIR, exist_ok=True)

    # Welcome sound — always convert to .wav for Asterisk native playback
    _remove_files_by_prefix(CUSTOM_SOUNDS_DIR, 'welcome')
    if sip_settings and sip_settings.welcome_sound:
        try:
            dst = os.path.join(CUSTOM_SOUNDS_DIR, 'welcome.wav')
            _convert_to_asterisk_wav(sip_settings.welcome_sound.path, dst)
        except Exception as e:
            logger.error(f"Failed to copy welcome sound: {e}")
            return False

    # Non-working hours sound — always convert to .wav
    _remove_files_by_prefix(CUSTOM_SOUNDS_DIR, 'non_working')
    if sip_settings and sip_settings.non_working_hours_sound:
        try:
            dst = os.path.join(CUSTOM_SOUNDS_DIR, 'non_working.wav')
            _convert_to_asterisk_wav(sip_settings.non_working_hours_sound.path, dst)
        except Exception as e:
            logger.error(f"Failed to copy non-working hours sound: {e}")
            return False

    return True


def reload_asterisk_dialplan():
    """Tell Asterisk to reload the dialplan (pbx_config) via ARI."""
    ari_url = getattr(settings, 'ASTERISK_ARI_URL', 'http://asterisk:8088')
    ari_user = getattr(settings, 'ASTERISK_ARI_USER', '')
    ari_password = getattr(settings, 'ASTERISK_ARI_PASSWORD', '')

    try:
        response = requests.put(
            f'{ari_url}/ari/asterisk/modules/pbx_config.so',
            auth=HTTPBasicAuth(ari_user, ari_password),
            timeout=10,
        )
        if response.status_code in (200, 204):
            logger.info("Asterisk dialplan reloaded successfully")
            return True
        else:
            logger.warning(
                f"Asterisk dialplan reload returned {response.status_code}: {response.text}"
            )
            return False
    except Exception as e:
        logger.error(f"Failed to reload Asterisk dialplan: {e}")
        return False


def apply_schedule_settings(sip_settings=None):
    """
    Full pipeline: write extensions_custom.conf, copy sound files, reload dialplan.
    Called when user saves/deletes schedule or sound settings.
    """
    written = write_extensions_config(sip_settings)
    if written:
        return reload_asterisk_dialplan()
    return False
