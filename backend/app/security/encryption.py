import base64
import binascii

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


def _get_fernet():
    key = settings.TOKEN_ENCRYPTION_KEY

    if not key:
        raise ValueError("Token encryption is not configured")

    normalized_key = key.strip()

    try:
        return Fernet(normalized_key.encode("utf-8"))
    except (ValueError, binascii.Error):
        pass

    try:
        raw_key = bytes.fromhex(normalized_key)
    except ValueError as exc:
        raise ValueError("Token encryption key is invalid") from exc

    try:
        return Fernet(base64.urlsafe_b64encode(raw_key))
    except (ValueError, binascii.Error) as exc:
        raise ValueError("Token encryption key is invalid") from exc


def encrypt_text(value: str) -> str:
    try:
        return _get_fernet().encrypt(value.encode("utf-8")).decode("utf-8")
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("Unable to encrypt token") from exc


def decrypt_text(value: str) -> str:
    try:
        return _get_fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Encrypted token is invalid") from exc
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("Unable to decrypt token") from exc
