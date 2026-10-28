"""One-way password storage; Fernet is used only to migrate legacy accounts."""

import base64
import hashlib
import hmac
import secrets


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1)
    return "scrypt$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(digest).decode()


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, salt, digest = stored.split("$")
        if algorithm != "scrypt":
            return False
        actual = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt), n=16384, r=8, p=1)
        return hmac.compare_digest(actual, base64.b64decode(digest))
    except (ValueError, TypeError):
        return False


def decrypt_legacy_password(encrypted: str) -> str:
    from cryptography.fernet import Fernet

    from core.config import settings

    if not settings.FERNET_KEY:
        raise ValueError("A legacy account requires FERNET_KEY for one-time migration")
    return Fernet(settings.FERNET_KEY.encode()).decrypt(encrypted.encode()).decode()
