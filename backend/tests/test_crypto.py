import pytest
from app.core.crypto import encrypt, decrypt


def test_encrypt_returns_string():
    result = encrypt("my-secret")
    assert isinstance(result, str)
    assert result != "my-secret"


def test_decrypt_returns_original():
    original = "session-id-abc123"
    encrypted = encrypt(original)
    assert decrypt(encrypted) == original


def test_different_encryptions_for_same_input():
    # Fernet is nondeterministic
    enc1 = encrypt("same")
    enc2 = encrypt("same")
    assert enc1 != enc2


def test_decrypt_invalid_raises():
    with pytest.raises(Exception):
        decrypt("not-valid-fernet-token")
