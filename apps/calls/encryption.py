import base64
import hashlib
from django.conf import settings

from cryptography.fernet import Fernet


def _get_fernet_key():
    """Derive a Fernet key from Django's SECRET_KEY."""
    key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return base64.urlsafe_b64encode(key)


def encrypt(plain_text):
    """Encrypt a string and return the ciphertext."""
    if not plain_text:
        return ''
    f = Fernet(_get_fernet_key())
    return f.encrypt(plain_text.encode()).decode()


def decrypt(cipher_text):
    """Decrypt a ciphertext string and return the plaintext."""
    if not cipher_text:
        return ''
    f = Fernet(_get_fernet_key())
    return f.decrypt(cipher_text.encode()).decode()
