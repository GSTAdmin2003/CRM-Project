FROM alpine:3.20

# Install Asterisk and dependencies
RUN apk add --no-cache \
    asterisk \
    asterisk-sample-config \
    asterisk-sounds-en \
    asterisk-sounds-moh

# Copy configuration files (overwrite defaults)
COPY pjsip.conf /etc/asterisk/pjsip.conf
COPY extensions.conf /etc/asterisk/extensions.conf
COPY ari.conf /etc/asterisk/ari.conf
COPY http.conf /etc/asterisk/http.conf
COPY modules.conf /etc/asterisk/modules.conf

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create recordings directory
RUN mkdir -p /var/spool/asterisk/recording && \
    chown asterisk:asterisk /var/spool/asterisk/recording

EXPOSE 5060/udp 8088 10000-10100/udp

ENTRYPOINT ["/entrypoint.sh"]
CMD ["asterisk", "-f", "-vvv"]
