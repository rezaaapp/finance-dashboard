import base64
from hashlib import pbkdf2_hmac
from hmac import compare_digest
import secrets
import string


ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 600_000
SALT_BYTES = 16


def validate_password_strength(password: str) -> None:
    value = str(password or "")
    if len(value) < 10:
        raise ValueError("Password minimal 10 karakter.")
    if not any(character.islower() for character in value):
        raise ValueError("Password harus memiliki huruf kecil.")
    if not any(character.isupper() for character in value):
        raise ValueError("Password harus memiliki huruf besar.")
    if not any(character.isdigit() for character in value):
        raise ValueError("Password harus memiliki angka.")
    if not any(character in string.punctuation for character in value):
        raise ValueError("Password harus memiliki simbol.")


def hash_password(password: str) -> str:
    validate_password_strength(password)
    salt = secrets.token_bytes(SALT_BYTES)
    digest = pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return "$".join((
        ALGORITHM,
        str(ITERATIONS),
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(digest).decode("ascii"),
    ))


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_value, digest_value = encoded.split("$", 3)
        if algorithm != ALGORITHM:
            return False
        salt = base64.urlsafe_b64decode(salt_value.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_value.encode("ascii"))
        actual = pbkdf2_hmac(
            "sha256",
            str(password or "").encode("utf-8"),
            salt,
            int(iterations),
        )
        return compare_digest(actual, expected)
    except (TypeError, ValueError):
        return False
