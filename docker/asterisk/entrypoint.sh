#!/bin/sh
mkdir -p /etc/asterisk/dynamic

# Replace ARI password placeholder
if [ -n "$ARI_PASSWORD" ]; then
    sed -i "s/ARI_PASSWORD_PLACEHOLDER/$ARI_PASSWORD/g" /etc/asterisk/ari.conf
fi

# Create empty dynamic trunk config if it doesn't exist yet
# (will be populated by the CRM app when user saves SIP settings)
if [ ! -f /etc/asterisk/dynamic/pjsip_trunk.conf ]; then
    echo "; No SIP trunk configured yet. Save credentials in CRM Settings > VoIP." > /etc/asterisk/dynamic/pjsip_trunk.conf
fi

# Create default WebRTC agent extensions (100-104) if not already present.
# Password defaults to WEBRTC_AGENT_PASSWORD env var or 'changeme'.
if [ ! -f /etc/asterisk/dynamic/pjsip_agents.conf ]; then
    AGENT_PASS="${WEBRTC_AGENT_PASSWORD:-changeme}"
    cat > /etc/asterisk/dynamic/pjsip_agents.conf <<EOF
; =============================================================================
; Auto-generated WebRTC agent extensions
; =============================================================================

$(for ext in 100 101 102 103 104; do
cat <<EXTEOF
[$ext]
type=endpoint
transport=transport-ws
context=from-internal
disallow=all
allow=ulaw
allow=alaw
webrtc=yes
dtls_auto_generate_cert=yes
dtls_verify=no
direct_media=no
rtp_symmetric=yes
force_rport=yes
rewrite_contact=yes
from_domain=localhost
auth=$ext-auth
aors=$ext

[$ext-auth]
type=auth
auth_type=userpass
username=$ext
password=$AGENT_PASS

[$ext]
type=aor
max_contacts=1
remove_existing=yes

EXTEOF
done)
EOF
    echo "Created default agent extensions 100-104"
fi

exec "$@"
