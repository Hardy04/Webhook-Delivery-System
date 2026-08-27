import hashlib
import hmac


def sign_payload(secret: str, payload: bytes) -> str:
    """Return 'sha256=<hex>' signature for the given payload bytes."""
    digest = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def verify_signature(secret: str, payload: bytes, signature: str) -> bool:
    """Constant-time comparison of expected vs provided signature."""
    expected = sign_payload(secret, payload)
    return hmac.compare_digest(expected, signature)
