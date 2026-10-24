import pytest
from app.infrastructure.settings.config import Settings
from app.modules.identity.infrastructure.csrf import SignedCsrf
from pydantic import ValidationError


@pytest.mark.parametrize(
    "changes",
    [
        {"database_url": "sqlite:///test.db"},
        {"csrf_secret": "short"},
        {"allowed_origins": ["*"]},
        {"environment": "production", "allowed_origins": ["http://localhost:3000"]},
        {"provider": "deepseek"},
    ],
)
def test_unsafe_or_unimplemented_configuration_rejected(settings, changes):
    values = settings.model_dump()
    values.update(changes)
    with pytest.raises(ValidationError):
        Settings(**values)


def test_csrf_tampering_future_timestamp_and_bounds(foundation):
    from datetime import timedelta

    signer = SignedCsrf("test-signing-key-at-least-32-characters")
    now = foundation[3][0]
    token = signer.issue("credential", now)
    assert signer.verify(token, "credential", now + timedelta(seconds=3599))
    assert not signer.verify(token, "credential", now + timedelta(seconds=3600))
    assert not signer.verify(token, "credential", now - timedelta(seconds=1))
    assert not signer.verify(token + "a", "credential", now)
    assert not signer.verify("x" * 257, "credential", now)
    assert not signer.verify("a.b.c", "credential", now)
