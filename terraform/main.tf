terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required Google Cloud APIs for Vertex AI and Secret Manager
resource "google_project_service" "aiplatform" {
  service                    = "aiplatform.googleapis.com"
  disable_on_destroy         = false
}

resource "google_project_service" "secretmanager" {
  service                    = "secretmanager.googleapis.com"
  disable_on_destroy         = false
}

resource "google_project_service" "logging" {
  service                    = "logging.googleapis.com"
  disable_on_destroy         = false
}

# Cloud Secret Manager storage for Gemini API key
resource "google_secret_manager_secret" "gemini_api_key" {
  secret_id = "GEMINI_API_KEY"
  replication {
    auto {}
  }
  depends_on = [google_project_service.secretmanager]
}

# Cloud Run Service for containerized PyCalcAgent execution
resource "google_cloud_run_v2_service" "pycalcagent_service" {
  name     = "pycalcagent-service"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    containers {
      image = var.container_image
      resources {
        limits = {
          memory = "1024Mi"
          cpu    = "1"
        }
      }
      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
    }
  }

  depends_on = [
    google_project_service.aiplatform,
    google_project_service.logging,
  ]
}
