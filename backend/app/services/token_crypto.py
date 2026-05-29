import base64
import hashlib

from cryptography.fernet import Fernet

from app.config import settings


def _build_fernet():
    digest = hashlib.sha256(settings.TOKEN_ENCRYPTION_SECRET.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)

    return Fernet(key)


def encrypt_token(token: str):
    return _build_fernet().encrypt(token.encode("utf-8")).decode("utf-8")


def decrypt_token(encrypted_token: str):
    return _build_fernet().decrypt(encrypted_token.encode("utf-8")).decode("utf-8")
