"""Unit tests for PIIRedactor (Criterion 4)."""

from pycalcagent.tracer import PIIRedactor


def test_pii_redactor_email_and_phone():
    """Verify PIIRedactor scrubs email addresses and phone numbers."""
    text = "User john.doe@google.com called from 650-555-0199 about order 12345."
    redacted = PIIRedactor.redact_text(text)
    assert "john.doe@google.com" not in redacted
    assert "[REDACTED_EMAIL]" in redacted
    assert "650-555-0199" not in redacted
    assert "[REDACTED_PHONE]" in redacted


def test_pii_redactor_secret_key():
    """Verify PIIRedactor scrubs API keys and tokens."""
    payload = {"query": "test", "key": "api_key=AIzaSyD-1234567890abcdefghijklmno"}
    redacted = PIIRedactor.redact_payload(payload)
    assert "AIzaSyD-1234567890abcdefghijklmno" not in str(redacted)
    assert "[REDACTED_SECRET]" in str(redacted)
