#!/bin/sh
# Replace ARI password placeholder
if [ -n "$ARI_PASSWORD" ]; then
    sed -i "s/ARI_PASSWORD_PLACEHOLDER/$ARI_PASSWORD/g" /etc/asterisk/ari.conf
fi

# Create empty dynamic trunk config if it doesn't exist yet
# (will be populated by the CRM app when user saves SIP settings)
if [ ! -f /etc/asterisk/dynamic/pjsip_trunk.conf ]; then
    mkdir -p /etc/asterisk/dynamic
    echo "; No SIP trunk configured yet. Save credentials in CRM Settings > VoIP." > /etc/asterisk/dynamic/pjsip_trunk.conf
fi

exec "$@"
