"""Google Cloud Secret Manager client integration for secure credentials (Criterion 5)."""

import os

from pycalcagent.tracer import default_tracer

try:
    from google.cloud import secretmanager
    SECRET_MANAGER_AVAILABLE = True
except ImportError:
    SECRET_MANAGER_AVAILABLE = False


class SecretManagerClient:
    """Retrieves secrets from Google Cloud Secret Manager with fallback to environment variables."""

    def __init__(self, project_id: str | None = None):
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT") or "test-project"
        self.client = None
        if SECRET_MANAGER_AVAILABLE:
            try:
                self.client = secretmanager.SecretManagerServiceClient()
            except Exception as e:  # noqa: BLE001
                default_tracer.log_event("SECRET_MANAGER_INIT_FALLBACK", {"error": str(e)})

    def get_secret(self, secret_name: str, version: str = "latest") -> str | None:
        """Fetch a secret value from Cloud Secret Manager or fallback to local environment variable."""
        # Try local environment variable first
        env_val = os.getenv(secret_name)
        if env_val:
            default_tracer.log_event("SECRET_FETCHED_ENV", {"secret_name": secret_name})
            return env_val

        # Attempt fetch from Google Cloud Secret Manager
        if self.client and self.project_id:
            try:
                name = f"projects/{self.project_id}/secrets/{secret_name}/versions/{version}"
                response = self.client.access_secret_version(request={"name": name})
                val = response.payload.data.decode("utf-8")
                default_tracer.log_event("SECRET_FETCHED_GCP", {"secret_name": secret_name})
                return val
            except Exception as e:  # noqa: BLE001
                default_tracer.log_event("SECRET_FETCH_GCP_ERROR", {"secret_name": secret_name, "error": str(e)})

        return None
