"""Unit tests for SecretManagerClient (Criterion 5)."""

from pycalcagent.secrets import SecretManagerClient


def test_secret_manager_env_fallback(monkeypatch):
    """Verify SecretManagerClient retrieves secrets from environment fallback."""
    monkeypatch.setenv("TEST_API_KEY", "test-secret-value-123")
    client = SecretManagerClient(project_id="test-project")
    val = client.get_secret("TEST_API_KEY")
    assert val == "test-secret-value-123"
