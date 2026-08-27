import pytest

from app.services.signer import sign_payload, verify_signature


def test_signature_format():
    sig = sign_payload("secret", b"payload")
    assert sig.startswith("sha256=")
    assert len(sig) == 71  # "sha256=" + 64 hex chars


def test_verify_valid_signature():
    secret = "my-secret"
    payload = b'{"event": "order.created"}'
    sig = sign_payload(secret, payload)
    assert verify_signature(secret, payload, sig) is True


def test_verify_tampered_payload():
    secret = "my-secret"
    sig = sign_payload(secret, b"original")
    assert verify_signature(secret, b"tampered", sig) is False


def test_verify_wrong_secret():
    payload = b"data"
    sig = sign_payload("correct-secret", payload)
    assert verify_signature("wrong-secret", payload, sig) is False


def test_different_secrets_produce_different_sigs():
    payload = b"same payload"
    sig1 = sign_payload("secret-A", payload)
    sig2 = sign_payload("secret-B", payload)
    assert sig1 != sig2


def test_deterministic():
    secret, payload = "s", b"p"
    assert sign_payload(secret, payload) == sign_payload(secret, payload)
