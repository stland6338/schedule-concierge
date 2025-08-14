"""Simple symmetric encryption wrapper (Fernet) for sensitive tokens.

In production: rotate keys, store in secret manager. For now we allow single key via env.
"""
from __future__ import annotations
import os
from cryptography.fernet import Fernet, InvalidToken
from functools import lru_cache

class EncryptionService:
    ENV_KEY = "APP_ENCRYPTION_KEY"

    def __init__(self, key: bytes | None = None):
        key_b64 = key or os.getenv(self.ENV_KEY)
        if not key_b64:
            # Generate ephemeral key (NOT for production persistence)
            key_b64 = Fernet.generate_key()
            os.environ[self.ENV_KEY] = key_b64.decode()
        if isinstance(key_b64, str):
            key_b64 = key_b64.encode()
        self._fernet = Fernet(key_b64)

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, token: str) -> str:
        try:
            return self._fernet.decrypt(token.encode()).decode()
        except InvalidToken:
            raise ValueError("INVALID_ENCRYPTED_VALUE")

@lru_cache(maxsize=1)
def get_encryption_service() -> EncryptionService:
    return EncryptionService()
