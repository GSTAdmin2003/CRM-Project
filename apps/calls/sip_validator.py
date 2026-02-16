"""
SIP credential validator — tests credentials against a SIP server
by attempting a REGISTER transaction with digest authentication.
"""
import hashlib
import logging
import random
import re
import socket
import string
import uuid

logger = logging.getLogger(__name__)

SOCKET_TIMEOUT = 5  # seconds


def _generate_branch():
    return f"z9hG4bK{''.join(random.choices(string.ascii_lowercase + string.digits, k=12))}"


def _generate_tag():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))


def _build_register(server_ip, server_port, username, call_id, branch, tag,
                    cseq=1, auth_header=None):
    """Build a SIP REGISTER request."""
    uri = f"sip:{server_ip}"
    lines = [
        f"REGISTER {uri} SIP/2.0",
        f"Via: SIP/2.0/UDP 0.0.0.0:5060;branch={branch}",
        f"From: <sip:{username}@{server_ip}>;tag={tag}",
        f"To: <sip:{username}@{server_ip}>",
        f"Call-ID: {call_id}",
        f"CSeq: {cseq} REGISTER",
        "Max-Forwards: 70",
        f"Contact: <sip:{username}@0.0.0.0:5060>",
        "Expires: 0",
        "Content-Length: 0",
    ]
    if auth_header:
        lines.insert(-1, auth_header)
    return "\r\n".join(lines) + "\r\n\r\n"


def _parse_www_authenticate(response_text):
    """Extract realm and nonce from WWW-Authenticate header."""
    match = re.search(r'WWW-Authenticate:\s*Digest\s+(.*)', response_text, re.IGNORECASE)
    if not match:
        return None, None
    header = match.group(1)
    realm_m = re.search(r'realm="([^"]*)"', header)
    nonce_m = re.search(r'nonce="([^"]*)"', header)
    return (realm_m.group(1) if realm_m else None,
            nonce_m.group(1) if nonce_m else None)


def _compute_digest(username, password, realm, nonce, uri):
    """Compute SIP digest authentication response (RFC 2617)."""
    ha1 = hashlib.md5(f"{username}:{realm}:{password}".encode()).hexdigest()
    ha2 = hashlib.md5(f"REGISTER:{uri}".encode()).hexdigest()
    return hashlib.md5(f"{ha1}:{nonce}:{ha2}".encode()).hexdigest()


def _get_response_code(text):
    match = re.match(r'SIP/2\.0\s+(\d+)', text)
    return int(match.group(1)) if match else None


def validate_sip_credentials(server_ip, server_port, username, password):
    """
    Test SIP credentials by sending a REGISTER request with digest auth.

    Returns:
        (is_valid: bool, error_message: str | None)
    """
    server_port = int(server_port)
    call_id = str(uuid.uuid4())
    branch = _generate_branch()
    tag = _generate_tag()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(SOCKET_TIMEOUT)

    try:
        # Step 1: initial REGISTER (no auth) — expect 401/407 challenge
        req = _build_register(server_ip, server_port, username, call_id,
                              branch, tag, cseq=1)
        sock.sendto(req.encode(), (server_ip, server_port))

        try:
            data, _ = sock.recvfrom(4096)
            resp = data.decode('utf-8', errors='replace')
        except socket.timeout:
            return False, "SIP server not responding. Check server IP and port."

        code = _get_response_code(resp)
        if code is None:
            return False, "Invalid response from SIP server."
        if code == 200:
            return True, None
        if code not in (401, 407):
            return False, f"SIP server returned unexpected response ({code})."

        # Step 2: parse challenge, compute digest, send authenticated REGISTER
        realm, nonce = _parse_www_authenticate(resp)
        if not realm or not nonce:
            return False, "Could not parse SIP authentication challenge."

        uri = f"sip:{server_ip}"
        digest = _compute_digest(username, password, realm, nonce, uri)
        auth = (
            f'Authorization: Digest username="{username}", realm="{realm}", '
            f'nonce="{nonce}", uri="{uri}", response="{digest}", algorithm=MD5'
        )

        branch2 = _generate_branch()
        req2 = _build_register(server_ip, server_port, username, call_id,
                               branch2, tag, cseq=2, auth_header=auth)
        sock.sendto(req2.encode(), (server_ip, server_port))

        try:
            data2, _ = sock.recvfrom(4096)
            resp2 = data2.decode('utf-8', errors='replace')
        except socket.timeout:
            return False, "SIP server did not respond to authentication."

        code2 = _get_response_code(resp2)
        if code2 == 200:
            return True, None
        elif code2 in (401, 403):
            return False, "Invalid SIP username or password."
        else:
            return False, f"SIP authentication failed (code {code2})."

    except socket.gaierror:
        return False, f"Cannot resolve hostname: {server_ip}"
    except ConnectionRefusedError:
        return False, f"Connection refused by {server_ip}:{server_port}"
    except OSError as e:
        return False, f"Network error: {e}"
    finally:
        sock.close()
