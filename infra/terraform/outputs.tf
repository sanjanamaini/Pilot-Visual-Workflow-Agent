output "backend_url" {
  description = "URL of the deployed Pilot backend on Cloud Run"
  value       = google_cloud_run_v2_service.pilot_backend.uri
}

output "firestore_db" {
  description = "Firestore database name"
  value       = google_firestore_database.pilot.name
}

output "screenshot_bucket" {
  description = "Cloud Storage bucket for screenshots"
  value       = google_storage_bucket.screenshots.name
}
