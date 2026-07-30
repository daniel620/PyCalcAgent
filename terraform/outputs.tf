output "cloud_run_service_uri" {
  description = "The URI of the deployed PyCalcAgent Cloud Run service."
  value       = google_cloud_run_v2_service.pycalcagent_service.uri
}

output "secret_id" {
  description = "Resource ID of the GEMINI_API_KEY secret."
  value       = google_secret_manager_secret.gemini_api_key.id
}
