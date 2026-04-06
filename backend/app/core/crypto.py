from cryptography.fernet import Fernet

from app.config import get_settings


def _get_fernet() -> Fernet:
    return Fernet(get_settings().secret_key.encode())


def encrypt(plaintext: str) -> str:
    """Encrypt a string using Fernet symmetric encryption."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """Decrypt a Fernet-encrypted string. Raises InvalidToken if tampered."""
    return _get_fernet().decrypt(ciphertext.encode()).decode()
