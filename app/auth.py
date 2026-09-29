"""Password hashing (stdlib PBKDF2 — no bcrypt dependency needed) and
signed-cookie session helpers."""
import hashlib
import hmac
import os
import secrets

from itsdangerous import URLSafeTimedSerializer, BadSignature

SECRET_KEY = os.environ.get("APP_SECRET_KEY", "dev-secret-change-me-in-production")
_serializer = URLSafeTimedSerializer(SECRET_KEY, salt="prague-app-session")

PBKDF2_ITERATIONS = 260_000


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    if salt is None:
        salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS)
    return dk.hex(), salt


def verify_password(password: str, salt: str, password_hash: str) -> bool:
    dk, _ = hash_password(password, salt)
    return hmac.compare_digest(dk, password_hash)


def make_session_cookie(user_id: int) -> str:
    return _serializer.dumps({"user_id": user_id})


def read_session_cookie(token: str, max_age: int = 60 * 60 * 24 * 14):
    try:
        data = _serializer.loads(token, max_age=max_age)
        return data.get("user_id")
    except BadSignature:
        return None
