import hashlib
import hmac
import secrets
from datetime import datetime


class SignedCsrf:
    def __init__(self, secret: str, ttl_seconds: int = 3600):
        self.secret = secret.encode()
        self.ttl = ttl_seconds

    def _signature(self, payload: str, credential: str) -> str:
        return hmac.new(self.secret, f"{payload}:{credential}".encode(), hashlib.sha256).hexdigest()

    def issue(self, credential: str, now: datetime) -> str:
        payload = f"{int(now.timestamp())}.{secrets.token_hex(16)}"
        return f"{payload}.{self._signature(payload, credential)}"

    def verify(self, token: str | None, credential: str, now: datetime) -> bool:
        if not token or len(token) > 256:
            return False
        try:
            issued, nonce, signature = token.split(".")
            age = int(now.timestamp()) - int(issued)
            return (
                0 <= age < self.ttl
                and len(nonce) == 32
                and hmac.compare_digest(signature, self._signature(f"{issued}.{nonce}", credential))
            )
        except (ValueError, TypeError):
            return False
