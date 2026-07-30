variable "project_id" {
  description = "Google Cloud Project ID where PyCalcAgent is deployed."
  type        = string
}

variable "region" {
  description = "GCP Region for Cloud Run and Vertex AI Agent Engine."
  type        = string
  default     = "us-central1"
}

variable "container_image" {
  description = "Container registry URI for PyCalcAgent Docker image."
  type        = string
  default     = "gcr.io/test-project/pycalcagent:latest"
}
