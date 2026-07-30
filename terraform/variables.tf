variable "project_id" {
  description = "Google Cloud Project ID where PyCalcAgent is deployed."
  type        = string
  default     = "hzuo-experiment-sandbox-551643"
}

variable "region" {
  description = "GCP Region for Cloud Run and Vertex AI Agent Engine."
  type        = string
  default     = "us-central1"
}

variable "container_image" {
  description = "Container registry URI for PyCalcAgent Docker image."
  type        = string
  default     = "gcr.io/hzuo-experiment-sandbox-551643/pycalcagent:latest"
}
